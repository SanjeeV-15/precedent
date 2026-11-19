# Eval changelog (prompt and harness changes after seeing results)

Changes to the evaluation are recorded here so results stay honest. Every change applies to BOTH arms, and earlier
results are kept under their own folder.

## v1 -> v2 (2026-11-18)
- **What:** answer rules now say to use the pair form `Dxx+Dyy` only when the question asks for pairs.
- **Why:** in v1 the graph arm answered `['D12+D21']` on E12 (proposal check, answer key `['D12']`) at 416 notes. The agent had
  queried the right data; the pair wording in the rules led it to over-apply the pair form. Counted as wrong in v1.
- **Results kept:** `results/base82`, `results/scale150` are v1. v2 runs are in `results/v2_*`.

## v2 -> v3 (2026-11-18)
- **What:** 12 new questions (E15-E26: replaced-all, stale paraphrase, three more proposal checks incl. one with an empty answer, ownership, counts, most-constrained technology, replaced-decision meetings, left-owner plus stale intersection). Total 26. Answer keys: `eval/answer_key_v3.json`, `scale/key_150_v3.json`, `scale/key_500_v3.json`. The reference Cypher for every question matches the key at all three vault sizes (`eval/verify_graph.py`).
- **Runs:** Haiku 5.5 with 3 runs per question on 82, 416 and 1,116 notes; Sonnet 5.5 with 1 run per question on 82 and 416 notes. Both arms. Same prompts as v2. Hard spend caps per run (see `scale/run_v3.sh`).
- **Not changed:** prompts, tools, effort (medium), no sampling parameters.
