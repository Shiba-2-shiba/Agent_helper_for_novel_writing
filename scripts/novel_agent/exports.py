import os
import re

from novel_agent.approvals import refresh_approval_statuses
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


def _approved_records(project_dir):
    payload = refresh_approval_statuses(project_dir)
    return {
        scene_id: record
        for scene_id, record in payload.get("scenes", {}).items()
        if isinstance(record, dict) and record.get("status") == "approved"
    }


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


def _fallback_scene_order(project_dir):
    return [f"{item['chapter']}-{item['scene']}" for item in collect_scene_metadata(project_dir)]


def export_manuscript(project_dir, *, include_warnings=False, output_path=""):
    approved = _approved_records(project_dir)
    stale = [
        scene_id
        for scene_id, record in refresh_approval_statuses(project_dir).get("scenes", {}).items()
        if isinstance(record, dict) and record.get("status") == "stale"
    ]
    if stale:
        raise UserFacingError("stale approval detected: " + ", ".join(sorted(stale)))

    ordered_ids = _outline_scene_order(project_dir) or _fallback_scene_order(project_dir)
    selected = []
    for scene_id in ordered_ids:
        record = approved.get(scene_id)
        if not record:
            continue
        if record.get("check_status") == "warning" and not include_warnings:
            continue
        selected.append((scene_id, record))

    if not selected:
        raise UserFacingError("no approved scenes available for export")

    lines = [f"# {os.path.basename(os.path.normpath(project_dir))}", ""]
    current_chapter = None
    for scene_id, record in selected:
        chapter = scene_id.split("-", 1)[0]
        if chapter != current_chapter:
            current_chapter = chapter
            lines.extend([f"## 第{chapter}章", ""])
        scene_path = os.path.join(project_dir, record.get("scene_path", ""))
        lines.append(read_text_file(scene_path).strip())
        lines.append("")

    output_path = output_path or os.path.join(project_dir, "exports", "manuscript.md")
    ensure_directory(os.path.dirname(output_path))
    write_text_file(output_path, "\n".join(lines).rstrip() + "\n")
    return {"output_path": output_path, "scene_count": len(selected), "scenes": [scene_id for scene_id, _ in selected]}

