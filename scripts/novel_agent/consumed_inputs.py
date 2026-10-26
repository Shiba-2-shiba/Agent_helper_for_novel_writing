"""Bind the actual consumed text/object to already-captured dependency evidence.

A final filesystem recheck alone misses an edit that is undone after a reader
has consumed it. These checks never resnapshot the source to bless new bytes.
"""
import hashlib

from novel_agent.dependencies import _digest, _path
from novel_agent.errors import UserFacingError


def _records(project_dir, path, guards):
    _, relative = _path(project_dir, path)
    return relative, [r for r in guards if r.get('path') == relative]


def check_consumed_text(project_dir, path, text, guards):
    relative, records = _records(project_dir, path, guards)
    hashes = [r['content_hash'] for r in records if 'content_hash' in r]
    actual = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if not hashes or any(expected != actual for expected in hashes):
        raise UserFacingError('consumed input changed from captured fingerprint: ' + relative)
    return text


def check_consumed_selection(project_dir, path, payload, guards):
    relative, records = _records(project_dir, path, guards)
    projections = [r for r in records if r.get('kind') == 'projection' and
                   r.get('selector') in {'memory_selection', 'keyframing_selection', 'dialogue_selection'}]
    if not projections or not isinstance(payload, dict):
        raise UserFacingError('consumed selection lacks captured input guard: ' + relative)
    for record in projections:
        selector = record['selector']
        if selector == 'dialogue_selection':
            value = {'exists': True, 'dialogue': payload.get('dialogue'), 'source_paths': [relative]}
        else:
            if selector == 'keyframing_selection':
                fields = ('version', 'config', 'dialogue', 'keyframing')
            elif record.get('projection_version') == 3:
                fields = ('version', 'config', 'memory', 'dialogue', 'keyframing')
            else:
                fields = ('version', 'config', 'memory', 'dialogue') if 'dialogue' in payload else ('version', 'config', 'memory')
            value = {'exists': True, 'selection': {key: payload.get(key) for key in fields}, 'source_paths': [relative]}
        if _digest(value) != record.get('projection_hash'):
            raise UserFacingError('consumed selection changed from captured input projection: ' + relative)
    return payload
