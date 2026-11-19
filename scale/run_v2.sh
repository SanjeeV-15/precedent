#!/bin/sh
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY eval/run_eval.py --arm graph --model claude-haiku-5-5 --store scale/store_150.rl --key scale/key_150.json --vault scale/vault_150 --out results/v2_scale150 > results/v2_scale150.graph.log 2>&1
$PY eval/run_eval.py --arm files --model claude-haiku-5-5 --store scale/store_150.rl --key scale/key_150.json --vault scale/vault_150 --out results/v2_scale150 > results/v2_scale150.files.log 2>&1
$PY eval/run_eval.py --arm graph --model claude-haiku-5-5 --store scale/store_500.rl --key scale/key_500.json --vault scale/vault_500 --out results/v2_scale500 > results/v2_scale500.graph.log 2>&1
$PY eval/run_eval.py --arm files --model claude-haiku-5-5 --store scale/store_500.rl --key scale/key_500.json --vault scale/vault_500 --out results/v2_scale500 > results/v2_scale500.files.log 2>&1
echo done > results/v2.done
