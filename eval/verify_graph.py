"""Check that the graph in the Relate store answers every question in eval/answer_key.json.

The answer key is computed in plain Python by scenario/fernwood.py. These Cypher queries are the reference
graph path; if they all match, the vault and the loader are sound.

Run from the repo root:  python eval/verify_graph.py
"""
import json
import pathlib
import sys

import relate

ROOT = pathlib.Path(__file__).resolve().parent.parent
ACTIVE = "NOT ()-[:SUPERSEDES]->(d)"

CYPHER = {
    "E01": "MATCH (n:Decision)-[:SUPERSEDES]->(:Decision {id:'D04'}) RETURN n.id AS v",
    "E02": "MATCH (n:Decision)-[:SUPERSEDES]->(:Decision {id:'D11'}) RETURN n.id AS v",
    "E03": "MATCH (:Decision {id:'D17'})-[:SUPERSEDES]->(o:Decision) RETURN o.id AS v",
    "E04": "MATCH (d:Decision)-[:DEPENDS_ON]->(:Decision {id:'D05'}) RETURN d.id AS v",
    "E05": f"MATCH (d:Decision)-[:CONSTRAINS]->(:Technology {{name:'Sentra Lidar'}}) WHERE {ACTIVE} RETURN DISTINCT d.id AS v",
    "E06": f"MATCH (d:Decision)-[:AFFECTS]->(:Project {{name:'Beacon'}}) WHERE {ACTIVE} RETURN DISTINCT d.id AS v",
    "E07": f"MATCH (d:Decision) WHERE {ACTIVE} RETURN count(d) AS v",
    "E08": f"MATCH (d:Decision)-[:CONSTRAINS]->(:Technology {{name:'Quanta DB'}}) WHERE {ACTIVE} RETURN DISTINCT d.id AS v",
    "E09": (
        "MATCH (a:Decision)-[ra:CONSTRAINS]->(t:Technology)<-[rb:CONSTRAINS]-(b:Decision) "
        "WHERE a.id <> b.id AND ra.stance = 'forbids' AND rb.stance IN ['requires','allows'] "
        "AND (ra.scope = rb.scope OR ra.scope = 'all' OR rb.scope = 'all') "
        "AND NOT ()-[:SUPERSEDES]->(a) AND NOT ()-[:SUPERSEDES]->(b) "
        "RETURN DISTINCT CASE WHEN a.id < b.id THEN a.id + '+' + b.id ELSE b.id + '+' + a.id END AS v"),
    "E10": (f"MATCH (d:Decision)-[:DEPENDS_ON]->(x:Decision), (:Decision)-[:SUPERSEDES]->(x) "
            f"WHERE {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E11": (f"MATCH (d:Decision)-[:OWNED_BY]->(p:Person) WHERE p.left IS NOT NULL AND {ACTIVE} "
            "RETURN DISTINCT d.id AS v"),
    "E12": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'Sentra Lidar'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'outdoor' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E13": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'VoltEdge Batteries'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'cobalt' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E14": f"MATCH (d:Decision)-[:MADE_BY]->(:Person {{name:'Priya Raman'}}) WHERE {ACTIVE} RETURN DISTINCT d.id AS v",
    "E15": "MATCH (:Decision)-[:SUPERSEDES]->(d:Decision) RETURN DISTINCT d.id AS v",
    "E16": (f"MATCH (d:Decision)-[:DEPENDS_ON]->(x:Decision), (:Decision)-[:SUPERSEDES]->(x) "
            f"WHERE {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E17": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'Sentra Lidar'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'outdoor' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E18": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'Mapwright'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'drift' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E19": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'Granite Auth'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'ember-kiosk' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E20": (f"MATCH (d:Decision)-[r:CONSTRAINS]->(:Technology {{name:'Kestrel RTOS'}}) WHERE r.stance = 'forbids' "
            f"AND (r.scope = 'new-controllers' OR r.scope = 'all') AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E21": f"MATCH (d:Decision)-[:MADE_BY]->(:Person {{name:'Sofia Marini'}}) WHERE {ACTIVE} RETURN DISTINCT d.id AS v",
    "E22": f"MATCH (d:Decision)-[:AFFECTS]->(:Project {{name:'Flux'}}) WHERE {ACTIVE} RETURN count(DISTINCT d) AS v",
    "E23": (f"MATCH (d:Decision)-[:CONSTRAINS]->(t:Technology) WHERE {ACTIVE} WITH t, count(DISTINCT d) AS c ORDER BY c DESC "
            "WITH collect({n:t.name, c:c}) AS rows WITH rows[0].c AS top, rows UNWIND rows AS r WITH r, top "
            "WHERE r.c = top RETURN r.n AS v"),
    "E24": (f"MATCH (d:Decision)-[:OWNED_BY]->(p:Person), (d)-[:DEPENDS_ON]->(x:Decision), (:Decision)-[:SUPERSEDES]->(x) "
            f"WHERE p.left IS NOT NULL AND {ACTIVE} RETURN DISTINCT d.id AS v"),
    "E25": (f"MATCH (d:Decision)-[:AFFECTS]->(:Project)-[:OWNED_BY]->(p:Person) WHERE p.left IS NOT NULL AND {ACTIVE} "
            "RETURN DISTINCT d.id AS v"),
    "E26": "MATCH (:Decision)-[:SUPERSEDES]->(o:Decision)-[:DECIDED_IN]->(m:Meeting) RETURN DISTINCT m.name AS v",
}


def main(store=str(ROOT / "store/precedent.rl"), key_path=str(ROOT / "eval/answer_key.json")):
    key = json.loads(pathlib.Path(key_path).read_text())
    cur = relate.connect(store, read_only=True).cursor()
    bad = 0
    for qid, q in key.items():
        cur.execute(CYPHER[qid])
        vals = [r["v"] for r in cur.fetchall()]
        got = vals[0] if q["kind"] == "scalar" else sorted(vals)
        ok = got == q["answer"]
        bad += not ok
        print(f"{qid} {'OK ' if ok else 'BAD'} {q['type']:<9} got={got} want={q['answer']}" if not ok
              else f"{qid} OK  {q['type']:<9} {got}")
    print("\nall graph answers match the key" if not bad else f"\n{bad} mismatches")
    return bad


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
