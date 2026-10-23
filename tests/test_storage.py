import hashlib
import json
import os

import pytest

from novel_agent.errors import ConflictError, DataCorruptionError
from novel_agent.storage import atomic_write_json, project_lock, read_json, text_content_hash


def test_missing_and_corrupt_are_distinct(tmp_path):
    path = tmp_path / 'ledger.json'
    assert read_json(str(path), default_factory=dict) == {}
    for text in ('{broken', '[]'):
        path.write_text(text, encoding='utf-8')
        with pytest.raises(DataCorruptionError):
            read_json(str(path), default_factory=dict)
        assert path.read_text(encoding='utf-8') == text


def test_replace_failure_preserves_original(tmp_path, monkeypatch):
    path = tmp_path / 'ledger.json'
    path.write_text('{"old": true}', encoding='utf-8')
    def fail(*args):
        raise OSError('interrupted replace')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError):
        atomic_write_json(str(path), {'new': True})
    assert json.loads(path.read_text()) == {'old': True}
    assert list(tmp_path.iterdir()) == [path]


def test_text_hash_legacy_compatibility(tmp_path):
    from novel_agent.ledgers import file_content_hash
    for ending in ('\n', '\r\n'):
        path = tmp_path / '日本語本文.txt'
        path.write_bytes(('日本語' + ending + '本文').encode('utf-8'))
        assert text_content_hash(str(path)) == file_content_hash(str(path))
        assert text_content_hash(str(path)) == hashlib.sha256('日本語\n本文'.encode('utf-8')).hexdigest()


def test_lock_rejects_second_writer(tmp_path):
    with project_lock(str(tmp_path)):
        with pytest.raises(ConflictError):
            with project_lock(str(tmp_path)):
                pass
    with project_lock(str(tmp_path)):
        pass


def test_corrupt_health_is_blocking_and_safe_fix_preserves_bytes(tmp_path):
    from novel_agent.health import build_health_report, run_safe_fixes
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    path = runtime / 'story_state.json'
    path.write_text('{broken', encoding='utf-8')
    report = build_health_report(str(tmp_path))
    assert any(i['type'] == 'data_corruption' and str(path) in i['message'] for i in report['blocking_issues'])
    run_safe_fixes(str(tmp_path))
    assert path.read_text() == '{broken'


def test_nested_corrupt_quality_budget_never_erased(tmp_path):
    from novel_agent.ledgers import update_quality_budget_from_check
    from novel_agent.health import build_health_report, run_safe_fixes
    ledger = tmp_path / 'runtime/quality_budget_ledger.json'
    ledger.parent.mkdir()
    ledger.write_text('{"version":1,"scenes":{"1-1":["original-malformed-record-DO-NOT-ERASE"]}}')
    before = ledger.read_bytes()
    with pytest.raises(DataCorruptionError):
        update_quality_budget_from_check(str(tmp_path), {'canonical_id': '1-1'}, {'actual_chars': 1000})
    assert ledger.read_bytes() == before
    assert any(issue['type'] == 'data_corruption' for issue in build_health_report(str(tmp_path))['blocking_issues'])
    run_safe_fixes(str(tmp_path))
    assert ledger.read_bytes() == before
