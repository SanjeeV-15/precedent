"""Build a single-file Relate store from a markdown vault (Label/name.md notes).

Vault conventions (same as Relate's markdown-vault codec): folder = node label, file name = node name,
frontmatter list keys = relationship types with [[Label/name]] targets (map form carries edge properties),
scalar frontmatter = node properties, body = text.
"""
import pathlib
import re
import sys

import relate
import yaml

_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_FM = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)


def parse_vault(root):
    root = pathlib.Path(root)
    nodes, rels = {}, []
    labels = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".") and any(d.glob("*.md")))
    for label in labels:
        for f in sorted((root / label).glob("*.md")):
            m = _FM.match(f.read_text(encoding="utf-8"))
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            props = {"name": f.stem, "text": m.group(2).strip()[:2000]}
            for key, val in fm.items():
                if key in ("type", "name"):
                    continue
                items = val if isinstance(val, list) else [val]
                targets = []
                for it in items:
                    if isinstance(it, str) and _LINK.search(it):
                        targets.append((_LINK.search(it).group(1), {}))
                    elif isinstance(it, dict) and "target" in it:
                        t = _LINK.search(str(it["target"]))
                        if t:
                            targets.append((t.group(1), {k: v for k, v in it.items() if k != "target"}))
                if targets:
                    rels += [(label, f.stem, re.sub(r"\W", "_", key), t, p) for t, p in targets]
                elif isinstance(val, (str, int, float, bool)):
                    props[key] = val
            nodes[(label, f.stem)] = props
    return nodes, rels


def build(vault_dir, out_path):
    out = pathlib.Path(out_path)
    if out.exists():
        out.unlink()
    nodes, rels = parse_vault(vault_dir)
    conn = relate.connect(str(out))
    cur = conn.cursor()
    for (label, _), props in nodes.items():
        cur.execute(f"CREATE (n:{label} $p)", {"p": props})
    loaded = 0
    for sl, sn, rt, target, p in rels:
        tl, _, tn = target.partition("/")
        if (tl, tn) in nodes:
            cur.execute(
                f"MATCH (a:{sl} {{name:$a}}), (b:{tl} {{name:$b}}) CREATE (a)-[:{rt} $p]->(b)",
                {"a": sn, "b": tn, "p": p},
            )
            loaded += 1
    conn.close()
    return {"nodes": len(nodes), "relationships": loaded, "dangling": len(rels) - loaded}


if __name__ == "__main__":
    vault = sys.argv[1] if len(sys.argv) > 1 else "vault"
    out = sys.argv[2] if len(sys.argv) > 2 else "store/precedent.rl"
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    print(build(vault, out))
