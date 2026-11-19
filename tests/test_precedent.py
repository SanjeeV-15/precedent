"""Offline tests: no API key, no network. Run with:  python -m pytest -q"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
import relate

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

from precedent import capture as cap  # noqa: E402
from precedent import queries as q  # noqa: E402
from precedent import store  # noqa: E402
from precedent.mcp_server import Server  # noqa: E402
import harness  # noqa: E402
import verify_graph  # noqa: E402


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("precedent")
    shutil.copytree(ROOT / "vault", d / "vault")
    counts = store.build(d / "vault", d / "p.rl")
    return d, counts


@pytest.fixture()
def cur(built):
    d, _ = built
    return relate.connect(str(d / "p.rl"), read_only=True).cursor()


def test_build_counts(built):
    _, counts = built
    assert counts == {"nodes": 82, "relationships": 298, "dangling": 0}


KEY = json.loads((ROOT / "eval/answer_key_v3.json").read_text())


@pytest.mark.parametrize("qid", sorted(KEY))
def test_reference_cypher_matches_answer_key(built, qid):
    d, _ = built
    cur = relate.connect(str(d / "p.rl"), read_only=True).cursor()
    cur.execute(verify_graph.CYPHER[qid])
    vals = [r["v"] for r in cur.fetchall()]
    want = KEY[qid]
    got = vals[0] if want["kind"] == "scalar" else sorted(vals)
    assert got == want["answer"]


def test_conflicts_stale_and_lineage(cur):
    pairs = {tuple(sorted((r["forbids_id"], r["other_id"]))) for r in q.conflicts(cur)}
    assert pairs == {("D06", "D29"), ("D12", "D21"), ("D13", "D24")}
    assert {r["id"] for r in q.stale(cur)} == {"D13", "D30"}
    assert {r["id"] for r in q.left_owned(cur)} == {"D18", "D30"}
    w = q.why(cur, "D04")
    assert w["active"] is False and [r["id"] for r in w["replaced_by"]] == ["D19"]
    assert q.is_active(cur, "D19") and not q.is_active(cur, "D02")


def test_scoped_exception_is_not_a_conflict(cur):
    # D10 forbids customer PII outside the primary region; D26 allows DR backups. Different scopes: not a conflict.
    flagged = {r["forbids_id"] for r in q.conflicts(cur)} | {r["other_id"] for r in q.conflicts(cur)}
    assert "D10" not in flagged and "D26" not in flagged


def test_alias_resolution(cur):
    for alias in ("QuantaDB", "Q-DB", "quanta db"):
        assert q.resolve_tech(cur, alias) == "Quanta DB"
    assert q.resolve_tech(cur, "nope") is None


def test_check_flags_exact_and_possible_conflicts(cur):
    exact = q.check(cur, "Sentra Lidar", "outdoor")
    assert [r["id"] for r in exact["conflicts"]] == ["D12"]
    nested = q.check(cur, "Sentra Lidar", "outdoor-yard-robots")
    assert nested["conflicts"] == [] and [r["id"] for r in nested["possible_conflicts"]] == ["D12"]
    assert q.check(cur, "Granite Auth", "ember-kiosk")["conflicts"] == []


def test_related_scopes():
    assert q.related_scopes("outdoor", "outdoor-yard-robots")
    assert not q.related_scopes("outdoor", "outdoor")
    assert not q.related_scopes("atlas-indoor", "outdoor")
    assert not q.related_scopes("all", "drift")


def _clean(**kw):
    base = {"title": "Test decision", "rationale": "Because.", "author": "Marcus Lee", "affects": ["Atlas"],
            "constraints": [{"technology": "Sentra Lidar", "stance": "allows", "scope": "outdoor"}],
            "supersedes": None, "depends_on": []}
    base.update(kw)
    return base


def test_validate_rejects_bad_fields(cur):
    vocab = cap.vocabulary(cur)
    data = {"title": "x", "rationale": "y", "author": "Nobody", "affects": ["Ghost"],
            "constraints": [{"technology": "Ghost DB", "stance": "must", "scope": "all"}],
            "supersedes": "D02", "depends_on": ["D999"]}
    _, problems, notices = cap.validate(cur, data, vocab)
    text = " | ".join(problems)
    assert "unknown project" in text and "unknown technology" in text and "bad stance" in text
    assert "already replaced" in text and "D999" in text and notices
    clean, problems, _ = cap.validate(cur, {**data, "supersedes": '"D12"', "affects": [], "depends_on": [],
                                            "constraints": [{"technology": "QuantaDB", "stance": "requires", "scope": "Backups!"}]}, vocab)
    assert clean["supersedes"] == "D12" and clean["constraints"][0]["technology"] == "Quanta DB"
    assert clean["constraints"][0]["scope"] == "backups"


def test_preflight_excludes_the_superseded_decision(cur):
    clean = _clean(supersedes="D12")
    pre = cap.preflight(cur, clean)
    assert pre["conflicts"] == []  # D12 is being replaced, so it no longer blocks
    assert [r["id"] for r in cap.preflight(cur, _clean())["conflicts"]] == ["D12"]


def test_capture_write_is_atomic_and_consistent(built, tmp_path):
    d, _ = built
    vault, db = tmp_path / "vault", tmp_path / "p.rl"
    shutil.copytree(d / "vault", vault)
    shutil.copy(d / "p.rl", db)
    ro = relate.connect(str(db), read_only=True)
    cur = ro.cursor()
    vocab = cap.vocabulary(cur)
    plan = cap.plan_write(cur, _clean(supersedes="D16", constraints=[], title="Raise payload limit to 15 kg"),
                          vocab, "2026-11-19", "Atlas Weekly")
    ro.close()  # the writer needs the store to itself
    files = cap.apply(str(db), vault, plan)
    assert files and all(pathlib.Path(f).exists() for f in files)
    # the transactional store equals a store rebuilt from the vault
    store.build(vault, tmp_path / "rebuilt.rl")

    def counts(p):
        c = relate.connect(str(p), read_only=True).cursor()
        c.execute("MATCH (n) RETURN count(n) AS n")
        n = c.fetchall()[0]["n"]
        c.execute("MATCH ()-[r]->() RETURN count(r) AS r")
        return n, c.fetchall()[0]["r"]

    assert counts(db) == counts(tmp_path / "rebuilt.rl")
    c = relate.connect(str(db), read_only=True).cursor()
    assert not q.is_active(c, "D16") and q.is_active(c, plan["id"])


def test_capture_failure_rolls_back_and_removes_files(built, tmp_path):
    d, _ = built
    vault, db = tmp_path / "vault", tmp_path / "p.rl"
    shutil.copytree(d / "vault", vault)
    shutil.copy(d / "p.rl", db)
    ro = relate.connect(str(db), read_only=True)
    cur = ro.cursor()
    plan = cap.plan_write(cur, _clean(constraints=[]), cap.vocabulary(cur), "2026-11-19", "Atlas Weekly")
    ro.close()
    plan["statements"].append(("THIS IS NOT CYPHER", {}))
    before = sorted(p.name for p in vault.rglob("*.md"))
    with pytest.raises(Exception) as err:
        cap.apply(str(db), vault, plan)
    assert "locked" not in str(err.value)  # it must fail on the bad statement, not on a lock
    assert sorted(p.name for p in vault.rglob("*.md")) == before
    c = relate.connect(str(db), read_only=True).cursor()
    c.execute("MATCH (n:Decision) RETURN count(n) AS n")
    assert c.fetchall()[0]["n"] == 30


def test_mcp_server(built):
    d, _ = built
    s = Server(str(d / "p.rl"))
    names = {t["name"] for t in s.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}
    assert names == {"precedent_check", "precedent_conflicts", "precedent_stale", "precedent_why", "precedent_active"}
    r = s.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": "precedent_check", "arguments": {"tech": "Sentra Lidar", "scope": "outdoor"}}})
    assert json.loads(r["result"]["content"][0]["text"])["conflicts"][0]["id"] == "D12"
    bad = s.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope", "arguments": {}}})
    assert bad["error"]["code"] == -32602
    assert s.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_scorer():
    g = {"kind": "set", "answer": ["D12", "D06+D29"]}
    assert harness.score(g, ["D12", "D29+D06"])["correct"]
    assert not harness.score(g, ["D12"])["correct"]
    assert harness.score({"kind": "set", "answer": []}, [])["correct"]
    assert harness.score({"kind": "scalar", "answer": 25}, [25])["correct"]
    assert not harness.score({"kind": "scalar", "answer": 25}, None)["correct"]


def test_saved_results_rescore_cleanly():
    out = subprocess.run([sys.executable, str(ROOT / "eval/rescore.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "0 differ" in out.stdout
