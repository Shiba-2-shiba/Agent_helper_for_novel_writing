import argparse
import sys

from novel_agent.context_compiler import collect_context_blocks, render_view, write_context_outputs
from novel_agent.ledgers import append_token_ledger
from prompt_utils import UserFacingError, resolve_project_path, validate_positive_int


def main():
    parser = argparse.ArgumentParser(description="Compile project source artifacts into VCC-style context views.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number")
    parser.add_argument("--scene", required=True, help="Scene ID (2-3 or chapter_2_scene_3)")
    parser.add_argument("--mode", required=True, choices=["draft", "resume", "review", "repair"], help="Projection mode")
    parser.add_argument("--grep", default="", help="Optional Python regex for context_view.txt")
    parser.add_argument("--runtime_dir", default="", help="Optional runtime directory path")
    args = parser.parse_args()

    validate_positive_int("chapter", args.chapter)
    project_dir = resolve_project_path(args.project)
    blocks = collect_context_blocks(
        project_dir,
        chapter=args.chapter,
        scene=args.scene,
        mode=args.mode,
        runtime_dir_arg=args.runtime_dir,
    )
    outputs = write_context_outputs(
        project_dir,
        chapter=args.chapter,
        scene=args.scene,
        mode=args.mode,
        blocks=blocks,
        grep_pattern=args.grep or None,
    )

    print(f"OK: context compiled blocks={len(blocks)}")
    print(f"OK: wrote {outputs['full_path']}")
    print(f"OK: wrote {outputs['min_path']}")
    print(f"OK: wrote {outputs['index_path']}")
    append_token_ledger(
        project_dir,
        {
            "command": "compile_project_context",
            "projection": args.mode,
            "chapter": args.chapter,
            "scene": args.scene,
            "runtime_dir": outputs["context_dir"],
            "total_estimated_tokens": sum(block.tokens_estimate for block in blocks),
            "sections": {block.id: block.tokens_estimate for block in blocks},
            "budget": None,
            "status": "recorded",
        },
    )
    if args.grep:
        view = render_view(blocks, args.grep)
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
        print(f"ERROR: unexpected failure while compiling project context: {exc}")
        sys.exit(1)
