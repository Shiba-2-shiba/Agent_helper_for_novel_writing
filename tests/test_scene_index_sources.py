"""Related-context pointers retain accepted, current, temporally eligible evidence."""
import json

import pytest

from novel_agent.scene_index import (
    read_scene_summaries, refresh_scene_summaries, render_related_context_pack, select_related_scenes,
)
from test_story_memory import accept, approved_scene, fact, proposal, save_json


def accepted_outcome(project):
    first = dict(approved_scene(project, "1-1", "導入。\n袋を渡した。\n受け取った。\n結末。\n"), line_start=2, line_end=3)
    second = dict(approved_scene(project, "1-2", "翌日。\n袋を確認した。\n"), line_start=2, line_end=2)
    accept(project, proposal(fact(first, "outcome", scene="1-2", kind="scene_outcome", scene_id="1-1",
                                  sources=[first, second], text="ACCEPTED_OUTCOME")))
    return first, second


def test_scene_index_persists_all_accepted_source_ranges_and_hashes(tmp_path):
    first, second = accepted_outcome(tmp_path)
    refresh_scene_summaries(str(tmp_path))
    record = next(r for r in read_scene_summaries(str(tmp_path)) if r["scene_id"] == "1-1")
    assert record["sources"] == [dict(first, scene_id="1-1"), dict(second, scene_id="1-2")]


def test_related_pack_renders_every_accepted_source_range(tmp_path):
    accepted_outcome(tmp_path)
    refresh_scene_summaries(str(tmp_path))
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="ACCEPTED_OUTCOME", limit=1)
    selected, pointers = pack.split("## Pointers")
    assert "ACCEPTED_OUTCOME" in selected
    for section in (selected, pointers):
        assert "scene_1-1.txt:2-3" in section
        assert "scene_1-2.txt:2-2" in section
        assert "scene_1-1.txt:1-1" not in section


def test_related_source_ranges_reproject_at_earlier_target(tmp_path):
    source = dict(approved_scene(tmp_path, "1-1", "過去。\nPAST_EVIDENCE\n末尾。\n"), line_start=2, line_end=2)
    accept(tmp_path, proposal(fact(source, "past", kind="scene_outcome", scene_id="1-1", text="PAST_OUTCOME")))
    future = dict(approved_scene(tmp_path, "9-1", "未来。\nFUTURE_EVIDENCE\n"), line_start=2, line_end=2)
    accept(tmp_path, proposal(fact(source, "future", scene="9-1", kind="scene_outcome", scene_id="1-1",
        sources=[source, future], supersedes=["past"], text="FUTURE_OUTCOME"), batch_id="future"), 1)
    refresh_scene_summaries(str(tmp_path))
    records = select_related_scenes(str(tmp_path), target_scene_id="2-1", query_text="PAST_OUTCOME", limit=1)
    assert records[0]["sources"] == [dict(source, scene_id="1-1")]
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="PAST_OUTCOME", limit=1)
    assert "PAST_OUTCOME" in pack
    assert "scene_1-1.txt:2-2" in pack
    assert "FUTURE" not in pack and "scene_9-1.txt" not in pack


@pytest.mark.parametrize("change", ["source_edit", "approval_revoke"])
def test_related_pack_drops_stale_outcome_and_its_source_ranges(tmp_path, change):
    accepted_outcome(tmp_path)
    refresh_scene_summaries(str(tmp_path))
    if change == "source_edit":
        (tmp_path / "scene_1-2.txt").write_text("改稿した。\n")
    else:
        path = tmp_path / "runtime" / "approval_ledger.json"
        ledger = json.loads(path.read_text())
        ledger["scenes"]["1-2"]["status"] = "revoked"
        save_json(path, ledger)
    records = select_related_scenes(str(tmp_path), target_scene_id="2-1", query_text="袋を渡した", limit=1)
    assert records[0]["summary_kind"] == "excerpt"
    assert all(source["path"] == "scene_1-1.txt" for source in records[0]["sources"])
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="袋を渡した", limit=1)
    assert "ACCEPTED_OUTCOME" not in pack
    assert "scene_1-2.txt" not in pack


def test_excerpt_pointer_covers_multiline_excerpt(tmp_path):
    approved_scene(tmp_path, "1-1", "導入。\n二行目。\n三行目。\n")
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="三行目")
    assert "三行目。" in pack
    assert "scene_1-1.txt:1-3" in pack
