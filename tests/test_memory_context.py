"""Reading-order and POV isolation, deterministic visible-character budgets."""
import copy
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from test_story_memory import SCRIPTS, accept, api, approved_scene, fact, proposal, save_json


def context():
    return importlib.import_module("novel_agent.memory_context")


def select(project, target="2-1", pov=None, **kwargs):
    return context().select_memory(str(project), target_scene_id=target, pov_character_id=pov,
                                   entity_ids=kwargs.pop("entity_ids", []), thread_ids=kwargs.pop("thread_ids", []), **kwargs)


def test_character_b_cannot_inherit_character_a_knowledge(tmp_path):
    source = approved_scene(tmp_path)
    accept(tmp_path, proposal(fact(source, text="AUTHOR_SECRET_鍵は井戸の底"),
        fact(source, "k1", kind="character_knowledge", character_id="aki", fact_id="f1", text="アキは鍵の場所を知る")))
    a = select(tmp_path, pov="aki")
    b = select(tmp_path, pov="ben")
    assert [r["id"] for r in a["pov_records"]] == ["k1"]
    assert "AUTHOR_SECRET" in context().render_memory_pack(a).split("## pov_context")[1]
    assert b["pov_records"] == []
    assert "AUTHOR_SECRET" in context().render_memory_pack(b).split("## pov_context")[0]
    assert "AUTHOR_SECRET" not in context().render_memory_pack(b).split("## pov_context")[1]


def test_unknown_pov_does_not_include_all_knowledge(tmp_path):
    source = approved_scene(tmp_path)
    accept(tmp_path, proposal(fact(source), fact(source, "k1", kind="character_knowledge", character_id="aki", fact_id="f1")))
    selected = select(tmp_path)
    assert selected["pov_records"] == []
    assert "知識未確定" in context().render_memory_pack(selected)


def test_future_summary_fact_and_target_scene_excluded(tmp_path):
    past = approved_scene(tmp_path)
    now = approved_scene(tmp_path, "2-1")
    future = approved_scene(tmp_path, "9-1")
    accept(tmp_path, proposal(fact(past), fact(now, "target", scene="2-1", text="TARGET_PROSE_SECRET"),
        fact(future, "future", scene="9-1", text="FUTURE_SECRET"),
        fact(future, "summary", scene="9-1", kind="part_summary", part_id="p1", covered_scenes=["9-1"], text="FUTURE_SUMMARY_SECRET")))
    pack = context().render_memory_pack(select(tmp_path))
    assert "扉は青い" in pack
    assert "FUTURE" not in pack
    assert "TARGET_PROSE" not in pack


def test_future_fact_reference_excluded_transitively_even_if_ledger_is_hand_edited(tmp_path):
    past = approved_scene(tmp_path)
    future = approved_scene(tmp_path, "9-1")
    accept(tmp_path, proposal(fact(future, "future", scene="9-1", text="FUTURE_FACT_SECRET"),
        fact(past, "knowledge", scene="9-1", kind="character_knowledge", character_id="aki", fact_id="future", text="FUTURE_KNOWLEDGE_SECRET")))
    path = tmp_path / "story_memory" / "accepted.json"
    payload = json.loads(path.read_text())
    payload["records"][1]["available_after_scene"] = "1-1"
    save_json(path, payload)
    pack = context().render_memory_pack(select(tmp_path, pov="aki"))
    assert "FUTURE" not in pack


def test_future_supersession_keeps_past_record(tmp_path):
    accept(tmp_path, proposal(fact(approved_scene(tmp_path), text="PAST_FACT")))
    accept(tmp_path, proposal(fact(approved_scene(tmp_path, "9-1"), "new", scene="9-1", text="FUTURE_CORRECTION", supersedes=["f1"]), batch_id="new"), 1)
    pack = context().render_memory_pack(select(tmp_path))
    assert "PAST_FACT" in pack
    assert "FUTURE_CORRECTION" not in pack


def test_stale_fact_and_inherited_knowledge_not_in_pack(tmp_path):
    source = approved_scene(tmp_path)
    source2 = approved_scene(tmp_path, "1-2")
    accept(tmp_path, proposal(fact(source, text="STALE_FACT"),
        fact(source2, "k", scene="1-2", kind="character_knowledge", character_id="aki", fact_id="f1", text="STALE_KNOWLEDGE")))
    (tmp_path / "scene_1-1.txt").write_text("改稿", encoding="utf-8")
    selection = select(tmp_path, pov="aki")
    assert "STALE_" not in context().render_memory_pack(selection)
    assert {r["id"] for r in selection["omitted"]} == {"f1", "k"}


def test_latest_thread_event_at_target_controls_open_threads(tmp_path):
    source = approved_scene(tmp_path)
    future = approved_scene(tmp_path, "9-1")
    accept(tmp_path, proposal(fact(source, "t1", kind="thread_event", thread_id="door", event="opened", text="未解決の扉"),
        fact(future, "t2", scene="9-1", kind="thread_event", thread_id="door", event="resolved", text="未来の解決")))
    assert [r["id"] for r in select(tmp_path)["author_records"]] == ["t1"]
    assert select(tmp_path, target="10-1")["author_records"] == []


def test_optional_omission_retains_ids_and_source_pointers(tmp_path):
    source = approved_scene(tmp_path)
    accept(tmp_path, proposal(*[fact(source, "f%s" % i, text="長文" * 600) for i in range(8)]))
    selection = select(tmp_path, max_chars=2000)
    assert len(context().render_memory_pack(selection)) <= 2000
    assert selection["omitted"]
    assert all(record["id"] and record["sources"] for record in selection["omitted"])
    assert all("line_start" in record["sources"][0] for record in selection["omitted"])
    assert "story_memory/accepted.json" in selection["dependencies"]


def test_required_overflow_fails_with_breakdown():
    from novel_agent.errors import UserFacingError
    with pytest.raises(UserFacingError, match="required.*101.*constraints"):
        context().assemble_prompt([{"name": "constraints", "text": "x" * 100, "required": True, "priority": 0, "source_ids": []}], max_chars=50)


def test_assembly_never_exceeds_budget_and_keeps_optional_units():
    result = context().assemble_prompt([
        {"name": "must", "text": "REQUIRED", "required": True, "priority": 0, "source_ids": []},
        {"name": "optional", "text": "a" * 40, "required": False, "priority": 1, "source_ids": ["f1"], "sources": [{"path": "scene_1-1.txt", "line_start": 1, "line_end": 1}]},
        {"name": "other", "text": "b" * 100, "required": False, "priority": 2, "source_ids": ["f2"]},
    ], max_chars=70)
    assert result["chars"] == len(result["prompt"]) <= 70
    assert "REQUIRED" in result["prompt"] and "a" * 40 in result["prompt"]
    assert "b" not in result["prompt"]
    assert result["omitted"][0]["source_ids"] == ["f2"]


def test_future_high_similarity_scene_is_excluded(tmp_path):
    from novel_agent.scene_index import refresh_scene_summaries, render_related_context_pack
    approved_scene(tmp_path, "1-1", "過去の町")
    approved_scene(tmp_path, "9-1", "FUTURE_SIMILAR_SECRET " * 20)
    refresh_scene_summaries(str(tmp_path))
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="FUTURE_SIMILAR_SECRET")
    assert "FUTURE_SIMILAR_SECRET" not in pack
    assert "過去の町" in pack
    assert "excerpt" in pack


def test_excerpt_not_labeled_semantic_summary(tmp_path):
    from novel_agent.scene_index import refresh_scene_summaries
    approved_scene(tmp_path)
    records = refresh_scene_summaries(str(tmp_path))
    assert records[0]["summary_kind"] == "excerpt"
    accept(tmp_path, proposal(fact(approved_scene(tmp_path), "outcome", kind="scene_outcome", scene_id="1-1", text="REVIEWED_OUTCOME")))
    records = refresh_scene_summaries(str(tmp_path))
    assert records[0]["summary_kind"] == "scene_outcome"
    assert records[0]["summary"] == "REVIEWED_OUTCOME"


def run_script(script, project, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), "--project", str(project), *args], capture_output=True, text=True)


def runtime_project(tmp_path):
    from test_scripts import create_runtime_project
    return Path(create_runtime_project(tmp_path))


def test_final_draft_prompt_includes_memory_and_related_pack(tmp_path):
    project = runtime_project(tmp_path)
    source = approved_scene(project, "2-1", "PAST_RELATED_EXCERPT\n")
    accept(project, proposal(fact(source, scene="2-1", text="ACCEPTED_MEMORY_SENTINEL")))
    future = project / "scene_9-1.txt"
    future.write_text("FUTURE_SIMILAR_SECRET", encoding="utf-8")
    built = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft", "--pov-character", "aki")
    assert built.returncode == 0, built.stdout + built.stderr
    prompted = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert prompted.returncode == 0, prompted.stdout + prompted.stderr
    runtime = project / "runtime" / "scenes" / "2-3" / "draft"
    prompt = (runtime / "draft_prompt.txt").read_text()
    assert "ACCEPTED_MEMORY_SENTINEL" in prompt
    assert "PAST_RELATED_EXCERPT" in prompt
    assert "FUTURE_SIMILAR_SECRET" not in prompt
    assert "planning" in prompt
    assert len(prompt) <= 16000
    assert (runtime / "context_selection.json").exists()


def test_no_memory_legacy_project_and_previous_excerpt_budget(tmp_path):
    project = runtime_project(tmp_path)
    (project / "chapter_2_scene_2.txt").write_text("直前本文" * 3000, encoding="utf-8")
    built = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft")
    assert built.returncode == 0, built.stdout + built.stderr
    runtime = project / "runtime" / "scenes" / "2-3" / "draft"
    continuity = (runtime / "continuity_pack.md").read_text()
    assert len(continuity) <= 4000
    assert "Excerpt" in continuity
    prompted = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert prompted.returncode == 0, prompted.stdout + prompted.stderr
    assert len((runtime / "draft_prompt.txt").read_text()) <= 16000


def test_repeated_prompt_stays_current_but_memory_adoption_invalidates_runtime(tmp_path):
    project = runtime_project(tmp_path)
    assert run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft").returncode == 0
    for _ in range(2):
        result = run_script("build_draft_prompt.py", project, "--scene", "2-3")
        assert result.returncode == 0, result.stdout + result.stderr
    source = approved_scene(project, "2-1")
    accept(project, proposal(fact(source, scene="2-1")))
    result = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert result.returncode != 0
    assert "stale" in result.stdout


def test_selection_config_and_record_changes_invalidate_runtime(tmp_path):
    project = runtime_project(tmp_path)
    assert run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft").returncode == 0
    path = project / "runtime" / "scenes" / "2-3" / "draft" / "context_selection.json"
    payload = json.loads(path.read_text())
    payload["config"]["pov_character_id"] = "other"
    save_json(path, payload)
    result = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert result.returncode != 0
    assert "stale" in result.stdout


def test_final_prompt_omissions_preserve_exact_memory_ids_and_pointers(tmp_path):
    project = runtime_project(tmp_path)
    source = approved_scene(project, "2-1")
    accept(project, proposal(*[fact(source, "f%s" % i, scene="2-1", text="任意情報" * 250) for i in range(12)]))
    # Large mandatory style contract forces omission from the final prompt too.
    notes = project / "agent" / "memory" / "global_notes.md"
    notes.write_text(notes.read_text().replace("一人称（主人公）", "必須制約" * 2900), encoding="utf-8")
    built = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft")
    assert built.returncode == 0, built.stdout
    result = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert result.returncode == 0, result.stdout + result.stderr
    runtime = project / "runtime" / "scenes" / "2-3" / "draft"
    selection = json.loads((runtime / "context_selection.json").read_text())
    omitted = [r for r in selection["final_prompt"]["omitted"] if r["name"].startswith("memory:")]
    assert omitted and all(r["source_ids"] and r["sources"] for r in omitted)
    assert len((runtime / "draft_prompt.txt").read_text()) <= 16000


def test_expand_prompt_uses_accepted_memory_without_promoting_target_prose(tmp_path):
    project = runtime_project(tmp_path)
    source = approved_scene(project, "2-1")
    accept(project, proposal(fact(source, scene="2-1", text="EXPAND_MEMORY_SENTINEL")))
    assert run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft").returncode == 0
    target = project / "chapter_2_scene_3.txt"
    target.write_text("彼は決断した。\n", encoding="utf-8")
    checked = run_script("check_scene_output.py", project, "--text", str(target))
    assert checked.returncode == 0, checked.stdout + checked.stderr
    expanded = run_script("build_expand_prompt.py", project, "--draft_text", str(target))
    assert expanded.returncode == 0, expanded.stdout + expanded.stderr
    runtime = project / "runtime" / "scenes" / "2-3" / "draft"
    prompt = (runtime / "expand_prompt.txt").read_text()
    assert "EXPAND_MEMORY_SENTINEL" in prompt
    assert "Existing Paragraph Map" in prompt
    assert len(prompt) <= 16000


def test_index_jsonl_corruption_is_explicit_and_never_silently_skipped(tmp_path):
    from novel_agent.scene_index import read_scene_summaries
    from novel_agent.errors import DataCorruptionError
    path = tmp_path / "runtime" / "scene_summaries.jsonl"
    path.parent.mkdir()
    path.write_text('{"scene_id":"1-1"}\n{', encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(DataCorruptionError, match="scene_summaries.jsonl"):
        read_scene_summaries(str(tmp_path))
    assert path.read_bytes() == before


def test_index_global_future_outcome_is_reprojected_at_target(tmp_path):
    from novel_agent.scene_index import refresh_scene_summaries, render_related_context_pack
    source = approved_scene(tmp_path)
    future = approved_scene(tmp_path, "9-1")
    accept(tmp_path, proposal(fact(source, "outcome", scene="9-1", kind="scene_outcome", scene_id="1-1",
                                     sources=[source, future], text="FUTURE_OUTCOME_SECRET")))
    assert "FUTURE_OUTCOME_SECRET" in refresh_scene_summaries(str(tmp_path))[0]["summary"]
    pack = render_related_context_pack(str(tmp_path), target_scene_id="2-1", query_text="FUTURE_OUTCOME_SECRET")
    assert "FUTURE_OUTCOME_SECRET" not in pack
    assert "excerpt" in pack


def test_final_empty_pov_knowledge_is_explicit(tmp_path):
    project = runtime_project(tmp_path)
    source = approved_scene(project, "2-1")
    accept(project, proposal(fact(source, scene="2-1", text="Author fact")))
    built = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft", "--pov-character", "ben")
    assert built.returncode == 0
    assert run_script("build_draft_prompt.py", project, "--scene", "2-3").returncode == 0
    prompt = (project / "runtime" / "scenes" / "2-3" / "draft" / "draft_prompt.txt").read_text()
    assert "## pov_context" in prompt
    assert "No explicitly accepted knowledge for this POV" in prompt


@pytest.mark.parametrize("source_id", ["2-3", "9-1"])
def test_explicit_previous_source_cannot_be_target_or_future(tmp_path, source_id):
    project = runtime_project(tmp_path)
    path = project / ("scene_%s.txt" % source_id)
    path.write_text("FUTURE_EXPLICIT_PREVIOUS_SECRET", encoding="utf-8")
    result = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft", "--previous_text", str(path))
    assert result.returncode != 0
    assert "before" in result.stdout


@pytest.mark.parametrize("change", ["revoke_approval", "edit_memory"])
def test_runtime_rejects_memory_changes_during_selection(tmp_path, monkeypatch, change):
    import build_runtime_context as runtime
    from types import SimpleNamespace
    from novel_agent.errors import UserFacingError
    project = runtime_project(tmp_path)
    source = approved_scene(project, "2-1")
    accept(project, proposal(fact(source, scene="2-1", text="REVOKED_MEMORY_SENTINEL")))
    original = runtime.select_memory
    def change_after_selection(*args, **kwargs):
        result = original(*args, **kwargs)
        if change == "revoke_approval":
            path = project / "runtime" / "approval_ledger.json"
            payload = json.loads(path.read_text())
            payload["scenes"]["2-1"]["status"] = "revoked"
        else:
            path = project / "story_memory" / "accepted.json"
            payload = json.loads(path.read_text())
            payload["records"][0]["text"] = "MODIFIED_MEMORY_SENTINEL"
        save_json(path, payload)
        return result
    monkeypatch.setattr(runtime, "select_memory", change_after_selection)
    args = SimpleNamespace(scene="2-3", chapter=2, previous_text="", mode="draft", for_check=False,
                           priority="quality", pov_character=None, entity=[], thread=[])
    with pytest.raises(UserFacingError, match="changed during runtime"):
        runtime._build_runtime_context_locked(str(project), args)
    prompted = run_script("build_draft_prompt.py", project, "--scene", "2-3")
    assert prompted.returncode != 0
    assert not (project / "runtime" / "scenes" / "2-3" / "draft" / "draft_prompt.txt").exists()


def test_noncanonical_explicit_previous_is_not_silently_temporal_verified(tmp_path):
    project = runtime_project(tmp_path)
    path = project / "future_notes.txt"
    path.write_text("UNVERIFIED_PREVIOUS_SECRET", encoding="utf-8")
    result = run_script("build_runtime_context.py", project, "--chapter", "2", "--scene", "2-3", "--mode", "draft", "--previous_text", str(path))
    assert result.returncode != 0
    assert "canonical" in result.stdout
