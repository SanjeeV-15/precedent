"""Precedent CLI.  python -m precedent <command> [--store store/precedent.rl]

  conflicts                      active decisions that contradict each other
  stale                          active decisions resting on replaced decisions, or owned by someone who left
  why D17                        lineage of one decision
  active [--project P | --tech T]  currently active decisions
  check --tech "Sentra Lidar" --scope outdoor   does a proposal conflict with anything in force?
"""
import argparse
import pathlib
import sys

import relate

from . import queries as q

DEFAULT_STORE = str(pathlib.Path(__file__).resolve().parent.parent / "store" / "precedent.rl")


def _line(r):
    return f"  {r['id']}  {r['title']}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="precedent", description="Decision memory on Relate")
    ap.add_argument("--store", default=DEFAULT_STORE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("conflicts")
    sub.add_parser("stale")
    w = sub.add_parser("why"); w.add_argument("id")
    a = sub.add_parser("active"); a.add_argument("--project"); a.add_argument("--tech")
    c = sub.add_parser("check"); c.add_argument("--tech", required=True); c.add_argument("--scope", required=True)
    args = ap.parse_args(argv)

    cur = relate.connect(args.store, read_only=True).cursor()

    if args.cmd == "conflicts":
        rows = q.conflicts(cur)
        print(f"{len(rows)} conflict(s) among active decisions:")
        for r in rows:
            print(f"- {r['tech']}: {r['forbids_id']} forbids ({r['forbids_scope']}) but {r['other_id']} "
                  f"{r['other_stance']} ({r['other_scope']})")
            print(f"    {r['forbids_id']}: {r['forbids_title']}\n    {r['other_id']}: {r['other_title']}")
    elif args.cmd == "stale":
        s = q.stale(cur)
        print(f"{len(s)} active decision(s) depend on a replaced decision:")
        for r in s:
            print(f"- {r['id']} {r['title']}\n    depends on {r['replaced_id']}, replaced by {r['replaced_by']}")
        lo = q.left_owned(cur)
        print(f"\n{len(lo)} active decision(s) owned by someone who left:")
        for r in lo:
            print(f"- {r['id']} {r['title']}\n    owner {r['owner']} left {r['left']}")
    elif args.cmd == "why":
        w = q.why(cur, args.id.upper())
        if not w:
            print(f"no decision {args.id}"); return 1
        print(f"{w['id']}: {w['title']} ({'ACTIVE' if w['active'] else 'REPLACED'})")
        print(f"  decided {w['meeting']}, by {w['made_by']}")
        for label, key in (("replaces", "replaces"), ("replaced by", "replaced_by"), ("depends on", "depends_on")):
            for r in w[key]:
                print(f"  {label}: {r['id']} {r['title']}")
    elif args.cmd == "active":
        rows = q.active(cur, args.project, args.tech)
        print(f"{len(rows)} active decision(s):")
        for r in rows:
            print(_line(r))
    elif args.cmd == "check":
        res = q.check(cur, args.tech, args.scope)
        if "error" in res:
            print(res["error"]); return 1
        if res["conflicts"]:
            print(f"CONFLICT: using {res['technology']} for scope '{args.scope}' contradicts {len(res['conflicts'])} active decision(s):")
            for r in res["conflicts"]:
                print(f"  {r['id']} (forbids, scope {r['scope']}): {r['title']}")
        else:
            print(f"No active decision forbids {res['technology']} for scope '{args.scope}'.")
        print("Active decisions on this technology:")
        for r in res["all_active_on_technology"]:
            print(f"  {r['id']} [{r['stance']}, {r['scope']}] {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
