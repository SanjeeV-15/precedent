#!/bin/sh
# Regenerate the larger vaults, stores and answer keys used for the scaling test.
cd "$(dirname "$0")/.."
PY=${PY:-python}
for n in 150 500; do
  $PY scenario/fernwood.py --filler $n --vault scale/vault_$n --key scale/key_$n.json > /dev/null
  $PY scenario/fernwood.py --key-only --filler $n --key scale/key_${n}_v3.json
  $PY -m precedent.store scale/vault_$n scale/store_$n.rl
  $PY eval/verify_graph.py scale/store_$n.rl scale/key_${n}_v3.json | tail -1
done
