"""Explicit, recoverable archival of generated dependency caches only."""
import hashlib
import json
import os
import re
import uuid

from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.ledgers import artifact_ledger_path, read_artifact_ledger, _validate_artifact_records
from novel_agent.runtime_paths import validate_runtime_identity
from novel_agent.storage import atomic_write_json, atomic_write_text, project_lock, read_json, validate_schema


def _relative(path, project_dir):
    return os.path.relpath(path, project_dir).replace(os.sep, '/')


def _managed_path(project_dir, path):
    """Reject escaping or aliased generated paths before any lock/read/write."""
    root = os.path.realpath(project_dir)
    absolute = os.path.abspath(path)
    try:
        contained = (os.path.commonpath([root, absolute]) == root
                     and os.path.commonpath([root, os.path.realpath(absolute)]) == root)
    except ValueError:
        contained = False
    if not contained:
        raise UserFacingError('dependency cache path escapes project: ' + path)
    current = root
    for component in os.path.relpath(absolute, root).split(os.sep):
        current = os.path.join(current, component)
        if os.path.islink(current):
            raise UserFacingError('dependency cache path must not be a symlink: ' + current)
    return absolute


def _managed_roots(project_dir):
    for relative in ('runtime', 'runtime/.project_write.lock', 'runtime/artifact_ledger.json',
                     'runtime/dependency_cache_rebuild.json', '.dependency_archive'):
        _managed_path(project_dir, os.path.join(project_dir, relative))


def _archive_ledger(project_dir, archive_path, expected_hash):
    _managed_path(project_dir, archive_path)
    payload = read_json(archive_path, default_factory=dict)
    validate_schema(payload, archive_path, fields={'artifacts': list})
    if 'artifacts' not in payload:
        raise DataCorruptionError('missing archived artifact records: ' + archive_path)
    _validate_artifact_records(payload['artifacts'], archive_path)
    with open(archive_path, 'rb') as handle:
        contents = handle.read()
    if hashlib.sha256(contents).hexdigest() != expected_hash:
        raise DataCorruptionError('archived ledger hash mismatch: ' + archive_path)
    return contents


def _runtime_manifests(project_dir):
    root = os.path.join(project_dir, 'runtime')
    found = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name != 'dependency_archive')
        for name in dirs:
            _managed_path(project_dir, os.path.join(directory, name))
        for name in ('runtime_manifest.json', 'request_compact.md', 'scene_brief_compact.md'):
            if name in files:
                _managed_path(project_dir, os.path.join(directory, name))
        if 'runtime_manifest.json' not in files and not any(name in files for name in ('request_compact.md', 'scene_brief_compact.md')):
            continue
        # A copied project's old absolute identity is expected to be stale.
        # Accept it only for archival, never as authorization to read that root.
        manifest = _managed_path(project_dir, os.path.join(directory, 'runtime_manifest.json'))
        identity_root = project_dir
        if os.path.isfile(manifest):
            stored = read_json(manifest, default_factory=dict)
            identity_root = stored.get('project_dir')
            if not isinstance(identity_root, str) or not identity_root:
                raise DataCorruptionError('invalid runtime project identity: ' + manifest)
        identity = validate_runtime_identity(identity_root, directory, scene_id=None, mode='')
        mode = identity.get('mode') or (os.path.basename(directory) if os.path.basename(directory) in ('draft', 'resume') else 'draft')
        found.append((os.path.join(directory, 'runtime_manifest.json'), identity, mode))
    return found


def _plan(project_dir):
    _managed_roots(project_dir)
    ledger_path = artifact_ledger_path(project_dir)
    ledger = read_artifact_ledger(project_dir)  # Corrupt evidence is never reset.
    manifests = _runtime_manifests(project_dir)
    return ledger, manifests, {
        'mode': 'dry_run', 'artifact_count': len(ledger['artifacts']),
        'active_ledger_bytes': os.path.getsize(ledger_path) if os.path.isfile(ledger_path) else 0,
        'runtime_count': len(manifests),
        'effect': 'archive exact old evidence, reset generated ledger, require prepare; no source/approval/memory changes',
        'disk_space_freed': False,
    }


def _pending_archive(project_dir, journal, manifests):
    if not journal:
        return None
    if journal.get('version') != 1 or journal.get('state') not in ('in_progress', 'complete'):
        raise DataCorruptionError('invalid dependency cache archive journal')
    if journal['state'] == 'complete':
        return None
    if not isinstance(journal.get('archive_dir'), str):
        raise DataCorruptionError('invalid dependency cache archive journal')
    expected_hash = journal.get('ledger_sha256')
    if not isinstance(expected_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_hash):
        raise DataCorruptionError('invalid archived ledger hash in journal')
    archive = _managed_path(project_dir, os.path.join(project_dir, journal['archive_dir']))
    archive_root = os.path.join(project_dir, '.dependency_archive')
    if os.path.commonpath([archive, archive_root]) != archive_root or archive == archive_root:
        raise DataCorruptionError('invalid dependency cache archive journal')
    _managed_path(project_dir, os.path.join(archive, 'artifact_ledger.json'))
    root = os.path.join(project_dir, 'runtime')
    for path, _, _ in manifests:
        _managed_path(project_dir, os.path.join(archive, 'manifests', _relative(path, root)))
    return archive, expected_hash


def _bytes(path):
    with open(path, 'rb') as handle:
        return handle.read()


def _hash(contents):
    return hashlib.sha256(contents).hexdigest()


def _json_hash(payload):
    return _hash((json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def _pending_manifest(project_dir, identity, mode):
    return {'version': 1, 'project_dir': os.path.realpath(project_dir),
            'scene_id': identity['scene_id'], 'mode': mode,
            'generation_state': 'cache_rebuild_required'}


def _manifest_receipts(project_dir, manifests):
    return {_relative(path, project_dir): {
        'source_hash': _hash(_bytes(path)) if os.path.isfile(path) else None,
        'pending_hash': _json_hash(_pending_manifest(project_dir, identity, mode))}
        for path, identity, mode in manifests}


def _validate_transaction(project_dir, journal, manifests, archive):
    """Allow only the exact original inputs or this transaction's reset image."""
    phase = journal.get('phase')
    if phase not in ('archiving', 'ready_to_reset'):
        raise DataCorruptionError('invalid pending cache transaction phase')
    active_hash = _hash(_bytes(artifact_ledger_path(project_dir)))
    reset_done = phase == 'ready_to_reset' and active_hash == journal.get('reset_ledger_sha256')
    if active_hash != journal['ledger_sha256'] and not reset_done:
        raise DataCorruptionError('active ledger changed during pending cache transaction')
    receipts = journal.get('manifests')
    expected_paths = {_relative(path, project_dir) for path, _, _ in manifests}
    if not isinstance(receipts, dict) or set(receipts) != expected_paths:
        raise DataCorruptionError('runtime manifest set changed during pending cache transaction')
    root = os.path.join(project_dir, 'runtime')
    for path, identity, mode in manifests:
        receipt = receipts[_relative(path, project_dir)]
        if not isinstance(receipt, dict) or receipt.get('pending_hash') != _json_hash(_pending_manifest(project_dir, identity, mode)):
            raise DataCorruptionError('invalid pending manifest identity: ' + path)
        source_hash = receipt.get('source_hash')
        if source_hash is not None and (not isinstance(source_hash, str) or not re.fullmatch(r'[0-9a-f]{64}', source_hash)):
            raise DataCorruptionError('invalid original manifest hash: ' + path)
        current_hash = _hash(_bytes(path)) if os.path.isfile(path) else None
        if current_hash not in (source_hash, receipt['pending_hash']):
            raise DataCorruptionError('active manifest changed during pending cache transaction: ' + path)
        backup = _managed_path(project_dir, os.path.join(archive, 'manifests', _relative(path, root)))
        if os.path.exists(backup):
            read_json(backup, default_factory=dict)
            if source_hash is None or _hash(_bytes(backup)) != source_hash:
                raise DataCorruptionError('archived manifest hash mismatch: ' + backup)
        elif source_hash is not None and current_hash != source_hash:
            raise DataCorruptionError('original manifest backup is missing: ' + backup)
    return reset_done


def rebuild_dependency_cache(project_dir, *, apply=False):
    """Archive exact generated evidence and require explicit prepare, never approve.

    The journal binds all original bytes before writes. Resume accepts only the
    original active state or its own phase-bound atomic reset image, never work
    added after an interruption. Saved manifests are checked as well as ledger.
    """
    project_dir = os.path.realpath(project_dir)
    _managed_roots(project_dir)  # Especially runtime: project_lock writes there.
    if not apply:
        return _plan(project_dir)[2]
    if not os.path.isfile(artifact_ledger_path(project_dir)):
        raise UserFacingError('artifact ledger is missing; nothing was reset')
    # Discover and validate all selected targets before even creating the lock.
    manifests = _runtime_manifests(project_dir)
    journal_path = os.path.join(project_dir, 'runtime', 'dependency_cache_rebuild.json')
    _pending_archive(project_dir, read_json(journal_path, default_factory=dict), manifests)
    with project_lock(project_dir):
        _, manifests, report = _plan(project_dir)
        root = os.path.join(project_dir, 'runtime')
        journal = read_json(journal_path, default_factory=dict)
        ledger_path = artifact_ledger_path(project_dir)
        reset_payload = {'version': 1, 'updated_at': '', 'artifacts': []}
        if journal.get('state') != 'in_progress':
            archive = os.path.join(project_dir, '.dependency_archive', uuid.uuid4().hex)
            journal = {'version': 1, 'state': 'in_progress', 'phase': 'archiving',
                       'archive_dir': _relative(archive, project_dir),
                       'ledger_sha256': _hash(_bytes(ledger_path)),
                       'reset_ledger_sha256': _json_hash(reset_payload),
                       'manifests': _manifest_receipts(project_dir, manifests)}
            atomic_write_json(journal_path, journal)
        archive, expected_hash = _pending_archive(project_dir, journal, manifests)
        reset_done = _validate_transaction(project_dir, journal, manifests, archive)
        archived_ledger = _managed_path(project_dir, os.path.join(archive, 'artifact_ledger.json'))
        if not os.path.exists(archived_ledger):
            original = _bytes(ledger_path)
            if _hash(original) != expected_hash:
                raise DataCorruptionError('active ledger no longer matches pending archive identity')
            atomic_write_text(archived_ledger, original.decode('utf-8'))
        archived = _archive_ledger(project_dir, archived_ledger, expected_hash)
        # Archive every original first; validate every saved hash before marking
        # any runtime unavailable or atomically resetting active evidence.
        for path, _, _ in manifests:
            backup = _managed_path(project_dir, os.path.join(archive, 'manifests', _relative(path, root)))
            if os.path.isfile(path) and not os.path.exists(backup):
                source_hash = journal['manifests'][_relative(path, project_dir)]['source_hash']
                if source_hash is not None:
                    atomic_write_text(backup, _bytes(path).decode('utf-8'))
        _validate_transaction(project_dir, journal, manifests, archive)
        for path, identity, mode in manifests:
            atomic_write_json(path, _pending_manifest(project_dir, identity, mode))
        # A crash after the atomic reset but before completion can be recognized
        # only in this phase and only by the exact serialized reset-image hash.
        journal['phase'] = 'ready_to_reset'
        atomic_write_json(journal_path, journal)
        if not reset_done:
            atomic_write_json(ledger_path, reset_payload)
        journal['state'] = 'complete'
        atomic_write_json(journal_path, journal)
        report.update(mode='applied', archive_ledger=_relative(archived_ledger, project_dir),
                      archived_ledger_bytes=len(archived), archived_ledger_sha256=_hash(archived),
                      active_ledger_bytes=os.path.getsize(ledger_path))
        return report
