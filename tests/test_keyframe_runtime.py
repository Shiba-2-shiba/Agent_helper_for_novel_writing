"""Versioned prepare inputs and untrusted external proposal provenance."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from novel_agent.dependencies import snapshot_dependencies, verify_dependencies
from novel_agent.errors import UserFacingError
from novel_agent.runtime_paths import require_runtime_current
from test_scripts import create_runtime_project, SCRIPTS_DIR


def project_fixture(tmp_path):
    project = Path(create_runtime_project(tmp_path, keyframing="default"))
    assert not (project / "narrative_keyframing.json").exists()
    return project


def cli(name, *args):
    return subprocess.run([sys.executable, str(Path(SCRIPTS_DIR) / name)] + list(map(str, args)), capture_output=True, text=True)


def prepare(project, *extra, mode='draft'):
    result = cli('build_runtime_context.py', '--project', project, '--chapter', 2, '--scene', '2-3', '--mode', mode, *extra)
    assert result.returncode == 0, result.stdout + result.stderr
    return project / 'runtime/scenes/2-3' / mode


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def test_prepare_without_config_is_enabled_and_pending(tmp_path):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--pov-character', 'mira')
    contract = read(runtime / 'narrative_keyframe_contract.json')
    assert contract['policy']['enabled'] is True
    assert contract['status'] == 'awaiting_keyframes' and contract['pov_character_id'] == 'mira'
    manifest = read(runtime / 'runtime_manifest.json')
    assert manifest['version'] == 1 and manifest['features'] == {'narrative_keyframing': 1}
    assert read(runtime / 'context_selection.json')['version'] == 2
    assert any(f['path'].endswith('/narrative_keyframe_contract.json') for f in manifest['files'])
    assert not (runtime / 'narrative_keyframes.json').exists()
    require_runtime_current(str(project), str(runtime))


def test_missing_pov_is_not_inferred(tmp_path):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--participant', 'mira')
    contract = read(runtime / 'narrative_keyframe_contract.json')
    assert contract['pov_character_id'] is None and contract['status'] == 'needs_pov'


def test_resume_is_inspection_only(tmp_path):
    project = project_fixture(tmp_path)
    runtime = prepare(project, mode='resume')
    assert read(runtime / 'context_selection.json')['keyframing']['status'] == 'needs_pov'
    assert 'keyfram' in (runtime / 'resume_brief.md').read_text().lower()
    require_runtime_current(str(project), str(runtime))


def test_off_override_is_not_inherited(tmp_path):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--keyframing', 'off', '--keyframing-reason', '視点を持たない外的記録。')
    assert read(runtime / 'narrative_keyframe_contract.json')['status'] == 'disabled'
    runtime = prepare(project)
    assert read(runtime / 'narrative_keyframe_contract.json')['policy']['enabled'] is True


@pytest.mark.parametrize('field', ['keyframing', 'config', 'dialogue'])
def test_v3_selection_tampering_is_stale(tmp_path, field):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--pov-character', 'mira')
    selection = read(runtime / 'context_selection.json')
    selection[field]['pov_character_id'] = 'other'
    write(runtime / 'context_selection.json', selection)
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


@pytest.mark.parametrize('mutation', ['delete', 'tamper'])
def test_contract_change_is_stale(tmp_path, mutation):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--pov-character', 'mira')
    path = runtime / 'narrative_keyframe_contract.json'
    if mutation == 'delete': path.unlink()
    else: path.write_text('{}')
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


def test_reports_do_not_stale_runtime(tmp_path):
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--pov-character', 'mira')
    selection = read(runtime / 'context_selection.json')
    for key in ['final_prompt', 'keyframe_prompt', 'expand_prompt']:
        selection[key] = {'selected': []}
    write(runtime / 'context_selection.json', selection)
    require_runtime_current(str(project), str(runtime))


def test_policy_scope_and_absence_are_tracked(tmp_path):
    project = project_fixture(tmp_path)
    path = project / 'narrative_keyframing.json'
    config = {'version': 1, 'scenes': {}}
    write(path, config)
    runtime = prepare(project, '--pov-character', 'mira')
    config['scenes']['1-1'] = {'enabled': False, 'disable_reason': '外的記録のみ。'}
    write(path, config)
    require_runtime_current(str(project), str(runtime))
    config['scenes']['2-3'] = {'enabled': False, 'disable_reason': '外的記録のみ。'}
    write(path, config)
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))
    runtime = prepare(project)
    path.unlink()
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


def test_legacy_v1_v2_projection_hashes_are_unchanged(tmp_path):
    from novel_agent.dependencies import _snapshot_one
    path = tmp_path / 'selection.json'
    write(path, {'version': 1, 'config': {}, 'memory': {}, 'dialogue': {}})
    spec = {'kind': 'projection', 'selector': 'memory_selection', 'path': 'selection.json'}
    old = [_snapshot_one(str(tmp_path), spec, legacy=True), _snapshot_one(str(tmp_path), spec)]
    new = snapshot_dependencies(str(tmp_path), [dict(spec, projection_version=3)])
    selection = read(path); selection['keyframing'] = {'enabled': True}; write(path, selection)
    assert verify_dependencies(str(tmp_path), old) == []
    assert verify_dependencies(str(tmp_path), new)
