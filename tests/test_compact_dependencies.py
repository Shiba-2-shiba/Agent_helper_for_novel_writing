"""Bounded provenance retains source checks without becoming writer input."""
import copy
import json

import pytest

from novel_agent import dependencies as api
from novel_agent.ledgers import register_artifact
from novel_agent.runtime_paths import require_runtime_current, write_runtime_manifest
from novel_agent.errors import UserFacingError
from test_dependency_tracking import project, write
from test_dialogue_context import cards, config, prepare_project, runtime_project


def test_new_projection_snapshot_omits_source_values_but_detects_changes(project):
    secret = "FUTURE_OUTLINE_SECRET_729"
    path = project / "05_chapter_outline.md"
    write(path, path.read_text() + "\n" + secret + "あ" * 20000)
    records = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "runtime_policy", "scene_id": "1-2"}])
    encoded = json.dumps(records, ensure_ascii=False)
    assert secret not in encoded
    assert len(encoded) < 1500
    assert api.verify_dependencies(str(project), records) == []
    write(path, path.read_text() + "changed original")
    assert api.verify_dependencies(str(project), records)


def test_new_artifact_edges_do_not_duplicate_transitive_evidence(project):
    source = project / "source.md"
    write(source, "原資料" * 20000)
    inputs = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "runtime_policy", "scene_id": "1-2"}])
    for index in range(12):
        path = project / "runtime" / ("layer{}.md".format(index))
        write(path, "derived {}".format(index))
        register_artifact(str(project), artifact_id="test", artifact_type="test", path=str(path), dependencies=inputs)
        inputs = api.snapshot_dependencies(str(project), [{"kind": "artifact", "path": str(path)}])
    assert len(json.dumps(inputs)) < 1000
    assert "dependencies" not in inputs[0]
    assert api.verify_dependencies(str(project), inputs) == []
    notes = project / "agent/memory/global_notes.md"
    write(notes, notes.read_text() + "\n- 禁止: 追加語")
    assert api.verify_dependencies(str(project), inputs)


def test_manifest_does_not_publish_future_values_even_for_legacy_inputs(project):
    path = project / "05_chapter_outline.md"
    write(path, path.read_text() + "\nFUTURE_MANIFEST_SECRET")
    # Exercise the compatibility publication boundary with a historical record.
    value = api._projection(str(project), "runtime_policy", "1-2")
    legacy = [{"kind": "projection", "path": ".", "selector": "runtime_policy", "scene_id": "1-2",
               "value": value, "source_paths": value["source_paths"], "projection_hash": api._digest(value)}]
    runtime = project / "runtime/scenes/1-2/draft"
    runtime.mkdir(parents=True)
    payload = write_runtime_manifest(str(project), str(runtime), scene_id="1-2", mode="draft", files=[], inputs=legacy)
    assert "FUTURE_MANIFEST_SECRET" not in json.dumps(payload, ensure_ascii=False)
    require_runtime_current(str(project), str(runtime))
    write(path, path.read_text() + "changed")
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))


@pytest.mark.parametrize("selector", ["check_policy", "runtime_policy"])
def test_unselected_voice_edit_does_not_invalidate_scene(project, selector):
    config(project, cards())
    records = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": selector, "scene_id": "1-2"}])
    payload = cards()
    payload["characters"]["future"]["response_goal"] = "unrelated changed"
    payload["scenes"]["9-9"] = {"participants": ["future"]}
    config(project, payload)
    assert api.verify_dependencies(str(project), records) == []


@pytest.mark.parametrize("mutation", ["selected", "delete", "participants", "pov", "file_missing"])
def test_relevant_voice_changes_invalidate_scene(project, mutation):
    config(project, cards())
    records = api.snapshot_dependencies(str(project), [{"kind": "projection", "selector": "check_policy", "scene_id": "1-2"}])
    payload = cards()
    if mutation == "selected":
        payload["characters"]["a"]["rhythm"] = "changed"
    elif mutation == "delete":
        del payload["characters"]["b"]
    elif mutation == "participants":
        payload["scenes"]["1-2"]["participants"] = ["a"]
    elif mutation == "pov":
        payload["scenes"]["1-2"]["pov_character_id"] = "b"
    else:
        (project / "dialogue_voice.json").unlink()
    if mutation != "file_missing":
        config(project, payload)
    assert api.verify_dependencies(str(project), records)


def test_runtime_cli_selected_voice_is_guarded_but_unselected_voice_is_not(tmp_path):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project, "--participant", "future", "--pov-character", "future")
    payload = cards()
    payload["scenes"]["2-3"] = payload["scenes"].pop("1-2")
    payload["characters"]["b"]["word_choice"] = "unused by CLI"
    config(project, payload)
    require_runtime_current(str(project), str(runtime))
    payload["characters"]["future"]["response_goal"] = "selected changed"
    config(project, payload)
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))


def test_legacy_projection_keeps_original_whole_voice_semantics(project):
    config(project, cards())
    value = api._projection(str(project), "runtime_policy", "1-2")
    legacy = [{"kind": "projection", "path": ".", "selector": "runtime_policy", "scene_id": "1-2",
               "value": value, "source_paths": value["source_paths"], "projection_hash": api._digest(value)}]
    original = copy.deepcopy(legacy)
    assert api.verify_dependencies(str(project), legacy) == []
    payload = cards()
    payload["characters"]["future"]["rhythm"] = "unrelated but legacy binds whole file"
    config(project, payload)
    assert api.verify_dependencies(str(project), legacy)
    assert legacy == original


def test_check_policy_value_and_guard_are_captured_together(project):
    assert hasattr(api, "snapshot_check_policy"), "compact guards need an atomic value/guard capture API"
    guard, value = api.snapshot_check_policy(str(project), "1-2")
    assert value["length_band"]["min"] == 1600
    assert "value" not in guard
    assert api.verify_dependencies(str(project), [guard]) == []


@pytest.mark.parametrize("mutation", ["mapping", "delete_mapping"])
def test_cli_override_still_binds_the_scene_configuration(tmp_path, mutation):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project, "--participant", "future", "--pov-character", "future")
    payload = cards()
    payload["scenes"]["2-3"] = payload["scenes"].pop("1-2")
    if mutation == "mapping":
        payload["scenes"]["2-3"]["participants"] = ["a"]
    else:
        del payload["scenes"]["2-3"]
    config(project, payload)
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))


def test_selection_change_during_check_is_not_blessed(tmp_path, monkeypatch):
    import check_scene_output as checker
    import sys
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    target = project / 'chapter_2_scene_3.txt'
    target.write_text('彼は決めた。\n', encoding='utf-8')
    original = checker.snapshot_check_policy
    def mutate_after_policy(*args, **kwargs):
        result = original(*args, **kwargs)
        path = runtime / 'context_selection.json'
        payload = json.loads(path.read_text())
        payload['dialogue']['participants'] = ['future']
        path.write_text(json.dumps(payload))
        return result
    monkeypatch.setattr(checker, 'snapshot_check_policy', mutate_after_policy)
    monkeypatch.setattr(sys, 'argv', ['check_scene_output.py', '--project', str(project), '--text', str(target)])
    with pytest.raises(UserFacingError, match='stale|changed'):
        checker.main()
    assert not (runtime / 'check_report.json').exists()


def test_regenerated_artifact_compacts_provided_legacy_guards_without_resnapshot(project):
    value = api._projection(str(project), 'runtime_policy', '1-2')
    legacy = [{'kind': 'projection', 'path': '.', 'selector': 'runtime_policy', 'scene_id': '1-2',
               'value': value, 'source_paths': value['source_paths'], 'projection_hash': api._digest(value)}]
    path = project / 'runtime/derived.md'
    write(path, 'derived')
    artifact = register_artifact(str(project), artifact_id='test', artifact_type='test', path=str(path), dependencies=legacy)
    assert 'value' not in artifact['dependencies'][0]
    assert artifact['dependencies'][0]['projection_version'] == 1
    assert api.verify_dependencies(str(project), artifact['dependencies']) == []


def test_downstream_runtime_binds_source_approval_effective_cli_voices(tmp_path):
    from test_dialogue_context import memory_source_project
    project, _ = memory_source_project(tmp_path)
    runtime = prepare_project(project, '--participant', 'future', '--pov-character', 'future')
    require_runtime_current(str(project), str(runtime))
    payload = json.loads((project / 'dialogue_voice.json').read_text())
    payload['characters']['a']['rhythm'] = 'source approval selected voice changed'
    config(project, payload)
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


def test_downstream_runtime_preserves_legacy_approval_broad_voice_binding(tmp_path):
    from test_dialogue_context import memory_source_project
    project, _ = memory_source_project(tmp_path)
    approval_path = project / 'runtime/approval_ledger.json'
    ledger = json.loads(approval_path.read_text())
    source = ledger['scenes']['2-1']
    value = api._projection(str(project), 'check_policy', '2-1')
    source['check_inputs'][0] = {'kind': 'projection', 'path': '.', 'selector': 'check_policy', 'scene_id': '2-1',
                                'value': value, 'source_paths': value['source_paths'], 'projection_hash': api._digest(value)}
    source['check_inputs_digest'] = api.dependency_digest(source['check_inputs'])
    approval_path.write_text(json.dumps(ledger))
    runtime = prepare_project(project, '--participant', 'future', '--pov-character', 'future')
    require_runtime_current(str(project), str(runtime))
    payload = json.loads((project / 'dialogue_voice.json').read_text())
    payload['characters']['b']['word_choice'] = 'legacy binds even an unrelated card'
    config(project, payload)
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


@pytest.mark.parametrize('field,value', [('guard_version', True), ('guard_version', 3), ('projection_version', True), ('projection_version', 3)])
def test_unsupported_compact_guard_versions_fail_closed(project, field, value):
    records = api.snapshot_dependencies(str(project), [{'kind': 'projection', 'selector': 'runtime_policy', 'scene_id': '1-2'}])
    records[0][field] = value
    assert api.verify_dependencies(str(project), records)


@pytest.mark.parametrize('field,value', [('guard_version', 3), ('guard_version', True), ('projection_version', 3), ('projection_version', True)])
def test_manifest_compaction_cannot_launder_unsupported_versions(project, field, value):
    from novel_agent.errors import DataCorruptionError
    records = api.snapshot_dependencies(str(project), [{'kind': 'projection', 'selector': 'runtime_policy', 'scene_id': '1-2'}])
    records[0][field] = value
    assert api.verify_dependencies(str(project), records)
    runtime = project / 'runtime/scenes/1-2/draft'
    runtime.mkdir(parents=True)
    with pytest.raises((UserFacingError, DataCorruptionError), match='version'):
        write_runtime_manifest(str(project), str(runtime), scene_id='1-2', mode='draft', files=[], inputs=records)
    assert not (runtime / 'runtime_manifest.json').exists()


@pytest.mark.parametrize('embedded_digest', [False, True])
def test_distinct_json_fallback_artifacts_keep_digest_inputs_alive(project, embedded_digest):
    specs, expected = [], {}
    for index in range(12):
        source = project / ('source{}.md'.format(index))
        write(source, 'unique source {}'.format(index))
        inputs = api.snapshot_dependencies(str(project), [{'kind': 'file', 'path': str(source)}])
        digest = api.dependency_digest(inputs)
        artifact = project / 'runtime' / ('fallback{}.json'.format(index))
        payload = {'inputs': inputs}
        if embedded_digest:
            payload['inputs_digest'] = digest
        write(artifact, json.dumps(payload))
        specs.append({'kind': 'artifact', 'path': str(artifact)})
        expected[str(artifact.relative_to(project))] = digest
    records = api.snapshot_dependencies(str(project), specs)
    assert {record['path']: record['dependency_digest'] for record in records} == expected
    assert api.verify_dependencies(str(project), records) == []


def test_manifest_compaction_does_not_normalize_noncanonical_legacy_versions(project):
    value = api._projection(str(project), 'runtime_policy', '1-2')
    legacy = {'kind': 'projection', 'path': '.', 'selector': 'runtime_policy', 'scene_id': '1-2',
              'value': value, 'source_paths': value['source_paths'], 'projection_hash': api._digest(value)}
    for extra in ({'guard_version': 1}, {'projection_version': 1}):
        record = dict(legacy, **extra)
        assert api.verify_dependencies(str(project), [record])
        with pytest.raises(UserFacingError, match='version'):
            api.compact_dependencies([record])
