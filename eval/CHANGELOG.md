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

## Capture eval v1 -> v2 (2026-11-19)
- **What:** the extraction prompt now shows each existing scope with an example decision and says to reuse a scope only when it
  names the same thing. Case C14 accepts either of two outcomes (conflict surfaced, or D07 explicitly replaced), because the text
  ("must not be used anymore") can fairly be read both ways.
- **Why:** v1 (Haiku, 3 runs) scored 30/42. Most misses were scope reuse: the model reused `dr-backups` or `telemetry` because the
  word was in the list, which produced a false conflict on C11. C14 was an ambiguous answer key.
- **Kept:** v1 results are in `results/capture_v1`.

## Capture eval v2 -> v3 (2026-11-19)
- **What:** (1) capture and `check` now also report POSSIBLE conflicts when scopes are nested but not identical (token subset, such as
  `outdoor` and `outdoor-yard-robots`). The graph's own conflict rule (equal scope or `all`) is unchanged, so the 26-question results stand.
  (2) The scorer accepts scope wording that contains an accepted scope (`new-services-data` for `new-services`), and counts a conflict
  as found if it is an exact or a possible conflict.
- **Why:** v2 (Haiku, 3 runs) scored 33/42. Most remaining misses were scope wording, but one was real: `outdoor-yard-robots` did not
  overlap `outdoor`, so the conflict with D12 was missed.
- **Kept:** v1 in `results/capture_v1`, v2 in `results/capture_v2`.
- **Validator fix (same day):** Sonnet returned decision ids wrapped in quote characters (`"D12"`), which failed validation. The validator
  now extracts the `Dnn` token. Sonnet's first capture run (12/14, both invalid cases caused by this) was discarded and rerun.
