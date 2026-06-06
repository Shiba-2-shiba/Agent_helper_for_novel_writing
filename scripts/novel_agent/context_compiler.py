import json
import os
import re
from datetime import datetime, timezone

from novel_agent.context_blocks import build_excerpt, make_block
from prompt_utils import (
    collect_scene_metadata,
    ensure_directory,
    parse_scene_reference,
    read_text_file,
    resolve_outline_path,
    resolve_runtime_dir,
    runtime_root_dir,
    write_json_file,
    write_text_file,
)


def _line_count(text):
    return text.count("\n") + (1 if text else 0)


def _read_lines(path):
    text = read_text_file(path)
    return text, text.splitlines()


def _add_whole_file_block(blocks, *, role, block_id, path, project_dir, title):
    if not os.path.isfile(path):
        return
    text = read_text_file(path)
    if not text.strip():
        return
    blocks.append(
        make_block(
            block_id=block_id,
            role=role,
            source_path=path,
            project_dir=project_dir,
            start_line=1,
            end_line=_line_count(text),
            title=title,
            content=text,
        )
    )


def _collect_outline_blocks(project_dir, chapter_num, scene_ref):
    blocks = []
    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if not os.path.isfile(outline_path):
        return blocks

    text, lines = _read_lines(outline_path)
    _add_whole_file_block(
        blocks,
        role="outline",
        block_id="outline:full",
        path=outline_path,
        project_dir=project_dir,
        title="Outline Full",
    )

    chapter_pattern = re.compile(rf"^#{{1,6}}\s*第{chapter_num}章")
    any_chapter_pattern = re.compile(r"^#{1,6}\s*第\d+章")
    chapter_start = None
    for index, line in enumerate(lines, start=1):
        if chapter_pattern.match(line.strip()):
            chapter_start = index
            break
    if chapter_start is None:
        return blocks

    chapter_end = len(lines)
    for index in range(chapter_start + 1, len(lines) + 1):
        if any_chapter_pattern.match(lines[index - 1].strip()):
            chapter_end = index - 1
            break
    chapter_text = "\n".join(lines[chapter_start - 1:chapter_end])
    blocks.append(
        make_block(
            block_id=f"outline:chapter:{chapter_num}",
            role="outline_chapter",
            source_path=outline_path,
            project_dir=project_dir,
            start_line=chapter_start,
            end_line=chapter_end,
            title=f"Chapter {chapter_num} Outline",
            content=chapter_text,
        )
    )

    target_scene = scene_ref["canonical_id"]
    for index, line in enumerate(lines[chapter_start - 1:chapter_end], start=chapter_start):
        if target_scene in line and line.strip().startswith("|"):
            blocks.append(
                make_block(
                    block_id=f"outline:scene:{target_scene}",
                    role="outline_scene",
                    source_path=outline_path,
                    project_dir=project_dir,
                    start_line=index,
                    end_line=index,
                    title=f"Scene Ledger {target_scene}",
                    content=line,
                    summary=f"Scene Ledger row for {target_scene}",
                )
            )
            break

    return blocks


def _collect_scene_blocks(project_dir):
    blocks = []
    for item in collect_scene_metadata(project_dir):
        path = item["path"]
        text = read_text_file(path)
        scene_id = f"{item['chapter']}-{item['scene']}"
        blocks.append(
            make_block(
                block_id=f"scene:{scene_id}",
                role="scene_text",
                source_path=path,
                project_dir=project_dir,
                start_line=1,
                end_line=_line_count(text),
                title=f"Scene {scene_id}",
                content=text,
            )
        )
    return blocks


def _collect_runtime_blocks(project_dir, mode, scene_ref, runtime_dir_arg=""):
    blocks = []
    runtime_dir = resolve_runtime_dir(project_dir, mode=mode, scene_ref=scene_ref, runtime_dir_arg=runtime_dir_arg)
    if not os.path.isdir(runtime_dir):
        return blocks

    for name in sorted(os.listdir(runtime_dir)):
        path = os.path.join(runtime_dir, name)
        if not os.path.isfile(path):
            continue
        root, ext = os.path.splitext(name)
        if ext.lower() == ".md":
            _add_whole_file_block(
                blocks,
                role="runtime",
                block_id=f"runtime:{root}",
                path=path,
                project_dir=project_dir,
                title=f"Runtime {name}",
            )
        elif name == "check_report.json":
            payload = json.loads(read_text_file(path))
            content = json.dumps(payload, ensure_ascii=False, indent=2)
            blocks.append(
                make_block(
                    block_id="runtime:check_report",
                    role="check_report",
                    source_path=path,
                    project_dir=project_dir,
                    start_line=1,
                    end_line=_line_count(content),
                    title="Runtime Check Report",
                    content=content,
                    summary=f"check_report status={payload.get('status', 'unknown')} needs_expand={payload.get('needs_expand')}",
                )
            )
    return blocks


def collect_context_blocks(project_dir, *, chapter, scene, mode, runtime_dir_arg=""):
    scene_ref = parse_scene_reference(scene)
    blocks = []
    blocks.extend(_collect_outline_blocks(project_dir, chapter, scene_ref))
    blocks.extend(_collect_scene_blocks(project_dir))
    blocks.extend(_collect_runtime_blocks(project_dir, mode, scene_ref, runtime_dir_arg=runtime_dir_arg))
    return blocks


def render_full(blocks):
    lines = []
    for block in blocks:
        lines.extend(
            [
                f">>> {block.id} [{block.role}]",
                f"source: {block.source_path}:{block.start_line}-{block.end_line}",
                f"title: {block.title}",
                "",
                block.content,
                f"<<< {block.id}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_min(blocks):
    lines = []
    for block in blocks:
        lines.append(
            f"* {block.title} ({block.source_path}:{block.start_line}-{block.end_line}) "
            f"[{block.role}] tokens~{block.tokens_estimate}"
        )
        if block.summary:
            lines.append(f"  {block.summary}")
    return "\n".join(lines).rstrip() + "\n"


def _matching_lines(block, regex):
    hits = []
    for offset, line in enumerate(block.content.splitlines(), start=block.start_line):
        if regex.search(line):
            hits.append((offset, line))
    return hits


def render_view(blocks, grep_pattern):
    if not grep_pattern:
        return ""
    regex = re.compile(grep_pattern)
    lines = []
    for block in blocks:
        hits = _matching_lines(block, regex)
        if not hits:
            continue
        lines.append(f"({block.source_path}:{block.start_line}-{block.end_line}) [{block.role}] {block.title}")
        for line_no, line in hits:
            lines.append(f"  {line_no}: {line}")
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def write_context_outputs(project_dir, *, chapter, scene, mode, blocks, grep_pattern=None):
    context_dir = os.path.join(runtime_root_dir(project_dir), "context")
    ensure_directory(context_dir)
    full_path = os.path.join(context_dir, "context_full.txt")
    min_path = os.path.join(context_dir, "context_min.txt")
    view_path = os.path.join(context_dir, "context_view.txt")
    index_path = os.path.join(context_dir, "context_index.json")

    write_text_file(full_path, render_full(blocks))
    write_text_file(min_path, render_min(blocks))
    if grep_pattern:
        write_text_file(view_path, render_view(blocks, grep_pattern))

    payload = {
        "version": 1,
        "project": project_dir,
        "chapter": chapter,
        "scene": parse_scene_reference(scene)["canonical_id"],
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blocks": [block.to_index_entry() for block in blocks],
    }
    write_json_file(index_path, payload)
    return {
        "context_dir": context_dir,
        "full_path": full_path,
        "min_path": min_path,
        "view_path": view_path if grep_pattern else "",
        "index_path": index_path,
    }
