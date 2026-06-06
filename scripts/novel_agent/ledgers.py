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


def quality_budget_ledger_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "quality_budget_ledger.json")


def default_quality_budget_policy():
    return {
        "max_scene_repair_prompts": 3,
        "max_issue_attempts": 2,
        "max_expand_without_recheck": 1,
        "block_expansion_for_issue_types": [
            "format_violation",
            "forbidden_hit",
            "over_max_for_type",
        ],
    }


def _default_quality_budget_ledger():
    return {
        "version": 1,
        "updated_at": "",
        "policy": default_quality_budget_policy(),
        "scenes": {},
    }


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


def read_quality_budget_ledger(project_dir):
    path = quality_budget_ledger_path(project_dir)
    if not os.path.isfile(path):
        return _default_quality_budget_ledger()
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return _default_quality_budget_ledger()
    if not isinstance(payload, dict):
        return _default_quality_budget_ledger()

    payload.setdefault("version", 1)
    payload.setdefault("updated_at", "")
    policy = default_quality_budget_policy()
    existing_policy = payload.get("policy")
    if isinstance(existing_policy, dict):
        policy.update(existing_policy)
    payload["policy"] = policy
    payload.setdefault("scenes", {})
    if not isinstance(payload["scenes"], dict):
        payload["scenes"] = {}
    return payload


def write_quality_budget_ledger(project_dir, payload):
    payload["updated_at"] = utc_now()
    write_json_file(quality_budget_ledger_path(project_dir), payload)


def _scene_id(scene_ref):
    if not scene_ref:
        return "unknown"
    if isinstance(scene_ref, dict):
        return scene_ref.get("canonical_id") or f"{scene_ref.get('chapter', 'unknown')}-{scene_ref.get('scene', 'unknown')}"
    return str(scene_ref)


def _scene_budget_record(payload, scene_id):
    scenes = payload.setdefault("scenes", {})
    record = scenes.get(scene_id)
    if not isinstance(record, dict):
        record = {
            "scene_id": scene_id,
            "status": "within_budget",
            "counters": {},
            "issues": {},
            "decisions": [],
        }
        scenes[scene_id] = record
    record.setdefault("scene_id", scene_id)
    record.setdefault("status", "within_budget")
    counters = record.setdefault("counters", {})
    counters.setdefault("check_runs", 0)
    counters.setdefault("expand_prompts", 0)
    counters.setdefault("expand_prompts_since_last_check", 0)
    counters.setdefault("expand_edits_applied", 0)
    counters.setdefault("forced_overrides", 0)
    record.setdefault("issues", {})
    record.setdefault("decisions", [])
    return record


def _short_evidence(report):
    return {
        "actual_chars": report.get("actual_chars"),
        "min_chars": report.get("min_chars"),
        "max_chars": report.get("max_chars"),
        "char_delta_to_min": report.get("char_delta_to_min"),
        "char_delta_to_target": report.get("char_delta_to_target"),
    }


def _issue_record(issue_type, severity, report, report_path=None, detail=None):
    record = {
        "issue_type": issue_type,
        "severity": severity,
        "last_evidence": _short_evidence(report),
    }
    if report_path:
        record["artifacts"] = [report_path]
    if detail:
        record["detail"] = detail
    return record


def collect_quality_issues_from_report(report, report_path=None):
    issues = {}

    if report.get("under_min_for_type") or report.get("needs_expand"):
        issues["under_min_for_type"] = _issue_record(
            "under_min_for_type",
            "blocking",
            report,
            report_path=report_path,
        )

    if report.get("over_max_for_type"):
        issues["over_max_for_type"] = _issue_record(
            "over_max_for_type",
            "blocking",
            report,
            report_path=report_path,
        )

    for detail in report.get("format_violations_detail", []) or []:
        detail_type = detail.get("type") or "unknown"
        issues[f"format_violation:{detail_type}"] = _issue_record(
            f"format_violation:{detail_type}",
            "blocking",
            report,
            report_path=report_path,
            detail={"type": detail_type, "rule": detail.get("rule", "")},
        )

    for detail in report.get("forbidden_hits_detail", []) or []:
        detail_type = detail.get("type") or detail.get("rule") or "unknown"
        issues[f"forbidden_hit:{detail_type}"] = _issue_record(
            f"forbidden_hit:{detail_type}",
            "blocking",
            report,
            report_path=report_path,
            detail={"type": detail_type, "rule": detail.get("rule", "")},
        )

    for warning in report.get("warnings", []) or []:
        warning_type = warning.get("type") or "unknown"
        issues[f"warning:{warning_type}"] = _issue_record(
            f"warning:{warning_type}",
            "warning",
            report,
            report_path=report_path,
            detail={"type": warning_type},
        )

    return issues


def update_quality_budget_from_check(project_dir, scene_ref, report, report_path=None):
    payload = read_quality_budget_ledger(project_dir)
    scene_id = _scene_id(scene_ref)
    scene = _scene_budget_record(payload, scene_id)
    now = utc_now()
    scene["counters"]["check_runs"] += 1
    scene["counters"]["expand_prompts_since_last_check"] = 0
    scene["last_check_at"] = now

    current_issues = collect_quality_issues_from_report(report, report_path=report_path)
    existing = scene.setdefault("issues", {})

    for key, issue in existing.items():
        if issue.get("status") == "open" and key not in current_issues:
            issue["status"] = "resolved"
            issue["resolved_at"] = now
            issue["last_seen_at"] = issue.get("last_seen_at", now)

    for key, issue in current_issues.items():
        previous = existing.get(key, {})
        attempts = int(previous.get("attempts", 0) or 0)
        first_seen = previous.get("first_seen_at") or now
        budget = int(previous.get("budget", payload["policy"]["max_issue_attempts"]) or payload["policy"]["max_issue_attempts"])
        existing[key] = {
            **previous,
            **issue,
            "status": "open",
            "attempts": attempts,
            "budget": budget,
            "first_seen_at": first_seen,
            "last_seen_at": now,
        }

    open_blocking = [
        issue
        for issue in existing.values()
        if issue.get("status") == "open" and issue.get("severity") == "blocking"
    ]
    exhausted = [
        issue
        for issue in open_blocking
        if int(issue.get("attempts", 0) or 0) >= int(issue.get("budget", payload["policy"]["max_issue_attempts"]) or 0)
    ]
    scene["status"] = "exhausted" if exhausted else "within_budget"
    write_quality_budget_ledger(project_dir, payload)
    return scene


def evaluate_quality_budget_for_expand(project_dir, scene_ref, report):
    payload = read_quality_budget_ledger(project_dir)
    scene_id = _scene_id(scene_ref)
    scene = _scene_budget_record(payload, scene_id)
    policy = payload["policy"]

    if report.get("over_max_for_type"):
        return {
            "allowed": False,
            "reason": "expansion is not appropriate for issue type: over_max_for_type",
            "issue_key": "over_max_for_type",
            "status": "blocked_inappropriate_issue",
        }
    if report.get("format_violations"):
        return {
            "allowed": False,
            "reason": "expansion is not appropriate for issue type: format_violation",
            "issue_key": "format_violation",
            "status": "blocked_inappropriate_issue",
        }
    if report.get("forbidden_hits"):
        return {
            "allowed": False,
            "reason": "expansion is not appropriate for issue type: forbidden_hit",
            "issue_key": "forbidden_hit",
            "status": "blocked_inappropriate_issue",
        }
    if not report.get("needs_expand"):
        return {
            "allowed": False,
            "reason": "expansion is not needed for this check report",
            "issue_key": "",
            "status": "blocked_not_needed",
        }

    counters = scene["counters"]
    if counters.get("expand_prompts_since_last_check", 0) >= policy["max_expand_without_recheck"]:
        return {
            "allowed": False,
            "reason": "quality budget requires check_scene_output.py before another expansion",
            "issue_key": "under_min_for_type",
            "status": "blocked_recheck_required",
        }
    if counters.get("expand_prompts", 0) >= policy["max_scene_repair_prompts"]:
        return {
            "allowed": False,
            "reason": "quality budget exhausted for scene repair prompts",
            "issue_key": "under_min_for_type",
            "status": "blocked_scene_budget_exhausted",
        }

    under_min_issue = scene.get("issues", {}).get("under_min_for_type", {})
    attempts = int(under_min_issue.get("attempts", 0) or 0)
    budget = int(under_min_issue.get("budget", policy["max_issue_attempts"]) or policy["max_issue_attempts"])
    if attempts >= budget:
        return {
            "allowed": False,
            "reason": "quality budget exhausted for issue: under_min_for_type",
            "issue_key": "under_min_for_type",
            "status": "blocked_issue_budget_exhausted",
        }

    return {
        "allowed": True,
        "reason": f"under_min_for_type attempts {attempts}/{budget}",
        "issue_key": "under_min_for_type",
        "status": "allowed",
    }


def record_quality_budget_action(project_dir, scene_ref, action, reason, artifacts=None, force=False, issue_key=""):
    payload = read_quality_budget_ledger(project_dir)
    scene_id = _scene_id(scene_ref)
    scene = _scene_budget_record(payload, scene_id)
    counters = scene["counters"]
    now = utc_now()
    rel_artifacts = [_rel(path, project_dir) for path in (artifacts or []) if path]

    if action == "expand_prompt_generated":
        counters["expand_prompts"] += 1
        counters["expand_prompts_since_last_check"] += 1
        target_issue_key = issue_key or "under_min_for_type"
        issue = scene.setdefault("issues", {}).setdefault(
            target_issue_key,
            {
                "issue_type": target_issue_key,
                "severity": "blocking",
                "status": "open",
                "attempts": 0,
                "budget": payload["policy"]["max_issue_attempts"],
                "first_seen_at": now,
                "last_seen_at": now,
            },
        )
        issue["attempts"] = int(issue.get("attempts", 0) or 0) + 1
        issue["last_attempt_at"] = now
    elif action == "expand_edits_applied":
        counters["expand_edits_applied"] += 1

    if force:
        counters["forced_overrides"] += 1

    scene.setdefault("decisions", []).append(
        {
            "created_at": now,
            "action": action,
            "reason": reason,
            "artifacts": rel_artifacts,
            "force": bool(force),
            **({"issue_key": issue_key} if issue_key else {}),
        }
    )
    write_quality_budget_ledger(project_dir, payload)
    return scene


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
