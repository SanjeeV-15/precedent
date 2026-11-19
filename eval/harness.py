"""Evaluation harness: the same questions answered by two agent arms with different tools.

  files : search and read the markdown vault (list_files, grep, read_file)
  graph : read-only Cypher over the Relate store (run_cypher), schema in the prompt

Both arms get the same glossary of what "active" and "conflict" mean, the same model, and the same pinned effort.
Neither uses forced tool choice or sampling parameters (the API rejects both on current models).
"""
import json
import pathlib
import re
import time

import relate

ROOT = pathlib.Path(__file__).resolve().parent.parent
VAULT = ROOT / "vault"
EFFORT = "medium"
MAX_TURNS = 25
MAX_TOKENS = 8000
ROW_CAP = 100
GREP_CAP = 40
READ_CAP = 6000

GLOSSARY = (
    "Definitions: a decision is ACTIVE unless another decision lists it under SUPERSEDES (SUPERSEDES points from the "
    "newer decision to the older one it replaces). A CONSTRAINS relationship from a decision to a technology carries "
    "a stance (requires, allows or forbids) and a scope. Two active decisions CONFLICT when one forbids a technology "
    "and the other requires or allows it over overlapping scope (equal scope, or either scope is 'all'). A decision "
    "is STALE when it is active but depends on (DEPENDS_ON) a decision that has been replaced. Some people have "
    "left the company (a 'left' date). Technologies can be written under aliases in notes."
)
ANSWER_RULES = (
    "When done, call final_answer once: a list of strings or an integer. Use decision ids like 'D17'. Use the pair "
    "form 'D12+D21' (lower number first) ONLY when the question asks for pairs of decisions; otherwise answer with "
    "single decision ids. Answer with an empty list if none apply. "
    f"You have at most {MAX_TURNS} turns."
)

FINAL_TOOL = {
    "name": "final_answer",
    "description": "Submit the final answer. Call exactly once. A list of strings (decision ids, or 'Dxx+Dyy' pairs) "
                   "or an integer.",
    "input_schema": {"type": "object", "properties": {"answer": {
        "description": "List of strings, or an integer.",
        "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "integer"}]}}, "required": ["answer"]},
}
FILES_TOOLS = [
    {"name": "list_files", "description": "List note files in a vault folder (Decision, Meeting, Person, Project, Technology).",
     "input_schema": {"type": "object", "properties": {"folder": {"type": "string"}}, "required": ["folder"]}},
    {"name": "grep", "description": f"Case-insensitive regex search over every note. Returns up to {GREP_CAP} matching "
                                     "lines as path:line: text.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "read_file", "description": "Read one note by path relative to the vault, e.g. 'Decision/D12 ... .md'.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    FINAL_TOOL,
]
GRAPH_TOOLS = [
    {"name": "run_cypher", "description": f"Run a read-only Cypher query. At most {ROW_CAP} rows are returned.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    FINAL_TOOL,
]


def files_system():
    return ("You answer questions about a team's decision notes, stored as markdown files with YAML frontmatter in "
            "a vault folder. Relationships appear in the frontmatter as [[Label/name]] links. Tools: list_files, "
            "grep, read_file.\n" + GLOSSARY + "\n" + ANSWER_RULES)


def graph_system(cur):
    cur.execute("MATCH (a)-[r]->(b) RETURN DISTINCT labels(a)[0] AS s, type(r) AS r, labels(b)[0] AS d ORDER BY r")
    rel_lines = "\n".join(f"  (:{x['s']})-[:{x['r']}]->(:{x['d']})" for x in cur.fetchall())
    return ("You answer questions about a team's decisions by writing read-only Cypher (Neo4j-style) with the "
            "run_cypher tool.\nRelationships:\n" + rel_lines + "\nProperties: Decision {id, title, date}; "
            "Person {name, role, left (date, only for people who left)}; Technology {name, aliases (comma-separated, "
            "optional)}; Project {name, summary}; Meeting {name, date}. CONSTRAINS edges have stance and scope.\n"
            + GLOSSARY + "\n" + ANSWER_RULES)


class FilesTools:
    def __init__(self, vault=VAULT):
        self.vault = pathlib.Path(vault)
        self.calls, self.errors, self.trail = 0, 0, []

    def _log(self, tool, args, err=None):
        self.calls += 1
        if err:
            self.errors += 1
        self.trail.append({"tool": tool, "args": args, **({"error": err} if err else {})})

    def list_files(self, folder):
        p = (self.vault / folder).resolve()
        if self.vault.resolve() not in p.parents or not p.is_dir():
            self._log("list_files", {"folder": folder}, "no such folder")
            return {"error": "no such folder; use Decision, Meeting, Person, Project or Technology"}
        self._log("list_files", {"folder": folder})
        return {"files": sorted(f.name for f in p.glob("*.md"))}

    def grep(self, pattern):
        try:
            rx = re.compile(pattern, re.I)
        except re.error as e:
            self._log("grep", {"pattern": pattern}, str(e))
            return {"error": f"bad regex: {e}"}
        hits, total = [], 0
        for f in sorted(self.vault.rglob("*.md")):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if rx.search(line):
                    total += 1
                    if len(hits) < GREP_CAP:
                        hits.append(f"{f.relative_to(self.vault)}:{i}: {line.strip()[:200]}")
        self._log("grep", {"pattern": pattern})
        return {"matches": hits, "total": total, "truncated": total > GREP_CAP}

    def read_file(self, path):
        p = (self.vault / path).resolve()
        if self.vault.resolve() not in p.parents or not p.is_file():
            self._log("read_file", {"path": path}, "no such file")
            return {"error": "no such file"}
        text = p.read_text(encoding="utf-8")
        self._log("read_file", {"path": path})
        return {"path": path, "text": text[:READ_CAP], "truncated": len(text) > READ_CAP}

    def receipt(self):
        return {"calls": self.calls, "errors": self.errors, "db_hits": 0, "trail": self.trail}

    def close(self):
        pass


def _sum_hits(plan):
    if not plan or not plan.get("root"):
        return 0

    def walk(op):
        return (((op.get("actual") or {}).get("db_hits")) or 0) + sum(walk(c) for c in op.get("children", []))

    return walk(plan["root"])


class GraphTools:
    def __init__(self, store):
        self.conn = relate.connect(store, read_only=True)
        self.cur = self.conn.cursor()
        self.calls, self.errors, self.db_hits, self.trail = 0, 0, 0, []

    def run_cypher(self, query):
        self.calls += 1
        try:
            self.cur.execute("PROFILE " + query)
            rows = self.cur.fetchall()
            self.db_hits += _sum_hits(self.cur.consume().plan)
            self.trail.append({"tool": "run_cypher", "args": {"query": query}, "returned": len(rows)})
            return {"rows": rows[:ROW_CAP], "row_count": len(rows), "truncated": len(rows) > ROW_CAP}
        except Exception as e:  # noqa: BLE001
            self.errors += 1
            self.trail.append({"tool": "run_cypher", "args": {"query": query}, "error": str(e)})
            return {"error": str(e)}

    def receipt(self):
        return {"calls": self.calls, "errors": self.errors, "db_hits": self.db_hits, "trail": self.trail}

    def close(self):
        self.conn.close()


def run_agent(client, model, arm, store, question, vault=None):
    if arm == "files":
        tool, system, tools = FilesTools(vault or VAULT), files_system(), FILES_TOOLS
        handlers = {"list_files": tool.list_files, "grep": tool.grep, "read_file": tool.read_file}
    elif arm == "graph":
        tool = GraphTools(store)
        system, tools = graph_system(tool.cur), GRAPH_TOOLS
        handlers = {"run_cypher": tool.run_cypher}
    else:
        raise ValueError(arm)

    messages = [{"role": "user", "content": question}]
    transcript, t_in, t_out = [], 0, 0
    answer, status, nudged, t0 = None, "no_answer", False, time.time()
    try:
        for _ in range(MAX_TURNS):
            resp = client.messages.create(model=model, max_tokens=MAX_TOKENS, system=system, tools=tools,
                                          messages=messages, output_config={"effort": EFFORT})
            t_in += resp.usage.input_tokens
            t_out += resp.usage.output_tokens
            transcript.append({"assistant": [b.model_dump() for b in resp.content], "stop": resp.stop_reason})
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason in ("refusal", "max_tokens"):
                status = resp.stop_reason
                break
            uses = [b for b in resp.content if b.type == "tool_use"]
            if not uses:
                if nudged:
                    break
                nudged = True
                messages.append({"role": "user", "content": "Call final_answer with your answer now."})
                continue
            results, done = [], False
            for u in uses:
                if u.name == "final_answer":
                    answer, status, done = u.input.get("answer"), "answered", True
                    break
                fn = handlers.get(u.name)
                out = fn(**u.input) if fn else {"error": f"unknown tool {u.name}"}
                results.append({"type": "tool_result", "tool_use_id": u.id,
                                "content": json.dumps(out, ensure_ascii=False, default=str),
                                **({"is_error": True} if isinstance(out, dict) and "error" in out else {})})
            if done:
                break
            messages.append({"role": "user", "content": results})
            transcript.append({"tool_results": [r["content"][:2000] for r in results]})
        else:
            status = "turn_limit"
    finally:
        receipt = tool.receipt()
        tool.close()
    return {"answer": answer, "status": status, "in_tokens": t_in, "out_tokens": t_out,
            "elapsed_s": round(time.time() - t0, 2), "calls": receipt["calls"], "errors": receipt["errors"],
            "db_hits": receipt["db_hits"], "trail": receipt["trail"], "transcript": transcript}


def _item(x):
    ids = sorted(set(re.findall(r"D\d+", str(x))), key=lambda i: int(i[1:]))
    return "+".join(ids) if ids else str(x).strip().lower()


def score(gold, ans):
    kind, want_raw = gold["kind"], gold["answer"]
    if ans is None:
        return {"correct": False, "precision": 0.0, "recall": 0.0, "f1": 0.0}
    if kind == "scalar":
        v = ans[0] if isinstance(ans, list) and len(ans) == 1 else ans
        try:
            ok = int(float(str(v).strip())) == int(want_raw)
        except ValueError:
            ok = False
        return {"correct": ok, "precision": float(ok), "recall": float(ok), "f1": float(ok)}
    got = {_item(x) for x in (ans if isinstance(ans, list) else [ans])}
    want = {_item(x) for x in want_raw}
    if not want and not got:
        return {"correct": True, "precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(got & want)
    p = tp / len(got) if got else 0.0
    r = tp / len(want) if want else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"correct": got == want, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}
