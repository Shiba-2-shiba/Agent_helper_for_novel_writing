"""Review proposed and accepted memory, or explicitly accept a batch."""
import argparse
import sys

from novel_agent.errors import UserFacingError
from novel_agent.story_memory import accept_proposal, write_memory_review
from prompt_utils import resolve_project_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--batch", default=None)
    parser.add_argument("--accept", action="store_true")
    parser.add_argument("--expected-revision", type=int, default=None)
    args = parser.parse_args()
    project = resolve_project_path(args.project)
    if args.accept:
        if args.batch is None or args.expected_revision is None:
            raise UserFacingError("--accept requires --batch and --expected-revision")
        accepted = accept_proposal(project, batch_id=args.batch, expected_revision=args.expected_revision)
        print("OK: accepted memory revision %s" % accepted["revision"])
    print(write_memory_review(project, batch_id=args.batch))


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print("ERROR: %s" % exc)
        sys.exit(1)
