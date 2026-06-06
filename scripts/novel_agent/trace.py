import json
import os
import re
from datetime import datetime, timezone

from prompt_utils import ensure_directory, read_text_file, write_text_file


def trace_dir(project_dir):
    return os.path.join(project_dir, "agent", "trace")


def trace_log_path(project_dir):
    return os.path.join(trace_dir(project_dir), "trace.jsonl")


def _shorten(value, limit=500):
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def append_trace_event(
    project_dir,
    *,
    event_type,
    chapter=None,
    scene="",
    summary="",
    artifacts=None,
    decision=None,
    evidence=None,
    tokens_estimate=None,
):
    ensure_directory(trace_dir(project_dir))
    event = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "chapter": chapter,
        "scene": scene or "",
        "summary": _shorten(summary),
        "artifacts": list(artifacts or []),
        "decision": _shorten(decision) if decision else None,
        "evidence": [_shorten(item, 240) for item in (evidence or [])],
        "tokens_estimate": tokens_estimate,
    }
    with open(trace_log_path(project_dir), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def read_trace_events(project_dir):
    path = trace_log_path(project_dir)
    if not os.path.isfile(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def render_trace_full(events):
    lines = []
    for index, event in enumerate(events, start=1):
        lines.extend(
            [
                f">>> trace:{index} [{event.get('event_type', 'unknown')}]",
                f"created_at: {event.get('created_at', '')}",
                f"chapter: {event.get('chapter')}",
                f"scene: {event.get('scene', '')}",
                f"summary: {event.get('summary', '')}",
                f"artifacts: {', '.join(event.get('artifacts', []))}",
                f"decision: {event.get('decision') or '-'}",
                f"tokens_estimate: {event.get('tokens_estimate')}",
                "<<< trace",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def render_trace_min(events):
    lines = []
    for index, event in enumerate(events, start=1):
        scene = event.get("scene") or "-"
        chapter = event.get("chapter")
        chapter_part = f" ch{chapter}" if chapter else ""
        lines.append(
            f"* trace:{index} [{event.get('event_type', 'unknown')}]{chapter_part} scene={scene} "
            f"tokens={event.get('tokens_estimate')} - {event.get('summary', '')}"
        )
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def render_trace_view(events, grep_pattern):
    if not grep_pattern:
        return ""
    regex = re.compile(grep_pattern)
    lines = []
    for index, event in enumerate(events, start=1):
        rendered = json.dumps(event, ensure_ascii=False, sort_keys=True)
        if not regex.search(rendered):
            continue
        lines.append(f"(trace.jsonl:{index}-{index}) [{event.get('event_type', 'unknown')}]")
        lines.append(f"  {index}: {rendered}")
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def compile_trace(project_dir, grep_pattern=""):
    events = read_trace_events(project_dir)
    ensure_directory(trace_dir(project_dir))
    full_path = os.path.join(trace_dir(project_dir), "trace_full.txt")
    min_path = os.path.join(trace_dir(project_dir), "trace_min.txt")
    view_path = os.path.join(trace_dir(project_dir), "trace_view.txt")
    write_text_file(full_path, render_trace_full(events))
    write_text_file(min_path, render_trace_min(events))
    if grep_pattern:
        write_text_file(view_path, render_trace_view(events, grep_pattern))
    return {
        "events": events,
        "full_path": full_path,
        "min_path": min_path,
        "view_path": view_path if grep_pattern else "",
    }
