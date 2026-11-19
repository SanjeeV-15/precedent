"""Native vault mode: Relate opens the notes folder itself as the store. Skipped when the relate CLI is not installed."""
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
import verify_graph  # noqa: E402

CLI = shutil.which("relate") or str(pathlib.Path.home() / ".local/bin/relate")
pytestmark = pytest.mark.skipif(not pathlib.Path(CLI).exists(), reason="relate CLI not installed")


@pytest.fixture()
def native(tmp_path):
    vault = tmp_path / "vault"
    shutil.copytree(ROOT / "vault", vault)
    out = subprocess.run([CLI, "--snapshot-format", "markdown", "--markdown-body-properties", "text", "--database", str(vault),
                          "-c", "MATCH (n) RETURN count(n) AS n"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return vault


def test_folder_is_the_store_and_answers_match_the_key(native):
    assert verify_graph.main(str(native), str(ROOT / "eval/answer_key_v3.json")) == 0


def test_edge_properties_survive(native):
    cur = relate.connect(str(native), read_only=True).cursor()
    cur.execute("MATCH (:Decision {id:'D12'})-[r:CONSTRAINS]->(t:Technology) RETURN r.stance AS s, r.scope AS sc, t.name AS t")
    assert cur.fetchall() == [{"s": "forbids", "sc": "outdoor", "t": "Sentra Lidar"}]


def _plan(native):
    ro = relate.connect(str(native), read_only=True)
    cur = ro.cursor()
    clean = {"title": "Raise payload limit to 15 kg", "rationale": "Gripper upgrade.", "author": "Marcus Lee",
             "affects": ["Atlas"], "constraints": [], "supersedes": "D16", "depends_on": []}
    plan = cap.plan_write(cur, clean, cap.vocabulary(cur), "2026-11-19", "Atlas Weekly")
    ro.close()
    return plan


def test_graph_only_write_makes_relate_render_the_note(native):
    plan = _plan(native)
    cap.apply(str(native), native, plan)  # folder store: graph transaction only, no hand-written files
    note = native / "Decision" / f"{plan['name']}.md"
    assert note.exists() and "SUPERSEDES" in note.read_text()
    assert (native / "Meeting" / "Atlas Weekly 2026-11-19.md").exists()
    cur = relate.connect(str(native), read_only=True).cursor()
    assert q.is_active(cur, plan["id"]) and not q.is_active(cur, "D16")


def test_failed_write_leaves_the_folder_untouched(native):
    plan = _plan(native)
    plan["statements"].append(("THIS IS NOT CYPHER", {}))
    before = sorted(p.name for p in native.rglob("*.md"))
    with pytest.raises(Exception):
        cap.apply(str(native), native, plan)
    assert sorted(p.name for p in native.rglob("*.md")) == before
