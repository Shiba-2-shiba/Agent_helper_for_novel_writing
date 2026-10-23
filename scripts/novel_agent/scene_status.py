"""Derive all progress projections from current text, checks and approvals.

A projection is not a new source of truth. Each file is replaced atomically,
while a project lock protects the shared read/modify/write boundary. A failed
multi-file update can be repaired by collecting and projecting again.
"""
import json
import os
import re
from datetime import datetime, timezone

from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.storage import atomic_write_json, atomic_write_text, project_lock, read_json


_CHECK_STATUSES = {'pass', 'warning', 'fail'}


def derive_scene_status(*, text_exists, report, check_current):
    if not text_exists:
        return 'planned'
    if not report or not check_current:
        return 'drafted'
    if report.get('status') == 'fail':
        return 'needs_repair'
    if report.get('status') == 'pass':
        return 'completed'
    return 'drafted'


def _read_text(path):
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return handle.read()


def _scene_order(scene_id):
    return tuple(int(part) for part in scene_id.split('-'))


def _load_scene_report(project_dir, scene_id, artifact_ledger=None):
    # Registered custom destinations are allowed, but every candidate must
    # identify this exact scene. Never consult another scene's latest pointer.
    from novel_agent.ledgers import read_artifact_ledger
    candidates = {os.path.join(project_dir, 'runtime', 'scenes', scene_id, 'draft', 'check_report.json'),
                  os.path.join(project_dir, 'runtime', 'check_report.json')}
    if artifact_ledger is None:
        artifact_ledger = read_artifact_ledger(project_dir)
    for artifact in artifact_ledger.get('artifacts', []):
        if artifact.get('type') == 'check_report' and artifact.get('path'):
            candidates.add(os.path.join(project_dir, artifact['path']))
    reports = []
    for path in candidates:
        if not os.path.isfile(path):
            continue
        payload = read_json(path, default_factory=dict)
        canonical = path == os.path.join(project_dir, 'runtime', 'scenes', scene_id, 'draft', 'check_report.json')
        if payload.get('scene_id') == scene_id or (canonical and payload.get('version') != 2):
            reports.append((payload.get('checked_at', ''), os.path.getmtime(path), path, payload))
    if not reports:
        return None, ''
    _, _, path, payload = max(reports, key=lambda item: item[:3])
    return payload, path


def collect_project_status(project_dir):
    # Import at the operation boundary: prompt_utils re-exports public APIs and
    # story_state delegates back to this module, so importing them eagerly
    # would create a cycle.
    from novel_agent.approvals import approval_status_for_scene, validate_check_identity
    from novel_agent.story_state import load_story_state
    from prompt_utils import (
        collect_scene_metadata, extract_chapter_block, parse_scene_ledger,
        parse_scene_reference, read_text_file, resolve_outline_path,
    )

    refs = {}
    paths = {}
    for item in collect_scene_metadata(project_dir):
        scene_id = '{}-{}'.format(item['chapter'], item['scene'])
        refs[scene_id] = parse_scene_reference(scene_id)
        paths[scene_id] = item['path']

    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if os.path.isfile(outline_path):
        outline = read_text_file(outline_path)
        chapters = {int(match.group(1)) for match in re.finditer(r'(?m)^#{1,6}\s*第(\d+)章', outline)}
        for chapter in sorted(chapters):
            for row in parse_scene_ledger(extract_chapter_block(outline, chapter)):
                if row['canonical_id']:
                    refs[row['canonical_id']] = parse_scene_reference(row['canonical_id'])

    state = load_story_state(project_dir)
    for scene_id in state.get('scenes', {}):
        # Preserve user keys that are not canonical scene identifiers, without
        # treating them as scenes or converting them to generated records.
        if re.fullmatch(r'[1-9]\d*-[1-9]\d*', scene_id):
            refs.setdefault(scene_id, parse_scene_reference(scene_id))

    progress = {
        'written_scene_count': 0,
        'checked_scene_count': 0,
        'completed_scene_count': 0,
        'approved_scene_count': 0,
        'total_chars_written': 0,
        'last_checked_scene': '',
        'last_completed_scene': '',
    }
    scenes = {}
    # Reuse a strictly validated snapshot only within this collection. The next
    # operation must read again, including any corruption or custom reports.
    from novel_agent.ledgers import read_artifact_ledger
    artifact_ledger = read_artifact_ledger(project_dir) if refs else None
    for scene_id in sorted(refs, key=_scene_order):
        scene_ref = refs[scene_id]
        path = paths.get(scene_id, '')
        text_exists = bool(path and os.path.isfile(path))
        actual_chars = len(read_text_file(path)) if text_exists else 0
        report, report_path = _load_scene_report(project_dir, scene_id, artifact_ledger)
        current = False
        reasons = []
        if text_exists and report is not None:
            try:
                validate_check_identity(project_dir, scene_ref, path, report)
                current = report.get('status') in _CHECK_STATUSES
                if not current:
                    reasons.append('check status is not recognized')
            except DataCorruptionError:
                raise
            except UserFacingError as exc:
                reasons.append(str(exc))
        status = derive_scene_status(text_exists=text_exists, report=report, check_current=current)
        approval = approval_status_for_scene(project_dir, scene_id)
        approval_status = approval.get('status', 'none') if approval else 'none'
        scenes[scene_id] = {
            'status': status,
            'path': path,
            'actual_chars': actual_chars,
            'check_status': report.get('status', 'unknown') if report else 'unknown',
            'check_current': current,
            'check_report_path': report_path,
            'check_stale_reasons': reasons,
            'approval_status': approval_status,
            'needs_expand': report.get('needs_expand', False) if current else False,
            'blocking_issue_count': len(report.get('blocking_issues', [])) if current else 0,
            'warning_count': len(report.get('warnings', [])) if current else 0,
        }
        if text_exists:
            progress['written_scene_count'] += 1
            progress['total_chars_written'] += actual_chars
        if current:
            progress['checked_scene_count'] += 1
            progress['last_checked_scene'] = scene_id
        if status == 'completed':
            progress['completed_scene_count'] += 1
            progress['last_completed_scene'] = scene_id
        if text_exists and approval_status == 'approved':
            progress['approved_scene_count'] += 1
    return {'scenes': scenes, 'progress': progress}


def _render_yaml_section(text, section_name, values):
    """Edit direct section scalars, retaining comments and other YAML."""
    ending = '\r\n' if '\r\n' in text else '\n'
    lines = text.splitlines(keepends=True)
    section = next((index for index, line in enumerate(lines)
                    if re.match(r'^' + re.escape(section_name) + r'\s*:\s*(?:#.*)?$', line.rstrip('\r\n'))), None)
    if section is None:
        if lines and not lines[-1].endswith(('\n', '\r')):
            lines[-1] += ending
        lines.append(section_name + ':' + ending)
        section = len(lines) - 1
    end = len(lines)
    for index in range(section + 1, len(lines)):
        if re.match(r'^[^\s#][^:]*:', lines[index]):
            end = index
            break
    for key, value in values.items():
        rendered = str(value) if isinstance(value, int) else json.dumps(value, ensure_ascii=False)
        pattern = re.compile(r'^(  ' + re.escape(key) + r':\s*)(.*?)([ \t]+#.*)?$')
        for index in range(section + 1, end):
            body = lines[index].rstrip('\r\n')
            match = pattern.match(body)
            if match:
                newline = lines[index][len(body):]
                lines[index] = match.group(1) + rendered + (match.group(3) or '') + newline
                break
        else:
            if end and not lines[end - 1].endswith(('\n', '\r')):
                lines[end - 1] += ending
            lines.insert(end, '  {}: {}{}'.format(key, rendered, ending))
            end += 1
    return ''.join(lines)


def _render_progress(text, progress):
    """Render progress for read-only projection comparisons such as health."""
    return _render_yaml_section(text, 'progress', progress)


def _render_outline(text, scenes):
    """Change a status cell only, without re-rendering user-authored rows."""
    lines = text.splitlines(keepends=True)
    chapter = None
    in_ledger = False
    header = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        heading = re.match(r'^#{1,6}\s*第(\d+)章', stripped)
        if heading:
            chapter = int(heading.group(1))
            in_ledger = False
            header = None
        if stripped.startswith('### Scene Ledger'):
            in_ledger = True
            header = None
            continue
        if not in_ledger:
            continue
        if stripped.startswith('#') or (not stripped and header is not None):
            in_ledger = False
            continue
        if not stripped.startswith('|') or not stripped.endswith('|'):
            continue
        raw_cells = line.split('|')
        cells = [cell.strip() for cell in raw_cells[1:-1]]
        if header is None:
            if 'scene_id' in cells and 'status' in cells:
                header = cells
            continue
        if len(cells) != len(header) or all(re.fullmatch(r'[:\s-]+', cell) for cell in cells):
            continue
        raw_id = cells[header.index('scene_id')]
        if re.fullmatch(r'\d+', raw_id) and chapter is not None:
            scene_id = '{}-{}'.format(chapter, int(raw_id))
        elif re.fullmatch(r'\d+-\d+', raw_id):
            scene_id = '{}-{}'.format(*_scene_order(raw_id))
        else:
            continue
        if scene_id not in scenes:
            continue
        cell_index = header.index('status') + 1
        cell = raw_cells[cell_index]
        leading = re.match(r'^\s*', cell).group(0)
        trailing = re.search(r'\s*$', cell).group(0)
        raw_cells[cell_index] = leading + scenes[scene_id]['status'] + trailing
        lines[index] = '|'.join(raw_cells)
    return ''.join(lines)


def _sync_status_projections_locked(project_dir, snapshot):
    """Project an already collected snapshot; the caller must hold the lock."""
    from novel_agent.story_state import load_story_state, story_state_path
    from prompt_utils import find_state_schema_path, parse_scene_reference, resolve_outline_path

    payload = load_story_state(project_dir)
    for scene_id, values in snapshot['scenes'].items():
        existing = payload['scenes'].get(scene_id, {})
        if not isinstance(existing, dict):
            raise DataCorruptionError('invalid scene record at {}: {}'.format(story_state_path(project_dir), scene_id))
        payload['scenes'][scene_id] = dict(existing, **values)
    progress = dict(snapshot['progress'])
    active_work = None
    if 'active_scene' in snapshot:
        ref = parse_scene_reference(snapshot['active_scene'])
        payload['active_scene'] = ref['canonical_id']
        progress.update(current_chapter=ref['chapter'], current_scene=ref['canonical_id'])
        active_work = {'active_chapter': ref['chapter'], 'active_scene': ref['canonical_id']}
    payload['progress'].update(progress)
    payload['updated_at'] = datetime.now(timezone.utc).isoformat()

    # Prepare all file contents before writing anything, so invalid inputs do
    # not needlessly produce a partial projection.
    writes = []
    state_path = find_state_schema_path(project_dir)
    if state_path:
        before = _read_text(state_path)
        after = _render_yaml_section(before, 'progress', progress)
        if active_work is not None:
            after = _render_yaml_section(after, 'active_work', active_work)
        if before != after:
            writes.append((state_path, after))
    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if os.path.isfile(outline_path):
        before = _read_text(outline_path)
        after = _render_outline(before, snapshot['scenes'])
        if before != after:
            writes.append((outline_path, after))

    atomic_write_json(story_state_path(project_dir), payload)
    for path, text in writes:
        atomic_write_text(path, text)


def sync_status_projections(project_dir, snapshot):
    # A caller may have collected before another writer changed the text or
    # approvals. Recollect under the lock rather than restore stale statuses.
    with project_lock(project_dir):
        current = collect_project_status(project_dir)
        if 'active_scene' in snapshot:
            current['active_scene'] = snapshot['active_scene']
        _sync_status_projections_locked(project_dir, current)
