"""Run questions through an arm and score against eval/answer_key.json.

From the repo root:
  .venv/bin/python eval/run_eval.py --arm graph --model claude-haiku-5-5 --ids E01,E09 --runs 1 --out results/smoke
Each finished question is appended to <out>/<arm>__<model>.jsonl with its full transcript (for replay).
"""
import argparse
import json
import os
import pathlib
import sys

import anthropic

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from harness import run_agent, score  # noqa: E402

# Cached list prices, USD per 1M tokens (Anthropic model table, cached 2026-11-03). Haiku: prompts <= 100K tokens.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}


def load_env(path):
    p = pathlib.Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["files", "graph"])
    ap.add_argument("--model", default="claude-haiku-5-5")
    ap.add_argument("--ids", default="")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--store", default=str(ROOT / "store/precedent.rl"))
    ap.add_argument("--key", default=str(ROOT / "eval/answer_key.json"))
    ap.add_argument("--vault", default=str(ROOT / "vault"))
    ap.add_argument("--out", default=str(ROOT / "results/smoke"))
    ap.add_argument("--max-cost", type=float, default=None, help="stop once the estimated spend (USD) passes this")
    ap.add_argument("--resume", action="store_true", help="skip (question, run) pairs already in the output file")
    a = ap.parse_args()

    load_env(ROOT / ".env")
    client = anthropic.Anthropic(timeout=180.0, max_retries=3)  # never hang on a dead connection
    key = json.loads(pathlib.Path(a.key).read_text())
    ids = [i for i in a.ids.split(",") if i] or list(key)
    out_dir = pathlib.Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{a.arm}__{a.model}.jsonl"

    done = set()
    if a.resume and out_file.exists():
        done = {(r["id"], r["run"]) for r in (json.loads(l) for l in out_file.read_text().splitlines() if l.strip())}
    tot_in = tot_out = n_ok = n_done = 0
    pin, pout = PRICES.get(a.model, (None, None))
    stopped = False
    for run in range(a.runs):
        for qid in ids:
            if a.max_cost is not None and pin is not None and (tot_in * pin + tot_out * pout) / 1e6 > a.max_cost:
                stopped = True
                break
            if (qid, run) in done:
                continue
            g = key[qid]
            res = run_agent(client, a.model, a.arm, a.store, g["text"], a.vault)
            s = score(g, res["answer"])
            rec = {"id": qid, "type": g["type"], "arm": a.arm, "model": a.model, "run": run, **s, **res}
            with out_file.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            tot_in += res["in_tokens"]
            tot_out += res["out_tokens"]
            n_ok += s["correct"]
            n_done += 1
            print(f"{qid} {g['type']:<9} {a.arm:<5} correct={s['correct']!s:<5} f1={s['f1']:.2f} status={res['status']:<10} "
                  f"calls={res['calls']:>2} err={res['errors']} hits={res['db_hits']:>5} "
                  f"tok={res['in_tokens']}+{res['out_tokens']} {res['elapsed_s']}s", flush=True)
        if stopped:
            break
    cost = f"~${(tot_in * pin + tot_out * pout) / 1e6:.4f}" if pin is not None else "price unknown"
    note = "  [STOPPED at cost cap; results incomplete]" if stopped else ""
    print(f"\n{a.arm}/{a.model}: {n_ok}/{n_done} correct (of {len(ids) * a.runs} planned); tokens in={tot_in} out={tot_out}; est. cost {cost}{note}")


if __name__ == "__main__":
    main()
