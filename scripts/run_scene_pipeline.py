import argparse
import os
import subprocess
import sys

from prompt_utils import UserFacingError, resolve_project_path


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _run_script(script_name, args):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, script_name), *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise UserFacingError(f"{script_name} failed")


def main():
    parser = argparse.ArgumentParser(description="Thin scene pipeline wrapper for common novel workflow commands.")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--project", required=True)
    prepare.add_argument("--chapter", required=True)
    prepare.add_argument("--scene", required=True)
    prepare.add_argument("--mode", default="draft", choices=["draft", "resume"])
    prepare.add_argument("--force", action="store_true")

    prompt = sub.add_parser("prompt")
    prompt.add_argument("--project", required=True)
    prompt.add_argument("--runtime_dir", default="")

    check = sub.add_parser("check")
    check.add_argument("--project", required=True)
    check.add_argument("--text", required=True)
    check.add_argument("--runtime_dir", default="")

    repair = sub.add_parser("repair")
    repair.add_argument("--project", required=True)
    repair.add_argument("--text", required=True)
    repair.add_argument("--runtime_dir", default="")
    repair.add_argument("--force", action="store_true")

    approve = sub.add_parser("approve")
    approve.add_argument("--project", required=True)
    approve.add_argument("--scene", required=True)
    approve.add_argument("--allow-warnings", action="store_true")

    export = sub.add_parser("export")
    export.add_argument("--project", required=True)
    export.add_argument("--include-warnings", action="store_true")

    health = sub.add_parser("health")
    health.add_argument("--project", required=True)
    health.add_argument("--fix-safe", action="store_true")
    health.add_argument("--json", action="store_true")

    args = parser.parse_args()
    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    if args.command == "prepare":
        script_args = ["--project", project_dir, "--chapter", args.chapter, "--scene", args.scene, "--mode", args.mode]
        if args.force:
            script_args.append("--force")
        _run_script("build_runtime_context.py", script_args)
        print("NEXT: run prompt to build draft_prompt.txt")
    elif args.command == "prompt":
        script_args = ["--project", project_dir]
        if args.runtime_dir:
            script_args.extend(["--runtime_dir", args.runtime_dir])
        _run_script("build_draft_prompt.py", script_args)
        print("NEXT: write scene text, then run check")
    elif args.command == "check":
        script_args = ["--project", project_dir, "--text", args.text]
        if args.runtime_dir:
            script_args.extend(["--runtime_dir", args.runtime_dir])
        _run_script("check_scene_output.py", script_args)
        print("NEXT: approve if pass, or repair/revise if needed")
    elif args.command == "repair":
        script_args = ["--project", project_dir, "--draft_text", args.text]
        if args.runtime_dir:
            script_args.extend(["--runtime_dir", args.runtime_dir])
        if args.force:
            script_args.append("--force")
        _run_script("build_expand_prompt.py", script_args)
        print("NEXT: apply local edits, then re-run check")
    elif args.command == "approve":
        script_args = ["--project", project_dir, "--scene", args.scene]
        if args.allow_warnings:
            script_args.append("--allow-warnings")
        _run_script("approve_scene.py", script_args)
        print("NEXT: export when all target scenes are approved")
    elif args.command == "export":
        script_args = ["--project", project_dir]
        if args.include_warnings:
            script_args.append("--include-warnings")
        _run_script("export_manuscript.py", script_args)
        print("NEXT: review exports/manuscript.md")
    elif args.command == "health":
        script_args = ["--project", project_dir]
        if args.fix_safe:
            script_args.append("--fix-safe")
        if args.json:
            script_args.append("--json")
        _run_script("sync_project_health.py", script_args)
        print("NEXT: fix blocking issues before approve/export")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while running scene pipeline")
        sys.exit(1)

