"""Dependency snapshots bind derived outputs to original, relevant inputs."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def dependency_api():
    # Keep the initial RED an explicit missing-feature failure, not an import error.
    from novel_agent import dependencies
    return dependencies


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    write(tmp_path / "05_chapter_outline.md", """# Outline
## 第1章 Chapter Card
### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 1-1 | standard | 開始 | 静 -> 動 | 種: 鍵 | 1000 | 1250 | 1500 | - | planned |
| 1-2 | anchor | 鍵を使う | 迷 -> 決 | 回収: 鍵 | 1600 | 2000 | 2400 | 1-1 | planned |
""")
    write(tmp_path / "agent/state_schema_novel.yaml", """targets:
  target_total_chars: 100000
  target_length_profile: novel_100k
  scene_type_bands:
    anchor:
      min: 2200
      target: 2700
      max: 3200
style_contract:
  narration_tense: 過去形
  dialogue_rules: [口調を固定]
profile:
  genre: fantasy
story_constraints:
  must_avoid: [説明過多]
active_work:
  runtime_generated_at: yesterday
  active_scene: 1-2
progress:
  completed_scene_count: 0
""")
    write(tmp_path / "agent/memory/global_notes.md", "- 視点: 一人称\n- 禁止: メタ発言\n")
    write(tmp_path / "agent/memory/session_notes.md", "- 鍵を回収する\n")
    write(tmp_path / "chapter_1/scene_1-1.txt", "彼女は鍵を拾った。\n")
    return tmp_path


def test_dependency_module_is_available():
    module_path = Path(__file__).resolve().parents[1] / "scripts/novel_agent/dependencies.py"
    assert module_path.is_file(), "dependency snapshot implementation is missing"


def test_file_snapshot_uses_normalized_text_hash_not_mtime(project):
    api = dependency_api()
    path = project / "日本語.txt"
    path.write_bytes("一行\r\n二行\r\n".encode("utf-8"))
    records = api.snapshot_dependencies(str(project), [{"kind": "file", "path": str(path)}])
    assert records[0]["path"] == "日本語.txt"
    assert records[0]["content_hash"] == hashlib.sha256("一行\n二行\n".encode("utf-8")).hexdigest()
    old_stat = path.stat()
    write(path, "別行\n二行\n")
    os.utime(str(path), (old_stat.st_atime, old_stat.st_mtime))
    assert api.verify_dependencies(str(project), records)


def test_missing_optional_file_appearance_invalidates(project):
    api = dependency_api()
    records = api.snapshot_dependencies(str(project), [{"kind": "file", "path": "optional.md"}])
    assert records[0]["exists"] is False
    assert api.verify_dependencies(str(project), records) == []
    write(project / "optional.md", "")
    assert api.verify_dependencies(str(project), records)[0]["path"] == "optional.md"


def test_scene_membership_add_remove_and_prior_text_invalidate(project):
    api = dependency_api()
    specs = [{"kind": "scene_set", "target_scene_id": "1-3"}]
    records = api.snapshot_dependencies(str(project), specs)
    assert [item["scene_id"] for item in records[0]["members"]] == ["1-1"]
    write(project / "scene_1-3.txt", "対象本文")
    write(project / "scene_2-1.txt", "未来本文")
    assert api.verify_dependencies(str(project), records) == []
    write(project / "scene_1-2.txt", "過去候補追加")
    assert api.verify_dependencies(str(project), records)
    records = api.snapshot_dependencies(str(project), specs)
    (project / "scene_1-2.txt").unlink()
    assert api.verify_dependencies(str(project), records)
    records = api.snapshot_dependencies(str(project), specs)
    write(project / "chapter_1/scene_1-1.txt", "過去本文改稿")
    assert api.verify_dependencies(str(project), records)


def test_scene_order_is_numeric_and_duplicates_are_rejected(project):
    api = dependency_api()
    write(project / "scene_2-1.txt", "第二章")
    write(project / "scene_10-1.txt", "第十章")
    record = api.snapshot_dependencies(str(project), [{"kind": "scene_set", "target_scene_id": "10-1"}])[0]
    assert [item["scene_id"] for item in record["members"]] == ["1-1", "2-1"]
    write(project / "chapter_1_scene_1.txt", "同一ID別ファイル")
    from novel_agent.errors import UserFacingError
    with pytest.raises(UserFacingError, match="ambiguous|duplicate"):
        api.snapshot_dependencies(str(project), [{"kind": "scene_set", "target_scene_id": "1-3"}])


def test_digest_is_order_independent_and_preserves_input(project):
    api = dependency_api()
    records = api.snapshot_dependencies(str(project), [{"kind": "file", "path": "05_chapter_outline.md"}, {"kind": "file", "path": "missing"}])
    before = json.loads(json.dumps(records))
    assert api.dependency_digest(records) == api.dependency_digest(list(reversed(records)))
    assert records == before


@pytest.mark.parametrize("relative_path,old,new", [
    ("agent/state_schema_novel.yaml", "過去形", "現在形"),
    ("agent/memory/global_notes.md", "一人称", "三人称"),
    ("chapter_1/scene_1-1.txt", "鍵", "手紙"),
    ("05_chapter_outline.md", "1600 | 2000 | 2400", "1800 | 2200 | 2600"),
    ("05_chapter_outline.md", "| 1-1 | planned |", "| - | planned |"),
])
def test_check_policy_recomputes_originals_even_when_runtime_unchanged(project, relative_path, old, new):
    api = dependency_api()
    write(project / "runtime/scenes/1-2/draft/scene_brief_compact.md", "Length Band: 1600 / 2000 / 2400\n")
    records = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "check_policy", "scene_id": "1-2"}])
    path = project / relative_path
    write(path, path.read_text(encoding="utf-8").replace(old, new))
    assert api.verify_dependencies(str(project), records)


def test_progress_and_status_write_do_not_invalidate_own_check(project):
    api = dependency_api()
    specs = [{"kind": "projection", "selector": "check_policy", "scene_id": "1-2"}]
    records = api.snapshot_dependencies(str(project), specs)
    state = project / "agent/state_schema_novel.yaml"
    write(state, state.read_text(encoding="utf-8").replace("completed_scene_count: 0", "completed_scene_count: 2").replace("yesterday", "today").replace("active_scene: 1-2", "active_scene: 2-1"))
    outline = project / "05_chapter_outline.md"
    write(outline, outline.read_text(encoding="utf-8").replace("| planned |", "| completed |"))
    assert api.verify_dependencies(str(project), records) == []


def test_current_check_policy_resolves_explicit_band_and_obligations(project):
    policy = dependency_api().current_check_policy(str(project), "1-2")
    assert policy["length_band"] == {"scene_type": "anchor", "min": 1600, "target": 2000, "max": 2400}
    assert policy["obligation_contract"]["required_dependencies"] == ["1-1"]
    assert policy["obligation_contract"]["must_hit_now"] == ["鍵を使う"]
    assert policy["required_dependencies"][0]["members"][0]["path"] == "chapter_1/scene_1-1.txt"


def test_check_policy_falls_back_to_original_state_bands(project):
    path = project / "05_chapter_outline.md"
    write(path, path.read_text(encoding="utf-8").replace("1600 | 2000 | 2400", "- | - | -"))
    policy = dependency_api().current_check_policy(str(project), "1-2")
    assert policy["length_band"] == {"scene_type": "anchor", "min": 2200, "target": 2700, "max": 3200}


def test_runtime_notes_and_resume_progress_are_separate_dependencies(project):
    api = dependency_api()
    runtime = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "runtime_policy"}])
    resume = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "resume_progress"}])
    state = project / "agent/state_schema_novel.yaml"
    write(state, state.read_text(encoding="utf-8").replace("completed_scene_count: 0", "completed_scene_count: 1"))
    assert api.verify_dependencies(str(project), runtime) == []
    assert api.verify_dependencies(str(project), resume)
    notes = project / "agent/memory/session_notes.md"
    write(notes, "- 別の再開事項\n")
    assert api.verify_dependencies(str(project), runtime)


def test_artifact_tracks_its_own_content_and_transitive_dependencies(project):
    api = dependency_api()
    source = project / "source.md"
    artifact = project / "runtime/compact.md"
    write(source, "original")
    write(artifact, "derived")
    upstream = api.snapshot_dependencies(str(project), [{"kind": "file", "path": "source.md"}])
    write(project / "runtime/artifact_ledger.json", json.dumps({"version": 2, "artifacts": [{"id": "artifact:runtime/compact.md", "path": "runtime/compact.md", "dependencies": upstream, "dependency_digest": api.dependency_digest(upstream)}]}))
    records = api.snapshot_dependencies(str(project), [{"kind": "artifact", "path": "runtime/compact.md"}])
    assert api.verify_dependencies(str(project), records) == []
    write(source, "changed without regenerating artifact")
    assert api.verify_dependencies(str(project), records)
    write(source, "original")
    write(artifact, "changed derived output")
    assert api.verify_dependencies(str(project), records)


def test_invalid_dependency_record_is_not_silently_dropped(project):
    api = dependency_api()
    assert api.verify_dependencies(str(project), [{"kind": "unknown", "path": "something"}])
    assert api.verify_dependencies(str(project), [{"kind": "file", "path": "missing"}])


def test_paths_must_remain_inside_project(project, tmp_path):
    api = dependency_api()
    from novel_agent.errors import UserFacingError
    outside = project.parent / "outside-secret.md"
    write(outside, "not a project source")
    (project / "escape.md").symlink_to(outside)
    for path in ["../outside-secret.md", "escape.md"]:
        with pytest.raises(UserFacingError):
            api.snapshot_dependencies(str(project), [{"kind": "file", "path": path}])


def test_dependency_module_import_does_not_load_prompt_utils():
    scripts = str(Path(__file__).resolve().parents[1] / "scripts")
    result = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r); import novel_agent.dependencies; assert 'prompt_utils' not in sys.modules" % scripts], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_no_originals_uses_legacy_default_policy(tmp_path):
    policy = dependency_api().current_check_policy(str(tmp_path), "2-3")
    assert policy["length_band"] == {"scene_type": "default", "min": 1000, "target": 1250, "max": 1500}
    assert policy["obligation_contract"]["required_dependencies"] == []
    assert all(source["exists"] is False for source in policy["sources"])


def test_new_higher_priority_source_invalidates_policy(project):
    api = dependency_api()
    preferred = project / "agent/state_schema_novel.yaml"
    fallback = project / "state_schema_novel.yaml"
    preferred.rename(fallback)
    records = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "check_policy", "scene_id": "1-2"}])
    write(preferred, fallback.read_text(encoding="utf-8"))
    assert api.verify_dependencies(str(project), records)


def test_file_dependency_rejects_directory_with_actionable_error(project):
    from novel_agent.errors import UserFacingError
    with pytest.raises(UserFacingError, match="file"):
        dependency_api().snapshot_dependencies(str(project), [{"kind": "file", "path": "agent"}])


def test_corrupt_artifact_ledger_is_reported_without_replacing_it(project):
    api = dependency_api()
    write(project / "runtime/artifact.txt", "value")
    path = project / "runtime/artifact_ledger.json"
    write(path, "{broken")
    before = path.read_bytes()
    issues = api.verify_dependencies(str(project), [{"kind": "artifact", "path": "runtime/artifact.txt"}])
    assert issues and "artifact_ledger.json" in issues[0]["detail"]
    assert path.read_bytes() == before


def test_artifact_without_dependency_evidence_is_unverified(project):
    api = dependency_api()
    write(project / "runtime/legacy.md", "legacy")
    records = api.snapshot_dependencies(str(project), [{"kind": "artifact", "path": "runtime/legacy.md"}])
    assert any(issue["reason"] == "unverified_artifact_dependencies" for issue in api.verify_dependencies(str(project), records))


def test_runtime_policy_tracks_other_outline_fields_but_not_status(project):
    api = dependency_api()
    specs = [{"kind": "projection", "selector": "runtime_policy"}]
    records = api.snapshot_dependencies(str(project), specs)
    outline = project / "05_chapter_outline.md"
    write(outline, outline.read_text(encoding="utf-8").replace("| planned |", "| completed |"))
    assert api.verify_dependencies(str(project), records) == []
    write(outline, outline.read_text(encoding="utf-8").replace("静 -> 動", "静 -> 悲"))
    assert api.verify_dependencies(str(project), records)


def test_runtime_policy_tracks_planning_scalars_without_check_progress(project):
    api = dependency_api()
    specs = [{"kind": "projection", "selector": "runtime_policy"}]
    state = project / "agent/state_schema_novel.yaml"
    write(state, state.read_text(encoding="utf-8").replace("active_work:", "active_work:\n  planning_gate_status: ready").replace("progress:", "progress:\n  planned_total_min_chars: 80000"))
    records = api.snapshot_dependencies(str(project), specs)
    write(state, state.read_text(encoding="utf-8").replace("planning_gate_status: ready", "planning_gate_status: blocked"))
    assert api.verify_dependencies(str(project), records)
    records = api.snapshot_dependencies(str(project), specs)
    write(state, state.read_text(encoding="utf-8").replace("planned_total_min_chars: 80000", "planned_total_min_chars: 160000"))
    assert api.verify_dependencies(str(project), records)


def test_empty_preferred_session_notes_tracks_consumed_fallback(tmp_path):
    preferred = tmp_path / 'agent/memory/session_notes.md'
    preferred.parent.mkdir(parents=True)
    preferred.write_text('', encoding='utf-8')
    fallback = tmp_path / 'memory/session_notes.md'
    fallback.parent.mkdir()
    fallback.write_text('実際に読まれるメモ。', encoding='utf-8')
    from novel_agent.dependencies import snapshot_dependencies, verify_dependencies
    records = snapshot_dependencies(str(tmp_path), [{'kind': 'projection', 'selector': 'runtime_policy'}])
    assert records[0]['source_paths'] == ['agent/state_schema_novel.yaml', 'agent/memory/global_notes.md', 'memory/session_notes.md', '05_chapter_outline.md']
    assert 'value' not in records[0]
    fallback.write_text('後から変えたメモ。', encoding='utf-8')
    assert verify_dependencies(str(tmp_path), records)
