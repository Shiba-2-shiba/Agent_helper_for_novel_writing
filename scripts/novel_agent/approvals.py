from novel_agent.storage import read_json, validate_schema, project_lock
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
    payload = read_json(path, default_factory=lambda: {"version": 1, "updated_at": "", "scenes": {}})
    validate_schema(payload, path, fields={"scenes": dict})
    payload.setdefault("version", 1)
    payload.setdefault("updated_at", "")
    payload.setdefault("scenes", {})
    for scene_id, record in payload["scenes"].items():
        if not isinstance(record, dict):
            from novel_agent.errors import DataCorruptionError
            raise DataCorruptionError("invalid approval record at {}: {}".format(path, scene_id))
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


HASH_ALGORITHM = "sha256-utf8-text-v1"


def validate_check_identity(project_dir, scene_ref, scene_path, report):
    from novel_agent.dependencies import dependency_digest, verify_dependencies
    if report.get("version") != 2:
        raise UserFacingError("legacy check report requires recheck before approval or repair")
    expected_scope = "scene" if scene_ref else "standalone"
    if report.get("scope") != expected_scope or report.get("scene_id") != (scene_ref["canonical_id"] if scene_ref else None):
        raise UserFacingError("check report scene identity mismatch")
    expected_path = os.path.realpath(scene_path)
    stored_path = os.path.realpath(os.path.join(project_dir, report.get("source_path", "")))
    if expected_path != stored_path or report.get("hash_algorithm") != HASH_ALGORITHM:
        raise UserFacingError("check report source identity mismatch")
    if not report.get("source_hash") or report["source_hash"] != file_content_hash(scene_path):
        raise UserFacingError("scene text changed after check; recheck required")
    inputs = report.get("check_inputs")
    if not isinstance(inputs, list) or report.get("check_inputs_digest") != dependency_digest(inputs):
        raise UserFacingError("check report conditions are invalid; recheck required")
    if scene_ref and not any(item.get("kind") == "projection" and item.get("selector") == "check_policy" and item.get("scene_id") == scene_ref["canonical_id"] for item in inputs):
        raise UserFacingError("check report lacks current policy binding; recheck required")
    if verify_dependencies(project_dir, inputs):
        raise UserFacingError("check conditions changed; prepare and recheck required")


def validate_approval_current(project_dir, record):
    legacy = record.get("version", 1) == 1
    result = {"status": record.get("status", "unknown"), "reasons": [], "legacy_guarantee": legacy}
    if result["status"] != "approved":
        return result
    path = os.path.join(project_dir, record.get("source_path", record.get("scene_path", "")))
    if legacy:
        if not record.get("content_hash") or record["content_hash"] != file_content_hash(path):
            result.update(status="stale", reasons=["scene text changed"])
        return result
    if record.get("version") != 2:
        result.update(status="stale", reasons=["unsupported approval version"])
        return result
    try:
        scene_ref = parse_scene_reference(record.get("scene_id", ""))
        canonical = find_scene_file(project_dir, scene_ref)
        if not canonical or os.path.realpath(canonical) != os.path.realpath(path):
            raise UserFacingError("approved scene path changed")
        validate_check_identity(project_dir, scene_ref, path, {**record, "scope": "scene"})
    except UserFacingError as exc:
        result.update(status="stale", reasons=[str(exc)])
    return result


def approval_status_for_scene(project_dir, scene_id):
    record = read_approval_ledger(project_dir).get("scenes", {}).get(scene_id)
    if not isinstance(record, dict):
        return None
    return {**record, **validate_approval_current(project_dir, record)}


def _sync_status_locked(project_dir):
    from novel_agent.scene_status import collect_project_status, _sync_status_projections_locked
    _sync_status_projections_locked(project_dir, collect_project_status(project_dir))


def approve_scene(project_dir, scene_raw, *, allow_warnings=False, runtime_dir_arg="", approved_by="user", notes=""):
    with project_lock(project_dir):
        scene_ref = parse_scene_reference(scene_raw)
        scene_path = find_scene_file(project_dir, scene_ref)
        if not scene_path:
            raise UserFacingError("scene text not found: " + scene_ref["canonical_id"])
        report_path = resolve_check_report_path(project_dir, scene_ref, runtime_dir_arg=runtime_dir_arg)
        report = _load_check_report(report_path)
        validate_check_identity(project_dir, scene_ref, scene_path, report)
        status = str(report.get("status", "")).lower()
        if status == "fail":
            raise UserFacingError("scene has failing check_report status; cannot approve")
        if status == "warning" and not allow_warnings:
            raise UserFacingError("scene has warning check_report status; rerun with --allow-warnings to approve")
        if status not in {"pass", "warning"}:
            raise UserFacingError("scene check_report status is not approvable: " + (status or "unknown"))
        payload = read_approval_ledger(project_dir)
        scene_id = scene_ref["canonical_id"]
        record = {key: report[key] for key in ("version", "scene_id", "source_path", "source_hash", "hash_algorithm", "check_inputs", "check_inputs_digest")}
        record.update(status="approved", approved_at=utc_now(), approved_by=approved_by,
                      scene_path=_relative(scene_path, project_dir), check_report_path=_relative(report_path, project_dir),
                      check_status=status, content_hash=report["source_hash"], notes=notes)
        payload["scenes"][scene_id] = record
        write_approval_ledger(project_dir, payload)
        _sync_status_locked(project_dir)
        return record


def revoke_scene_approval(project_dir, scene_raw, *, notes=""):
    with project_lock(project_dir):
        scene_id = parse_scene_reference(scene_raw)["canonical_id"]
        payload = read_approval_ledger(project_dir)
        existing = payload["scenes"].get(scene_id, {})
        payload["scenes"][scene_id] = {**existing, "status": "revoked", "revoked_at": utc_now(), "notes": notes or existing.get("notes", "")}
        write_approval_ledger(project_dir, payload)
        _sync_status_locked(project_dir)
        return payload["scenes"][scene_id]


def _refresh_approval_statuses_locked(project_dir):
    payload = read_approval_ledger(project_dir)
    changed = False
    for record in payload.get("scenes", {}).values():
        current = validate_approval_current(project_dir, record)
        if current["status"] != record.get("status"):
            record.update(status=current["status"], stale_at=utc_now(), stale_reasons=current["reasons"])
            changed = True
    if changed:
        write_approval_ledger(project_dir, payload)
    return payload


def refresh_approval_statuses(project_dir):
    with project_lock(project_dir):
        return _refresh_approval_statuses_locked(project_dir)
