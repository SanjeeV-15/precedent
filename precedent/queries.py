"""Graph queries behind the Precedent CLI and tools. All read-only Cypher against a Relate store.

A decision is *active* when no other decision SUPERSEDES it. That is derived, never stored.
"""
import re

ACTIVE = "NOT ()-[:SUPERSEDES]->(d)"


def _rows(cur, cypher, params=None):
    cur.execute(cypher, params or {})
    return cur.fetchall()


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def resolve_tech(cur, text):
    """Find a Technology by name or alias, ignoring case, spaces and hyphens (QuantaDB, Q-DB -> Quanta DB)."""
    want = _norm(text)
    for r in _rows(cur, "MATCH (t:Technology) RETURN t.name AS name, t.aliases AS aliases"):
        names = [r["name"]] + [a.strip() for a in (r["aliases"] or "").split(",") if a.strip()]
        if want in {_norm(n) for n in names}:
            return r["name"]
    return None


def _tokens(scope):
    return {t for t in re.split(r"[^a-z0-9]+", str(scope).lower()) if t}


def related_scopes(a, b):
    """True when two scopes are nested but not identical (for example 'outdoor' and 'outdoor-yard-robots').
    The graph's own conflict rule only treats equal scopes (or 'all') as overlapping; this flags the near misses."""
    if a == b or "all" in (a, b):
        return False
    ta, tb = _tokens(a), _tokens(b)
    return bool(ta and tb) and (ta <= tb or tb <= ta)


def possible_conflicts(cur, tech, scope, stance):
    """Active decisions with the opposing stance on a related (nested) scope."""
    other = "r.stance = 'forbids'" if stance in ("requires", "allows") else "r.stance IN ['requires','allows']"
    rows = _rows(cur, "MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {name:$t}) "
                      f"WHERE {other} AND {ACTIVE} RETURN d.id AS id, d.title AS title, r.stance AS stance, r.scope AS scope "
                      "ORDER BY id", {"t": tech})
    return [r for r in rows if related_scopes(scope, r["scope"])]


def decision_brief(cur, did):
    rows = _rows(cur, "MATCH (d:Decision {id:$id}) RETURN d.title AS title, d.date AS date", {"id": did})
    return rows[0] if rows else None


def is_active(cur, did):
    return bool(_rows(cur, f"MATCH (d:Decision {{id:$id}}) WHERE {ACTIVE} RETURN d.id AS v", {"id": did}))


def active(cur, project=None, tech=None):
    if project:
        q = (f"MATCH (d:Decision)-[:AFFECTS]->(:Project {{name:$x}}) WHERE {ACTIVE} "
             "RETURN DISTINCT d.id AS id, d.title AS title, d.date AS date ORDER BY id")
        return _rows(cur, q, {"x": project})
    if tech:
        name = resolve_tech(cur, tech) or tech
        q = (f"MATCH (d:Decision)-[:CONSTRAINS]->(:Technology {{name:$x}}) WHERE {ACTIVE} "
             "RETURN DISTINCT d.id AS id, d.title AS title, d.date AS date ORDER BY id")
        return _rows(cur, q, {"x": name})
    return _rows(cur, f"MATCH (d:Decision) WHERE {ACTIVE} RETURN d.id AS id, d.title AS title, d.date AS date ORDER BY id")


def conflicts(cur):
    q = ("MATCH (a:Decision)-[ra:CONSTRAINS]->(t:Technology)<-[rb:CONSTRAINS]-(b:Decision) "
         "WHERE a.id <> b.id AND ra.stance = 'forbids' AND rb.stance IN ['requires','allows'] "
         "AND (ra.scope = rb.scope OR ra.scope = 'all' OR rb.scope = 'all') "
         "AND NOT ()-[:SUPERSEDES]->(a) AND NOT ()-[:SUPERSEDES]->(b) "
         "RETURN t.name AS tech, a.id AS forbids_id, a.title AS forbids_title, ra.scope AS forbids_scope, "
         "b.id AS other_id, b.title AS other_title, rb.stance AS other_stance, rb.scope AS other_scope "
         "ORDER BY forbids_id")
    return _rows(cur, q)


def stale(cur):
    """Active decisions that depend on a decision that has since been replaced."""
    q = ("MATCH (d:Decision)-[:DEPENDS_ON]->(x:Decision), (n:Decision)-[:SUPERSEDES]->(x) "
         f"WHERE {ACTIVE} RETURN d.id AS id, d.title AS title, x.id AS replaced_id, n.id AS replaced_by "
         "ORDER BY id")
    return _rows(cur, q)


def left_owned(cur):
    q = (f"MATCH (d:Decision)-[:OWNED_BY]->(p:Person) WHERE p.left IS NOT NULL AND {ACTIVE} "
         "RETURN d.id AS id, d.title AS title, p.name AS owner, p.left AS left ORDER BY id")
    return _rows(cur, q)


def why(cur, did):
    """Lineage for one decision: what it replaced, what replaced it, what it depends on, who and where."""
    head = decision_brief(cur, did)
    if not head:
        return None
    replaces = _rows(cur, "MATCH (:Decision {id:$id})-[:SUPERSEDES*1..5]->(o:Decision) "
                          "RETURN DISTINCT o.id AS id, o.title AS title ORDER BY id", {"id": did})
    replaced_by = _rows(cur, "MATCH (n:Decision)-[:SUPERSEDES*1..5]->(:Decision {id:$id}) "
                             "RETURN DISTINCT n.id AS id, n.title AS title ORDER BY id", {"id": did})
    depends = _rows(cur, "MATCH (:Decision {id:$id})-[:DEPENDS_ON]->(x:Decision) "
                         "RETURN x.id AS id, x.title AS title ORDER BY id", {"id": did})
    meeting = _rows(cur, "MATCH (:Decision {id:$id})-[:DECIDED_IN]->(m:Meeting) RETURN m.name AS name", {"id": did})
    by = _rows(cur, "MATCH (:Decision {id:$id})-[:MADE_BY]->(p:Person) RETURN p.name AS name", {"id": did})
    return {"id": did, **head, "active": is_active(cur, did), "replaces": replaces, "replaced_by": replaced_by,
            "depends_on": depends, "meeting": meeting[0]["name"] if meeting else None,
            "made_by": by[0]["name"] if by else None}


def check(cur, tech, scope):
    """Which active decisions forbid this technology over an overlapping scope?"""
    name = resolve_tech(cur, tech)
    if not name:
        return {"error": f"unknown technology {tech!r}"}
    q = ("MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {name:$t}) "
         f"WHERE r.stance = 'forbids' AND (r.scope = $s OR r.scope = 'all' OR $s = 'all') AND {ACTIVE} "
         "RETURN d.id AS id, d.title AS title, r.scope AS scope ORDER BY id")
    related = _rows(cur, "MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {name:$t}) "
                         f"WHERE {ACTIVE} RETURN d.id AS id, d.title AS title, r.stance AS stance, r.scope AS scope "
                         "ORDER BY id", {"t": name})
    conflicts = _rows(cur, q, {"t": name, "s": scope})
    return {"technology": name, "scope": scope, "conflicts": conflicts,
            "possible_conflicts": possible_conflicts(cur, name, scope, "requires"),
            "all_active_on_technology": related}


def scopes(cur):
    return [r["s"] for r in _rows(cur, "MATCH ()-[r:CONSTRAINS]->() RETURN DISTINCT r.scope AS s ORDER BY s")]
