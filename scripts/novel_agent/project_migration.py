"""Reviewable, byte-preserving target changes with a recoverable journal.

Only supported YAML scalars and known outline metadata are edited. A transaction
covers several atomic file replacements, not a multi-file atomic operation.
"""
import difflib
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from novel_agent.errors import ConflictError, UserFacingError
from novel_agent.length_profiles import compute_gate_threshold, compute_target_length_profile, resolve_target_profile_from_state
from novel_agent.storage import atomic_write_json, atomic_write_text, project_lock, read_json


STATE_PATHS = ('agent/state_schema_novel.yaml', 'state_schema_novel.yaml', 'state/state_schema_novel.yaml')
OUTLINE_PATHS = tuple(prefix + name for prefix in ('', 'plot/', 'memory/') for name in ('05_chapter_outline.md', '05_chapter_outline_100k.md'))
TARGET_PATHS = STATE_PATHS + OUTLINE_PATHS


def _hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _path(project, relative):
    root = Path(project).resolve()
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise UserFacingError('unsafe migration path: {}'.format(relative))
    try:
        path.resolve().relative_to(root)
    except ValueError:
        raise UserFacingError('migration path leaves project: {}'.format(relative))
    # Replacing even an internal symlink changes its identity; require a normal file.
    if path.is_symlink():
        raise UserFacingError('migration does not replace symlinks: {}'.format(relative))
    return path


def _current_hash(project, relative):
    path = _path(project, relative)
    return _hash_bytes(path.read_bytes()) if path.is_file() else None


def _plan_hash(plan):
    body = {key: value for key, value in plan.items() if key != 'plan_hash'}
    return _hash_bytes(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def _scalar(text, key):
    matches = re.findall(r'(?m)^  ' + re.escape(key) + r':[^\S\r\n]*(.*?)[^\S\r\n]*(?:#.*)?$', text)
    if len(matches) > 1:
        raise ConflictError('duplicate state field: {}'.format(key))
    return matches[0].strip().strip('"\'') if matches else ''


def _yaml_value(value):
    return str(value) if type(value) is int else json.dumps(value, ensure_ascii=False)


def _edit_section(text, section, updates):
    newline = '\r\n' if '\r\n' in text else '\n'
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if re.fullmatch(re.escape(section) + r':[^\S\r\n]*(?:#.*)?\r?\n?', line)]
    if len(starts) > 1:
        raise ConflictError('duplicate state section: {}'.format(section))
    if not starts:
        if any(re.search(r'(?m)^\s*' + re.escape(key) + r':', text) for key in updates):
            raise ConflictError('target fields outside expected {} section'.format(section))
        if text and not text.endswith(('\r', '\n')):
            text += newline
        return text + section + ':' + newline + ''.join('  {}: {}{}'.format(k, _yaml_value(v), newline) for k, v in updates.items())
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if re.match(r'^[^\s#][^:]*:', lines[i])), len(lines))
    for key, value in updates.items():
        indexes = [i for i in range(start + 1, end) if re.match(r'^  ' + re.escape(key) + r':', lines[i])]
        if len(indexes) > 1:
            raise ConflictError('duplicate state field: {}'.format(key))
        if indexes:
            i = indexes[0]
            match = re.fullmatch(r'(  ' + re.escape(key) + r':[^\S\r\n]*)("[^"\r\n]*"|\'[^\'\r\n]*\'|[^#\r\n]*?)([^\S\r\n]*(?:#.*)?)(\r?\n)?', lines[i])
            if not match or match.group(2).strip() in {'|', '>'}:
                raise ConflictError('state field is not a supported scalar: {}'.format(key))
            if match.group(2).strip().strip('"\'') != str(value):
                lines[i] = match.group(1) + _yaml_value(value) + match.group(3) + (match.group(4) or '')
        else:
            if end and not lines[end - 1].endswith(('\r', '\n')):
                lines[end - 1] += newline
            lines.insert(end, '  {}: {}{}'.format(key, _yaml_value(value), newline))
            end += 1
    return ''.join(lines)


def _edit_outline(text, values):
    lines = text.splitlines(keepends=True)
    for label, value in values.items():
        indexes = [i for i, line in enumerate(lines) if re.search(re.escape(label) + r'\s*:', line)]
        if len(indexes) > 1:
            raise ConflictError('duplicate outline label: {}'.format(label))
        if not indexes:
            continue
        i = indexes[0]
        match = re.fullmatch(r'(-[ \t]+' + re.escape(label) + r':[ \t]*)([0-9,]+)([ \t]*(?:#.*)?)(\r?\n)?', lines[i])
        if not match:
            raise ConflictError('ambiguous outline label: {}'.format(label))
        if int(match.group(2).replace(',', '')) != value:
            lines[i] = match.group(1) + str(value) + match.group(3) + (match.group(4) or '')
    return ''.join(lines)


def _planning_totals(outline):
    totals = {'planned_scene_count': 0, 'planned_total_min_chars': 0, 'planned_total_target_chars': 0}
    headers = []
    seen = set()
    for line in outline.splitlines():
        if not line.strip().startswith('|'):
            headers = []
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if 'scene_id' in cells and 'min' in cells and 'target' in cells:
            headers = cells
        elif headers and len(cells) == len(headers):
            row = dict(zip(headers, cells))
            if re.fullmatch(r'\d+-\d+', row['scene_id']):
                if row['scene_id'] in seen:
                    raise ConflictError('duplicate outline scene: {}'.format(row['scene_id']))
                seen.add(row['scene_id'])
                try:
                    minimum = int(row['min'].replace(',', ''))
                    target = int(row['target'].replace(',', ''))
                except ValueError:
                    raise ConflictError('non-numeric scene length: {}'.format(row['scene_id']))
                totals['planned_scene_count'] += 1
                totals['planned_total_min_chars'] += minimum
                totals['planned_total_target_chars'] += target
    return totals


def _migration_directory(project, migration_id):
    if not re.fullmatch(r'[0-9a-f]{32}', migration_id):
        raise UserFacingError('invalid migration ID')
    return _path(project, 'runtime/migrations/' + migration_id)


def plan_target_migration(project_dir: str, *, target_total_chars: int, gate_policy: Optional[str] = None) -> dict:
    """Save a review plan, without changing state, outline, prose, or approvals."""
    target_profile = compute_target_length_profile(target_total_chars)
    if gate_policy not in (None, 'profile', 'preserve'):
        raise UserFacingError('gate_policy must be profile or preserve')
    if not Path(project_dir).is_dir():
        raise UserFacingError('project directory not found: {}'.format(project_dir))
    _path(project_dir, "runtime")
    with project_lock(project_dir):
        before = {relative: _current_hash(project_dir, relative) for relative in TARGET_PATHS}
        state_path = next((p for p in STATE_PATHS if before[p] is not None), None)
        outline_path = next((p for p in OUTLINE_PATHS if before[p] is not None), None)
        if state_path is None:
            raise UserFacingError('state_schema_novel.yaml not found')
        original = _path(project_dir, state_path).read_bytes().decode('utf-8')
        outline = _path(project_dir, outline_path).read_bytes().decode('utf-8') if outline_path else ''
        migration_id = uuid.uuid4().hex
        plan = {
            'version': 1, 'migration_id': migration_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'project': str(Path(project_dir).resolve()),
            'hash_algorithm': 'sha256-bytes-v1', 'target_total_chars': target_total_chars,
            'gate_policy': gate_policy, 'before_hashes': before, 'changes': [], 'conflicts': [],
            'backup_paths': {}, 'affected_artifacts': [],
        }
        try:
            source = resolve_target_profile_from_state(original)
            old_total = source['target_total_chars']
            raw_gate = _scalar(original, 'planning_gate_min_chars')
            if raw_gate and not re.fullmatch(r'\d+', raw_gate):
                raise ConflictError('invalid planning_gate_min_chars')
            current_gate = int(raw_gate) if raw_gate else compute_gate_threshold(old_total)
            legacy_totals = [_scalar(original, key) for key in ('planning_target_total_chars', 'total_chars')]
            default_gates = {compute_gate_threshold(old_total)}
            # A previously hand-updated canonical total may still have a matching old default pair.
            for total in legacy_totals if old_total == target_total_chars else []:
                if total.isdigit():
                    try:
                        default_gates.add(compute_gate_threshold(int(total)))
                    except UserFacingError:
                        pass
            custom_gate = current_gate not in default_gates or _scalar(original, 'planning_gate_policy') == 'custom'
            if custom_gate and gate_policy is None:
                raise ConflictError('custom planning gate requires --gate-policy profile or preserve')
            for label in ('計画ゲート下限', 'gate_threshold'):
                values = re.findall(r'(?m)^-[ \t]+' + re.escape(label) + r':[ \t]*([0-9,]+)[ \t]*(?:#.*)?$', outline)
                for raw in values:
                    outline_gate = int(raw.replace(',', ''))
                    if outline_gate not in default_gates and outline_gate != current_gate and gate_policy != 'profile':
                        raise ConflictError('custom outline gate differs from state; choose --gate-policy profile or reconcile metadata manually')
                    if outline_gate not in default_gates and gate_policy is None:
                        raise ConflictError('custom outline gate requires explicit --gate-policy profile or preserve')
            gate = current_gate if gate_policy == 'preserve' else compute_gate_threshold(target_total_chars)
            policy = 'custom' if gate_policy == 'preserve' and gate != compute_gate_threshold(target_total_chars) else 'profile'
            updates = {'target_total_chars': target_total_chars, 'target_length_profile': target_profile,
                       'planning_target_total_chars': target_total_chars, 'planning_gate_min_chars': gate,
                       'planning_gate_policy': policy}
            if _scalar(original, 'total_chars'):
                updates['total_chars'] = target_total_chars
            after = _edit_section(original, 'targets', updates)
            if old_total != target_total_chars or current_gate != gate:
                after = _edit_section(after, 'active_work', {'planning_gate_status': 'blocked'})
            changed_outline = _edit_outline(outline, {'全体目標文字数': target_total_chars, '計画ゲート下限': gate, 'gate_threshold': gate})
            totals = _planning_totals(outline)
            totals.update({'gate_threshold': gate, 'shortfall_chars': max(0, gate - totals['planned_total_min_chars'])})
            plan['planning'] = totals
            plan['resolved_gate_policy'] = policy
            for relative, old, new in [(state_path, original, after), (outline_path, outline, changed_outline)]:
                if relative is None or old == new:
                    continue
                plan['changes'].append({'path': relative, 'before_hash': before[relative], 'after_hash': _hash_bytes(new.encode('utf-8')),
                                        'after_text': new, 'diff': ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=relative, tofile=relative))})
                plan['backup_paths'][relative] = 'runtime/migrations/{}/backups/{}'.format(migration_id, relative)
            runtime = _path(project_dir, 'runtime')
            plan['affected_artifacts'] = sorted(str(p.relative_to(Path(project_dir).resolve())).replace(os.sep, '/') for p in runtime.rglob('*') if p.is_file() and 'migrations' not in p.relative_to(runtime).parts and p.name != '.project_write.lock')
        except (ConflictError, UserFacingError) as exc:
            plan['conflicts'].append({'reason': str(exc)})
            plan['changes'] = []
            plan['backup_paths'] = {}
        plan['plan_hash'] = _plan_hash(plan)
        directory = _migration_directory(project_dir, migration_id)
        atomic_write_json(str(directory / 'plan.json'), plan)
        return plan


def _validate_plan(project, plan, expected_plan_hash):
    if plan.get('version') != 1 or plan.get('hash_algorithm') != 'sha256-bytes-v1':
        raise ConflictError('unsupported migration plan version or hash algorithm')
    if plan.get('plan_hash') != expected_plan_hash or _plan_hash(plan) != expected_plan_hash:
        raise ConflictError('migration plan hash mismatch; run dry-run and review again')
    if plan.get('project') != str(Path(project).resolve()):
        raise ConflictError('migration plan belongs to a different project')
    if plan.get('conflicts'):
        raise ConflictError('migration plan has conflicts; resolve them and run dry-run again')
    if set(plan.get('before_hashes', {})) != set(TARGET_PATHS):
        raise ConflictError('invalid migration source inventory')
    paths = set()
    for change in plan.get('changes', []):
        relative = change['path']
        if relative not in TARGET_PATHS or relative in paths or plan['before_hashes'][relative] != change['before_hash']:
            raise ConflictError('invalid migration change path')
        paths.add(relative)
        if _hash_bytes(change['after_text'].encode('utf-8')) != change['after_hash']:
            raise ConflictError('migration after-content hash mismatch')
        expected_backup = 'runtime/migrations/{}/backups/{}'.format(plan['migration_id'], relative)
        if plan['backup_paths'].get(relative) != expected_backup:
            raise ConflictError('invalid migration backup path')
        _path(project, relative)
    _migration_directory(project, plan['migration_id'])


def _verify_snapshot(project, plan, allow_after=False, require_after=False):
    changes = {change['path']: change for change in plan['changes']}
    for relative, before in plan['before_hashes'].items():
        current = _current_hash(project, relative)
        allowed = {before}
        if relative in changes:
            if allow_after:
                allowed.add(changes[relative]['after_hash'])
            if require_after:
                allowed = {changes[relative]['after_hash']}
        if current not in allowed:
            raise ConflictError('file changed since migration review: {}; preserve edits and run dry-run again'.format(relative))


def _load_journal(directory):
    journal = read_json(str(directory / 'journal.json'), default_factory=dict)
    if journal and (journal.get('version') != 1 or journal.get('status') not in {'prepared', 'committed', 'rolling_back', 'rolled_back'}):
        raise ConflictError('unsupported migration journal; retain backups for manual recovery')
    if journal and (not isinstance(journal.get('plan_hash'), str) or
                    not isinstance(journal.get('applied'), list) or
                    any(not isinstance(path, str) or path not in TARGET_PATHS for path in journal['applied'])):
        raise ConflictError('invalid migration journal fields; retain backups for manual recovery')
    return journal


def apply_target_migration(project_dir: str, plan: dict, *, expected_plan_hash: str) -> dict:
    _validate_plan(project_dir, plan, expected_plan_hash)
    _path(project_dir, "runtime")
    with project_lock(project_dir):
        directory = _migration_directory(project_dir, plan['migration_id'])
        journal = _load_journal(directory)
        if journal and journal.get('plan_hash') != expected_plan_hash:
            raise ConflictError('journal does not match reviewed plan')
        if journal.get('status') == 'committed':
            _verify_snapshot(project_dir, plan, require_after=True)
            return {'status': 'noop', 'migration_id': plan['migration_id']}
        if journal.get('status') in {'rolling_back', 'rolled_back'}:
            raise ConflictError('migration was rolled back or rollback is pending; finish rollback or create a new plan')
        _verify_snapshot(project_dir, plan, allow_after=bool(journal))
        # Backups precede prepared journal and all source changes. Existing backups
        # must match, so interrupted backup creation is safe to resume as well.
        for change in plan['changes']:
            backup = _path(project_dir, plan['backup_paths'][change['path']])
            if backup.exists():
                if _hash_bytes(backup.read_bytes()) != change['before_hash']:
                    raise ConflictError('backup hash mismatch: {}'.format(backup))
            elif journal:
                raise ConflictError('prepared migration backup is missing: {}'.format(backup))
            else:
                atomic_write_text(str(backup), _path(project_dir, change['path']).read_bytes().decode('utf-8'))
        if not journal:
            atomic_write_json(str(directory / 'plan.json'), plan)
            journal = {'version': 1, 'status': 'prepared', 'plan_hash': expected_plan_hash, 'applied': []}
            atomic_write_json(str(directory / 'journal.json'), journal)
        try:
            for change in plan['changes']:
                _verify_snapshot(project_dir, plan, allow_after=True)
                if _current_hash(project_dir, change['path']) != change['after_hash']:
                    atomic_write_text(str(_path(project_dir, change['path'])), change['after_text'])
                if change['path'] not in journal['applied']:
                    journal['applied'].append(change['path'])
                atomic_write_json(str(directory / 'journal.json'), journal)
            _verify_snapshot(project_dir, plan, require_after=True)
            journal['status'] = 'committed'
            atomic_write_json(str(directory / 'journal.json'), journal)
        except Exception as exc:
            raise UserFacingError('migration {} interrupted: {}; resume --apply-plan or use --rollback {}'.format(plan['migration_id'], exc, plan['migration_id'])) from exc
        return {'status': 'committed' if plan['changes'] else 'noop', 'migration_id': plan['migration_id'],
                'planning': plan.get('planning', {}), 'runtime_requires_refresh': bool(plan['changes']),
                'affected_artifacts': plan['affected_artifacts']}


def rollback_target_migration(project_dir: str, migration_id: str) -> dict:
    directory = _migration_directory(project_dir, migration_id)
    _path(project_dir, "runtime")
    with project_lock(project_dir):
        plan = read_json(str(directory / 'plan.json'), default_factory=dict)
        _validate_plan(project_dir, plan, plan.get('plan_hash'))
        journal = _load_journal(directory)
        if not journal or journal.get('plan_hash') != plan['plan_hash']:
            raise ConflictError('migration has no matching journal to roll back')
        if journal['status'] == 'rolled_back':
            _verify_snapshot(project_dir, plan)
            return {'status': 'noop', 'migration_id': migration_id}
        _verify_snapshot(project_dir, plan, allow_after=True)
        originals = []
        for change in plan['changes']:
            backup = _path(project_dir, plan['backup_paths'][change['path']])
            if not backup.is_file() or _hash_bytes(backup.read_bytes()) != change['before_hash']:
                raise ConflictError('backup missing or changed: {}'.format(backup))
            originals.append((change['path'], backup.read_bytes().decode('utf-8')))
        journal['status'] = 'rolling_back'
        atomic_write_json(str(directory / 'journal.json'), journal)
        try:
            for relative, original in originals:
                _verify_snapshot(project_dir, plan, allow_after=True)
                atomic_write_text(str(_path(project_dir, relative)), original)
            _verify_snapshot(project_dir, plan)
            journal['status'] = 'rolled_back'
            atomic_write_json(str(directory / 'journal.json'), journal)
        except Exception as exc:
            raise UserFacingError('rollback {} interrupted: {}; retry --rollback {}'.format(migration_id, exc, migration_id)) from exc
        return {'status': 'rolled_back', 'migration_id': migration_id, 'runtime_requires_refresh': True}
