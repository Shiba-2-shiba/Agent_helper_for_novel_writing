import json
import os

from novel_agent.ledgers import file_content_hash, utc_now
from prompt_utils import (
    UserFacingError,
    ensure_directory,
    find_scene_file,
    parse_scene_reference,
    read_text_file,
    resolve_runtime_dir,
    runtime_root_dir,
    write_json_file,
)


def approval_ledger_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "approval_ledger.json")


def read_approval_ledger(project_dir):
    path = approval_ledger_path(project_dir)
    if not os.path.isfile(path):
        return {"version": 1, "updated_at": "", "scenes": {}}
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": "", "scenes": {}}
    if not isinstance(payload, dict):
        return {"version": 1, "updated_at": "", "scenes": {}}
    payload.setdefault("version", 1)
    payload.setdefault("updated_at", "")
    payload.setdefault("scenes", {})
    if not isinstance(payload["scenes"], dict):
        payload["scenes"] = {}
    return payload


def write_approval_ledger(project_dir, payload):
    payload["version"] = 1
    payload["updated_at"] = utc_now()
    write_json_file(approval_ledger_path(project_dir), payload)
    return payload


def _relative(path, project_dir):
    try:
        return os.path.relpath(path, project_dir)
    except ValueError:
        return os.path.abspath(path)


def _load_check_report(path):
    if not os.path.isfile(path):
        raise UserFacingError(f"check_report.json not found: {path}")
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        raise UserFacingError("check_report.json is invalid")
    if not isinstance(payload, dict):
        raise UserFacingError("check_report.json is invalid")
    return payload


def resolve_check_report_path(project_dir, scene_ref, runtime_dir_arg=""):
    runtime_dir = resolve_runtime_dir(
        project_dir,
        mode="draft",
        scene_ref=scene_ref,
        runtime_dir_arg=runtime_dir_arg,
    )
    return os.path.join(runtime_dir, "check_report.json")


def approval_status_for_scene(project_dir, scene_id):
    payload = read_approval_ledger(project_dir)
    record = payload.get("scenes", {}).get(scene_id)
    if not isinstance(record, dict):
        return None
    if record.get("status") != "approved":
        return record
    scene_path = os.path.join(project_dir, record.get("scene_path", ""))
    if record.get("content_hash") != file_content_hash(scene_path):
        record = {**record, "status": "stale"}
    return record


def approve_scene(project_dir, scene_raw, *, allow_warnings=False, runtime_dir_arg="", approved_by="user", notes=""):
    scene_ref = parse_scene_reference(scene_raw)
    scene_path = find_scene_file(project_dir, scene_ref)
    if not scene_path:
        raise UserFacingError(f"scene text not found: {scene_ref['canonical_id']}")
    report_path = resolve_check_report_path(project_dir, scene_ref, runtime_dir_arg=runtime_dir_arg)
    report = _load_check_report(report_path)
    check_status = str(report.get("status", "")).lower()
    if check_status == "fail":
        raise UserFacingError("scene has failing check_report status; cannot approve")
    if check_status == "warning" and not allow_warnings:
        raise UserFacingError("scene has warning check_report status; rerun with --allow-warnings to approve")
    if check_status not in {"pass", "warning"}:
        raise UserFacingError(f"scene check_report status is not approvable: {check_status or 'unknown'}")

    payload = read_approval_ledger(project_dir)
    scene_id = scene_ref["canonical_id"]
    payload["scenes"][scene_id] = {
        "status": "approved",
        "approved_at": utc_now(),
        "approved_by": approved_by,
        "scene_path": _relative(scene_path, project_dir),
        "check_report_path": _relative(report_path, project_dir),
        "check_status": check_status,
        "content_hash": file_content_hash(scene_path),
        "notes": notes,
    }
    write_approval_ledger(project_dir, payload)
    return payload["scenes"][scene_id]


def revoke_scene_approval(project_dir, scene_raw, *, notes=""):
    scene_ref = parse_scene_reference(scene_raw)
    payload = read_approval_ledger(project_dir)
    scene_id = scene_ref["canonical_id"]
    existing = payload["scenes"].get(scene_id, {})
    payload["scenes"][scene_id] = {
        **existing,
        "status": "revoked",
        "revoked_at": utc_now(),
        "notes": notes or existing.get("notes", ""),
    }
    write_approval_ledger(project_dir, payload)
    return payload["scenes"][scene_id]


def refresh_approval_statuses(project_dir):
    payload = read_approval_ledger(project_dir)
    changed = False
    for scene_id, record in payload.get("scenes", {}).items():
        if not isinstance(record, dict) or record.get("status") != "approved":
            continue
        scene_path = os.path.join(project_dir, record.get("scene_path", ""))
        current_hash = file_content_hash(scene_path)
        if record.get("content_hash") != current_hash:
            record["status"] = "stale"
            record["stale_at"] = utc_now()
            changed = True
    if changed:
        write_approval_ledger(project_dir, payload)
    return payload

