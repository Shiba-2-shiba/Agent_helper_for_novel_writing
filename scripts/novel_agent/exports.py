import os
import re

from novel_agent.approvals import _refresh_approval_statuses_locked
from novel_agent.storage import project_lock
from prompt_utils import (
    UserFacingError,
    collect_scene_metadata,
    ensure_directory,
    extract_chapter_block,
    parse_scene_ledger,
    read_text_file,
    resolve_outline_path,
    write_text_file,
)


def _outline_scene_order(project_dir):
    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if not os.path.isfile(outline_path):
        return []
    outline_text = read_text_file(outline_path)
    chapter_numbers = sorted({int(match.group(1)) for match in re.finditer(r"(?m)^#{1,6}\s*第(\d+)章", outline_text)})
    ordered = []
    for chapter_num in chapter_numbers:
        chapter_block = extract_chapter_block(outline_text, chapter_num)
        for row in parse_scene_ledger(chapter_block):
            if row.get("canonical_id"):
                ordered.append(row["canonical_id"])
    return ordered


def export_manuscript(project_dir, *, include_warnings=False, output_path="", title=None, require_complete=False):
    if title is not None and (not title.strip() or len(title.splitlines()) != 1):
        raise UserFacingError("title must be a non-empty single line")
    with project_lock(project_dir):
        return _export_manuscript_locked(project_dir, include_warnings=include_warnings, output_path=output_path,
                                         title=title, require_complete=require_complete)


def _export_manuscript_locked(project_dir, *, include_warnings=False, output_path="", title=None, require_complete=False):
    records = _refresh_approval_statuses_locked(project_dir).get("scenes", {})
    stale = [
        scene_id
        for scene_id, record in records.items()
        if isinstance(record, dict) and record.get("status") == "stale"
    ]
    if stale:
        raise UserFacingError("stale approval detected: " + ", ".join(sorted(stale)))

    inventory_ids = [f"{item['chapter']}-{item['scene']}" for item in collect_scene_metadata(project_dir)]
    available_ids = set(inventory_ids)
    ordered_ids = _outline_scene_order(project_dir) or inventory_ids
    selected = []
    omitted = []
    for scene_id in ordered_ids:
        record = records.get(scene_id)
        if scene_id not in available_ids:
            omitted.append({"scene_id": scene_id, "reason": "scene_missing"})
            continue
        if not record or record.get("status") != "approved":
            omitted.append({"scene_id": scene_id, "reason": "not_approved"})
            continue
        if record.get("check_status") == "warning" and not include_warnings:
            omitted.append({"scene_id": scene_id, "reason": "warning_excluded"})
            continue
        selected.append((scene_id, record))

    omissions = ", ".join("{scene_id} ({reason})".format(**item) for item in omitted)
    if require_complete and omitted:
        raise UserFacingError("incomplete manuscript; omitted scenes: " + omissions)
    if not selected:
        message = "no approved scenes available for export"
        raise UserFacingError(message + ("; omitted scenes: " + omissions if omitted else ""))

    title = title.strip() if title is not None else os.path.basename(os.path.normpath(project_dir))
    lines = [f"# {title}", ""]
    current_chapter = None
    for scene_id, record in selected:
        chapter = scene_id.split("-", 1)[0]
        if chapter != current_chapter:
            current_chapter = chapter
            lines.extend([f"## 第{chapter}章", ""])
        scene_path = os.path.join(project_dir, record.get("scene_path", ""))
        # Preserve the approved source verbatim, including indentation, boundary
        # whitespace, and line endings. Separators belong to the export only.
        with open(scene_path, "r", encoding="utf-8", newline="") as handle:
            lines.append(handle.read())
        lines.append("")

    output_path = output_path or os.path.join(project_dir, "exports", "manuscript.md")
    ensure_directory(os.path.dirname(output_path))
    write_text_file(output_path, "\n".join(lines) + "\n")
    return {"output_path": output_path, "scene_count": len(selected),
            "scenes": [scene_id for scene_id, _ in selected],
            "complete": not omitted, "omitted_scenes": omitted}

