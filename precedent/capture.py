"""Capture: free text -> structured decision -> pre-flight conflict check -> markdown note + graph write.

A model drafts the structured fields (technology, stance, scope, affected projects, what it replaces). Code then
validates every field against the graph's own vocabulary, runs the same conflict logic as `precedent check`, and only
writes (a markdown note in the vault AND the graph, in one Relate transaction) after confirmation.
"""
import datetime
import json
import os
import pathlib
import re

import relate
import yaml

from . import queries as q

STANCES = ("requires", "allows", "forbids")
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_FORUM = "Decision Log"

RECORD_TOOL = {
    "name": "record_decision",
    "description": "Record the decision found in the text as structured fields. Call exactly once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short imperative title, no colons or slashes."},
            "rationale": {"type": "string", "description": "One or two sentences of why, taken from the text."},
            "author": {"type": ["string", "null"], "description": "Person who made it, exactly as in the people list, or null."},
            "affects": {"type": "array", "items": {"type": "string"},
                        "description": "Project names from the projects list that this decision affects."},
            "constraints": {"type": "array", "items": {
                "type": "object",
                "properties": {"technology": {"type": "string", "description": "Technology name or alias from the list."},
                               "stance": {"type": "string", "enum": list(STANCES)},
                               "scope": {"type": "string", "description": "Lowercase-hyphenated scope; reuse an existing scope when it fits."}},
                "required": ["technology", "stance", "scope"]},
                "description": "What the decision requires, allows or forbids about a technology, and where."},
            "supersedes": {"type": ["string", "null"],
                           "description": "Id of the ACTIVE decision this one explicitly replaces or reverses, else null."},
            "depends_on": {"type": "array", "items": {"type": "string"},
                           "description": "Ids of decisions this one explicitly builds on, else empty."},
        },
        "required": ["title", "rationale", "author", "affects", "constraints", "supersedes", "depends_on"],
    },
}


def load_env(path):
    p = pathlib.Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def vocabulary(cur):
    techs = q._rows(cur, "MATCH (t:Technology) RETURN t.name AS name, t.aliases AS aliases ORDER BY name")
    active = q.active(cur)
    ids = [int(r["id"][1:]) for r in q._rows(cur, "MATCH (d:Decision) RETURN d.id AS id")]
    return {
        "technologies": [{"name": t["name"], "aliases": t["aliases"] or ""} for t in techs],
        "projects": [r["name"] for r in q._rows(cur, "MATCH (p:Project) RETURN p.name AS name ORDER BY name")],
        "people": [r["name"] for r in q._rows(cur, "MATCH (p:Person) RETURN p.name AS name ORDER BY name")],
        "scopes": q.scopes(cur),
        "scope_examples": {r["scope"]: f"{r['id']}: {r['title']}" for r in reversed(q._rows(
            cur, "MATCH (d:Decision)-[r:CONSTRAINS]->() WHERE NOT ()-[:SUPERSEDES]->(d) "
                 "RETURN r.scope AS scope, d.id AS id, d.title AS title ORDER BY id"))},
        "active": [{"id": r["id"], "title": r["title"]} for r in active],
        "next_id": f"D{max(ids) + 1}" if ids else "D1",
    }


def _system(vocab):
    techs = "; ".join(t["name"] + (f" (also written: {t['aliases']})" if t["aliases"] else "") for t in vocab["technologies"])
    active = "\n".join(f"  {d['id']}: {d['title']}" for d in vocab["active"])
    scopes = "\n".join(f"  {k}  <- {v}" for k, v in vocab["scope_examples"].items())
    return (
        "You turn a short note about a decision into structured fields by calling record_decision once. "
        "Use only what the text says. Add a constraint ONLY when the text itself names a technology (or an alias) and says it must, may or must not be used; never infer a technology from related decisions, and use an empty constraints list when the text is about something else (limits, schedules, durations). Stances: requires (must use), allows (may use), forbids (must not use). "
        "Scope says what the rule applies to, taken from the text itself. Reuse an existing scope ONLY when it names the same thing "
        "(see the example decision shown for each scope); do not reuse one just because it appears in the list. Otherwise invent a "
        "short lowercase-hyphenated scope that describes this rule. "
        "Map technology names and aliases to the names in the list. Set supersedes only when the text explicitly replaces, "
        "reverses or changes a rule that matches an ACTIVE decision below; otherwise null.\n"
        f"Technologies: {techs}\nProjects: {', '.join(vocab['projects'])}\nPeople: {', '.join(vocab['people'])}\n"
        f"Existing scopes (with an example decision each):\n{scopes}\nActive decisions:\n{active}"
    )


def extract(client, model, text, vocab):
    messages = [{"role": "user", "content": text}]
    for attempt in range(2):
        resp = client.messages.create(model=model, max_tokens=2000, system=_system(vocab), tools=[RECORD_TOOL],
                                      messages=messages, output_config={"effort": "medium"})
        use = next((b for b in resp.content if b.type == "tool_use" and b.name == "record_decision"), None)
        if use:
            return use.input, {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
        messages += [{"role": "assistant", "content": resp.content},
                     {"role": "user", "content": "Call record_decision now."}]
    raise RuntimeError("the model did not return a structured decision")


def validate(cur, data, vocab, allow_new=False):
    """Check fields against the graph. Returns (clean decision, problems, notices)."""
    problems, notices = [], []
    people = {p.lower(): p for p in vocab["people"]}
    projects = {p.lower(): p for p in vocab["projects"]}
    active_ids = {d["id"] for d in vocab["active"]}
    all_ids = {r["id"] for r in q._rows(cur, "MATCH (d:Decision) RETURN d.id AS id")}

    author = data.get("author")
    author = people.get((author or "").lower()) if author else None
    if data.get("author") and not author:
        notices.append(f"author {data['author']!r} is not a known person; left empty")

    affects = []
    for name in data.get("affects") or []:
        if name.lower() in projects:
            affects.append(projects[name.lower()])
        elif allow_new:
            affects.append(name)
            notices.append(f"new project {name!r} will be created")
        else:
            problems.append(f"unknown project {name!r} (use --allow-new to create it)")

    constraints = []
    for c in data.get("constraints") or []:
        stance = (c.get("stance") or "").lower()
        scope = re.sub(r"[^a-z0-9]+", "-", (c.get("scope") or "").lower()).strip("-")
        tech = q.resolve_tech(cur, c.get("technology", ""))
        if stance not in STANCES:
            problems.append(f"bad stance {c.get('stance')!r}")
        if not scope:
            problems.append("empty scope")
        if not tech:
            if allow_new:
                tech = c.get("technology")
                notices.append(f"new technology {tech!r} will be created")
            else:
                problems.append(f"unknown technology {c.get('technology')!r} (use --allow-new to create it)")
                continue
        constraints.append({"technology": tech, "stance": stance, "scope": scope})

    def _id(x):  # models sometimes wrap ids in quotes or prose; take the Dnn token
        m = re.search(r"D\d+", str(x).upper())
        return m.group(0) if m else str(x).strip().upper()

    sup = data.get("supersedes")
    if sup:
        sup = _id(sup)
        if sup not in all_ids:
            problems.append(f"{sup} does not exist")
        elif sup not in active_ids:
            problems.append(f"{sup} is already replaced")
    deps = []
    for d in data.get("depends_on") or []:
        d = _id(d)
        if d in all_ids:
            deps.append(d)
        else:
            problems.append(f"depends on unknown decision {d}")
    title = re.sub(r"[\\/:*?\"<>|#\[\]]", " ", data.get("title", "")).strip()
    title = re.sub(r"\s+", " ", title)
    if not title:
        problems.append("empty title")
    clean = {"title": title, "rationale": (data.get("rationale") or "").strip(), "author": author, "affects": affects,
             "constraints": constraints, "supersedes": sup or None, "depends_on": deps}
    return clean, problems, notices


def preflight(cur, clean):
    """What the new decision would conflict with, and what it would leave stale."""
    sup = clean.get("supersedes") or ""
    conflicts, possible = [], []
    for c in clean["constraints"]:
        other = "r.stance = 'forbids'" if c["stance"] in ("requires", "allows") else "r.stance IN ['requires','allows']"
        rows = q._rows(
            cur,
            "MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {name:$t}) "
            f"WHERE {other} AND (r.scope = $s OR r.scope = 'all' OR $s = 'all') AND NOT ()-[:SUPERSEDES]->(d) AND d.id <> $sup "
            "RETURN d.id AS id, d.title AS title, r.stance AS stance, r.scope AS scope ORDER BY id",
            {"t": c["technology"], "s": c["scope"], "sup": sup})
        for r in rows:
            conflicts.append({"new": f"{c['stance']} {c['technology']} ({c['scope']})", **r})
        for r in q.possible_conflicts(cur, c["technology"], c["scope"], c["stance"]):
            if r["id"] != sup and r["id"] not in {x["id"] for x in rows}:
                possible.append({"new": f"{c['stance']} {c['technology']} ({c['scope']})", **r})
    stale = []
    if sup:
        stale = q._rows(cur, "MATCH (x:Decision)-[:DEPENDS_ON]->(:Decision {id:$id}) WHERE NOT ()-[:SUPERSEDES]->(x) "
                             "RETURN x.id AS id, x.title AS title ORDER BY id", {"id": sup})
    return {"conflicts": conflicts, "possible_conflicts": possible, "would_become_stale": stale}


def _link(label, name):
    return f"[[{label}/{name}]]"


def _note(label, name, fm, body):
    return label, name, "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body.strip() + "\n"


def plan_write(cur, clean, vocab, date, forum):
    """Build the note files and the graph statements (nothing is written yet)."""
    did = vocab["next_id"]
    name = f"{did} {clean['title']}"
    meeting = f"{forum} {date}"
    meeting_exists = bool(q._rows(cur, "MATCH (m:Meeting {name:$n}) RETURN m.name AS n", {"n": meeting}))
    fm = {"type": "Decision", "name": name, "id": did, "title": clean["title"], "date": date,
          "DECIDED_IN": [_link("Meeting", meeting)]}
    if clean["author"]:
        fm["MADE_BY"] = [_link("Person", clean["author"])]
        fm["OWNED_BY"] = [_link("Person", clean["author"])]
    if clean["affects"]:
        fm["AFFECTS"] = [_link("Project", p) for p in clean["affects"]]
    if clean["constraints"]:
        fm["CONSTRAINS"] = [{"target": _link("Technology", c["technology"]), "stance": c["stance"], "scope": c["scope"]}
                            for c in clean["constraints"]]
    sup_name = None
    if clean["supersedes"]:
        sup_name = q._rows(cur, "MATCH (d:Decision {id:$i}) RETURN d.name AS n", {"i": clean["supersedes"]})[0]["n"]
        fm["SUPERSEDES"] = [_link("Decision", sup_name)]
    dep_names = []
    for d in clean["depends_on"]:
        dep_names.append(q._rows(cur, "MATCH (d:Decision {id:$i}) RETURN d.name AS n", {"i": d})[0]["n"])
    if dep_names:
        fm["DEPENDS_ON"] = [_link("Decision", n) for n in dep_names]
    body = f"# {did}: {clean['title']}\n\n{clean['rationale']}\n"
    notes = [_note("Decision", name, fm, body)]
    if not meeting_exists:
        mfm = {"type": "Meeting", "name": meeting, "date": date}
        if clean["author"]:
            mfm["ATTENDED_BY"] = [_link("Person", clean["author"])]
        notes.append(_note("Meeting", meeting, mfm, f"Decisions: {did} {clean['title']}."))
    known_techs = {t["name"] for t in vocab["technologies"]}
    known_projects = set(vocab["projects"])
    for c in clean["constraints"]:
        if c["technology"] not in known_techs:
            known_techs.add(c["technology"])
            notes.append(_note("Technology", c["technology"], {"type": "Technology", "name": c["technology"]},
                               f"{c['technology']} (added by capture)."))
    for p in clean["affects"]:
        if p not in known_projects:
            known_projects.add(p)
            notes.append(_note("Project", p, {"type": "Project", "name": p}, f"{p} (added by capture)."))

    stmts = []  # (cypher, params)
    for label, nname, content in notes:
        if label == "Decision":
            stmts.append(("CREATE (:Decision {name:$name, id:$id, title:$title, date:$date, text:$text})",
                          {"name": name, "id": did, "title": clean["title"], "date": date, "text": body[:2000]}))
        elif label == "Meeting":
            stmts.append(("CREATE (:Meeting {name:$name, date:$date})", {"name": nname, "date": date}))
        elif label == "Technology":
            stmts.append(("CREATE (:Technology {name:$name})", {"name": nname}))
        elif label == "Project":
            stmts.append(("CREATE (:Project {name:$name})", {"name": nname}))
    d_ = "MATCH (d:Decision {id:$id}), "
    stmts.append((d_ + "(m:Meeting {name:$m}) CREATE (d)-[:DECIDED_IN]->(m)", {"id": did, "m": meeting}))
    if not meeting_exists and clean["author"]:
        stmts.append(("MATCH (m:Meeting {name:$m}), (p:Person {name:$p}) CREATE (m)-[:ATTENDED_BY]->(p)",
                      {"m": meeting, "p": clean["author"]}))
    if clean["author"]:
        for rel in ("MADE_BY", "OWNED_BY"):
            stmts.append((d_ + f"(p:Person {{name:$p}}) CREATE (d)-[:{rel}]->(p)", {"id": did, "p": clean["author"]}))
    for p in clean["affects"]:
        stmts.append((d_ + "(p:Project {name:$p}) CREATE (d)-[:AFFECTS]->(p)", {"id": did, "p": p}))
    for c in clean["constraints"]:
        stmts.append((d_ + "(t:Technology {name:$t}) CREATE (d)-[:CONSTRAINS {stance:$s, scope:$sc}]->(t)",
                      {"id": did, "t": c["technology"], "s": c["stance"], "sc": c["scope"]}))
    if clean["supersedes"]:
        stmts.append((d_ + "(o:Decision {id:$o}) CREATE (d)-[:SUPERSEDES]->(o)", {"id": did, "o": clean["supersedes"]}))
    for dep in clean["depends_on"]:
        stmts.append((d_ + "(o:Decision {id:$o}) CREATE (d)-[:DEPENDS_ON]->(o)", {"id": did, "o": dep}))
    return {"id": did, "name": name, "notes": notes, "statements": stmts}


def apply(store, vault, plan):
    """Write the notes and the graph together. Any failure rolls the graph back and removes the new files."""
    vault = pathlib.Path(vault)
    written = []
    native = pathlib.Path(store).is_dir()  # native vault mode: the folder is the store, Relate renders the notes
    conn = relate.connect(store)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        for cypher, params in plan["statements"]:
            cur.execute(cypher, params)
        for label, name, content in ([] if native else plan["notes"]):
            d = vault / label
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"{name}.md"
            f.write_text(content, encoding="utf-8")
            written.append(f)
        conn.commit()
    except Exception:
        conn.rollback()
        for f in written:
            f.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    return [str(f) for f in written]
