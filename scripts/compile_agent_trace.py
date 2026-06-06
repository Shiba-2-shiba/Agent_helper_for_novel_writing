import argparse
import sys

from novel_agent.trace import compile_trace, render_trace_view
from prompt_utils import UserFacingError, resolve_project_path


def main():
    parser = argparse.ArgumentParser(description="Compile project-local agent trace into full/min/search views.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--grep", default="", help="Optional Python regex for trace_view.txt")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    outputs = compile_trace(project_dir, grep_pattern=args.grep)
    events = outputs["events"]
    if not events:
        print("WARN: no trace events found")
    print(f"OK: trace compiled events={len(events)}")
    print(f"OK: wrote {outputs['full_path']}")
    print(f"OK: wrote {outputs['min_path']}")
    if args.grep:
        view = render_trace_view(events, args.grep)
        if view:
            print(view.rstrip())
        print(f"OK: wrote {outputs['view_path']}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: unexpected failure while compiling agent trace: {exc}")
        sys.exit(1)
