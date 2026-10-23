import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from novel_agent.approvals import approve_scene, read_approval_ledger, validate_approval_current
from novel_agent.dependencies import snapshot_dependencies, dependency_digest
from novel_agent.errors import ConflictError, UserFacingError
from novel_agent.exports import export_manuscript
from novel_agent.health import build_health_report, run_safe_fixes
from novel_agent.ledgers import register_artifact, read_artifact_ledger
from novel_agent.storage import atomic_write_json, text_content_hash
from test_scripts import create_runtime_project, SCRIPTS_DIR
from test_approval_identity import setup_checked


def run_script(script, project, *args):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, script), '--project', str(project)] + list(args), capture_output=True, text=True)


def prepare(project):
    result = run_script('build_runtime_context.py', project, '--chapter', '2', '--scene', '2-3', '--mode', 'draft')
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('change', ['band', 'style', 'dependency'])
def test_approved_text_unchanged_but_conditions_change_blocks_export(tmp_path, change):
    project = create_runtime_project(tmp_path, outline_filename='05_chapter_outline.md')
    scene = os.path.join(project, 'chapter_2_scene_3.txt')
    with open(scene, 'w') as handle:
        handle.write('あ' * 1300)
    prepare(project)
    result = run_script('check_scene_output.py', project, '--text', scene)
    assert result.returncode == 0, result.stdout
    record = approve_scene(project, '2-3')
    original = text_content_hash(scene)
    assert export_manuscript(project)['scenes'] == ['2-3']
    if change == 'band':
        path = os.path.join(project, '05_chapter_outline.md')
        with open(path) as handle:
            text = handle.read()
        with open(path, 'w') as handle:
            handle.write(text.replace('| 1000 | 1250 | 1500 | 2-2 |', '| 1100 | 1300 | 1500 | 2-2 |'))
    else:
        path = os.path.join(project, 'agent/memory/global_notes.md' if change == 'style' else 'chapter_2_scene_2.txt')
        with open(path, 'a') as handle:
            handle.write('\n- 口調: 静かな語り\n' if change == 'style' else '遠くで鐘が鳴った。')
    assert text_content_hash(scene) == original
    assert validate_approval_current(project, record)['status'] == 'stale'
    with pytest.raises(UserFacingError, match='stale approval'):
        export_manuscript(project)
    prepare(project)
    result = run_script('check_scene_output.py', project, '--text', scene)
    assert result.returncode == 0, result.stdout
    approve_scene(project, '2-3')
    assert export_manuscript(project)['scenes'] == ['2-3']


def test_new_stale_runtime_blocks_prompt_and_health_recomputes(tmp_path):
    project = create_runtime_project(tmp_path, outline_filename='05_chapter_outline.md')
    prepare(project)
    with open(os.path.join(project, 'agent/memory/session_notes.md'), 'a') as handle:
        handle.write('\n大事な変更。')
    result = run_script('build_draft_prompt.py', project, '--scene', '2-3')
    assert result.returncode != 0 and 'stale runtime' in result.stdout
    report = build_health_report(project)
    assert any(item['type'] == 'stale_artifacts' for item in report['warnings'])


def test_standalone_check_cannot_approve_or_update_scene(tmp_path):
    project = create_runtime_project(tmp_path, outline_filename='05_chapter_outline.md')
    prepare(project)
    state_path = os.path.join(project, 'runtime/story_state.json')
    before = open(state_path, 'rb').read()
    generic = os.path.join(project, 'draft.txt')
    with open(generic, 'w') as handle:
        handle.write('あ' * 1300)
    result = run_script('check_scene_output.py', project, '--text', generic)
    assert result.returncode == 0, result.stdout
    assert open(state_path, 'rb').read() == before
    report = json.load(open(os.path.join(project, 'runtime/check_report.json')))
    assert report['scope'] == 'standalone' and report['scene_id'] is None
    with pytest.raises(UserFacingError):
        approve_scene(project, '2-3')


def test_existing_hash_bound_approval_remains_exportable(tmp_path):
    (tmp_path / 'scene_1-1.txt').write_text('旧承認の本文。')
    atomic_write_json(str(tmp_path / 'runtime/approval_ledger.json'), {'version': 1, 'scenes': {'1-1': {'status': 'approved', 'scene_path': 'scene_1-1.txt', 'content_hash': text_content_hash(str(tmp_path / 'scene_1-1.txt')), 'check_status': 'pass'}}})
    assert export_manuscript(str(tmp_path))['scenes'] == ['1-1']
    assert read_approval_ledger(str(tmp_path))['scenes']['1-1'].get('version', 1) == 1


def test_two_scene_approvals_never_lose_update(tmp_path):
    setup_checked(tmp_path)
    second = tmp_path / 'scene_1-2.txt'
    second.write_text('第二場面。')
    runtime = tmp_path / 'runtime/scenes/1-2/draft'
    runtime.mkdir(parents=True)
    (runtime / 'scene_brief_compact.md').write_text('- Scene ID: 1-2\n')
    inputs = snapshot_dependencies(str(tmp_path), [{'kind': 'projection', 'selector': 'check_policy', 'scene_id': '1-2'}])
    atomic_write_json(str(runtime / 'check_report.json'), dict(version=2, scope='scene', scene_id='1-2', source_path='scene_1-2.txt', source_hash=text_content_hash(str(second)), hash_algorithm='sha256-utf8-text-v1', check_inputs=inputs, check_inputs_digest=dependency_digest(inputs), status='pass'))
    def approve(scene):
        try:
            approve_scene(str(tmp_path), scene)
            return scene
        except ConflictError:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, ['1-1', '1-2']))
    scenes = read_approval_ledger(str(tmp_path))['scenes']
    assert set(scenes) == {result for result in results if result != 'conflict'}
    assert len(scenes) + results.count('conflict') == 2


def test_artifact_ids_distinguish_contract_and_related_pack(tmp_path):
    files = [tmp_path / 'runtime/obligation_contract.json', tmp_path / 'runtime/related_context_pack.md']
    for path in files:
        path.parent.mkdir(exist_ok=True)
        path.write_text('{}')
        register_artifact(str(tmp_path), artifact_id='old-colliding-id', artifact_type='runtime_artifact', path=str(path))
    ledger = read_artifact_ledger(str(tmp_path))
    assert len(ledger['artifacts']) == 2
    assert len({item['id'] for item in ledger['artifacts']}) == 2


def test_custom_runtime_check_updates_scene_status(tmp_path):
    import shutil
    project = create_runtime_project(tmp_path, outline_filename='05_chapter_outline.md')
    prepare(project)
    custom = os.path.join(project, 'runtime/custom-check')
    shutil.copytree(os.path.join(project, 'runtime/scenes/2-3/draft'), custom)
    scene = os.path.join(project, 'chapter_2_scene_3.txt')
    with open(scene, 'w') as handle:
        handle.write('あ' * 1300)
    result = run_script('check_scene_output.py', project, '--text', scene, '--runtime_dir', custom)
    assert result.returncode == 0, result.stdout
    state = json.load(open(os.path.join(project, 'runtime/story_state.json')))
    assert state['scenes']['2-3']['status'] == 'completed'
    assert state['progress']['completed_scene_count'] == 1


def test_corrupt_dependency_record_is_blocking_and_not_replaced(tmp_path):
    ledger = tmp_path / 'runtime/artifact_ledger.json'
    atomic_write_json(str(ledger), {'version': 1, 'artifacts': [{'id': 'broken', 'path': 'runtime/x', 'dependencies': 'not-a-list'}]})
    before = ledger.read_bytes()
    report = build_health_report(str(tmp_path))
    assert any(item['type'] == 'data_corruption' for item in report['blocking_issues'])
    run_safe_fixes(str(tmp_path))
    assert ledger.read_bytes() == before


def test_regenerating_legacy_artifact_preserves_other_colliding_path(tmp_path):
    first = tmp_path / 'runtime/contract.json'
    second = tmp_path / 'runtime/related.md'
    first.parent.mkdir()
    first.write_text('{}')
    second.write_text('関連')
    atomic_write_json(str(tmp_path / 'runtime/artifact_ledger.json'), {'version': 1, 'artifacts': [
        {'id': 'runtime:collision', 'path': 'runtime/contract.json', 'depends_on': [], 'protected_user_content': True},
        {'id': 'runtime:collision', 'path': 'runtime/related.md', 'depends_on': []},
    ]})
    register_artifact(str(tmp_path), artifact_id='runtime:collision', artifact_type='contract', path=str(first))
    artifacts = read_artifact_ledger(str(tmp_path))['artifacts']
    assert len(artifacts) == 2
    assert next(item for item in artifacts if item['path'] == 'runtime/contract.json')['protected_user_content']
    assert next(item for item in artifacts if item['path'] == 'runtime/related.md')['id'] == 'runtime:collision'


@pytest.mark.parametrize('change', ['target_add', 'target_remove', 'later_add'])
def test_resume_tracks_target_and_latest_scene_inventory(tmp_path, change):
    from novel_agent.runtime_paths import require_runtime_current
    project = create_runtime_project(tmp_path, outline_filename='05_chapter_outline.md')
    target = os.path.join(project, 'chapter_2_scene_3.txt')
    if change == 'target_remove':
        with open(target, 'w') as handle:
            handle.write('対象の本文。')
    result = run_script('build_runtime_context.py', project, '--chapter', '2', '--scene', '2-3', '--mode', 'resume')
    assert result.returncode == 0, result.stdout
    runtime = os.path.join(project, 'runtime/scenes/2-3/resume')
    require_runtime_current(project, runtime)
    if change == 'target_remove':
        os.remove(target)
    else:
        path = target if change == 'target_add' else os.path.join(project, 'chapter_3_scene_1.txt')
        with open(path, 'w') as handle:
            handle.write('新しく執筆した本文。')
    with pytest.raises(UserFacingError, match='stale runtime'):
        require_runtime_current(project, runtime)
