"""Re-score every saved v3 answer against the answer keys and compare with the recorded result.

No API key and no model calls: this proves the committed tables follow from the committed transcripts and keys.

  python eval/rescore.py
"""
import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from harness import score  # noqa: E402

KEYS = {"82": "eval/answer_key_v3.json", "416": "scale/key_150_v3.json", "1116": "scale/key_500_v3.json"}


def main():
    mismatched = checked = 0
    for folder in sorted(glob.glob(str(ROOT / "results/v3_*_*"))):
        p = pathlib.Path(folder)
        if not p.is_dir():
            continue
        key = json.loads((ROOT / KEYS[p.name.rsplit("_", 1)[1]]).read_text())
        for f in sorted(p.glob("*.jsonl")):
            for line in f.read_text().splitlines():
                r = json.loads(line)
                s = score(key[r["id"]], r["answer"])
                checked += 1
                if s["correct"] != r["correct"] or abs(s["f1"] - r["f1"]) > 1e-9:
                    mismatched += 1
                    print("MISMATCH", p.name, r["arm"], r["id"], "recorded", r["correct"], "rescored", s["correct"])
    print(f"re-scored {checked} saved answers; {mismatched} differ from the recorded result")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
