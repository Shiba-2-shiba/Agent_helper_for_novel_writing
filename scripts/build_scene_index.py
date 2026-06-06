import argparse
import sys

from novel_agent.scene_index import refresh_scene_summaries, scene_summaries_path
from prompt_utils import UserFacingError, resolve_project_path


def main():
    parser = argparse.ArgumentParser(description="Build a lightweight scene summary index.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    records = refresh_scene_summaries(project_dir)
    print(f"OK: scene summaries indexed count={len(records)}")
    print(f"OK: wrote {scene_summaries_path(project_dir)}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: unexpected failure while building scene index: {exc}")
        sys.exit(1)
