"""Precedent CLI.  python -m precedent <command> [--store store/precedent.rl]

  conflicts                      active decisions that contradict each other
  stale                          active decisions resting on replaced decisions, or owned by someone who left
  why D17                        lineage of one decision
  active [--project P | --tech T]  currently active decisions
  check --tech "Sentra Lidar" --scope outdoor   does a proposal conflict with anything in force?
  capture --text "..."           turn a note into a structured decision, check it, then write it (note + graph)
  rebuild                        rebuild the store from the vault notes
"""
import argparse
import pathlib
import sys

import relate

from . import queries as q

DEFAULT_STORE = str(pathlib.Path(__file__).resolve().parent.parent / "store" / "precedent.rl")


def _line(r):
    return f"  {r['id']}  {r['title']}"


def _capture(args):
    import datetime
    import anthropic
    from . import capture as cap

    text = args.text or (pathlib.Path(args.file).read_text() if args.file else None)
    if not text:
        print("give --text or --file"); return 2
    cap.load_env(pathlib.Path(__file__).resolve().parent.parent / ".env")
    date = args.date or datetime.date.today().isoformat()
    ro = relate.connect(args.store, read_only=True)
    cur = ro.cursor()
    vocab = cap.vocabulary(cur)
    client = anthropic.Anthropic(timeout=120.0, max_retries=2)
    data, usage = cap.extract(client, args.model, text, vocab)
    if args.author:
        data["author"] = args.author
    clean, problems, notices = cap.validate(cur, data, vocab, allow_new=args.allow_new)
    pre = cap.preflight(cur, clean) if not problems else {"conflicts": [], "possible_conflicts": [], "would_become_stale": []}
    print(f"Proposed {vocab['next_id']} ({args.model}, {usage['in']}+{usage['out']} tokens):")
    print(f"  title:      {clean['title']}\n  author:     {clean['author']}\n  affects:    {', '.join(clean['affects']) or '-'}")
    for c in clean["constraints"]:
        print(f"  constraint: {c['stance']} {c['technology']} (scope {c['scope']})")
    print(f"  replaces:   {clean['supersedes'] or '-'}\n  depends on: {', '.join(clean['depends_on']) or '-'}")
    for n in notices:
        print(f"  note: {n}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    if pre["conflicts"]:
        print("PRE-FLIGHT CONFLICTS with decisions in force:")
        for r in pre["conflicts"]:
            print(f"  {r['id']} ({r['stance']} {r['scope']}): {r['title']}   <- vs new: {r['new']}")
    else:
        print("Pre-flight: no conflicts with decisions in force.")
    if pre["possible_conflicts"]:
        print("POSSIBLE conflicts (related but not identical scope; check by hand):")
        for r in pre["possible_conflicts"]:
            print(f"  {r['id']} ({r['stance']} {r['scope']}): {r['title']}   <- vs new: {r['new']}")
    if pre["would_become_stale"]:
        print("Would leave stale (depend on the decision being replaced):")
        for r in pre["would_become_stale"]:
            print(f"  {r['id']}: {r['title']}")
    if problems:
        print("Not written: fix the problems above."); return 1
    if args.dry_run:
        print("Dry run: nothing written."); return 0
    if not args.yes:
        if input("Write this decision (note + graph)? [y/N] ").strip().lower() != "y":
            print("Not written."); return 0
    plan = cap.plan_write(cur, clean, vocab, date, args.forum)
    ro.close()
    files = cap.apply(args.store, args.vault, plan)
    print(f"Written {plan['id']}: {len(files)} note(s) and {len(plan['statements'])} graph statement(s) in one transaction.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="precedent", description="Decision memory on Relate")
    ap.add_argument("--store", default=DEFAULT_STORE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("conflicts")
    sub.add_parser("stale")
    w = sub.add_parser("why"); w.add_argument("id")
    a = sub.add_parser("active"); a.add_argument("--project"); a.add_argument("--tech")
    c = sub.add_parser("check"); c.add_argument("--tech", required=True); c.add_argument("--scope", required=True)
    k = sub.add_parser("capture")
    k.add_argument("--text"); k.add_argument("--file")
    k.add_argument("--date", default=None); k.add_argument("--forum", default="Decision Log")
    k.add_argument("--author", default=None); k.add_argument("--model", default="claude-haiku-5-5")
    k.add_argument("--vault", default=str(pathlib.Path(__file__).resolve().parent.parent / "vault"))
    k.add_argument("--dry-run", action="store_true"); k.add_argument("--yes", action="store_true")
    k.add_argument("--allow-new", action="store_true", help="allow creating new technologies or projects")
    rb = sub.add_parser("rebuild"); rb.add_argument("--vault", default=str(pathlib.Path(__file__).resolve().parent.parent / "vault"))
    args = ap.parse_args(argv)

    if args.cmd == "rebuild":
        from . import store as _store
        print(_store.build(args.vault, args.store))
        return 0
    if args.cmd == "capture":
        return _capture(args)

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
        for r in res.get("possible_conflicts", []):
            print(f"  possible: {r['id']} ({r['stance']}, scope {r['scope']} is related to '{args.scope}'): {r['title']}")
        print("Active decisions on this technology:")
        for r in res["all_active_on_technology"]:
            print(f"  {r['id']} [{r['stance']}, {r['scope']}] {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
