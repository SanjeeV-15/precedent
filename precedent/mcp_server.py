"""Precedent as an MCP server (stdio, JSON-RPC 2.0, one message per line).

Lets any MCP-capable agent ask the decision graph: conflicts, stale decisions, lineage, active decisions, and whether a
proposal conflicts with anything in force. Read-only. No model is called here; answers are exact graph queries.

Run:  python -m precedent.mcp_server [--store store/precedent.rl]
Client config example:  see docs/mcp.md
"""
import argparse
import json
import pathlib
import sys

import relate

from . import queries as q

DEFAULT_STORE = str(pathlib.Path(__file__).resolve().parent.parent / "store" / "precedent.rl")
PROTOCOL = "2024-11-05"

TOOLS = [
    {"name": "precedent_check",
     "description": "Check a proposal against decisions in force. Give a technology (aliases like 'QuantaDB' work) and "
                    "the scope it would be used in (for example 'outdoor' or 'drift'). Returns active decisions that "
                    "forbid it over an overlapping scope, plus every active decision on that technology.",
     "inputSchema": {"type": "object", "properties": {"tech": {"type": "string"}, "scope": {"type": "string"}},
                     "required": ["tech", "scope"]}},
    {"name": "precedent_conflicts",
     "description": "Pairs of currently active decisions that contradict each other (one forbids a technology the other "
                    "requires or allows, over overlapping scope).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "precedent_stale",
     "description": "Active decisions that depend on a decision that has since been replaced, and active decisions owned "
                    "by someone who has left.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "precedent_why",
     "description": "Lineage of one decision by id (for example D17): what it replaced, what replaced it, what it "
                    "depends on, who made it and in which meeting, and whether it is still active.",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "precedent_active",
     "description": "Currently active decisions, optionally filtered by project name or technology name/alias.",
     "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}, "tech": {"type": "string"}}}},
]


class Server:
    def __init__(self, store):
        self.cur = relate.connect(store, read_only=True).cursor()

    def call(self, name, args):
        if name == "precedent_check":
            return q.check(self.cur, args["tech"], args["scope"])
        if name == "precedent_conflicts":
            return q.conflicts(self.cur)
        if name == "precedent_stale":
            return {"stale": q.stale(self.cur), "owned_by_someone_who_left": q.left_owned(self.cur)}
        if name == "precedent_why":
            return q.why(self.cur, str(args["id"]).upper()) or {"error": f"no decision {args['id']}"}
        if name == "precedent_active":
            return q.active(self.cur, args.get("project"), args.get("tech"))
        raise KeyError(name)

    def handle(self, msg):
        method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": params.get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}},
                "serverInfo": {"name": "precedent", "version": "0.1.0"}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": mid, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
        if method == "tools/call":
            try:
                out = self.call(params.get("name"), params.get("arguments") or {})
                text, err = json.dumps(out, ensure_ascii=False, default=str), "error" in out if isinstance(out, dict) else False
            except KeyError as e:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool or argument: {e}"}}
            except Exception as e:  # noqa: BLE001 - report to the agent
                text, err = json.dumps({"error": str(e)}), True
            return {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}], "isError": err}}
        if mid is None:  # notification (for example notifications/initialized): no reply
            return None
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=DEFAULT_STORE)
    args = ap.parse_args(argv)
    server = Server(args.store)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = server.handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
