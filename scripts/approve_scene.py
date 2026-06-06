import argparse
import os
import sys

from novel_agent.approvals import approve_scene, revoke_scene_approval
from prompt_utils import UserFacingError, resolve_project_path


def main():
    parser = argparse.ArgumentParser(description="Approve a checked scene for manuscript export.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--scene", required=True, help="Scene ID, e.g. 2-3")
    parser.add_argument("--runtime_dir", default="", help="Optional runtime directory path")
    parser.add_argument("--allow-warnings", action="store_true", help="Allow approving warning check status")
    parser.add_argument("--revoke", action="store_true", help="Revoke an existing approval")
    parser.add_argument("--notes", default="", help="Optional approval/revocation notes")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    if args.revoke:
        record = revoke_scene_approval(project_dir, args.scene, notes=args.notes)
        print(f"OK: scene approval revoked scene={args.scene} status={record['status']}")
        return

    record = approve_scene(
        project_dir,
        args.scene,
        allow_warnings=args.allow_warnings,
        runtime_dir_arg=args.runtime_dir,
        notes=args.notes,
    )
    print(f"OK: scene approved scene={args.scene} check_status={record['check_status']}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while approving scene")
        sys.exit(1)

