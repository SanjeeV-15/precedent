"""Draw docs/decision-graph.svg from the Relate store: the six situations Precedent is built to catch.

Edges and labels are read from the graph (SUPERSEDES, DEPENDS_ON, CONSTRAINS, active status); only the layout is fixed.

  python scripts/make_graph_svg.py [store] [out.svg]
"""
import html
import pathlib
import sys

import relate

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precedent import queries as q  # noqa: E402

FONT = "ITC Franklin Gothic, Franklin Gothic Medium, Arial, sans-serif"
PANELS = [
    ("Scoped conflict", "D12 forbids Sentra Lidar outdoors; D21 plans an outdoor pilot", ["D03", "D12", "D21"]),
    ("Replaced, but still depended on", "D13 rests on D05, which D24 replaced; D24 also forbids what D13 requires", ["D05", "D24", "D13"]),
    ("Contradiction in force", "D06 requires Kestrel on all controllers; D29 pauses new licenses", ["D06", "D29"]),
    ("Stale after a replacement", "D17 replaced D02; D30 was decided on the old standard", ["D02", "D17", "D30"]),
    ("Replacement chains", "The old rule is kept for history, never cited as current", ["D04", "D19", "D11", "D27"]),
    ("Not a conflict", "Different scopes: D26 is an exception for backups, not a contradiction", ["D10", "D26"]),
]
W, H, BOX_W, BOX_H = 410, 350, 350, 52
COLS = 3
GREEN, GREY, RED, AMBER, INK, MUTED = "#1D7A46", "#8A8F98", "#C0392B", "#B8860B", "#1B1F24", "#5B636E"


def esc(s):
    return html.escape(str(s), quote=True)


def trunc(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def main(store=str(ROOT / "store/precedent.rl"), out=str(ROOT / "docs/decision-graph.svg")):
    cur = relate.connect(store, read_only=True).cursor()
    info = {}
    for r in q._rows(cur, "MATCH (d:Decision) RETURN d.id AS id, d.title AS title"):
        info[r["id"]] = {"title": r["title"], "active": q.is_active(cur, r["id"]), "cons": []}
    for r in q._rows(cur, "MATCH (d:Decision)-[c:CONSTRAINS]->(t:Technology) RETURN d.id AS id, c.stance AS s, t.name AS t, c.scope AS sc"):
        info[r["id"]]["cons"].append(f"{r['s']} {r['t']} · {r['sc']}")
    sup = {(r["a"], r["b"]) for r in q._rows(cur, "MATCH (a:Decision)-[:SUPERSEDES]->(b:Decision) RETURN a.id AS a, b.id AS b")}
    dep = {(r["a"], r["b"]) for r in q._rows(cur, "MATCH (a:Decision)-[:DEPENDS_ON]->(b:Decision) RETURN a.id AS a, b.id AS b")}
    conf = {tuple(sorted((r["forbids_id"], r["other_id"]))) for r in q.conflicts(cur)}

    rows = (len(PANELS) + COLS - 1) // COLS
    total_w, total_h = COLS * W + 40, rows * H + 120
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {total_h}" width="{total_w}" height="{total_h}" '
           f'font-family="{FONT}">',
           '<defs>' + "".join(
               f'<marker id="a{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
               f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for n, c in (("g", GREY), ("r", RED), ("y", AMBER))) + '</defs>',
           f'<rect width="100%" height="100%" fill="#FFFFFF"/>',
           f'<text x="20" y="32" font-size="20" font-weight="700" fill="{INK}">Precedent: what it catches, read from the Relate graph</text>',
           f'<text x="20" y="54" font-size="12.5" fill="{MUTED}">Green = active decision. Grey = replaced. Red = conflict. Amber dashed = depends on. '
           f'Grey arrow = replaces (new points to old).</text>']
    for i, (title, sub, ids) in enumerate(PANELS):
        ox, oy = 20 + (i % COLS) * W, 78 + (i // COLS) * H
        svg.append(f'<rect x="{ox}" y="{oy}" width="{W - 16}" height="{H - 16}" rx="10" fill="#F6F8FA" stroke="#D8DEE4"/>')
        svg.append(f'<text x="{ox + 14}" y="{oy + 24}" font-size="14" font-weight="700" fill="{INK}">{esc(title)}</text>')
        svg.append(f'<text x="{ox + 14}" y="{oy + 41}" font-size="10.5" fill="{MUTED}">{esc(trunc(sub, 78))}</text>')
        pos = {}
        step = (H - 16 - 62 - BOX_H) / max(len(ids) - 1, 1) if len(ids) > 1 else 0
        for k, did in enumerate(ids):
            x, y = ox + 14, oy + 54 + k * min(step, 88)
            pos[did] = (x, y)
        slot = 0
        for a in ids:
            for b in ids:
                kind = None
                if (a, b) in sup:
                    kind = "sup"
                elif (a, b) in dep:
                    kind = "dep"
                if not kind:
                    continue
                xa, ya = pos[a]
                xb, yb = pos[b]
                cx = xa + BOX_W + 18 + 12 * slot
                slot += 1
                col, mk, dash = (GREY, "ag", "") if kind == "sup" else (AMBER, "ay", ' stroke-dasharray="5 4"')
                svg.append(f'<path d="M{xa + BOX_W},{ya + BOX_H / 2} C{cx},{ya + BOX_H / 2} {cx},{yb + BOX_H / 2} {xb + BOX_W},{yb + BOX_H / 2}" '
                           f'fill="none" stroke="{col}" stroke-width="1.8"{dash} marker-end="url(#{mk})"/>')
        for a in ids:
            for b in ids:
                if a < b and tuple(sorted((a, b))) in conf:
                    xa, ya = pos[a]
                    xb, yb = pos[b]
                    xm = xa + BOX_W / 2 - 20
                    top, bot = (ya, yb) if ya < yb else (yb, ya)
                    ymid = (top + BOX_H + bot) / 2
                    svg.append(f'<path d="M{xm},{top + BOX_H} L{xm},{bot}" stroke="{RED}" stroke-width="2.6"/>')
                    svg.append(f'<rect x="{xm - 34}" y="{ymid - 10}" width="68" height="20" rx="10" fill="{RED}"/>')
                    svg.append(f'<text x="{xm}" y="{ymid + 4}" font-size="11" font-weight="700" fill="#FFFFFF" text-anchor="middle">conflict</text>')
        if title == "Not a conflict":  # one 'forbids' and one 'allows' on the same technology, but the scopes differ
            (xa, ya), (xb, yb) = pos[ids[0]], pos[ids[1]]
            xm, ymid = xa + BOX_W / 2 - 20, (ya + BOX_H + yb) / 2
            svg.append(f'<path d="M{xm},{ya + BOX_H} L{xm},{yb}" stroke="{GREEN}" stroke-width="2.6"/>')
            svg.append(f'<rect x="{xm - 92}" y="{ymid - 10}" width="184" height="20" rx="10" fill="{GREEN}"/>')
            svg.append(f'<text x="{xm}" y="{ymid + 4}" font-size="11" font-weight="700" fill="#FFFFFF" text-anchor="middle">scopes differ: no conflict</text>')
        for did in ids:
            x, y = pos[did]
            d = info[did]
            col = GREEN if d["active"] else GREY
            svg.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="7" fill="#FFFFFF" stroke="{col}" stroke-width="2"/>')
            svg.append(f'<rect x="{x}" y="{y}" width="6" height="{BOX_H}" rx="3" fill="{col}"/>')
            deco = "" if d["active"] else ' text-decoration="line-through"'
            svg.append(f'<text x="{x + 14}" y="{y + 20}" font-size="12.5" font-weight="700" fill="{INK if d["active"] else MUTED}"{deco}>'
                       f'{esc(did)}  {esc(trunc(d["title"], 44))}</text>')
            sub2 = d["cons"][0] if d["cons"] else ("replaced" if not d["active"] else "active")
            svg.append(f'<text x="{x + 14}" y="{y + 38}" font-size="11" fill="{MUTED}">{esc(trunc(sub2, 56))}</text>')
    svg.append(f'<text x="20" y="{total_h - 16}" font-size="11" fill="{MUTED}">Fictional company (Fernwood Robotics). Generated by scripts/make_graph_svg.py from store/precedent.rl.</text>')
    svg.append("</svg>")
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out).write_text("\n".join(svg), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
