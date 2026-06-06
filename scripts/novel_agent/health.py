import json
import os

from novel_agent.approvals import refresh_approval_statuses
from novel_agent.ledgers import read_artifact_ledger, read_quality_budget_ledger, token_ledger_path, utc_now
from novel_agent.scene_index import refresh_scene_summaries, scene_summaries_path
from novel_agent.story_state import initialize_story_state, load_story_state, save_story_state, story_state_path
from novel_agent.trace import compile_trace, trace_log_path
from prompt_utils import (
    collect_scene_metadata,
    ensure_directory,
    find_latest_scene_file,
    read_runtime_index,
    read_text_file,
    resolve_outline_path,
    runtime_root_dir,
    write_json_file,
)


def health_report_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "health_report.json")


def _issue(issue_type, message, **extra):
    return {"type": issue_type, "message": message, **extra}


def _load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        return json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return None


def _scene_id(item):
    return f"{item['chapter']}-{item['scene']}"


def _latest_check_scene(project_dir):
    latest = None
    runtime_root = runtime_root_dir(project_dir)
    if not os.path.isdir(runtime_root):
        return None
    for root, _, files in os.walk(runtime_root):
        if "check_report.json" not in files:
            continue
        path = os.path.join(root, "check_report.json")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if latest is None or mtime > latest["mtime"]:
            latest = {"path": path, "mtime": mtime, "payload": _load_json(path) or {}}
    return latest


def _count_token_ledger_records(project_dir):
    path = token_ledger_path(project_dir)
    if not os.path.isfile(path):
        return {"records": 0, "total_estimated_tokens": 0}
    count = 0
    total = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            count += 1
            total += int(payload.get("total_estimated_tokens", 0) or 0)
    return {"records": count, "total_estimated_tokens": total}


def build_health_report(project_dir):
    blocking = []
    warnings = []
    info = []

    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if not os.path.isfile(outline_path):
        blocking.append(_issue("outline_missing", "outline file is missing"))

    scene_items = collect_scene_metadata(project_dir)
    for item in scene_items:
        try:
            read_text_file(item["path"])
        except OSError:
            blocking.append(_issue("scene_unreadable", "scene text cannot be read", path=item["path"]))

    approval_payload = refresh_approval_statuses(project_dir)
    approved_count = 0
    for scene_id, record in approval_payload.get("scenes", {}).items():
        if not isinstance(record, dict):
            continue
        if record.get("status") == "approved":
            approved_count += 1
        if record.get("status") == "stale":
            blocking.append(_issue("approval_stale", "approved scene content hash changed", scene_id=scene_id))

    latest_check = _latest_check_scene(project_dir)
    state = load_story_state(project_dir)
    if latest_check:
        report = latest_check["payload"]
        target = report.get("target_file", "")
        latest_scene_id = ""
        for item in scene_items:
            if os.path.abspath(item["path"]) == os.path.abspath(target):
                latest_scene_id = _scene_id(item)
                break
        if latest_scene_id and latest_scene_id not in state.get("scenes", {}):
            warnings.append(_issue("story_state_stale", "latest checked scene is not reflected in story_state", scene_id=latest_scene_id))

    summaries_path = scene_summaries_path(project_dir)
    if scene_items and not os.path.isfile(summaries_path):
        warnings.append(_issue("scene_summaries_missing", "scene_summaries.jsonl is missing"))
    elif os.path.isfile(summaries_path):
        summary_mtime = os.path.getmtime(summaries_path)
        newer = [item for item in scene_items if os.path.getmtime(item["path"]) > summary_mtime]
        if newer:
            warnings.append(_issue("scene_summaries_stale", "scene_summaries.jsonl is older than scene text", count=len(newer)))

    artifact_payload = read_artifact_ledger(project_dir)
    stale_artifacts = [
        item for item in artifact_payload.get("artifacts", [])
        if isinstance(item, dict) and item.get("status") == "stale"
    ]
    if stale_artifacts:
        warnings.append(_issue("stale_artifacts", "artifact ledger contains stale artifacts", count=len(stale_artifacts)))

    runtime_index = read_runtime_index(project_dir)
    for mode, latest in runtime_index.get("latest_by_mode", {}).items():
        runtime_dir = latest.get("runtime_dir", "")
        if runtime_dir and not os.path.isdir(runtime_dir):
            warnings.append(_issue("runtime_index_missing_dir", "runtime_index points to missing runtime directory", mode=mode, runtime_dir=runtime_dir))

    if not os.path.isfile(trace_log_path(project_dir)):
        warnings.append(_issue("trace_missing", "agent trace log is missing"))

    latest_scene = find_latest_scene_file(project_dir)
    info.append(_issue("scene_count", "scene text count", value=len(scene_items)))
    info.append(_issue("approved_scene_count", "approved scene count", value=approved_count))
    info.append(_issue("latest_scene", "latest scene text", value=_scene_id(latest_scene) if latest_scene else ""))
    token_summary = _count_token_ledger_records(project_dir)
    info.append(_issue("token_ledger", "token ledger summary", **token_summary))
    quality_payload = read_quality_budget_ledger(project_dir)
    exhausted_count = sum(
        1
        for record in quality_payload.get("scenes", {}).values()
        if isinstance(record, dict) and record.get("status") == "exhausted"
    )
    info.append(_issue("quality_budget_exhausted_scene_count", "quality budget exhausted scenes", value=exhausted_count))

    status = "fail" if blocking else "warning" if warnings else "pass"
    return {
        "version": 1,
        "created_at": utc_now(),
        "status": status,
        "blocking_issues": blocking,
        "warnings": warnings,
        "info": info,
    }


def write_health_report(project_dir, report):
    ensure_directory(runtime_root_dir(project_dir))
    write_json_file(health_report_path(project_dir), report)
    return health_report_path(project_dir)


def run_safe_fixes(project_dir):
    fixed = []
    if collect_scene_metadata(project_dir):
        refresh_scene_summaries(project_dir)
        fixed.append("scene_summaries")
    initialize_story_state(project_dir)
    fixed.append("story_state")
    compile_trace(project_dir)
    fixed.append("trace_views")
    return fixed

