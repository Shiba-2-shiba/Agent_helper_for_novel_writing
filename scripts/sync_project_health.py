import argparse
import json
import os
import sys

from novel_agent.health import build_health_report, run_safe_fixes, write_health_report
from prompt_utils import UserFacingError, resolve_project_path


def main():
    parser = argparse.ArgumentParser(description="Check project runtime/state/summary health.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--fix-safe", action="store_true", help="Regenerate safe derived artifacts only")
    parser.add_argument("--json", action="store_true", help="Print the health report as JSON")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    fixed = []
    if args.fix_safe:
        fixed = run_safe_fixes(project_dir)
    report = build_health_report(project_dir)
    path = write_health_report(project_dir, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"OK: health status={report['status']}")
        print(f"OK: blocking={len(report['blocking_issues'])} warnings={len(report['warnings'])}")
        if fixed:
            print(f"OK: fixed_safe={','.join(fixed)}")
        print(f"OK: report={path}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while checking project health")
        sys.exit(1)

