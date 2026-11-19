"""Summarize result folders into a markdown table: accuracy, F1, tokens, calls, cost per arm and run set.

  python eval/summarize.py results/v2_scale150 results/v2_scale500
  python eval/summarize.py --by-type results/v3_haiku_416
"""
import argparse
import collections
import json
import pathlib

PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}  # USD per 1M tokens, cached list prices


def load(folder):
    rows = []
    for f in sorted(pathlib.Path(folder).glob("*.jsonl")):
        rows += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    return rows


def cost(r):
    pin, pout = PRICES.get(r["model"], (0, 0))
    return (r["in_tokens"] * pin + r["out_tokens"] * pout) / 1e6


def agg(rows):
    n = len(rows)
    return {
        "n": n,
        "acc": sum(r["correct"] for r in rows) / n,
        "f1": sum(r["f1"] for r in rows) / n,
        "tok": sum(r["in_tokens"] + r["out_tokens"] for r in rows),
        "calls": sum(r["calls"] for r in rows) / n,
        "err": sum(r["errors"] for r in rows),
        "cost": sum(cost(r) for r in rows),
        "turn_limit": sum(r["status"] != "answered" for r in rows),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--by-type", action="store_true")
    a = ap.parse_args()
    print("| Run set | Model | Arm | Qs | Correct | Mean F1 | Tokens | Calls/Q | Tool errors | Not answered | Est. cost |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    detail = []
    for folder in a.folders:
        rows = load(folder)
        groups = collections.defaultdict(list)
        for r in rows:
            groups[(r["model"], r["arm"])].append(r)
        for (model, arm), g in sorted(groups.items()):
            s = agg(g)
            print(f"| {pathlib.Path(folder).name} | {model.replace('claude-', '')} | {arm} | {s['n']} | {s['acc']:.0%} | "
                  f"{s['f1']:.2f} | {s['tok']:,} | {s['calls']:.1f} | {s['err']} | {s['turn_limit']} | ${s['cost']:.3f} |")
            detail.append((folder, model, arm, g))
    if a.by_type:
        for folder, model, arm, g in detail:
            print(f"\n{pathlib.Path(folder).name} / {model} / {arm}")
            bt = collections.defaultdict(list)
            for r in g:
                bt[r["type"]].append(r)
            for t, rs in sorted(bt.items()):
                s = agg(rs)
                print(f"  {t:<9} n={s['n']:<3} correct={s['acc']:.0%} calls/q={s['calls']:.1f} tokens={s['tok']:,}")
            wrong = sorted({r["id"] for r in g if not r["correct"]})
            if wrong:
                print("  missed:", ", ".join(wrong))


if __name__ == "__main__":
    main()
