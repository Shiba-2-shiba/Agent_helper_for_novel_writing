"""Import a proposed memory batch without adopting it."""
import argparse
import json
import sys

from novel_agent.errors import UserFacingError
from novel_agent.storage import read_json
from novel_agent.story_memory import import_proposal, validate_proposal
from prompt_utils import resolve_project_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    project = resolve_project_path(args.project)
    payload = read_json(args.input, default_factory=dict)
    if args.validate_only:
        result = validate_proposal(project, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["valid"]:
            raise UserFacingError("proposal validation failed; nothing was imported")
    else:
        result = import_proposal(project, payload)
        print("OK: proposed batch %s saved; not accepted" % result["batch_id"])


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print("ERROR: %s" % exc)
        sys.exit(1)
