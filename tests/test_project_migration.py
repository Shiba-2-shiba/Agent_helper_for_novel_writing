"""Reviewed target changes never rewrite prose or silently lose later edits."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from novel_agent.errors import ConflictError, UserFacingError
from novel_agent import project_migration as migration
from prompt_utils import load_planning_metadata


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'agent').mkdir()
    (tmp_path / 'agent/state_schema_novel.yaml').write_bytes(b'targets:\r\n  target_total_chars: 100000 # keep comment\r\n  target_length_profile: "novel_100k"\r\n  planning_gate_min_chars: 80000\r\n  planning_target_total_chars: 100000\r\n  total_chars: 100000\r\n  unknown_field: "keep me"\r\nactive_work:\r\n  planning_gate_status: "ready" # old approval\r\n')
    (tmp_path / '05_chapter_outline.md').write_text('# Outline\n- 全体目標文字数: 100000\n- 計画ゲート下限: 80000\n\n## 第1章 Chapter Card\n### Scene Ledger\n| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |\n|---|---|---|---|---|---:|---:|---:|---|---|\n| 1-1 | standard | 本文を守る |  |  | 1600 | 2000 | 2400 | - | completed |\n\n## Planning Totals\n- gate_threshold: 80000\n')
    (tmp_path / 'chapter_1').mkdir()
    (tmp_path / 'chapter_1/scene_1-1.txt').write_bytes('作者の本文\r\n変更しない。'.encode())
    (tmp_path / 'chapter_1/body.md').write_text('# 作者の章メモ\n')
    (tmp_path / 'runtime').mkdir()
    (tmp_path / 'runtime/approval_ledger.json').write_text('{"scenes":{"1-1":{"source_hash":"unchanged"}}}')
    return tmp_path


def snapshot(project):
    return {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file() and 'migrations' not in p.parts}


def plan(project, **kwargs):
    return migration.plan_target_migration(str(project), target_total_chars=200000, **kwargs)


def apply(project, payload):
    return migration.apply_target_migration(str(project), payload, expected_plan_hash=payload['plan_hash'])


def test_100k_defaults_all_become_200k(project):
    before = snapshot(project)
    payload = plan(project)
    assert payload['conflicts'] == []
    assert payload['planning']['planned_total_min_chars'] == 1600
    assert payload['planning']['shortfall_chars'] == 158400
    result = apply(project, payload)
    assert result['status'] == 'committed'
    meta = load_planning_metadata(str(project))
    assert (meta['target_total_chars'], meta['planning_target_total_chars'], meta['planning_gate_min_chars']) == (200000, 200000, 160000)
    assert meta['planning_gate_status'] == 'blocked'
    state = (project / 'agent/state_schema_novel.yaml').read_bytes()
    assert b'80000' not in state and b'100000' not in state
    assert b'# keep comment\r\n' in state and b'unknown_field: "keep me"\r\n' in state
    outline = (project / '05_chapter_outline.md').read_text()
    assert '- 全体目標文字数: 200000' in outline and '- gate_threshold: 160000' in outline
    for path in ['chapter_1/scene_1-1.txt', 'chapter_1/body.md', 'runtime/approval_ledger.json']:
        assert (project / path).read_bytes() == before[path]


def test_custom_gate_needs_explicit_policy(project):
    p = project / 'agent/state_schema_novel.yaml'
    p.write_bytes(p.read_bytes().replace(b'80000', b'70000'))
    payload = plan(project)
    assert any('custom' in conflict['reason'] for conflict in payload['conflicts'])
    with pytest.raises(ConflictError):
        apply(project, payload)
    assert plan(project, gate_policy='profile')['conflicts'] == []


def test_nondefault_gate_preserve_records_custom_policy(project):
    p = project / 'agent/state_schema_novel.yaml'
    p.write_bytes(p.read_bytes().replace(b'80000', b'70000'))
    payload = plan(project, gate_policy='preserve')
    apply(project, payload)
    assert load_planning_metadata(str(project))['planning_gate_min_chars'] == 70000
    assert 'planning_gate_policy: "custom"' in p.read_text()
    assert '- gate_threshold: 70000' in (project / '05_chapter_outline.md').read_text()


def test_dry_run_preserves_original_bytes(project):
    before = snapshot(project)
    payload = plan(project)
    assert snapshot(project) == before
    assert payload['before_hashes'] and payload['backup_paths']
    assert all(change['diff'] for change in payload['changes'])
    assert (project / 'runtime/migrations' / payload['migration_id'] / 'plan.json').is_file()


def test_post_review_edit_blocks_apply(project):
    payload = plan(project)
    p = project / '05_chapter_outline.md'
    p.write_text(p.read_text() + '\n作者の追記\n')
    before = snapshot(project)
    with pytest.raises(ConflictError):
        apply(project, payload)
    assert snapshot(project) == before


def test_repeat_apply_is_noop(project):
    payload = plan(project)
    apply(project, payload)
    before = snapshot(project)
    assert apply(project, payload)['status'] == 'noop'
    assert snapshot(project) == before
    again = plan(project)
    assert again['changes'] == []


def test_plan_hash_mismatch_blocks_apply(project):
    payload = plan(project)
    with pytest.raises(ConflictError):
        migration.apply_target_migration(str(project), payload, expected_plan_hash='wrong')


def test_mid_apply_failure_leaves_backups_and_recoverable_journal(project, monkeypatch):
    payload = plan(project)
    before = snapshot(project)
    original = migration.atomic_write_text
    count = [0]
    def fail_second(path, text):
        if str(path) in [str(project / c['path']) for c in payload['changes']]:
            count[0] += 1
            if count[0] == 2:
                raise OSError('simulated interruption')
        return original(path, text)
    with monkeypatch.context() as patch:
        patch.setattr(migration, 'atomic_write_text', fail_second)
        with pytest.raises(UserFacingError, match='rollback|resume|interrupted'):
            apply(project, payload)
    directory = project / 'runtime/migrations' / payload['migration_id']
    assert json.loads((directory / 'journal.json').read_text())['status'] == 'prepared'
    assert all((project / p).exists() for p in payload['backup_paths'].values())
    assert migration.rollback_target_migration(str(project), payload['migration_id'])['status'] == 'rolled_back'
    assert snapshot(project) == before


def test_interrupted_apply_can_resume(project, monkeypatch):
    payload = plan(project)
    original = migration.atomic_write_text
    with monkeypatch.context() as patch:
        def fail_outline(path, text):
            if str(path) == str(project / '05_chapter_outline.md'):
                raise OSError('interrupted')
            original(path, text)
        patch.setattr(migration, 'atomic_write_text', fail_outline)
        with pytest.raises(UserFacingError):
            apply(project, payload)
    assert apply(project, payload)['status'] == 'committed'


def test_rollback_refuses_later_user_edits(project):
    payload = plan(project)
    apply(project, payload)
    p = project / 'agent/state_schema_novel.yaml'
    p.write_text(p.read_text() + '\n# later edit\n')
    before = snapshot(project)
    with pytest.raises(ConflictError):
        migration.rollback_target_migration(str(project), payload['migration_id'])
    assert snapshot(project) == before


def test_legacy_outline_only_preserved(project):
    (project / '05_chapter_outline.md').rename(project / '05_chapter_outline_100k.md')
    apply(project, plan(project))
    assert not (project / '05_chapter_outline.md').exists()
    assert '- 全体目標文字数: 200000' in (project / '05_chapter_outline_100k.md').read_text()


@pytest.mark.parametrize('extra', ['\n- 全体目標文字数: 100000\n', '\n- 計画ゲート下限: 8万字くらいを考える\n'])
def test_ambiguous_outline_label_is_conflict(project, extra):
    p = project / '05_chapter_outline.md'
    p.write_text(p.read_text() + extra)
    assert plan(project)['conflicts']


def test_new_canonical_outline_after_review_is_conflict(project):
    (project / '05_chapter_outline.md').rename(project / '05_chapter_outline_100k.md')
    payload = plan(project)
    (project / '05_chapter_outline.md').write_text('# new canonical\n')
    with pytest.raises(ConflictError):
        apply(project, payload)


def test_symlink_outside_project_rejected(project, tmp_path_factory):
    external = tmp_path_factory.mktemp('elsewhere') / 'outline.md'
    external.write_text('- 全体目標文字数: 100000\n')
    (project / '05_chapter_outline.md').unlink()
    (project / '05_chapter_outline.md').symlink_to(external)
    with pytest.raises(UserFacingError):
        plan(project)


def test_custom_outline_gate_also_needs_explicit_policy(project):
    p = project / '05_chapter_outline.md'
    p.write_text(p.read_text().replace('80000', '75000'))
    assert plan(project)['conflicts']
    assert plan(project, gate_policy='profile')['conflicts'] == []
    assert plan(project, gate_policy='preserve')['conflicts']


def test_old_legacy_total_does_not_excuse_custom_current_gate(project):
    p = project / 'agent/state_schema_novel.yaml'
    p.write_text(p.read_text().replace('total_chars: 100000\n', 'total_chars: 50000\n').replace('planning_gate_min_chars: 80000', 'planning_gate_min_chars: 40000'))
    assert plan(project)['conflicts']


def test_rollback_retry_after_interruption_is_safe(project, monkeypatch):
    payload = plan(project)
    before = snapshot(project)
    apply(project, payload)
    original = migration.atomic_write_text
    with monkeypatch.context() as patch:
        def fail_outline(path, text):
            if str(path) == str(project / '05_chapter_outline.md'):
                raise OSError('interrupted rollback')
            original(path, text)
        patch.setattr(migration, 'atomic_write_text', fail_outline)
        with pytest.raises(UserFacingError, match='rollback'):
            migration.rollback_target_migration(str(project), payload['migration_id'])
    assert migration.rollback_target_migration(str(project), payload['migration_id'])['status'] == 'rolled_back'
    assert snapshot(project) == before


def test_cli_review_apply_rollback_roundtrip(project):
    import subprocess
    script = Path(__file__).resolve().parents[1] / 'scripts/migrate_project_state.py'
    base = [sys.executable, str(script), '--project', str(project)]
    before = snapshot(project)
    dry = subprocess.run(base + ['--target-total-chars', '200000', '--dry-run'], capture_output=True, text=True)
    assert dry.returncode == 0, dry.stdout + dry.stderr
    payload = json.loads(dry.stdout)
    applied = subprocess.run(base + ['--apply-plan', payload['plan_path'], '--expected-plan-hash', payload['plan_hash']], capture_output=True, text=True)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert json.loads(applied.stdout)['status'] == 'committed'
    reverted = subprocess.run(base + ['--rollback', payload['migration_id']], capture_output=True, text=True)
    assert reverted.returncode == 0, reverted.stdout + reverted.stderr
    assert snapshot(project) == before


def test_runtime_symlink_cannot_write_outside_project(project, tmp_path_factory):
    import shutil
    shutil.rmtree(project / 'runtime')
    external = tmp_path_factory.mktemp('external-runtime')
    (project / 'runtime').symlink_to(external, target_is_directory=True)
    with pytest.raises(UserFacingError):
        plan(project)
    assert list(external.iterdir()) == []


def test_edit_after_journal_preparation_is_not_overwritten(project, monkeypatch):
    payload = plan(project)
    source = project / 'agent/state_schema_novel.yaml'
    original = migration.atomic_write_json
    altered = source.read_bytes() + b'# concurrent author edit\r\n'
    triggered = [False]
    def edit_after_prepare(path, data):
        original(path, data)
        if not triggered[0] and str(path).endswith('journal.json') and data.get('status') == 'prepared':
            source.write_bytes(altered)
            triggered[0] = True
    monkeypatch.setattr(migration, 'atomic_write_json', edit_after_prepare)
    with pytest.raises(UserFacingError, match='interrupted|changed'):
        apply(project, payload)
    assert source.read_bytes() == altered


def test_malformed_journal_blocks_before_source_write(project):
    payload = plan(project)
    directory = project / 'runtime/migrations' / payload['migration_id']
    (directory / 'journal.json').write_text(json.dumps({'version': 1, 'status': 'prepared', 'plan_hash': payload['plan_hash'], 'applied': {}}))
    before = snapshot(project)
    with pytest.raises(UserFacingError, match='^invalid migration journal'):
        apply(project, payload)
    assert snapshot(project) == before
