"""Synthetic scenario: Fernwood Robotics, a fictional warehouse-robot company (no real data).

Generates a markdown vault (folder = node label) and the evaluation answer key.
The answer key is computed here in plain Python, independent of any Cypher, so graph queries and agent
answers can be checked against it.

Run from the repo root:  python scenario/fernwood.py
"""
import datetime
import hashlib
import json
import pathlib
import re
import shutil

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
VAULT = ROOT / "vault"

PEOPLE = {  # key: (name, role, left_on)
    "priya": ("Priya Raman", "CTO", None),
    "marcus": ("Marcus Lee", "Atlas lead", None),
    "elena": ("Elena Voss", "Cobalt lead", None),
    "tomas": ("Tomas Rivera", "Drift lead", None),
    "aiko": ("Aiko Tanaka", "Ember lead", None),
    "daniel": ("Daniel Okafor", "Flux lead", None),
    "sofia": ("Sofia Marini", "Security lead", None),
    "ben": ("Ben Hartley", "Beacon lead", "2026-08-15"),
}
PROJECTS = {  # key: (name, summary, owner)
    "atlas": ("Atlas", "Robotic picker arm", "marcus"),
    "beacon": ("Beacon", "Fleet manager software", "ben"),
    "cobalt": ("Cobalt", "Robot charging docks", "elena"),
    "drift": ("Drift", "Navigation stack", "tomas"),
    "ember": ("Ember", "Customer portal", "aiko"),
    "flux": ("Flux", "Fleet data platform", "daniel"),
}
TECH = {  # key: (name, aliases)
    "orbit-cloud": ("Orbit Cloud", ""),
    "pulse-telemetry": ("Pulse Telemetry", ""),
    "sentra-lidar": ("Sentra Lidar", ""),
    "voltedge-batteries": ("VoltEdge Batteries", ""),
    "helio-cells": ("Helio Cells", ""),
    "mapwright": ("Mapwright", ""),
    "kestrel-rtos": ("Kestrel RTOS", ""),
    "granite-auth": ("Granite Auth", ""),
    "quanta-db": ("Quanta DB", "QuantaDB, Q-DB"),
}
FORUMS = {
    "arch-review": "Architecture Review", "atlas-weekly": "Atlas Weekly", "cobalt-kickoff": "Cobalt Kickoff",
    "cobalt-review": "Cobalt Review", "drift-sync": "Drift Sync", "ember-kickoff": "Ember Kickoff",
    "ember-review": "Ember Review", "flux-planning": "Flux Planning", "security-review": "Security Review",
    "beacon-planning": "Beacon Planning",
}

# id, date, forum, author, title, rationale, affects(projects), constrains[(tech, stance, scope)], supersedes, depends_on
D = [
    ("D01", "2025-02-11", "arch-review", "priya", "Adopt Orbit Cloud as the primary cloud provider",
     "Consolidates hosting and gives us one security boundary.", ["flux", "beacon"],
     [("orbit-cloud", "requires", "hosting")], None, []),
    ("D02", "2025-02-11", "arch-review", "priya", "Standardize fleet telemetry on Pulse Telemetry",
     "One schema for robot metrics across projects.", ["beacon", "drift"],
     [("pulse-telemetry", "requires", "telemetry")], None, []),
    ("D03", "2025-03-18", "atlas-weekly", "marcus", "Use Sentra Lidar for Atlas picker arm sensing",
     "Best depth accuracy at short range in the bake-off.", ["atlas"],
     [("sentra-lidar", "requires", "atlas-indoor")], None, []),
    ("D04", "2025-04-02", "cobalt-kickoff", "elena", "Build Cobalt charging docks on VoltEdge Batteries",
     "Lowest cost per cycle in the supplier comparison.", ["cobalt"],
     [("voltedge-batteries", "requires", "cobalt")], None, []),
    ("D05", "2025-04-22", "drift-sync", "tomas", "Drift uses Mapwright for map tiles",
     "Mapwright covers every pilot warehouse.", ["drift"], [("mapwright", "requires", "drift")], None, []),
    ("D06", "2025-05-13", "arch-review", "priya", "Run Kestrel RTOS on all onboard controllers",
     "Real-time guarantees and a single toolchain.", ["atlas", "drift", "cobalt"],
     [("kestrel-rtos", "requires", "all")], None, []),
    ("D07", "2025-06-03", "ember-kickoff", "aiko", "Ember authenticates users with Granite Auth",
     "Managed SSO saves us building login.", ["ember"], [("granite-auth", "requires", "ember")], None, []),
    ("D08", "2025-06-24", "flux-planning", "daniel", "Store fleet data in Quanta DB",
     "Handles time-series volume and the team already knows it. Some notes write it QuantaDB.", ["flux"],
     [("quanta-db", "requires", "flux")], None, ["D01"]),
    ("D09", "2025-07-15", "atlas-weekly", "marcus", "Atlas firmware freeze every second Friday",
     "Predictable release train for field teams.", ["atlas"], [], None, []),
    ("D10", "2025-08-05", "security-review", "sofia", "Customer PII must stay in the primary cloud region",
     "Data residency commitment in customer contracts.", ["flux", "ember"],
     [("orbit-cloud", "forbids", "customer-pii-outside-primary")], None, ["D01"]),
    ("D11", "2025-08-26", "cobalt-review", "elena", "Cobalt docks support 48V systems only",
     "Simplifies the power electronics.", ["cobalt"], [], None, []),
    ("D12", "2025-09-16", "arch-review", "priya", "Sentra Lidar approved for indoor use only",
     "Sunlight washes out returns outdoors; outdoor trials failed.", ["atlas", "drift"],
     [("sentra-lidar", "forbids", "outdoor")], None, ["D03"]),
    ("D13", "2025-10-07", "drift-sync", "tomas", "Drift falls back to dead reckoning when Mapwright tiles are older than 24 hours",
     "Avoids routing on stale maps.", ["drift"], [("mapwright", "requires", "drift")], None, ["D05"]),
    ("D14", "2025-10-28", "ember-review", "aiko", "Ember web sessions expire after 30 minutes",
     "Security review asked for short sessions.", ["ember"], [], None, ["D07"]),
    ("D15", "2025-11-18", "flux-planning", "daniel", "Retain raw telemetry for 90 days",
     "Matches the Pulse Telemetry export format and support needs.", ["flux", "beacon"], [], None, ["D02", "D08"]),
    ("D16", "2025-12-09", "atlas-weekly", "marcus", "Atlas picker accepts payloads up to 12 kg",
     "Gripper torque limit.", ["atlas"], [], None, []),
    ("D17", "2026-01-13", "arch-review", "priya", "Move telemetry from Pulse Telemetry to Orbit Cloud native metrics",
     "Drops a vendor and a bill; replaces the 2025 telemetry standard.", ["beacon", "drift"],
     [("orbit-cloud", "requires", "telemetry"), ("pulse-telemetry", "forbids", "telemetry")], "D02", ["D01"]),
    ("D18", "2026-02-03", "beacon-planning", "ben", "Beacon fleet scheduling runs on Q-DB queues",
     "Avoids adding a message broker. Q-DB is our name for Quanta DB.", ["beacon"],
     [("quanta-db", "requires", "beacon")], None, ["D08"]),
    ("D19", "2026-02-24", "cobalt-review", "elena", "Switch Cobalt dock batteries from VoltEdge to Helio Cells",
     "VoltEdge lead times doubled.", ["cobalt"],
     [("helio-cells", "requires", "cobalt"), ("voltedge-batteries", "forbids", "cobalt")], "D04", []),
    ("D20", "2026-03-17", "security-review", "sofia", "All internal dashboards require SSO through Granite Auth",
     "Audit finding on shared passwords.", ["beacon", "flux"],
     [("granite-auth", "requires", "internal-dashboards")], None, ["D07"]),
    ("D21", "2026-04-07", "atlas-weekly", "marcus", "Start the Atlas Yard pilot using the existing Sentra Lidar sensors",
     "Reuse hardware so the pilot can start in May.", ["atlas"], [("sentra-lidar", "allows", "outdoor")], None, ["D03"]),
    ("D22", "2026-05-12", "flux-planning", "daniel", "Cut raw telemetry retention to 30 days",
     "Storage cost; replaces the 90-day rule.", ["flux", "beacon"], [], "D15", ["D08"]),
    ("D23", "2026-06-02", "ember-review", "aiko", "Ember kiosk sessions expire after 8 hours",
     "Warehouse kiosks stay signed in for a whole shift.", ["ember"], [], None, ["D07"]),
    ("D24", "2026-06-23", "drift-sync", "tomas", "Replace Mapwright with in-house map tiles",
     "Mapwright pricing changed.", ["drift"], [("mapwright", "forbids", "drift")], "D05", []),
    ("D25", "2026-07-14", "arch-review", "priya", "Every new vendor needs a security questionnaire before purchase",
     "Follow-up from the audit.", [], [], None, []),
    ("D26", "2026-08-04", "security-review", "sofia", "Encrypted disaster-recovery backups may hold customer PII in the secondary region",
     "Disaster recovery exception, backups only.", ["flux"], [("orbit-cloud", "allows", "dr-backups")], None, ["D10"]),
    ("D27", "2026-09-15", "cobalt-review", "elena", "Cobalt docks also support 24V systems",
     "Customer demand from forklift fleets; replaces the 48V-only rule.", ["cobalt"], [], "D11", []),
    ("D28", "2026-10-06", "security-review", "sofia", "QuantaDB must enable encryption at rest",
     "Compliance requirement for fleet data.", ["flux", "beacon"],
     [("quanta-db", "requires", "encryption-at-rest")], None, ["D08"]),
    ("D29", "2026-10-20", "arch-review", "priya", "Pause new Kestrel RTOS licenses while we evaluate open-source options",
     "Licensing cost review.", ["atlas", "drift", "cobalt"], [("kestrel-rtos", "forbids", "new-controllers")], None, []),
    ("D30", "2026-02-17", "beacon-planning", "ben", "Beacon dashboards read telemetry from the Pulse Telemetry exporter",
     "Reuses the existing exporter.", ["beacon"], [("pulse-telemetry", "requires", "beacon")], None, ["D02"]),
]


# ---- optional filler so the vault can be scaled up without touching the planted answers -----------------------
FIRST = ["Alex", "Jordan", "Sam", "Riley", "Casey", "Morgan", "Jamie", "Taylor", "Drew", "Quinn"]
LAST = ["Hale", "Ibarra", "Novak", "Okoye", "Petrov", "Quist", "Reyes", "Soto", "Tran", "Vance"]
F_PROJECTS = ["Quasar", "Pebble", "Lantern", "Harbor", "Mosaic", "Cinder", "Tundra", "Vertex", "Willow", "Zenith",
              "Aurora", "Bramble"]
F_TECH = ["Corvid DB", "Larkspur Queue", "Nimbus Cache", "Tessera Search", "Ironbark CI", "Meridian Logs",
          "Opal Mail", "Pylon Gateway", "Quill Docs", "Riven Build", "Sable Vault", "Thistle Metrics"]
F_COMPONENTS = ["build pipeline", "alerting", "job scheduling", "search", "documentation", "access control",
                "metrics", "release gating", "backups", "staging environment"]
F_FORUMS = {"ops-review": "Ops Review", "product-sync": "Product Sync", "platform-sync": "Platform Sync",
            "field-review": "Field Review"}


def add_filler(n, seed=7):
    """Append n filler decisions about invented projects and tools. They never touch planted technologies or
    projects, add no 'forbids' stances, and never create stale dependencies, so only counts (E07) change."""
    import random
    rng = random.Random(seed)
    FORUMS.update(F_FORUMS)
    authors = []
    for i in range(10):
        key = f"f{i:02d}"
        PEOPLE[key] = (f"{FIRST[i]} {LAST[i]}", "Engineer", None)
        authors.append(key)
    for i, name in enumerate(F_PROJECTS):
        PROJECTS[f"fp{i:02d}"] = (f"Project {name}", "Internal tooling", authors[i % len(authors)])
    for name in F_TECH:
        TECH["f-" + name.lower().replace(" ", "-")] = (name, "")
    tkeys = ["f-" + n.lower().replace(" ", "-") for n in F_TECH]
    start, end = datetime.date(2025, 1, 6), datetime.date(2026, 10, 30)
    span = (end - start).days
    superseded, depended, rows = set(), set(), []
    for i in range(n):
        did = f"D{31 + i}"
        date = (start + datetime.timedelta(days=int(span * i / max(n - 1, 1)))).isoformat()
        pk = f"fp{rng.randrange(len(F_PROJECTS)):02d}"
        tk = tkeys[rng.randrange(len(tkeys))]
        comp = F_COMPONENTS[rng.randrange(len(F_COMPONENTS))]
        title = f"Use {TECH[tk][0]} for {PROJECTS[pk][0]} {comp}"
        sup = None
        earlier = [r for r in rows if r[0] not in superseded and r[0] not in depended and pk in r[6]]
        if earlier and rng.random() < 0.12:
            sup = earlier[rng.randrange(len(earlier))][0]
            superseded.add(sup)
            title = f"Switch {PROJECTS[pk][0]} {comp} to {TECH[tk][0]}"
        deps = []
        cand = [r for r in rows if r[0] not in superseded and r[0] != sup]
        if cand and rng.random() < 0.2:
            dep = cand[rng.randrange(len(cand))][0]
            depended.add(dep)
            deps = [dep]
        forum = list(F_FORUMS)[rng.randrange(len(F_FORUMS))]
        stance = "requires" if rng.random() < 0.7 else "allows"
        rows.append((did, date, forum, authors[rng.randrange(len(authors))], title,
                     f"Chosen for {comp} after a short trial.", [pk], [(tk, stance, PROJECTS[pk][0].lower())], sup, deps))
    D.extend(rows)


def tname(k):
    return TECH[k][0]


def dname(row):
    return f"{row[0]} {row[4]}"


def meeting_name(forum, date):
    return f"{FORUMS[forum]} {date}"


def link(label, name):
    return f"[[{label}/{name}]]"


def slug_pick(seed, pool, n):
    pool = sorted(pool)
    pool.sort(key=lambda p: hashlib.sha1((seed + p).encode()).hexdigest())
    return pool[:n]


def write_note(label, name, fm, body=""):
    d = VAULT / label
    d.mkdir(parents=True, exist_ok=True)
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body.strip() + "\n"
    (d / f"{name}.md").write_text(text, encoding="utf-8")


def compute_key():
    by_id = {r[0]: r for r in D}
    superseded_by = {}
    for r in D:
        if r[8]:
            superseded_by[r[8]] = r[0]
    active = [r[0] for r in D if r[0] not in superseded_by]
    left = {k for k, v in PEOPLE.items() if v[2]}

    def overlap(a, b):
        return a == b or a == "all" or b == "all"

    conflicts = set()
    for a in D:
        for b in D:
            if a[0] == b[0] or a[0] not in active or b[0] not in active:
                continue
            for (ta, sa, sca) in a[7]:
                for (tb, sb, scb) in b[7]:
                    if ta == tb and sa == "forbids" and sb in ("requires", "allows") and overlap(sca, scb):
                        conflicts.add("+".join(sorted([a[0], b[0]], key=lambda x: int(x[1:]))))
    stale = sorted(r[0] for r in D if r[0] in active and any(dep in superseded_by for dep in r[9]))
    left_owned = sorted(r[0] for r in D if r[0] in active and r[3] in left)

    def active_on_tech(tk):
        return sorted(r[0] for r in D if r[0] in active and any(c[0] == tk for c in r[7]))

    def active_on_project(pk):
        return sorted(r[0] for r in D if r[0] in active and pk in r[6])

    def conflicts_with_proposal(tech, scope, stance):
        # a proposal that 'requires' or 'allows' a tech conflicts with active 'forbids' on overlapping scope
        out = []
        for r in D:
            if r[0] in active:
                for (t, s, sc) in r[7]:
                    if t == tech and s == "forbids" and overlap(sc, scope):
                        out.append(r[0])
        return sorted(set(out))

    def replaced_by(did):
        return [superseded_by[did]] if did in superseded_by else []

    tech_counts = {}
    for r in D:
        if r[0] in active:
            for tk in {c[0] for c in r[7]}:
                tech_counts[tk] = tech_counts.get(tk, 0) + 1
    top = max(tech_counts.values())
    tech_top = sorted(k for k, v in tech_counts.items() if v == top)

    return {
        "E01": dict(type="lineage", kind="set", text="Which decision replaced D04?", answer=replaced_by("D04")),
        "E02": dict(type="lineage", kind="set", text="Which decision replaced D11?", answer=replaced_by("D11")),
        "E03": dict(type="lineage", kind="set", text="Which decisions does D17 replace?",
                    answer=[by_id["D17"][8]]),
        "E04": dict(type="lineage", kind="set", text="Which decisions list D05 as something they depend on?",
                    answer=sorted(r[0] for r in D if "D05" in r[9])),
        "E05": dict(type="active", kind="set", text="Which currently active decisions constrain Sentra Lidar?",
                    answer=active_on_tech("sentra-lidar")),
        "E06": dict(type="active", kind="set", text="Which currently active decisions affect the Beacon project?",
                    answer=active_on_project("beacon")),
        "E07": dict(type="active", kind="scalar", text="How many decisions are currently active (not replaced by a later decision)?",
                    answer=len(active)),
        "E08": dict(type="alias", kind="set",
                    text="Which currently active decisions concern Quanta DB? It may be written QuantaDB or Q-DB in notes.",
                    answer=active_on_tech("quanta-db")),
        "E09": dict(type="conflict", kind="set", text="Which pairs of currently active decisions conflict with each other? "
                    "Answer each pair as 'Dxx+Dyy' with the lower number first.", answer=sorted(conflicts)),
        "E10": dict(type="stale", kind="set", text="Which currently active decisions depend on a decision that has since been replaced?",
                    answer=stale),
        "E11": dict(type="stale", kind="set", text="Which currently active decisions are owned by someone who has left the company?",
                    answer=left_owned),
        "E12": dict(type="proposal", kind="set",
                    text="Proposal: use Sentra Lidar on the outdoor yard robots. Which currently active decisions conflict with this proposal?",
                    answer=conflicts_with_proposal("sentra-lidar", "outdoor", "allows")),
        "E13": dict(type="proposal", kind="set",
                    text="Proposal: switch the Cobalt charging docks back to VoltEdge Batteries. Which currently active decisions conflict with this proposal?",
                    answer=conflicts_with_proposal("voltedge-batteries", "cobalt", "requires")),
        "E14": dict(type="active", kind="set", text="Which currently active decisions were made by Priya Raman?",
                    answer=sorted(r[0] for r in D if r[0] in active and r[3] == "priya")),
        "E15": dict(type="lineage", kind="set", text="Which decisions have been replaced by a later decision?",
                    answer=sorted(superseded_by)),
        "E16": dict(type="stale", kind="set",
                    text="Which decisions that are still in force were made on the basis of an earlier decision that no longer holds?",
                    answer=stale),
        "E17": dict(type="proposal", kind="set",
                    text="We want to deploy Sentra Lidar sensors on the outdoor yard robots next quarter. Is there an active decision "
                         "that blocks this? List the decision ids.",
                    answer=conflicts_with_proposal("sentra-lidar", "outdoor", "allows")),
        "E18": dict(type="proposal", kind="set",
                    text="Proposal: Drift should use Mapwright map tiles again for the new warehouses. Which currently active "
                         "decisions conflict with this proposal?",
                    answer=conflicts_with_proposal("mapwright", "drift", "requires")),
        "E19": dict(type="proposal", kind="set",
                    text="Proposal: use Granite Auth single sign-on for the Ember warehouse kiosks. Which currently active "
                         "decisions conflict with this proposal? Answer with an empty list if none do.",
                    answer=conflicts_with_proposal("granite-auth", "ember-kiosk", "requires")),
        "E20": dict(type="proposal", kind="set",
                    text="Proposal: run the new Atlas controller on Kestrel RTOS under a fresh license. Which currently active "
                         "decisions conflict with this proposal?",
                    answer=conflicts_with_proposal("kestrel-rtos", "new-controllers", "requires")),
        "E21": dict(type="active", kind="set", text="Which currently active decisions were made by Sofia Marini?",
                    answer=sorted(r[0] for r in D if r[0] in active and r[3] == "sofia")),
        "E22": dict(type="active", kind="scalar", text="How many currently active decisions affect the Flux project?",
                    answer=len(active_on_project("flux"))),
        "E23": dict(type="active", kind="set",
                    text="Which technology has the most currently active decisions constraining it? Answer with the technology name; "
                         "include every technology that ties.",
                    answer=[TECH[k][0] for k in tech_top]),
        "E24": dict(type="stale", kind="set",
                    text="Which currently active decisions are both owned by someone who has left the company and depend on a replaced decision?",
                    answer=sorted(set(stale) & set(left_owned))),
        "E25": dict(type="active", kind="set",
                    text="Which currently active decisions affect a project that is owned by someone who has left the company?",
                    answer=sorted(r[0] for r in D if r[0] in active and any(PROJECTS[p][2] in left for p in r[6]))),
        "E26": dict(type="lineage", kind="set",
                    text="Which meetings produced a decision that has since been replaced? Answer with the meeting names.",
                    answer=sorted({meeting_name(by_id[x][2], by_id[x][1]) for x in superseded_by})),
    }


def main(filler=0, vault=None, key_path=None, key_only=False):
    global VAULT
    if vault:
        VAULT = pathlib.Path(vault)
    if filler:
        add_filler(filler)
    if key_only:
        kp = pathlib.Path(key_path) if key_path else ROOT / "eval" / "answer_key.json"
        kp.parent.mkdir(exist_ok=True)
        kp.write_text(json.dumps(compute_key(), indent=2, ensure_ascii=False) + "\n")
        print("key written:", kp)
        return
    if VAULT.exists():
        shutil.rmtree(VAULT)
    for k, (name, role, left) in PEOPLE.items():
        fm = {"type": "Person", "name": name, "role": role}
        if left:
            fm["left"] = left
        write_note("Person", name, fm, f"{name}, {role} at Fernwood Robotics (fictional).")
    for k, (name, summary, owner) in PROJECTS.items():
        write_note("Project", name, {"type": "Project", "name": name, "summary": summary,
                                     "OWNED_BY": [link("Person", PEOPLE[owner][0])]}, summary)
    for k, (name, aliases) in TECH.items():
        fm = {"type": "Technology", "name": name}
        if aliases:
            fm["aliases"] = aliases
        write_note("Technology", name, fm, f"{name} (fictional vendor or product)." + (f" Also written: {aliases}." if aliases else ""))

    meetings = {}
    for r in D:
        meetings.setdefault((r[2], r[1]), []).append(r)
    for (forum, date), rows in sorted(meetings.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        authors = {r[3] for r in rows}
        present = [k for k, v in PEOPLE.items() if not v[2] or v[2] > date]
        attendees = sorted(authors | set(slug_pick(forum + date, [p for p in present if p not in authors], 3)))
        write_note("Meeting", meeting_name(forum, date),
                   {"type": "Meeting", "name": meeting_name(forum, date), "date": date,
                    "ATTENDED_BY": [link("Person", PEOPLE[p][0]) for p in attendees]},
                   "Decisions: " + "; ".join(f"{r[0]} {r[4]}" for r in rows) + ".")

    for r in D:
        did, date, forum, author, title, why, affects, cons, sup, deps = r
        fm = {"type": "Decision", "name": dname(r), "id": did, "title": title, "date": date,
              "DECIDED_IN": [link("Meeting", meeting_name(forum, date))],
              "MADE_BY": [link("Person", PEOPLE[author][0])],
              "OWNED_BY": [link("Person", PEOPLE[author][0])]}
        if affects:
            fm["AFFECTS"] = [link("Project", PROJECTS[p][0]) for p in affects]
        if cons:
            fm["CONSTRAINS"] = [{"target": link("Technology", tname(t)), "stance": s, "scope": sc} for t, s, sc in cons]
        if sup:
            fm["SUPERSEDES"] = [link("Decision", dname(next(x for x in D if x[0] == sup)))]
        if deps:
            fm["DEPENDS_ON"] = [link("Decision", dname(next(x for x in D if x[0] == d))) for d in deps]
        body = f"# {did}: {title}\n\n{why}\n"
        write_note("Decision", dname(r), fm, body)

    key = compute_key()
    kp = pathlib.Path(key_path) if key_path else ROOT / "eval" / "answer_key.json"
    kp.parent.mkdir(exist_ok=True)
    kp.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n")
    print("notes:", sum(1 for _ in VAULT.rglob("*.md")), "questions:", len(key))
    for qid, q in key.items():
        print(qid, q["type"], q["answer"])


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--filler", type=int, default=0, help="extra filler decisions (scales the vault)")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--key-only", action="store_true", help="write only the answer key; leave the vault untouched")
    a = ap.parse_args()
    main(a.filler, a.vault, a.key, a.key_only)
