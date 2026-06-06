import hashlib
import json
import os
from datetime import datetime, timezone

from prompt_utils import ensure_directory, read_text_file, runtime_root_dir, write_json_file


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_content_hash(path):
    if not path or not os.path.isfile(path):
        return None
    return hashlib.sha256(read_text_file(path).encode("utf-8")).hexdigest()


def _rel(path, project_dir):
    try:
        return os.path.relpath(path, project_dir)
    except ValueError:
        return os.path.abspath(path)


def artifact_ledger_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "artifact_ledger.json")


def token_ledger_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "token_ledger.jsonl")


def read_artifact_ledger(project_dir):
    path = artifact_ledger_path(project_dir)
    if not os.path.isfile(path):
        return {"version": 1, "updated_at": "", "artifacts": []}
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": "", "artifacts": []}
    if not isinstance(payload, dict):
        return {"version": 1, "updated_at": "", "artifacts": []}
    payload.setdefault("version", 1)
    payload.setdefault("artifacts", [])
    return payload


def write_artifact_ledger(project_dir, payload):
    payload["updated_at"] = utc_now()
    write_json_file(artifact_ledger_path(project_dir), payload)


def dependency_record(project_dir, path, dependency_id=None):
    return {
        "id": dependency_id or f"source:{_rel(path, project_dir)}",
        "path": _rel(path, project_dir),
        "content_hash": file_content_hash(path),
    }


def register_artifact(project_dir, *, artifact_id, artifact_type, path, depends_on_paths=None, source="generated"):
    payload = read_artifact_ledger(project_dir)
    now = utc_now()
    rel_path = _rel(path, project_dir)
    existing = next((item for item in payload["artifacts"] if item.get("id") == artifact_id), None)
    created_at = existing.get("created_at") if existing else now
    protected = bool(existing.get("protected_user_content")) if existing else False
    artifact = {
        "id": artifact_id,
        "type": artifact_type,
        "path": rel_path,
        "content_hash": file_content_hash(path),
        "status": "protected" if protected else "active",
        "source": existing.get("source", source) if existing else source,
        "protected_user_content": protected,
        "depends_on": [
            dependency_record(project_dir, dep_path)
            for dep_path in (depends_on_paths or [])
            if dep_path and os.path.isfile(dep_path)
        ],
        "created_at": created_at,
        "updated_at": now,
    }
    payload["artifacts"] = [item for item in payload["artifacts"] if item.get("id") != artifact_id]
    payload["artifacts"].append(artifact)
    write_artifact_ledger(project_dir, payload)
    return artifact


def register_artifacts(project_dir, items):
    for item in items:
        register_artifact(project_dir, **item)
    return read_artifact_ledger(project_dir)


def refresh_artifact_statuses(project_dir):
    payload = read_artifact_ledger(project_dir)
    changed = False
    for artifact in payload["artifacts"]:
        if artifact.get("status") in {"protected", "superseded", "rejected"}:
            continue
        stale = False
        for dependency in artifact.get("depends_on", []):
            dep_path = os.path.join(project_dir, dependency.get("path", ""))
            if dependency.get("content_hash") != file_content_hash(dep_path):
                stale = True
                break
        next_status = "stale" if stale else "active"
        if artifact.get("status") != next_status:
            artifact["status"] = next_status
            artifact["updated_at"] = utc_now()
            changed = True
    if changed:
        write_artifact_ledger(project_dir, payload)
    return payload


def find_artifact_by_path(project_dir, path):
    rel_path = _rel(path, project_dir)
    payload = refresh_artifact_statuses(project_dir)
    for artifact in payload.get("artifacts", []):
        if artifact.get("path") == rel_path:
            return artifact
    return None


def append_token_ledger(project_dir, record):
    path = token_ledger_path(project_dir)
    ensure_directory(os.path.dirname(path))
    payload = {"created_at": utc_now(), **record}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload
