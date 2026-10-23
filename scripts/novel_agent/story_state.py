from novel_agent.storage import read_json, validate_schema
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
    payload = read_json(path, default_factory=empty_story_state)
    validate_schema(payload, path, fields={"progress": dict, "scenes": dict, "characters": dict, "threads": dict, "payoffs": dict, "timeline": list, "open_questions": list, "continuity_findings": list})
    for scene_id, record in payload.get("scenes", {}).items():
        if not isinstance(record, dict):
            from novel_agent.errors import DataCorruptionError
            raise DataCorruptionError("invalid story scene at {}: {}".format(path, scene_id))
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
    if not scene_ref or report.get("scope") != "scene":
        return load_story_state(project_dir)
    from novel_agent.scene_status import collect_project_status, _sync_status_projections_locked
    from novel_agent.storage import project_lock
    with project_lock(project_dir):
        snapshot = collect_project_status(project_dir)
        snapshot["active_scene"] = scene_ref["canonical_id"]
        _sync_status_projections_locked(project_dir, snapshot)
        return load_story_state(project_dir)
