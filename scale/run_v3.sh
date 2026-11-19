#!/bin/sh
# Waits for the v2 job, then runs the v3 evaluation (26 questions). Hard spend caps per run (USD, estimated).
cd "$(dirname "$0")/.."
PY=.venv/bin/python
run() { # name model arm runs cap store key vault
  $PY eval/run_eval.py --arm "$3" --model "$2" --runs "$4" --max-cost "$5" --store "$6" --key "$7" --vault "$8" \
      --out "results/$1" --resume >> "results/$1.$3.log" 2>&1
}
H=claude-haiku-5-5; S=claude-sonnet-5-5
for arm in graph files; do
  run v3_haiku_82   $H $arm 3 0.60 store/precedent.rl   eval/answer_key_v3.json   vault
  run v3_haiku_416  $H $arm 3 0.90 scale/store_150.rl   scale/key_150_v3.json     scale/vault_150
  run v3_haiku_1116 $H $arm 3 1.50 scale/store_500.rl   scale/key_500_v3.json     scale/vault_500
done
for arm in graph files; do
  cap82=0.60; cap416=1.00; [ "$arm" = files ] && cap82=1.50 && cap416=3.00
  run v3_sonnet_82  $S $arm 1 $cap82  store/precedent.rl eval/answer_key_v3.json vault
  run v3_sonnet_416 $S $arm 1 $cap416 scale/store_150.rl scale/key_150_v3.json   scale/vault_150
done
echo done > results/v3.done
