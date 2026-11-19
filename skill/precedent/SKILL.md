---
name: precedent
description: Check a proposal or question against a team's recorded decisions. Use when someone asks whether something is still decided, what replaced a decision, whether a new proposal contradicts anything in force, or which decisions are stale or owned by someone who left. Reads a Relate graph built from decision notes; answers are exact queries, not guesses.
---

# Precedent

Precedent answers questions about a team's decisions from a Relate graph (single file, `store/precedent.rl`).
A decision is **active** unless a later decision supersedes it. Never answer from memory or from searching note text
when a Precedent tool can answer, because replaced decisions still look current in the notes.

## Tools (MCP server `precedent`, or the CLI `python -m precedent ...`)
| Question | Tool | CLI |
|---|---|---|
| Does this proposal conflict with anything in force? | `precedent_check(tech, scope)` | `check --tech T --scope S` |
| Where do we contradict ourselves today? | `precedent_conflicts` | `conflicts` |
| What should we revisit? | `precedent_stale` | `stale` |
| What led to decision D17? Is it still active? | `precedent_why(id)` | `why D17` |
| What is in force for a project or technology? | `precedent_active(project?, tech?)` | `active --project P` |

## How to use it
1. For a proposal in plain language, pick the technology and the scope it would be used in (for example `outdoor`,
   `drift`, `new-controllers`). Technology aliases work ("QuantaDB", "Q-DB" resolve to "Quanta DB").
2. Call `precedent_check`. Report each conflicting decision by id and title, and say it is active.
3. If a decision you want to cite shows `active: false`, say what replaced it (`precedent_why`) instead of citing it.
4. A "forbids" and an "allows" on the same technology only conflict when their scopes overlap (equal, or one is `all`).
   Do not flag scoped exceptions as conflicts.
5. Say plainly when nothing conflicts. An empty result is a valid answer.

## Limits
Conflict logic depends on the `stance` and `scope` recorded on each decision note. If a note lacks them, say the
graph cannot judge that decision, rather than inferring.
