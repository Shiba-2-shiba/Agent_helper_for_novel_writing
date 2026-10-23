import json

import pytest

from novel_agent.approvals import approve_scene, approval_ledger_path
from novel_agent.errors import UserFacingError
from novel_agent.storage import text_content_hash


def setup_checked(tmp_path, status='pass'):
    path = tmp_path / 'scene_1-1.txt'
    path.write_text('日本語本文。')
    runtime = tmp_path / 'runtime' / 'scenes' / '1-1' / 'draft'
    runtime.mkdir(parents=True)
    (runtime / 'scene_brief_compact.md').write_text('- Scene ID: 1-1\n')
    from novel_agent.dependencies import snapshot_dependencies, dependency_digest
    inputs = snapshot_dependencies(str(tmp_path), [{'kind': 'projection', 'selector': 'check_policy', 'scene_id': '1-1'}])
    report = {'version': 2, 'scope': 'scene', 'scene_id': '1-1', 'source_path': 'scene_1-1.txt', 'source_hash': text_content_hash(str(path)), 'hash_algorithm': 'sha256-utf8-text-v1', 'check_inputs': inputs, 'check_inputs_digest': dependency_digest(inputs), 'status': status}
    report_path = runtime / 'check_report.json'
    report_path.write_text(json.dumps(report))
    return path, report_path


def test_check_then_edit_before_approve_rejected(tmp_path):
    path, _ = setup_checked(tmp_path)
    path.write_text('改稿した本文。')
    with pytest.raises(UserFacingError):
        approve_scene(str(tmp_path), '1-1')
    assert not (tmp_path / 'runtime' / 'approval_ledger.json').exists()


def test_wrong_scene_report_rejected(tmp_path):
    _, report_path = setup_checked(tmp_path)
    report = json.loads(report_path.read_text())
    report['scene_id'] = '1-2'
    report_path.write_text(json.dumps(report))
    with pytest.raises(UserFacingError):
        approve_scene(str(tmp_path), '1-1')


def test_legacy_report_requires_recheck_before_new_approval(tmp_path):
    _, report_path = setup_checked(tmp_path)
    report_path.write_text('{"status": "pass"}')
    with pytest.raises(UserFacingError, match='recheck'):
        approve_scene(str(tmp_path), '1-1')


def test_warning_flag_still_required(tmp_path):
    setup_checked(tmp_path, 'warning')
    with pytest.raises(UserFacingError, match='allow-warnings'):
        approve_scene(str(tmp_path), '1-1')
    assert approve_scene(str(tmp_path), '1-1', allow_warnings=True)['status'] == 'approved'
