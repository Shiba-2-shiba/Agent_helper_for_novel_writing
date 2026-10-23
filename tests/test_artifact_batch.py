"""Batch registration must retain strict validation without per-artifact I/O."""
import json
from contextlib import contextmanager

import pytest

from novel_agent import ledgers
from novel_agent.errors import DataCorruptionError, UserFacingError


def items_for(root):
    items = []
    for name in ('scenes/1-1/draft/context.md', 'scenes/1-2/draft/context.md'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding='utf-8')
        items.append(dict(artifact_id='same-legacy-id', artifact_type='context', path=str(path), dependencies=[]))
    return items


def count_io(monkeypatch, root):
    counts = dict(read=0, write=0, lock=0)
    original_read, original_write, original_lock = ledgers.read_json, ledgers.write_json_file, ledgers.project_lock
    ledger_path = ledgers.artifact_ledger_path(str(root))
    def read(path, *args, **kwargs):
        if path == ledger_path:
            counts['read'] += 1
        return original_read(path, *args, **kwargs)
    def write(path, *args, **kwargs):
        if path == ledger_path:
            counts['write'] += 1
        return original_write(path, *args, **kwargs)
    @contextmanager
    def lock(*args, **kwargs):
        counts['lock'] += 1
        with original_lock(*args, **kwargs):
            yield
    monkeypatch.setattr(ledgers, 'read_json', read)
    monkeypatch.setattr(ledgers, 'write_json_file', write)
    monkeypatch.setattr(ledgers, 'project_lock', lock)
    return counts


def test_batch_reads_writes_and_locks_once_with_distinct_path_ids(tmp_path, monkeypatch):
    items = items_for(tmp_path)
    counts = count_io(monkeypatch, tmp_path)
    payload = ledgers.register_artifacts(str(tmp_path), items)
    assert counts == dict(read=1, write=1, lock=1)
    assert [a['id'] for a in payload['artifacts']] == [
        'artifact:scenes/1-1/draft/context.md', 'artifact:scenes/1-2/draft/context.md']
    assert json.loads((tmp_path / 'runtime/artifact_ledger.json').read_text()) == payload


@pytest.mark.parametrize('invalid', [dict(dependencies='invalid'), dict(dependencies=[{'kind': 'invalid'}]), dict(unexpected=True)])
def test_invalid_later_item_never_partially_writes(tmp_path, invalid):
    items = items_for(tmp_path)
    ledgers.register_artifact(str(tmp_path), **items[0])
    path = tmp_path / 'runtime/artifact_ledger.json'
    before = path.read_bytes()
    items[1].update(invalid)
    with pytest.raises((DataCorruptionError, UserFacingError, TypeError)):
        ledgers.register_artifacts(str(tmp_path), items)
    assert path.read_bytes() == before


def test_corrupt_existing_digest_is_preserved(tmp_path):
    items = items_for(tmp_path)
    ledgers.register_artifact(str(tmp_path), **items[0])
    path = tmp_path / 'runtime/artifact_ledger.json'
    payload = json.loads(path.read_text())
    payload['artifacts'][0]['dependency_digest'] = 'corrupted'
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(DataCorruptionError, match='dependency digest'):
        ledgers.register_artifacts(str(tmp_path), items)
    assert path.read_bytes() == before


def test_batch_matches_sequential_preserving_protected_source_and_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(ledgers, 'utc_now', lambda: 'stable-timestamp')
    items = items_for(tmp_path)
    ledgers.register_artifact(str(tmp_path), **items[0])
    path = tmp_path / 'runtime/artifact_ledger.json'
    initial = json.loads(path.read_text())
    initial['artifacts'][0].update(protected_user_content=True, source='user', created_at='original')
    path.write_text(json.dumps(initial))
    for item in [*items, items[0]]:
        ledgers.register_artifact(str(tmp_path), **item)
    expected = json.loads(path.read_text())
    path.write_text(json.dumps(initial))
    actual = ledgers.register_artifacts(str(tmp_path), [*items, items[0]])
    assert actual == expected
    assert actual['artifacts'][-1]['status'] == 'protected'
    assert actual['artifacts'][-1]['source'] == 'user'
    assert actual['artifacts'][-1]['created_at'] == 'original'


def test_runtime_registration_batches_with_existing_outer_lock(tmp_path, monkeypatch):
    from build_runtime_context import _register_runtime_artifacts
    items = items_for(tmp_path)
    counts = count_io(monkeypatch, tmp_path)
    with ledgers.project_lock(str(tmp_path)):
        _register_runtime_artifacts(str(tmp_path), [item['path'] for item in items], None, dependencies=[])
    assert counts == dict(read=1, write=1, lock=1)


def test_status_reads_ledger_once_per_operation_and_sees_new_custom_reports(tmp_path, monkeypatch):
    from novel_agent.scene_status import collect_project_status
    for scene in ('1-1', '1-2'):
        (tmp_path / ('scene_' + scene + '.txt')).write_text('本文')
    counts = count_io(monkeypatch, tmp_path)
    status = collect_project_status(str(tmp_path))
    assert counts['read'] == 1
    assert status['scenes']['1-1']['check_report_path'] == ''
    report = tmp_path / 'custom-check.json'
    report.write_text(json.dumps(dict(version=2, scene_id='1-1', checked_at='later', status='pass')))
    ledgers.register_artifact(str(tmp_path), artifact_id='check', artifact_type='check_report', path=str(report), dependencies=[])
    counts['read'] = 0
    status = collect_project_status(str(tmp_path))
    assert counts['read'] == 1
    assert status['scenes']['1-1']['check_report_path'] == str(report)
    assert status['scenes']['1-2']['check_report_path'] == ''
    path = tmp_path / 'runtime/artifact_ledger.json'
    payload = json.loads(path.read_text())
    payload['artifacts'][0]['dependency_digest'] = 'bad'
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(DataCorruptionError, match='dependency digest'):
        collect_project_status(str(tmp_path))
    assert path.read_bytes() == before


def test_empty_batch_reads_without_publishing(tmp_path, monkeypatch):
    counts = count_io(monkeypatch, tmp_path)
    assert ledgers.register_artifacts(str(tmp_path), []) == dict(version=1, updated_at='', artifacts=[])
    assert counts == dict(read=1, write=0, lock=1)
    assert not (tmp_path / 'runtime/artifact_ledger.json').exists()


def test_invalid_batch_does_not_create_a_new_ledger(tmp_path):
    items = items_for(tmp_path)
    items[1]['dependencies'] = [{'kind': 'not-supported'}]
    with pytest.raises(DataCorruptionError):
        ledgers.register_artifacts(str(tmp_path), items)
    assert not (tmp_path / 'runtime/artifact_ledger.json').exists()
