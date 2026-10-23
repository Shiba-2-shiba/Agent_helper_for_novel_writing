"""Count work, not machine-dependent elapsed time, on shared provenance graphs."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from novel_agent import dependencies as api
from novel_agent import ledgers


def graph(tmp_path):
    (tmp_path / 'runtime').mkdir()
    (tmp_path / 'source').write_text('accepted memory source', encoding='utf8')
    leaf = api.snapshot_dependencies(str(tmp_path), [{'kind': 'file', 'path': 'source'}])
    records = []
    for name in ('shared', 'left', 'right'):
        (tmp_path / name).write_text(name, encoding='utf8')
        inputs = leaf * 20 if name == 'shared' else api.snapshot_dependencies(str(tmp_path), [{'kind': 'artifact', 'path': 'shared'}])
        records.append({'path': name, 'dependencies': inputs, 'dependency_digest': api.dependency_digest(inputs), 'status': 'active'})
        (tmp_path / 'runtime/artifact_ledger.json').write_text(json.dumps({'artifacts': records}), encoding='utf8')
    return api.snapshot_dependencies(str(tmp_path), [{'kind': 'artifact', 'path': p} for p in ('left', 'right')])


def test_diamond_verification_reads_one_ledger_and_each_source_once(tmp_path, monkeypatch):
    records = graph(tmp_path)
    loads, hashes = [], []
    read, hash_file = api.read_json, api.text_content_hash
    def counted_read(path, **kwargs):
        loads.append(str(path))
        return read(path, **kwargs)
    def counted_hash(path):
        hashes.append(str(path))
        return hash_file(path)
    monkeypatch.setattr(api, 'read_json', counted_read)
    monkeypatch.setattr(api, 'text_content_hash', counted_hash)
    assert api.verify_dependencies(str(tmp_path), records) == []
    assert len(loads) == 1
    assert hashes.count(str(tmp_path / 'source')) == 1
    (tmp_path / 'source').write_text('changed', encoding='utf8')
    assert api.verify_dependencies(str(tmp_path), records), 'a new operation must read fresh sources'


def test_new_snapshots_deduplicate_exact_sources_not_projection_guards(tmp_path):
    specs = [{'kind': 'file', 'path': 'source'}] * 200 + [
        {'kind': 'projection', 'selector': 'runtime_policy'},
        {'kind': 'projection', 'selector': 'resume_progress'},
        {'kind': 'scene_set', 'target_scene_id': '1-2'},
        {'kind': 'scene_set', 'target_scene_id': '1-3'}]
    records = api.snapshot_dependencies(str(tmp_path), specs)
    assert len(records) == 5


def test_lookup_does_not_refresh_unrelated_artifacts(tmp_path, monkeypatch):
    graph(tmp_path)
    (tmp_path / 'unrelated').write_text('other', encoding='utf8')
    ledgers.register_artifact(str(tmp_path), artifact_id='other', artifact_type='test', path=str(tmp_path / 'unrelated'))
    calls = []
    original = api.verify_dependencies
    def counted(project, records, **kwargs):
        calls.append(records)
        return original(project, records, **kwargs)
    monkeypatch.setattr(api, 'verify_dependencies', counted)
    assert ledgers.find_artifact_by_path(str(tmp_path), str(tmp_path / 'unrelated'))['status'] == 'active'
    assert len(calls) == 1


def test_batch_selected_lookup_loads_ledger_once(tmp_path, monkeypatch):
    graph(tmp_path)
    assert hasattr(ledgers, 'find_artifacts_by_paths'), 'batch lookup is missing'
    reads = []
    original = ledgers.read_json
    def counted(path, **kwargs):
        reads.append(path)
        return original(path, **kwargs)
    monkeypatch.setattr(ledgers, 'read_json', counted)
    found = ledgers.find_artifacts_by_paths(str(tmp_path), [str(tmp_path / p) for p in ('left', 'right')])
    assert [item['path'] for item in found] == ['left', 'right']
    assert len(reads) == 1


def test_selected_lookup_rejects_duplicate_paths_without_rewriting(tmp_path):
    import pytest
    from novel_agent.errors import DataCorruptionError
    graph(tmp_path)
    path = tmp_path / 'runtime/artifact_ledger.json'
    payload = json.loads(path.read_text())
    payload['artifacts'].append(dict(payload['artifacts'][0], status='rejected'))
    path.write_text(json.dumps(payload), encoding='utf8')
    before = path.read_bytes()
    with pytest.raises(DataCorruptionError, match='duplicate'):
        ledgers.find_artifact_by_path(str(tmp_path), str(tmp_path / 'shared'))
    assert path.read_bytes() == before


def test_distinct_historical_guards_for_same_source_are_not_hidden(tmp_path):
    (tmp_path / 'source').write_text('old', encoding='utf8')
    old = api.snapshot_dependencies(str(tmp_path), [{'kind': 'file', 'path': 'source'}])
    (tmp_path / 'source').write_text('new', encoding='utf8')
    current = api.snapshot_dependencies(str(tmp_path), [{'kind': 'file', 'path': 'source'}])
    assert api.verify_dependencies(str(tmp_path), current + old)
    assert api.verify_dependencies(str(tmp_path), old + current)


def test_repeated_prior_scene_guard_is_observed_once(tmp_path, monkeypatch):
    calls = []
    original = api._scene_members
    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(api, '_scene_members', counted)
    api.snapshot_dependencies(str(tmp_path), [{'kind': 'scene_set', 'target_scene_id': '2-1'}] * 20)
    assert len(calls) == 1


def test_final_prompt_recheck_observes_sources_changed_during_assembly(tmp_path, monkeypatch):
    import pytest
    import build_draft_prompt as prompt
    from novel_agent.errors import UserFacingError
    from test_memory_context import runtime_project, run_script
    project = runtime_project(tmp_path)
    built = run_script('build_runtime_context.py', project, '--chapter', '2', '--scene', '2-3', '--mode', 'draft')
    assert built.returncode == 0, built.stdout + built.stderr
    original = prompt.assemble_prompt
    def mutate(sections):
        assembled = original(sections)
        target = project / 'runtime/scenes/2-3/draft/style_contract_compact.md'
        target.write_text(target.read_text() + '\nchanged during generation', encoding='utf8')
        return assembled
    monkeypatch.setattr(prompt, 'assemble_prompt', mutate)
    monkeypatch.setattr(sys, 'argv', ['build_draft_prompt.py', '--project', str(project), '--scene', '2-3'])
    with pytest.raises(UserFacingError, match='changed during prompt'):
        prompt.main()
    assert not (project / 'runtime/scenes/2-3/draft/draft_prompt.txt').exists()


def test_cycle_and_digest_tampering_remain_fail_closed(tmp_path):
    (tmp_path / 'runtime').mkdir()
    (tmp_path / 'a').write_text('a', encoding='utf8')
    edge = api.snapshot_dependencies(str(tmp_path), [{'kind': 'artifact', 'path': 'a'}])
    ledger = tmp_path / 'runtime/artifact_ledger.json'
    payload = {'artifacts': [{'path': 'a', 'dependencies': edge, 'dependency_digest': api.dependency_digest(edge)}]}
    ledger.write_text(json.dumps(payload), encoding='utf8')
    snapshot = api.snapshot_dependencies(str(tmp_path), [{'kind': 'artifact', 'path': 'a'}])
    assert 'cyclic_artifact_dependency' in json.dumps(api.verify_dependencies(str(tmp_path), snapshot))
    payload['artifacts'][0]['dependency_digest'] = 'tampered'
    ledger.write_text(json.dumps(payload), encoding='utf8')
    assert 'invalid_artifact_dependency_digest' in json.dumps(api.verify_dependencies(str(tmp_path), snapshot))
