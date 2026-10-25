"""Voice routing is explicit, compact, and never a biography/knowledge import."""
import json
from pathlib import Path

import pytest

from novel_agent.errors import UserFacingError
from novel_agent.dependencies import current_check_policy
from prompt_utils import build_style_contract


def config(project, payload):
    (project / "dialogue_voice.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def cards():
    return {"version": 1, "characters": {
        "a": {"name": "甲", "response_goal": "断りたいのに引き受ける", "rhythm": "返事を言い直す"},
        "b": {"name": "乙", "word_choice": "率直に尋ねる", "relationship_stance": "甲に遠慮しない"},
        "future": {"name": "未来人物", "response_goal": "UNSELECTED_SECRET"}},
        "scenes": {"1-2": {"participants": ["a", "b"], "pov_character_id": "a"}}}


def build(project, **kwargs):
    from novel_agent.dialogue_context import build_dialogue_context
    return build_dialogue_context(str(project), scene_id="1-2", **kwargs)


def test_global_conversation_note_reaches_both_style_contracts(tmp_path):
    (tmp_path / "memory").mkdir()
    note = "会話は丁寧に断り損ねる平介と率直な千夏のずれ"
    (tmp_path / "memory/global_notes.md").write_text(note)
    assert note in build_style_contract(str(tmp_path))[0]
    assert note in current_check_policy(str(tmp_path), "1-2")["style_contract"]


def test_selected_cards_and_subjective_guidance_not_biography(tmp_path):
    config(tmp_path, cards())
    (tmp_path / "02_character_sheet.md").write_text("FUTURE_BIOGRAPHY_SECRET")
    result = build(tmp_path)
    assert result["participants"] == ["a", "b"]
    assert result["pov_character_id"] == "a"
    text = result["text"]
    for expected in ("断りたいのに引き受ける", "率直に尋ねる", "受け取り", "省略", "断定しない"):
        assert expected in text
    assert "FUTURE_BIOGRAPHY_SECRET" not in text
    assert "UNSELECTED_SECRET" not in text
    assert len(text) <= 3000


def test_cli_selection_overrides_scene_defaults_and_includes_pov(tmp_path):
    config(tmp_path, cards())
    result = build(tmp_path, participants=["b", "b"], pov_character_id="a")
    assert result["participants"] == ["b"]
    assert result["selected_character_ids"] == ["b", "a"]
    assert "断りたいのに引き受ける" in result["text"]


def test_legacy_missing_cards_warn_without_inventing_participants(tmp_path):
    result = build(tmp_path, pov_character_id="a")
    assert result["participants"] == []
    assert any("participants" in warning for warning in result["warnings"])
    assert any("a" in warning and "card" in warning for warning in result["warnings"])
    assert "WARN" in result["text"]


def test_missing_selected_card_warns_with_id(tmp_path):
    config(tmp_path, cards())
    result = build(tmp_path, participants=["missing"])
    assert any("missing" in warning for warning in result["warnings"])
    assert "率直に尋ねる" not in result["text"]


@pytest.mark.parametrize("change", [
    lambda c: c.update(version=2),
    lambda c: c["characters"]["a"].update(biography="secret"),
    lambda c: c["characters"]["a"].update(rhythm=["not text"]),
    lambda c: c["scenes"]["1-2"].update(participants="a,b"),
    lambda c: c["scenes"]["1-2"].update(pov_character_id=[]),
    lambda c: c.update(unrecognized=True),
])
def test_malformed_explicit_config_is_not_silently_ignored(tmp_path, change):
    payload = cards()
    change(payload)
    config(tmp_path, payload)
    with pytest.raises(UserFacingError, match="dialogue_voice"):
        build(tmp_path)


def test_selected_voice_budget_fails_without_truncating(tmp_path):
    payload = cards()
    payload["characters"]["a"]["rhythm"] = "あ" * 3001
    config(tmp_path, payload)
    with pytest.raises(UserFacingError, match="budget"):
        build(tmp_path)


def run_script(name, *args):
    import subprocess
    import sys
    from test_scripts import SCRIPTS_DIR
    return subprocess.run([sys.executable, str(Path(SCRIPTS_DIR) / name), *map(str, args)], capture_output=True, text=True)


def runtime_project(tmp_path):
    from test_scripts import create_runtime_project
    project = Path(create_runtime_project(tmp_path))
    payload = cards()
    payload["scenes"]["2-3"] = payload["scenes"].pop("1-2")
    config(project, payload)
    return project


def prepare_project(project, *extra):
    result = run_script("run_scene_pipeline.py", "prepare", "--project", project, "--chapter", "2", "--scene", "2-3", *extra)
    assert result.returncode == 0, result.stdout + result.stderr
    return project / "runtime/scenes/2-3/draft"


def test_pipeline_routes_dialogue_pack_into_actual_prompt_and_memory_pov(tmp_path):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project, "--participant", "b", "--pov-character", "a")
    result = run_script("build_draft_prompt.py", "--project", project, "--scene", "2-3")
    assert result.returncode == 0, result.stdout + result.stderr
    prompt = (runtime / "draft_prompt.txt").read_text()
    assert "断りたいのに引き受ける" in prompt
    assert "率直に尋ねる" in prompt
    assert "受け取り" in prompt and "省略" in prompt
    assert "UNSELECTED_SECRET" not in prompt
    assert len(prompt) <= 16000
    selection = json.loads((runtime / "context_selection.json").read_text())
    assert selection["dialogue"]["participants"] == ["b"]
    assert selection["memory"]["pov_character_id"] == "a"
    assert any(s["name"] == "dialogue_context" for s in selection["final_prompt"]["selected"])


@pytest.mark.parametrize("mutation", ["change", "delete", "create"])
def test_voice_config_changes_invalidate_runtime_and_check_policy(tmp_path, mutation):
    from novel_agent.dependencies import snapshot_dependencies, verify_dependencies
    from novel_agent.runtime_paths import require_runtime_current
    project = runtime_project(tmp_path)
    path = project / "dialogue_voice.json"
    if mutation == "create":
        path.unlink()
    runtime = prepare_project(project)
    before = snapshot_dependencies(str(project), [{"kind": "projection", "selector": "check_policy", "scene_id": "2-3"}])
    if mutation == "delete":
        path.unlink()
    else:
        payload = cards()
        payload["characters"]["a"]["rhythm"] = "変わった応答"
        config(project, payload)
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))
    assert verify_dependencies(str(project), before)


def test_dialogue_selection_tampering_invalidates_runtime(tmp_path):
    from novel_agent.runtime_paths import require_runtime_current
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    path = runtime / "context_selection.json"
    payload = json.loads(path.read_text())
    payload["dialogue"] = {"participants": ["future"]}
    path.write_text(json.dumps(payload))
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))


def test_legacy_prompt_has_guidance_and_actionable_missing_pack_warning(tmp_path):
    from test_scripts import create_runtime_project
    project = Path(create_runtime_project(tmp_path))
    runtime = prepare_project(project)
    # Old runtime without manifest and new pack is still supported, but explicit.
    (runtime / "runtime_manifest.json").unlink()
    pack = runtime / "dialogue_context_pack.md"
    if pack.exists():
        pack.unlink()
    result = run_script("build_draft_prompt.py", "--project", project, "--scene", "2-3")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dialogue" in result.stdout and "prepare" in result.stdout
    assert "受け取り" in (runtime / "draft_prompt.txt").read_text()


def test_local_expansion_keeps_selected_voice_and_selective_guidance(tmp_path):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    target = project / "chapter_2_scene_3.txt"
    target.write_text("彼は決断した。\n")
    checked = run_script("check_scene_output.py", "--project", project, "--text", target)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    result = run_script("build_expand_prompt.py", "--project", project, "--draft_text", target)
    assert result.returncode == 0, result.stdout + result.stderr
    prompt = (runtime / "expand_prompt.txt").read_text()
    assert "断りたいのに引き受ける" in prompt
    assert "受け取り" in prompt and "省略" in prompt
    assert len(prompt) <= 16000


def test_explicit_empty_participants_are_not_missing_configuration(tmp_path):
    payload = cards()
    payload["scenes"]["1-2"]["participants"] = []
    config(tmp_path, payload)
    result = build(tmp_path)
    assert not any("participants not configured" in warning for warning in result["warnings"])
    assert "率直に尋ねる" not in result["text"]


def test_actual_prompt_fails_if_required_context_and_voices_exceed_budget(tmp_path):
    project = runtime_project(tmp_path)
    notes = project / "agent/memory/global_notes.md"
    notes.write_text(notes.read_text() + "\n会話: " + "あ" * 16000)
    prepare_project(project)
    result = run_script("build_draft_prompt.py", "--project", project, "--scene", "2-3")
    assert result.returncode != 0
    assert "required prompt sections exceed budget" in result.stdout


@pytest.mark.parametrize("override", [("--participant", "b"), ("--pov-character", "b")])
def test_reprepare_with_cli_selection_change_invalidates_previous_check(tmp_path, override):
    from novel_agent.dependencies import verify_dependencies
    project = runtime_project(tmp_path)
    runtime = prepare_project(project, "--participant", "a", "--pov-character", "a")
    target = project / "chapter_2_scene_3.txt"
    target.write_text("彼は決断した。\n")
    result = run_script("check_scene_output.py", "--project", project, "--text", target)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((runtime / "check_report.json").read_text())
    prepare_project(project, *override)
    assert verify_dependencies(str(project), report["check_inputs"])


def test_absent_opt_in_uses_compact_guards_without_voice_source(tmp_path):
    from novel_agent.dependencies import snapshot_dependencies
    policy = current_check_policy(str(tmp_path), "1-2")
    assert "dialogue_voice_hash" not in policy
    assert "dialogue_voice.json" not in policy["source_paths"]
    runtime_policy = snapshot_dependencies(str(tmp_path), [{"kind": "projection", "selector": "runtime_policy", "scene_id": "1-2"}])[0]
    assert "value" not in runtime_policy
    assert "dialogue_voice.json" not in runtime_policy["source_paths"]
    path = tmp_path / "context_selection.json"
    payload = {"version": 1, "config": {}, "memory": {}}
    path.write_text(json.dumps(payload))
    selected = snapshot_dependencies(str(tmp_path), [{"kind": "projection", "selector": "memory_selection", "path": str(path)}])[0]
    assert "value" not in selected
    from novel_agent.dependencies import verify_dependencies
    assert verify_dependencies(str(tmp_path), [selected]) == []
    payload["memory"]["changed"] = True
    path.write_text(json.dumps(payload))
    assert verify_dependencies(str(tmp_path), [selected])


def memory_source_project(tmp_path):
    from test_story_memory import approved_scene, accept, proposal, fact, save_json
    project = runtime_project(tmp_path)
    approved_scene(project, "1-1")
    source = approved_scene(project, "2-1")
    args = ["--project", project, "--chapter", "2", "--scene", "2-1", "--mode", "draft", "--participant", "a", "--pov-character", "a"]
    result = run_script("build_runtime_context.py", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_script("check_scene_output.py", "--project", project, "--text", project / source["path"])
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((project / "runtime/scenes/2-1/draft/check_report.json").read_text())
    # Synthetic approval fixture, not literary approval, using real v2 conditions.
    ledger_path = project / "runtime/approval_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger["scenes"]["2-1"] = {**report, "status": "approved"}
    save_json(ledger_path, ledger)
    accept(project, proposal(fact(source, scene="2-1", text="STALE_APPROVAL_MEMORY")))
    return project, args


def test_source_selection_change_stales_downstream_accepted_memory(tmp_path):
    from novel_agent.runtime_paths import require_runtime_current
    from novel_agent.approvals import approval_status_for_scene
    project, args = memory_source_project(tmp_path)
    runtime = prepare_project(project)
    assert "STALE_APPROVAL_MEMORY" in (runtime / "story_memory_pack.md").read_text()
    require_runtime_current(str(project), str(runtime))
    args[-3] = "b"
    args[-1] = "b"
    result = run_script("build_runtime_context.py", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert approval_status_for_scene(str(project), "2-1")["status"] == "stale"
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))
    result = run_script("build_draft_prompt.py", "--project", project, "--scene", "2-3")
    assert result.returncode != 0


def test_source_selection_mutation_during_prepare_cannot_be_blessed(tmp_path, monkeypatch):
    import build_runtime_context as runtime
    from types import SimpleNamespace
    project, _ = memory_source_project(tmp_path)
    original = runtime.select_memory
    def mutate_after_selection(*args, **kwargs):
        selection = original(*args, **kwargs)
        assert any(record["text"] == "STALE_APPROVAL_MEMORY" for record in selection["author_records"])
        path = project / "runtime/scenes/2-1/draft/context_selection.json"
        payload = json.loads(path.read_text())
        payload["dialogue"]["participants"] = ["b"]
        path.write_text(json.dumps(payload))
        return selection
    monkeypatch.setattr(runtime, "select_memory", mutate_after_selection)
    args = SimpleNamespace(scene="2-3", chapter=2, previous_text="", mode="draft", for_check=False,
                           priority="quality", pov_character=None, participant=None, entity=[], thread=[])
    with pytest.raises(UserFacingError, match="changed during runtime"):
        runtime._build_runtime_context_locked(str(project), args)
