import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from prompt_utils import (
    collect_scene_metadata,
    collect_missing_dependencies,
    UserFacingError,
    count_completed_scene_files,
    count_total_written_chars,
    extract_chapter_block,
    find_latest_scene_file,
    find_scene_file,
    find_state_schema_path,
    parse_scene_ledger,
    parse_scene_reference,
    read_optional_text,
    read_text_file,
    resolve_outline_path,
    resolve_project_path,
    resolve_target_profile_from_state,
    suggest_scene_output_path,
    runtime_index_path,
    runtime_root_dir,
    sync_state_schema,
    update_runtime_index,
    update_scene_ledger_status,
    write_json_file,
)


def parse_legacy_scene_brief_scene_id(runtime_root):
    text = read_optional_text(os.path.join(runtime_root, "scene_brief_compact.md"))
    match = re.search(r"(?m)^- Scene ID:\s*(\d+-\d+)$", text)
    if not match:
        return None
    return parse_scene_reference(match.group(1))


def parse_legacy_resume_scene_id(runtime_root):
    text = read_optional_text(os.path.join(runtime_root, "resume_brief.md"))
    match = re.search(r"Current Position:\s*chapter\s+(\d+)\s+scene\s+(\d+)", text)
    if not match:
        return None
    return parse_scene_reference(f"{match.group(1)}-{match.group(2)}")


def parse_legacy_check_scene_id(runtime_root):
    text = read_optional_text(os.path.join(runtime_root, "check_report.json"))
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    target_file = str(payload.get("target_file", ""))
    match = re.search(r"chapter_?(\d+)_scene_?(\d+)\.txt$", target_file, flags=re.IGNORECASE)
    if not match:
        return None
    return parse_scene_reference(f"{match.group(1)}-{match.group(2)}")


def sync_outline_statuses_for_existing_scenes(project_dir):
    updated = []
    for item in collect_scene_metadata(project_dir):
        scene_ref = parse_scene_reference(f"{item['chapter']}-{item['scene']}")
        path = update_scene_ledger_status(project_dir, scene_ref, "drafted")
        if path:
            updated.append(scene_ref["canonical_id"])
    return updated


def main():
    parser = argparse.ArgumentParser(description="Migrate an existing project state to the refactored runtime/state conventions.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument(
        "--target-source",
        default="migration",
        choices=["migration", "late_update"],
        help="How to label an already-present target_total_chars when adding confirmation metadata",
    )
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    state_path = find_state_schema_path(project_dir)
    if state_path is None:
        raise UserFacingError("state_schema_novel.yaml not found")

    state_text = read_text_file(state_path)
    target_profile = resolve_target_profile_from_state(state_text)

    latest_scene = find_latest_scene_file(project_dir)
    latest_scene_id = f"{latest_scene['chapter']}-{latest_scene['scene']}" if latest_scene else ""
    target_confirmed = "target_confirmed: true" in state_text
    existing_source_match = re.search(r'(?m)^\s*target_confirmation_source:\s*"?(.*?)"?\s*$', state_text)
    existing_source = existing_source_match.group(1).strip() if existing_source_match else ""
    existing_by_match = re.search(r'(?m)^\s*target_confirmed_by:\s*"?(.*?)"?\s*$', state_text)
    existing_by = existing_by_match.group(1).strip() if existing_by_match else ""
    existing_at_match = re.search(r'(?m)^\s*target_confirmed_at:\s*"?(.*?)"?\s*$', state_text)
    existing_at = existing_at_match.group(1).strip() if existing_at_match else ""
    confirmed_at = datetime.now(timezone.utc).isoformat()
    updates = {
        "targets": {
            "target_total_chars": target_profile["target_total_chars"],
            "target_length_profile": target_profile["target_length_profile"],
            "target_confirmed": True,
            "target_confirmation_source": existing_source or args.target_source,
            "target_confirmed_at": existing_at or confirmed_at,
            "target_confirmed_by": existing_by or "migration",
        },
        "progress": {
            "completed_scene_count": count_completed_scene_files(project_dir),
            "total_chars_written": count_total_written_chars(project_dir),
            "last_completed_scene": latest_scene_id,
            "current_scene": latest_scene_id,
            "current_chapter": latest_scene["chapter"] if latest_scene else 0,
        },
        "active_work": {
            "current_mode": "resume_orchestrator",
            "recommended_skill": "resume-orchestrator",
            "active_scene": latest_scene_id,
            "active_chapter": latest_scene["chapter"] if latest_scene else 0,
            "next_action": "resume-orchestrator で現在地と runtime の整合を確認する",
        },
    }
    sync_state_schema(project_dir, updates)

    runtime_root = runtime_root_dir(project_dir)
    draft_scene_ref = parse_legacy_scene_brief_scene_id(runtime_root) or parse_legacy_check_scene_id(runtime_root)
    if draft_scene_ref is not None:
        update_runtime_index(project_dir, mode="draft", scene_ref=draft_scene_ref, runtime_dir=runtime_root)
    resume_scene_ref = parse_legacy_resume_scene_id(runtime_root)
    if resume_scene_ref is not None:
        update_runtime_index(project_dir, mode="resume", scene_ref=resume_scene_ref, runtime_dir=runtime_root)
    outline_status_updates = sync_outline_statuses_for_existing_scenes(project_dir)
    missing_dependencies = collect_missing_dependencies(project_dir)

    regenerated_resume_runtime = ""
    if latest_scene_id:
        regenerated_resume_runtime = os.path.join(
            project_dir,
            "runtime",
            "scenes",
            latest_scene_id,
            "resume",
            "resume_brief.md",
        )
        subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "build_runtime_context.py"),
                "--project",
                project_dir,
                "--chapter",
                str(latest_scene["chapter"]),
                "--scene",
                latest_scene_id,
                "--mode",
                "resume",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    next_write_target = None
    if missing_dependencies:
        dependency_ref = parse_scene_reference(missing_dependencies[0]["depends_on"])
        next_write_target = {
            "scene_id": dependency_ref["canonical_id"],
            "output_path": suggest_scene_output_path(project_dir, dependency_ref),
            "reason": f"{missing_dependencies[0]['scene_id']} depends_on {missing_dependencies[0]['depends_on']}",
        }

    report = {
        "project": project_dir,
        "target_confirmation_source": args.target_source,
        "state_path": state_path,
        "runtime_index_path": runtime_index_path(project_dir),
        "latest_scene": latest_scene_id or None,
        "legacy_runtime_detected": os.path.isdir(runtime_root),
        "legacy_draft_scene": draft_scene_ref["canonical_id"] if draft_scene_ref else None,
        "legacy_resume_scene": resume_scene_ref["canonical_id"] if resume_scene_ref else None,
        "outline_status_updates": outline_status_updates,
        "regenerated_resume_runtime": regenerated_resume_runtime or None,
        "missing_dependencies": missing_dependencies,
        "next_write_target": next_write_target,
    }
    report_path = os.path.join(runtime_root, "migration_report.json")
    write_json_file(report_path, report)

    print("OK: project state migrated")
    print(f"OK: report={report_path}")
    print(f"OK: latest_scene={latest_scene_id or '-'}")
    print(f"OK: missing_dependencies={len(report['missing_dependencies'])}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while migrating project state")
        sys.exit(1)
