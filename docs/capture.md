# Capture: from a meeting note to a checked decision

`precedent capture` turns a plain-language note into the structured fields the graph needs, checks the result against the
decisions already in force, and only writes after you confirm. It answers the main caveat of the project: the conflict logic
needs `stance` and `scope` on each decision, and capture is how those get filled in.

```bash
python -m precedent capture --text "Atlas weekly: Marcus says we will mount Sentra Lidar sensors on the outdoor yard robots next month." --dry-run
```
```text
Proposed D31 (claude-haiku-5-5, 2517+824 tokens):
  title:      Mount Sentra Lidar sensors on outdoor yard robots
  author:     Marcus Lee
  affects:    Atlas
  constraint: allows Sentra Lidar (scope outdoor)
  replaces:   -
  depends on: -
PRE-FLIGHT CONFLICTS with decisions in force:
  D12 (forbids outdoor): Sentra Lidar approved for indoor use only   <- vs new: allows Sentra Lidar (outdoor)
Dry run: nothing written.
```

## How it works
1. **Extract.** A model reads the note and calls one tool, `record_decision`, with a title, author, affected projects, constraints
   (technology, stance, scope), what it replaces, and what it depends on. It is given the graph's own vocabulary: technology names
   and aliases, projects, people, existing scopes (each with an example decision) and the active decisions.
2. **Validate.** Code checks every field against the graph: aliases resolve (QuantaDB, Q-DB -> Quanta DB), unknown technologies or
   projects are refused unless `--allow-new`, and a decision can only replace one that is still active.
3. **Pre-flight.** The same conflict logic as `precedent check` runs on the proposed decision (excluding the decision it replaces),
   plus a "possible conflict" warning when scopes are nested but not identical (`outdoor` and `outdoor-yard-robots`), and a list of
   decisions that would be left stale.
4. **Confirm and write.** Nothing is written without `--yes` or an interactive yes. The note files and the graph change go in together:
   the graph write is a single Relate transaction, and if anything fails the transaction is rolled back and the new files removed.
   `python -m precedent rebuild` rebuilds the store from the vault and gives the same graph (a test checks this).

## How well does extraction work?
14 hand-written notes (`eval/capture_cases.json`), scored on: constraints (technology, stance, scope), affected projects, what it
replaces, and whether the pre-flight conflict result matches. Nothing is written during the eval.

| Model | Runs | Fully correct | Constraints | Replaces | Conflict result | Est. cost |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 3 x 14 | 41/42 | 41/42 | 42/42 | 42/42 | $0.02 |
| Sonnet 5.5 | 1 x 14 | 13/14 | 14/14 | 13/14 | 13/14 | $0.11 |

It took three rounds, all kept in `results/` and logged in `eval/CHANGELOG.md`:
- **v1, Haiku 30/42.** The model reused an existing scope word because it was in the list (for example `dr-backups` for a new backups
  rule), which produced a false conflict.
- **v2, 33/42.** Showing each scope with an example decision fixed most of that. A real gap remained: the model wrote
  `outdoor-yard-robots`, which does not equal `outdoor`, so the conflict with D12 was missed.
- **v3, 41/42.** Added the "possible conflict" check for nested scopes. The graph's own conflict rule is unchanged, so the 26-question
  results are unaffected.

What still goes wrong: Haiku once reused the broad scope `telemetry` for a rule about new services only. Sonnet, on one case, treated
"we will mount sensors outdoors" as replacing D12 although the note never says so. Both are visible in the preview and need your
confirmation before anything is written.

Limitations: scopes are flat words, not a hierarchy (nested scopes are only flagged as "possible"); 14 cases is a small set; the
scorer accepts scope wording that contains an accepted scope.
