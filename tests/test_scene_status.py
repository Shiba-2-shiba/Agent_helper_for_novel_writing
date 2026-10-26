import json

import pytest

from novel_agent.errors import ConflictError, DataCorruptionError
from novel_agent.storage import project_lock, text_content_hash
from novel_agent.scene_status import (
    collect_project_status,
    derive_scene_status,
    sync_status_projections,
    _sync_status_projections_locked,
)


def make_project(tmp_path, scene_ids=('1-1', '1-2', '1-3')):
    project = tmp_path / '物語'
    project.mkdir()
    outline = ['# Outline', 'User introduction stays.', '']
    chapters = sorted({int(scene_id.split('-')[0]) for scene_id in scene_ids})
    for chapter in chapters:
        outline.extend([
            '## 第{}章 Chapter Card'.format(chapter),
            '### Scene Ledger',
            '| scene_id | purpose | status | user_note |',
            '|---|---|---|---|',
        ])
        for scene_id in scene_ids:
            if int(scene_id.split('-')[0]) == chapter:
                outline.append('| {} | 手書きの目的 | planned | 残すメモ |'.format(scene_id))
        outline.extend(['', '### Notes', 'User chapter notes stay.', ''])
    (project / '05_chapter_outline.md').write_text('\n'.join(outline), encoding='utf-8')
    (project / 'state_schema_novel.yaml').write_text(
        '# User state comment\nprogress:\n'
        '  completed_scene_count: 99 # Keep completion comment\n'
        '  user_counter: 19 # Keep unknown comment\n'
        '  planned_scene_count: {}\n'
        'custom_section:\n  note: "do not change"\n'.format(len(scene_ids)),
        encoding='utf-8',
    )
    return project


def write_scene(project, scene_id, text='日本語の本文。'):
    path = project / ('scene_{}.txt'.format(scene_id))
    path.write_text(text, encoding='utf-8')
    return path


def write_report(project, reference_id, *, status='pass', blocking_issues=None, warnings=None, **updates):
    from novel_agent.dependencies import dependency_digest, snapshot_dependencies
    scene_id = reference_id
    path = project / ('scene_{}.txt'.format(scene_id))
    inputs = snapshot_dependencies(str(project), [
        {'kind': 'projection', 'selector': 'check_policy', 'scene_id': scene_id},
    ])
    report = {
        'version': 2,
        'scope': 'scene',
        'scene_id': scene_id,
        'source_path': path.name,
        'source_hash': text_content_hash(str(path)),
        'hash_algorithm': 'sha256-utf8-text-v1',
        'check_inputs': inputs,
        'check_inputs_digest': dependency_digest(inputs),
        'target_file': str(path),
        'status': status,
        'actual_chars': len(path.read_text(encoding='utf-8')),
        'needs_expand': False,
        'within_max': True,
        'blocking_issues': blocking_issues or [],
        'warnings': warnings or [],
    }
    report.update(updates)
    report_path = project / 'runtime' / 'scenes' / scene_id / 'draft' / 'check_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    from helpers.keyframe_fixtures import bind_disabled_check_fixture
    bind_disabled_check_fixture(project, report_path.parent, report, scene_id=scene_id)
    report_path.write_text(json.dumps(report), encoding='utf-8')
    (report_path.parent / 'scene_brief_compact.md').write_text('- Scene ID: {}\n'.format(scene_id), encoding='utf-8')
    return report, report_path


def assert_projection(project, scene_id, status, completed_count):
    story = json.loads((project / 'runtime' / 'story_state.json').read_text(encoding='utf-8'))
    assert story['scenes'][scene_id]['status'] == status
    assert story['progress']['completed_scene_count'] == completed_count
    outline = (project / '05_chapter_outline.md').read_text(encoding='utf-8')
    assert '| {} | 手書きの目的 | {} | 残すメモ |'.format(scene_id, status) in outline
    yaml = (project / 'state_schema_novel.yaml').read_text(encoding='utf-8')
    assert '  completed_scene_count: {}'.format(completed_count) in yaml


@pytest.mark.parametrize('text_exists,report,current,expected', [
    (False, None, False, 'planned'),
    (False, {'status': 'pass'}, True, 'planned'),
    (True, None, False, 'drafted'),
    (True, {'status': 'pass'}, False, 'drafted'),
    (True, {'status': 'fail'}, False, 'drafted'),
    (True, {'status': 'fail'}, True, 'needs_repair'),
    (True, {'status': 'warning'}, True, 'drafted'),
    (True, {'status': 'pass'}, True, 'completed'),
])
def test_scene_status_table(text_exists, report, current, expected):
    assert derive_scene_status(text_exists=text_exists, report=report, check_current=current) == expected


def test_dependency_fail_is_never_completed(tmp_path):
    project = make_project(tmp_path)
    write_scene(project, '1-1')
    write_report(project, '1-1', status='fail', blocking_issues=[{'type': 'dependency_missing'}])
    snapshot = collect_project_status(str(project))
    assert snapshot['progress']['checked_scene_count'] == 1
    sync_status_projections(str(project), snapshot)
    assert_projection(project, '1-1', 'needs_repair', 0)


def test_warning_is_drafted_even_when_length_passes(tmp_path):
    project = make_project(tmp_path)
    write_scene(project, '1-1')
    write_report(project, '1-1', status='warning', warnings=[{'type': 'style'}])
    snapshot = collect_project_status(str(project))
    sync_status_projections(str(project), snapshot)
    assert_projection(project, '1-1', 'drafted', 0)


def test_file_count_is_not_completed_count(tmp_path):
    project = make_project(tmp_path)
    for scene_id in ('1-1', '1-2', '1-3'):
        write_scene(project, scene_id)
    write_report(project, '1-1')
    snapshot = collect_project_status(str(project))
    assert snapshot['progress'] == {
        'written_scene_count': 3,
        'checked_scene_count': 1,
        'completed_scene_count': 1,
        'approved_scene_count': 0,
        'total_chars_written': 3 * len('日本語の本文。'),
        'last_checked_scene': '1-1',
        'last_completed_scene': '1-1',
    }
    assert snapshot['scenes']['1-2']['status'] == 'drafted'


def test_edit_invalidates_completion(tmp_path):
    project = make_project(tmp_path)
    path = write_scene(project, '1-1')
    write_report(project, '1-1')
    sync_status_projections(str(project), collect_project_status(str(project)))
    path.write_text('改稿した本文。', encoding='utf-8')
    snapshot = collect_project_status(str(project))
    assert snapshot['progress']['checked_scene_count'] == 0
    assert snapshot['progress']['last_completed_scene'] == ''
    assert snapshot['scenes']['1-1']['actual_chars'] == len('改稿した本文。')
    sync_status_projections(str(project), snapshot)
    assert_projection(project, '1-1', 'drafted', 0)


def test_last_completed_does_not_advance_on_fail(tmp_path):
    project = make_project(tmp_path, ('2-1', '10-1', '11-1'))
    for scene_id in ('2-1', '10-1', '11-1'):
        write_scene(project, scene_id)
        write_report(project, scene_id, status='fail' if scene_id == '11-1' else 'pass')
    snapshot = collect_project_status(str(project))
    assert snapshot['progress']['last_checked_scene'] == '11-1'
    assert snapshot['progress']['last_completed_scene'] == '10-1'


def test_concurrent_projection_is_serialized_or_conflict(tmp_path):
    project = make_project(tmp_path)
    snapshot = collect_project_status(str(project))
    state = project / 'runtime' / 'story_state.json'
    with project_lock(str(project)):
        with pytest.raises(ConflictError):
            sync_status_projections(str(project), snapshot)
        assert not state.exists()
        _sync_status_projections_locked(str(project), snapshot)
        assert state.exists()
    sync_status_projections(str(project), snapshot)


def test_projection_rebuild_preserves_user_notes(tmp_path):
    project = make_project(tmp_path)
    write_scene(project, '1-1')
    write_report(project, '1-1')
    state = project / 'runtime' / 'story_state.json'
    state.write_text(json.dumps({
        'version': 1,
        'progress': {'custom_progress': 'unchanged'},
        'scenes': {'1-1': {'author_note': '手書きメモ'}},
        'characters': {'hero': {'secret': 'kept'}},
        'threads': {'thread-1': {'note': 'kept'}},
        'custom_root': {'anything': [1, 2]},
    }), encoding='utf-8')
    sync_status_projections(str(project), collect_project_status(str(project)))
    rebuilt = json.loads(state.read_text(encoding='utf-8'))
    assert rebuilt['scenes']['1-1']['author_note'] == '手書きメモ'
    assert rebuilt['progress']['custom_progress'] == 'unchanged'
    assert rebuilt['characters'] == {'hero': {'secret': 'kept'}}
    assert rebuilt['threads'] == {'thread-1': {'note': 'kept'}}
    assert rebuilt['custom_root'] == {'anything': [1, 2]}
    yaml = (project / 'state_schema_novel.yaml').read_text(encoding='utf-8')
    assert '# User state comment' in yaml
    assert 'completed_scene_count: 1 # Keep completion comment' in yaml
    assert 'user_counter: 19 # Keep unknown comment' in yaml
    assert 'custom_section:\n  note: "do not change"' in yaml
    outline = (project / '05_chapter_outline.md').read_text(encoding='utf-8')
    assert 'User introduction stays.' in outline
    assert 'User chapter notes stay.' in outline
    assert outline.count('残すメモ') == 3


def test_approved_warning_has_separate_counts(tmp_path):
    from novel_agent.approvals import approve_scene
    project = make_project(tmp_path)
    write_scene(project, '1-1')
    write_report(project, '1-1', status='warning', warnings=[{'type': 'style'}])
    approve_scene(str(project), '1-1', allow_warnings=True)
    snapshot = collect_project_status(str(project))
    assert snapshot['progress']['completed_scene_count'] == 0
    assert snapshot['progress']['approved_scene_count'] == 1
    assert snapshot['scenes']['1-1']['status'] == 'drafted'
    assert snapshot['scenes']['1-1']['approval_status'] == 'approved'


@pytest.mark.parametrize('updates', [
    {'scene_id': '2-1'},
    {'scope': 'standalone'},
    {'version': 1},
])
def test_unbound_reports_cannot_complete_scene(tmp_path, updates):
    project = make_project(tmp_path)
    write_scene(project, '1-1')
    write_report(project, '1-1', **updates)
    snapshot = collect_project_status(str(project))
    assert snapshot['scenes']['1-1']['status'] == 'drafted'
    assert snapshot['progress']['checked_scene_count'] == 0


def test_deleted_text_resets_existing_projection(tmp_path):
    project = make_project(tmp_path)
    path = write_scene(project, '1-1')
    write_report(project, '1-1')
    sync_status_projections(str(project), collect_project_status(str(project)))
    path.unlink()
    snapshot = collect_project_status(str(project))
    assert snapshot['scenes']['1-1']['status'] == 'planned'
    assert snapshot['progress']['written_scene_count'] == 0
    assert snapshot['progress']['completed_scene_count'] == 0


def test_corrupt_story_state_is_not_overwritten(tmp_path):
    project = make_project(tmp_path)
    snapshot = collect_project_status(str(project))
    state = project / 'runtime' / 'story_state.json'
    state.parent.mkdir(exist_ok=True)
    state.write_text('{broken', encoding='utf-8')
    outline_before = (project / '05_chapter_outline.md').read_bytes()
    with pytest.raises(DataCorruptionError):
        sync_status_projections(str(project), snapshot)
    assert state.read_text(encoding='utf-8') == '{broken'
    assert (project / '05_chapter_outline.md').read_bytes() == outline_before


def test_projection_applies_explicit_active_scene_only(tmp_path):
    project = make_project(tmp_path)
    snapshot = collect_project_status(str(project))
    snapshot['active_scene'] = '1-2'
    sync_status_projections(str(project), snapshot)
    state = json.loads((project / 'runtime' / 'story_state.json').read_text(encoding='utf-8'))
    assert state['active_scene'] == '1-2'
    assert state['progress']['current_scene'] == '1-2'
    assert state['progress']['current_chapter'] == 1
    yaml = (project / 'state_schema_novel.yaml').read_text(encoding='utf-8')
    assert 'active_work:\n  active_chapter: 1\n  active_scene: "1-2"' in yaml
    assert '  current_scene: "1-2"' in yaml
    sync_status_projections(str(project), collect_project_status(str(project)))
    state = json.loads((project / 'runtime' / 'story_state.json').read_text(encoding='utf-8'))
    assert state['active_scene'] == '1-2'
    assert state['progress']['current_scene'] == '1-2'


def test_projection_recollects_after_text_edit_before_lock(tmp_path):
    project = make_project(tmp_path)
    path = write_scene(project, '1-1')
    write_report(project, '1-1')
    stale = collect_project_status(str(project))
    assert stale['scenes']['1-1']['status'] == 'completed'
    path.write_text('検査後に改稿された本文。', encoding='utf-8')
    stale['active_scene'] = '1-1'
    sync_status_projections(str(project), stale)
    assert_projection(project, '1-1', 'drafted', 0)
    state = json.loads((project / 'runtime' / 'story_state.json').read_text(encoding='utf-8'))
    assert state['active_scene'] == '1-1'
