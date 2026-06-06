import argparse
import os
import sys

from novel_agent.exports import export_manuscript
from prompt_utils import UserFacingError, resolve_project_path


def main():
    parser = argparse.ArgumentParser(description="Export approved scene texts into a manuscript markdown file.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--format", default="markdown", choices=["markdown"], help="Export format")
    parser.add_argument("--include-warnings", action="store_true", help="Include scenes approved with warning status")
    parser.add_argument("--output", default="", help="Optional output path")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    result = export_manuscript(project_dir, include_warnings=args.include_warnings, output_path=args.output)
    print(f"OK: manuscript exported scenes={result['scene_count']}")
    print(f"OK: output={result['output_path']}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while exporting manuscript")
        sys.exit(1)

