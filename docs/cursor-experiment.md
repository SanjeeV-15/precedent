# What we learned before building Precedent: a node-by-node "cursor" lost to plain Cypher

We first tried a different idea: give an agent a `next_hop(node, goal)` tool that only exposes edges that exist, instead of
letting it write Cypher. We built it and ran a small dry run (Haiku 5.5, 5 questions, one run each) against an agent that
writes free-form Cypher with the schema in its prompt, on a public graph of about 380 nodes and 1,900 relationships.

| Arm | Correct | Tool calls | Tokens (in + out) | Est. cost |
|---|---|---|---|---|
| Free Cypher, schema in prompt | 5/5 | 7 | 15,955 + 2,331 | about $0.003 |
| Node-by-node cursor | 4/5 | 86 (63 on one question) | 321,054 + 18,051 | about $0.041 |

With the schema in the prompt, a small model writes correct Cypher almost every time, and does so more cheaply. The cursor
failed by fan-out: a question needing a set-level join over about 100 nodes took 63 calls and returned a partial answer.
The sample is tiny (5 questions, one run), so treat it as a warning, not a verdict.

So we stopped trying to beat Cypher on easy questions and moved to a problem where relationships matter and text search
struggles: replacement chains, dependencies on replaced decisions, scoped conflicts, aliases and ownership. That became
Precedent. See `PRODUCT.md`.
