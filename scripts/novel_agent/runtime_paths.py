"""Resolve runtime context without silently substituting a different scene."""
import os
import re

from novel_agent.errors import UserFacingError, DataCorruptionError
from novel_agent.storage import atomic_write_json, read_json, text_content_hash


def validate_runtime_identity(project_dir, runtime_dir, *, scene_id, mode):
    manifest_path = os.path.join(runtime_dir, 'runtime_manifest.json')
    if os.path.isfile(manifest_path):
        payload = read_json(manifest_path, default_factory=dict)
        if payload.get('version') != 1:
            raise DataCorruptionError('unsupported runtime manifest: ' + manifest_path)
        if payload.get('project_dir') != os.path.realpath(project_dir):
            raise UserFacingError('runtime project identity mismatch: ' + runtime_dir)
        if not payload.get('scene_id') or (scene_id and payload['scene_id'] != scene_id) or (mode and payload.get('mode') != mode):
            raise UserFacingError('runtime scene or mode identity mismatch: ' + runtime_dir)
        return payload
    candidates = []
    for name in ('scene_brief_compact.md', 'request_compact.md'):
        path = os.path.join(runtime_dir, name)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                candidates.extend(re.findall(r'(?m)^\s*(?:-\s*)?Scene ID:\s*(\d+-\d+)\s*$', handle.read()))
    identities = set(candidates)
    if len(identities) != 1 or (scene_id and scene_id not in identities):
        raise UserFacingError('runtime scene identity is missing or mismatched; prepare the requested scene: ' + runtime_dir)
    # Scene-local paths also have a mode identity, unlike the legacy flat layout.
    if os.path.basename(os.path.dirname(runtime_dir)) in identities and mode and os.path.basename(runtime_dir) != mode:
        raise UserFacingError('runtime mode identity mismatch: ' + runtime_dir)
    return {'version': 0, 'scene_id': next(iter(identities)), 'mode': mode, 'legacy': True}


def resolve_runtime_dir(project_dir, *, mode='', scene_ref=None, runtime_dir_arg=''):
    root = os.path.join(project_dir, 'runtime')
    scene_id = scene_ref['canonical_id'] if scene_ref else None
    if runtime_dir_arg:
        candidate = runtime_dir_arg
        if not os.path.isabs(candidate):
            options = [os.path.abspath(candidate), os.path.join(project_dir, candidate)]
            candidate = next((path for path in options if os.path.isdir(path)), options[-1])
        if not os.path.isdir(candidate):
            raise UserFacingError('runtime directory not found: ' + candidate)
        if scene_id or os.path.isfile(os.path.join(candidate, 'runtime_manifest.json')):
            validate_runtime_identity(project_dir, candidate, scene_id=scene_id, mode=mode)
        return candidate
    if scene_id:
        candidate = os.path.join(root, 'scenes', scene_id, mode or 'draft')
        if os.path.isdir(candidate):
            validate_runtime_identity(project_dir, candidate, scene_id=scene_id, mode=mode)
            return candidate
        if os.path.isdir(root):
            validate_runtime_identity(project_dir, root, scene_id=scene_id, mode=mode)
            return root
        raise UserFacingError('runtime missing; prepare scene ' + scene_id)
    index = read_json(os.path.join(root, 'runtime_index.json'), default_factory=lambda: {'latest_by_mode': {}})
    latest = index.get('latest_by_mode', {}).get(mode, {})
    candidate = latest.get('runtime_dir', '')
    if candidate and os.path.isdir(candidate):
        indexed_scene_id = latest.get('scene_id')
        if not isinstance(indexed_scene_id, str) or not re.fullmatch(r'[1-9]\d*-[1-9]\d*', indexed_scene_id):
            raise UserFacingError('runtime index scene identity is missing or invalid; prepare again')
        chapter, scene = (int(part) for part in indexed_scene_id.split('-'))
        if ('chapter' in latest and latest['chapter'] != chapter) or ('scene' in latest and latest['scene'] != scene):
            raise UserFacingError('runtime index scene identity is contradictory; prepare again')
        validate_runtime_identity(project_dir, candidate, scene_id=indexed_scene_id, mode=mode)
        return candidate
    return root


def write_runtime_manifest(project_dir, runtime_dir, *, scene_id, mode, files, inputs):
    from novel_agent.dependencies import compact_dependencies, dependency_digest
    inputs = compact_dependencies(inputs)
    payload = {'version': 1, 'project_dir': os.path.realpath(project_dir), 'scene_id': scene_id, 'mode': mode,
               'files': [{'path': os.path.relpath(path, project_dir).replace(os.sep, '/'), 'content_hash': text_content_hash(path)} for path in files],
               'inputs': inputs, 'inputs_digest': dependency_digest(inputs)}
    atomic_write_json(os.path.join(runtime_dir, 'runtime_manifest.json'), payload)
    return payload


def require_runtime_current(project_dir, runtime_dir):
    path = os.path.join(runtime_dir, 'runtime_manifest.json')
    if not os.path.isfile(path):
        return  # Legacy runtime remains a warning-only compatibility path.
    from novel_agent.dependencies import dependency_digest, verify_dependencies
    payload = read_json(path, default_factory=dict)
    if payload.get('generation_state', 'complete') != 'complete':
        raise UserFacingError('runtime generation is incomplete; prepare again: ' + path)
    inputs = payload.get('inputs')
    if not isinstance(inputs, list) or payload.get('inputs_digest') != dependency_digest(inputs):
        raise DataCorruptionError('invalid runtime dependency manifest: ' + path)
    changed = verify_dependencies(project_dir, inputs)
    for record in payload.get('files', []):
        if text_content_hash(os.path.join(project_dir, record['path'])) != record['content_hash']:
            changed.append({'path': record['path'], 'reason': 'generated runtime file changed'})
    if changed:
        raise UserFacingError('stale runtime; prepare again: ' + ', '.join(item.get('path', '') for item in changed))
