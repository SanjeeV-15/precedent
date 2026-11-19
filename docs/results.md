# Evaluation results (v3)

26 questions, answer key computed independently of Cypher, same prompts and tools for both arms.
**graph** = agent writes read-only Cypher against the Relate store; **files** = agent searches and reads the markdown notes.
Haiku 5.5: 3 runs per question (78 answers per cell). Sonnet 5.5: 1 run per question (26 answers per cell).
Costs are estimates from list prices; total spend for this table was about $5.87.

| Model | Notes | Arm | Correct | Tokens | Tool calls / question | Est. cost | Out of budget |
|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 82 | graph | 77/78 (99%) | 424,002 | 1.9 | $0.06 | 0 |
| Haiku 5.5 | 82 | files | 77/78 (99%) | 1,483,269 | 9.6 | $0.19 | 0 |
| Haiku 5.5 | 416 | graph | 77/78 (99%) | 769,771 | 2.1 | $0.10 | 0 |
| Haiku 5.5 | 416 | files | 76/78 (97%) | 3,986,029 | 13.7 | $0.48 | 1 |
| Haiku 5.5 | 1,116 | graph | 77/78 (99%) | 802,559 | 2.3 | $0.10 | 0 |
| Haiku 5.5 | 1,116 | files | 72/78 (92%) | 12,328,128 | 24.4 | $1.42 | 3 |
| Sonnet 5.5 | 82 | graph | 26/26 (100%) | 93,223 | 1.5 | $0.25 | 0 |
| Sonnet 5.5 | 82 | files | 24/26 (92%) | 332,019 | 6.1 | $0.78 | 0 |
| Sonnet 5.5 | 416 | graph | 26/26 (100%) | 97,529 | 1.5 | $0.26 | 0 |
| Sonnet 5.5 | 416 | files | 24/26 (92%) | 1,005,098 | 8.0 | $2.23 | 0 |

"Out of budget" counts answers where the agent ran out of output tokens (8,000 per request) before calling `final_answer`.

## What the numbers say
- **Graph answers stay correct and cheap as the vault grows.** Haiku graph: 77/78, 77/78, 77/78. Sonnet graph: 26/26 at both sizes. Tool calls stay near 2 per question.
- **File search gets slower, costlier and less reliable with size.** Haiku accuracy fell from 77/78 to 76/78 to 72/78. At 1,116 notes the file agent used 15x the tokens and cost 14x as much; at 82 notes the ratios were 3.5x and 3.1x.
- **Sonnet does not close the gap on accuracy.** Sonnet file search got 24/26 at both sizes (misses on stale-decision and conflict questions); Sonnet graph got 26/26. Sonnet file search cost 8.6x the graph arm at 416 notes.
- **Where file search struggles:** stale-decision questions (decisions that depend on a replaced decision) and long-lineage questions, which need many reads and cross-checks.

## Honest caveats
- Small sample: 26 questions, repeated runs of the same question are not independent. Differences of one or two answers at 82 and 416 notes are within noise. The 1,116-note gap (Haiku 72/78 vs 77/78) is more meaningful but still a small sample.
- The graph arm also makes mistakes: Haiku missed 3 of 234 answers. The misses were over-inclusion (flagging an extra decision or pair), not failed retrieval.
- Several file-arm failures at 1,116 notes were running out of the 8,000-token output budget after 43 to 71 tool calls. A larger budget might recover some of those answers, at higher cost.
- The conflict logic relies on structured `stance` and `scope` fields captured on each decision note. In this synthetic vault the scenario generator writes them. In real use a capture step would.
- Synthetic data only. Questions were written by us, and the prompt wording was adjusted once after seeing v1 results (see `eval/CHANGELOG.md`).

Reproduce: see the README. Raw transcripts for every run are in `results/`.
