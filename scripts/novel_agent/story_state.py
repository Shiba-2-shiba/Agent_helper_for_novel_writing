import json
import os
from datetime import datetime, timezone

from prompt_utils import (
    count_completed_scene_files,
    count_total_written_chars,
    read_text_file,
    runtime_root_dir,
    write_json_file,
)


def story_state_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "story_state.json")


def empty_story_state():
    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "active_scene": "",
        "progress": {
            "completed_scene_count": 0,
            "total_chars_written": 0,
        },
        "scenes": {},
        "characters": {},
        "threads": {},
        "payoffs": {},
        "timeline": [],
        "open_questions": [],
        "continuity_findings": [],
    }


def load_story_state(project_dir):
    path = story_state_path(project_dir)
    if not os.path.isfile(path):
        return empty_story_state()
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return empty_story_state()
    if not isinstance(payload, dict):
        return empty_story_state()
    base = empty_story_state()
    base.update(payload)
    base.setdefault("progress", {})
    base.setdefault("scenes", {})
    base.setdefault("characters", {})
    base.setdefault("threads", {})
    base.setdefault("payoffs", {})
    base.setdefault("timeline", [])
    base.setdefault("open_questions", [])
    base.setdefault("continuity_findings", [])
    return base


def save_story_state(project_dir, payload):
    payload["version"] = 1
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json_file(story_state_path(project_dir), payload)
    return payload


def initialize_story_state(project_dir):
    return save_story_state(project_dir, load_story_state(project_dir))


def update_story_state_from_check(project_dir, scene_ref, report):
    payload = load_story_state(project_dir)
    scene_id = scene_ref["canonical_id"] if scene_ref else ""
    if scene_id:
        status = "completed" if report.get("status") == "pass" else "needs_repair"
        if report.get("status") == "warning":
            status = "drafted"
        payload["active_scene"] = scene_id
        payload["scenes"][scene_id] = {
            "status": status,
            "path": report.get("target_file", ""),
            "actual_chars": report.get("actual_chars", 0),
            "check_status": report.get("status", "unknown"),
            "needs_expand": report.get("needs_expand", False),
            "blocking_issue_count": len(report.get("blocking_issues", [])),
            "warning_count": len(report.get("warnings", [])),
        }
    payload["progress"] = {
        "completed_scene_count": count_completed_scene_files(project_dir),
        "total_chars_written": count_total_written_chars(project_dir),
    }
    return save_story_state(project_dir, payload)
