# Native vault mode: the notes folder is the database

Relate's markdown-vault codec can open a folder of notes as a store: one `Label/name.md` per node, scalar frontmatter as
properties, `[[wikilinks]]` in frontmatter as relationships. Precedent works in this mode, so the same folder you read in an
editor is the graph you query, and changes made through the graph are written back as markdown.

## Set it up
Needs the Relate command-line tool (installs to `~/.local/bin`, signed release): https://relatedb.ai

```bash
sh scripts/native_init.sh            # copies vault/ to vault_native/ and lets Relate open it once
python -m precedent --store vault_native conflicts
```

Use a copy, not the committed `vault/`: the first open rewrites every note in Relate's canonical format (same content, different
key order and quoting), which would show up as noise in git.

## What was verified (all in `tests/test_native_vault.py`, skipped when the CLI is absent)
- All 26 reference queries on the native folder match the answer key.
- Edge properties (`stance`, `scope` on `CONSTRAINS`) survive the round trip.
- A decision written with one Cypher transaction makes Relate render the new decision note and its meeting note into the folder.
- A failed transaction leaves the folder untouched.
- `precedent capture` detects a folder store and writes through the graph only; Relate renders the notes.

## One schema rule worth knowing
The codec requires every relationship type to appear at least once as a plain link, so it can tell it is a relationship and not a
nested value. `CONSTRAINS` always carries properties, so `vault/Schema.md` declares it once. That adds one `Vault` node and one
extra edge in native mode (83 nodes, 299 relationships vs 82 and 298 in the single-file store); every Precedent query filters on
`Decision`, so answers are unaffected.

## Serve it to agents with Relate's own MCP server
```bash
relate serve --database vault_native --read-only --mcp 8791 --auth none      # loopback only
```
Relate exposes two tools, `get_schema` and `read_cypher` (argument `statement`). We checked that the conflict query returns the three
expected pairs through it. Precedent's own server (`python -m precedent.mcp_server`) is narrower on purpose: it offers domain
questions (conflicts, stale, lineage, check) instead of a query language. Use whichever suits the agent.
