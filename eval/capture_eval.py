"""Evaluate `precedent capture`: can a model turn free text into the structured fields the graph needs?

Scores, per case: constraints (technology, stance, scope), affected projects, what it replaces, and whether the
pre-flight conflict result matches. Nothing is written (read-only store, extraction + validation + pre-flight only).

  python eval/capture_eval.py --check-gold                    # check the expected conflicts against the graph
  python eval/capture_eval.py --model claude-haiku-5-5 --runs 3 --out results/capture
"""
import argparse
import json
import pathlib
import sys

import anthropic
import relate

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precedent import capture as cap  # noqa: E402

PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}


def gold_clean(case):
    cons = [{"technology": c["tech"], "stance": c["stance"][0], "scope": c["scope"][0]} for c in case["constraints"]]
    return {"constraints": cons, "supersedes": case["supersedes"]}


def score(case, clean, problems, pre):
    want = [c for c in case["constraints"] if not c.get("optional")]
    optional = [c for c in case["constraints"] if c.get("optional")]
    got = clean["constraints"]

    def scope_ok(chosen, accepted):
        # same scope, or the model's wording contains an accepted scope (for example new-services-data for new-services)
        return any(chosen == a or cap.q._tokens(a) <= cap.q._tokens(chosen) for a in accepted)

    def matches(g, c):
        return c["technology"] == g["tech"] and c["stance"] in g["stance"] and scope_ok(c["scope"], g["scope"])

    used = set()
    ok_want = True
    for g in want:
        hit = next((i for i, c in enumerate(got) if i not in used and matches(g, c)), None)
        if hit is None:
            ok_want = False
        else:
            used.add(hit)
    extra = [c for i, c in enumerate(got) if i not in used and not any(matches(g, c) for g in optional)]
    s = {"valid": not problems,
         "constraints": ok_want and not extra,
         "affects": set(clean["affects"]) == set(case["affects"]),
         "supersedes": clean["supersedes"] == case["supersedes"],
         "conflicts": ({c["id"] for c in pre["conflicts"]} | {c["id"] for c in pre.get("possible_conflicts", [])})
         == set(case["conflicts"])}
    if case.get("outcomes"):  # ambiguous text: any listed (replaces, conflicts) outcome is acceptable
        found = {x["id"] for x in pre["conflicts"]} | {x["id"] for x in pre.get("possible_conflicts", [])}
        ok = any(clean["supersedes"] == o["supersedes"] and found == set(o["conflicts"]) for o in case["outcomes"])
        s["supersedes"] = s["conflicts"] = ok
    s["overall"] = all(s.values())
    return s, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--store", default=str(ROOT / "store/precedent.rl"))
    ap.add_argument("--cases", default=str(ROOT / "eval/capture_cases.json"))
    ap.add_argument("--out", default=str(ROOT / "results/capture"))
    ap.add_argument("--check-gold", action="store_true")
    a = ap.parse_args()

    cases = json.loads(pathlib.Path(a.cases).read_text())
    cur = relate.connect(a.store, read_only=True).cursor()
    vocab = cap.vocabulary(cur)

    if a.check_gold:
        bad = 0
        for c in cases:
            pre = cap.preflight(cur, gold_clean(c))
            got = sorted(x["id"] for x in pre["conflicts"])
            ok = got == sorted(c["conflicts"])
            bad += not ok
            print(c["id"], "OK " if ok else "BAD", "expected", c["conflicts"], "graph says", got)
        print("gold consistent with the graph" if not bad else f"{bad} gold mismatches")
        return bad

    cap.load_env(ROOT / ".env")
    client = anthropic.Anthropic(timeout=120.0, max_retries=3)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / f"capture__{a.model}.jsonl"
    tin = tout = 0
    rows = []
    for run in range(a.runs):
        for c in cases:
            data, usage = cap.extract(client, a.model, c["text"], vocab)
            clean, problems, notices = cap.validate(cur, data, vocab)
            pre = cap.preflight(cur, clean) if not problems else {"conflicts": [], "possible_conflicts": [], "would_become_stale": []}
            s, extra = score(c, clean, problems, pre)
            rec = {"id": c["id"], "run": run, "model": a.model, **s, "extra_constraints": extra, "problems": problems,
                   "clean": clean, "conflicts_found": [x["id"] for x in pre["conflicts"]],
                   "possible_conflicts_found": [x["id"] for x in pre.get("possible_conflicts", [])], "usage": usage}
            rows.append(rec)
            tin += usage["in"]
            tout += usage["out"]
            with out_file.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            flag = "OK " if s["overall"] else "MISS"
            print(f"{c['id']} run{run} {flag} " + " ".join(f"{k}={'y' if v else 'N'}" for k, v in s.items() if k != "overall"), flush=True)
    n = len(rows)
    print(f"\n{a.model}: overall {sum(r['overall'] for r in rows)}/{n}")
    for k in ("valid", "constraints", "affects", "supersedes", "conflicts"):
        print(f"  {k:<12} {sum(r[k] for r in rows)}/{n}")
    pin, pout = PRICES.get(a.model, (0, 0))
    print(f"  tokens in={tin} out={tout}; est. cost ${(tin * pin + tout * pout) / 1e6:.4f}")


if __name__ == "__main__":
    sys.exit(main())
