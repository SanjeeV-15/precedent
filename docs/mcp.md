# Using Precedent from an agent (MCP)

`precedent/mcp_server.py` is a small read-only MCP server over stdio. It exposes five tools backed by exact graph
queries on the Relate store (no model is called inside the server):

`precedent_check`, `precedent_conflicts`, `precedent_stale`, `precedent_why`, `precedent_active`

## Run it
```bash
python -m precedent.mcp_server --store store/precedent.rl
```

## Client configuration
Most MCP clients accept a server entry like this (adjust the paths to where you cloned the repo):
```json
{
  "mcpServers": {
    "precedent": {
      "command": "/path/to/precedent/.venv/bin/python",
      "args": ["-m", "precedent.mcp_server", "--store", "/path/to/precedent/store/precedent.rl"],
      "cwd": "/path/to/precedent"
    }
  }
}
```

## Agent skill
`skill/precedent/SKILL.md` tells an agent when and how to use these tools (check a proposal, cite only active decisions,
do not flag scoped exceptions). Copy the `skill/precedent` folder into your agent's skills directory.

## Try it without a client
```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"precedent_check","arguments":{"tech":"Sentra Lidar","scope":"outdoor"}}}' \
  | python -m precedent.mcp_server
```

## Relate's own MCP server
Relate can also serve the same store directly (`relate serve --mcp`), exposing generic Cypher tools. Precedent's server
is narrower on purpose: it gives agents domain questions (conflicts, stale, lineage) instead of a query language.
