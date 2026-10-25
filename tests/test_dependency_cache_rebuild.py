"""Explicit cache rebuilding archives, never upgrades authored evidence."""
import json
from pathlib import Path

import pytest

from novel_agent.errors import UserFacingError
from novel_agent.runtime_paths import require_runtime_current
from test_dialogue_context import prepare_project, runtime_project, run_script


def test_cache_rebuild_dry_run_changes_nothing(tmp_path):
    project = runtime_project(tmp_path)
    prepare_project(project)
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    result = run_script('rebuild_dependency_cache.py', '--project', project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'dry_run' in result.stdout
    assert {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()} == before


def test_rebuild_archives_exact_ledger_and_requires_reprepare_without_reapproving(tmp_path):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    ledger = project / 'runtime/artifact_ledger.json'
    old_bytes = ledger.read_bytes()
    approval = project / 'runtime/approval_ledger.json'
    approval.write_text(json.dumps({'version': 1, 'scenes': {}}))
    accepted = project / 'story_memory/accepted.json'
    accepted.parent.mkdir(exist_ok=True)
    accepted.write_text(json.dumps({'version': 1, 'revision': 0, 'records': []}))
    source = project / 'chapter_2_scene_2.txt'
    source_bytes, approval_bytes, accepted_bytes = source.read_bytes(), approval.read_bytes(), accepted.read_bytes()
    result = run_script('rebuild_dependency_cache.py', '--project', project, '--apply')
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    archive = project / report['archive_ledger']
    assert archive.read_bytes() == old_bytes
    assert json.loads(ledger.read_text())['artifacts'] == []
    assert source.read_bytes() == source_bytes
    assert approval.read_bytes() == approval_bytes
    assert accepted.read_bytes() == accepted_bytes
    with pytest.raises(UserFacingError, match='incomplete|rebuild|prepare'):
        require_runtime_current(str(project), str(runtime))
    prepare_project(project)
    require_runtime_current(str(project), str(runtime))
    assert approval.read_bytes() == approval_bytes
    assert accepted.read_bytes() == accepted_bytes
    assert archive.read_bytes() == old_bytes


def test_rebuild_refuses_corrupt_ledger_without_writing(tmp_path):
    project = runtime_project(tmp_path)
    prepare_project(project)
    path = project / 'runtime/artifact_ledger.json'
    path.write_text('{broken')
    before = path.read_bytes()
    result = run_script('rebuild_dependency_cache.py', '--project', project, '--apply')
    assert result.returncode != 0
    assert path.read_bytes() == before
    assert not (project / 'runtime/dependency_cache_rebuild.json').exists()


def test_rebuild_on_relocated_copy_archives_original_identity(tmp_path):
    import shutil
    project = runtime_project(tmp_path)
    old_runtime = prepare_project(project)
    original_manifest = (old_runtime / 'runtime_manifest.json').read_bytes()
    relocated = tmp_path / 'relocated'
    shutil.copytree(project, relocated)
    result = run_script('rebuild_dependency_cache.py', '--project', relocated, '--apply')
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    archived = relocated / report['archive_ledger']
    saved = archived.parent / 'manifests/scenes/2-3/draft/runtime_manifest.json'
    assert saved.read_bytes() == original_manifest
    runtime = relocated / 'runtime/scenes/2-3/draft'
    with pytest.raises(UserFacingError, match='incomplete|prepare'):
        require_runtime_current(str(relocated), str(runtime))


def test_interrupted_rebuild_leaves_evidence_and_can_resume(tmp_path, monkeypatch):
    from novel_agent import dependency_cache as cache
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    ledger = project / 'runtime/artifact_ledger.json'
    old_bytes = ledger.read_bytes()
    original = cache.atomic_write_json
    def interrupt_reset(path, payload):
        if str(path) == str(ledger):
            raise OSError('simulated interruption before reset')
        return original(path, payload)
    monkeypatch.setattr(cache, 'atomic_write_json', interrupt_reset)
    with pytest.raises(OSError, match='simulated interruption'):
        cache.rebuild_dependency_cache(str(project), apply=True)
    assert ledger.read_bytes() == old_bytes
    with pytest.raises(UserFacingError, match='incomplete|prepare'):
        require_runtime_current(str(project), str(runtime))
    journal = json.loads((project / 'runtime/dependency_cache_rebuild.json').read_text())
    backup = project / journal['archive_dir'] / 'artifact_ledger.json'
    assert backup.read_bytes() == old_bytes
    monkeypatch.setattr(cache, 'atomic_write_json', original)
    cache.rebuild_dependency_cache(str(project), apply=True)
    assert backup.read_bytes() == old_bytes
    assert json.loads(ledger.read_text())['artifacts'] == []


def test_rebuild_keeps_archived_future_values_outside_active_runtime(tmp_path):
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    manifest = runtime / 'runtime_manifest.json'
    payload = json.loads(manifest.read_text())
    payload['inputs'][0]['value'] = {'future_outline': 'ARCHIVED_FUTURE_ONLY_721'}
    manifest.write_text(json.dumps(payload))
    original = manifest.read_bytes()
    result = run_script('rebuild_dependency_cache.py', '--project', project, '--apply')
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    archive = project / report['archive_ledger']
    assert not str(archive).startswith(str(project / 'runtime') + '/')
    assert (archive.parent / 'manifests/scenes/2-3/draft/runtime_manifest.json').read_bytes() == original
    assert 'ARCHIVED_FUTURE_ONLY_721' not in manifest.read_text()
    assert set(json.loads(manifest.read_text())) == {'version', 'project_dir', 'scene_id', 'mode', 'generation_state'}


@pytest.mark.parametrize('target', ['runtime', 'ledger', 'manifest', 'archive', 'journal'])
def test_rebuild_rejects_escaping_symlink_before_any_write(tmp_path, target):
    import shutil
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    outside = tmp_path / 'outside'
    outside.mkdir()
    if target == 'runtime':
        destination = outside / 'runtime'
        shutil.move(str(project / 'runtime'), str(destination))
        (project / 'runtime').symlink_to(destination, target_is_directory=True)
    elif target == 'archive':
        (project / '.dependency_archive').symlink_to(outside, target_is_directory=True)
    else:
        selected = {'ledger': project / 'runtime/artifact_ledger.json',
                    'manifest': runtime / 'runtime_manifest.json',
                    'journal': project / 'runtime/dependency_cache_rebuild.json'}[target]
        destination = outside / selected.name
        if selected.exists():
            shutil.move(str(selected), str(destination))
        else:
            destination.write_text('{}')
        selected.symlink_to(destination)
    before = {str(p.relative_to(outside)): p.read_bytes() for p in outside.rglob('*') if p.is_file()}
    from novel_agent.dependency_cache import rebuild_dependency_cache
    with pytest.raises(UserFacingError, match='symlink|escape|outside'):
        rebuild_dependency_cache(str(project), apply=True)
    assert {str(p.relative_to(outside)): p.read_bytes() for p in outside.rglob('*') if p.is_file()} == before
    assert not (outside / 'runtime/.project_write.lock').exists()


def test_pending_rebuild_refuses_corrupted_archived_ledger(tmp_path, monkeypatch):
    from novel_agent import dependency_cache as cache
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    ledger = project / 'runtime/artifact_ledger.json'
    original_ledger = ledger.read_bytes()
    original = cache.atomic_write_json
    def interrupt_reset(path, payload):
        if str(path) == str(ledger):
            raise OSError('simulated interruption')
        return original(path, payload)
    monkeypatch.setattr(cache, 'atomic_write_json', interrupt_reset)
    with pytest.raises(OSError):
        cache.rebuild_dependency_cache(str(project), apply=True)
    journal = json.loads((project / 'runtime/dependency_cache_rebuild.json').read_text())
    archive = project / journal['archive_dir'] / 'artifact_ledger.json'
    archive.write_text('{broken archive')
    monkeypatch.setattr(cache, 'atomic_write_json', original)
    with pytest.raises(UserFacingError, match='archive|JSON|digest|hash'):
        cache.rebuild_dependency_cache(str(project), apply=True)
    assert ledger.read_bytes() == original_ledger
    assert archive.read_text() == '{broken archive'


@pytest.mark.parametrize('target', ['runtime_directory', 'request_file', 'archive_ledger', 'archive_manifest'])
def test_nested_cache_symlinks_are_rejected_before_lock(tmp_path, monkeypatch, target):
    import shutil
    from novel_agent import dependency_cache as cache
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    outside = tmp_path / 'outside'
    outside.mkdir()
    if target in ('archive_ledger', 'archive_manifest'):
        ledger = project / 'runtime/artifact_ledger.json'
        original = cache.atomic_write_json
        def interrupt_reset(path, payload):
            if str(path) == str(ledger):
                raise OSError('simulated interruption')
            return original(path, payload)
        monkeypatch.setattr(cache, 'atomic_write_json', interrupt_reset)
        with pytest.raises(OSError):
            cache.rebuild_dependency_cache(str(project), apply=True)
        monkeypatch.setattr(cache, 'atomic_write_json', original)
        journal = json.loads((project / 'runtime/dependency_cache_rebuild.json').read_text())
        archive = project / journal['archive_dir']
        selected = archive / ('artifact_ledger.json' if target == 'archive_ledger' else 'manifests/scenes/2-3/draft/runtime_manifest.json')
    else:
        selected = runtime if target == 'runtime_directory' else runtime / 'request_compact.md'
    destination = outside / selected.name
    shutil.move(str(selected), str(destination))
    selected.symlink_to(destination, target_is_directory=destination.is_dir())
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}
    def no_lock(*args, **kwargs):
        pytest.fail('lock must not be created before rejecting the symlink')
    monkeypatch.setattr(cache, 'project_lock', no_lock)
    with pytest.raises(UserFacingError, match='symlink|escape'):
        cache.rebuild_dependency_cache(str(project), apply=True)
    assert {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()} == before


@pytest.mark.parametrize('changed', ['archived_manifest', 'active_ledger', 'active_manifest'])
def test_pending_rebuild_is_bound_to_every_original_evidence_file(tmp_path, monkeypatch, changed):
    from novel_agent import dependency_cache as cache
    from novel_agent.ledgers import register_artifact
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    ledger = project / 'runtime/artifact_ledger.json'
    original = cache.atomic_write_json
    def interrupt_reset(path, payload):
        if str(path) == str(ledger):
            raise OSError('simulated interruption before reset')
        return original(path, payload)
    monkeypatch.setattr(cache, 'atomic_write_json', interrupt_reset)
    with pytest.raises(OSError):
        cache.rebuild_dependency_cache(str(project), apply=True)
    journal = json.loads((project / 'runtime/dependency_cache_rebuild.json').read_text())
    archived_manifest = project / journal['archive_dir'] / 'manifests/scenes/2-3/draft/runtime_manifest.json'
    if changed == 'archived_manifest':
        archived_manifest.write_text('CORRUPTED MANIFEST')
    elif changed == 'active_ledger':
        path = project / 'runtime/new-evidence.md'
        path.write_text('new valid evidence after interruption')
        register_artifact(str(project), artifact_id='new', artifact_type='test', path=str(path))
    else:
        payload = json.loads((runtime / 'runtime_manifest.json').read_text())
        payload['newer_work'] = True
        (runtime / 'runtime_manifest.json').write_text(json.dumps(payload))
    before_ledger = ledger.read_bytes()
    before_manifest = (runtime / 'runtime_manifest.json').read_bytes()
    monkeypatch.setattr(cache, 'atomic_write_json', original)
    with pytest.raises(UserFacingError, match='archive|manifest|ledger|transaction|hash'):
        cache.rebuild_dependency_cache(str(project), apply=True)
    assert ledger.read_bytes() == before_ledger
    assert (runtime / 'runtime_manifest.json').read_bytes() == before_manifest


def test_cache_rebuild_without_ledger_has_actionable_error(tmp_path):
    from novel_agent.dependency_cache import rebuild_dependency_cache
    with pytest.raises(UserFacingError, match='artifact ledger is missing'):
        rebuild_dependency_cache(str(tmp_path), apply=True)
    assert not (tmp_path / 'runtime/dependency_cache_rebuild.json').exists()


def test_rebuild_resumes_after_atomic_reset_before_completion(tmp_path, monkeypatch):
    from novel_agent import dependency_cache as cache
    project = runtime_project(tmp_path)
    runtime = prepare_project(project)
    journal_path = project / 'runtime/dependency_cache_rebuild.json'
    ledger = project / 'runtime/artifact_ledger.json'
    old_ledger = ledger.read_bytes()
    original = cache.atomic_write_json
    def interrupt_complete(path, payload):
        if str(path) == str(journal_path) and payload.get('state') == 'complete':
            raise OSError('simulated interruption after reset')
        return original(path, payload)
    monkeypatch.setattr(cache, 'atomic_write_json', interrupt_complete)
    with pytest.raises(OSError):
        cache.rebuild_dependency_cache(str(project), apply=True)
    assert json.loads(ledger.read_text())['artifacts'] == []
    journal = json.loads(journal_path.read_text())
    assert journal['phase'] == 'ready_to_reset'
    archive = project / journal['archive_dir'] / 'artifact_ledger.json'
    assert archive.read_bytes() == old_ledger
    monkeypatch.setattr(cache, 'atomic_write_json', original)
    cache.rebuild_dependency_cache(str(project), apply=True)
    assert json.loads(journal_path.read_text())['state'] == 'complete'
    assert archive.read_bytes() == old_ledger
    with pytest.raises(UserFacingError, match='incomplete|prepare'):
        require_runtime_current(str(project), str(runtime))
