"""Dry-run or explicitly archive/reset a project's generated dependency cache."""
import argparse
import json
import os
import sys

from novel_agent.dependency_cache import rebuild_dependency_cache
from novel_agent.errors import UserFacingError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Project copy to rebuild; authored sources and approvals are unchanged')
    parser.add_argument('--apply', action='store_true', help='Archive exact old ledger and mark old runtimes for explicit prepare')
    args = parser.parse_args()
    project = os.path.realpath(args.project)
    if not os.path.isdir(project):
        raise UserFacingError('project directory not found: ' + project)
    print(json.dumps(rebuild_dependency_cache(project, apply=args.apply), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except UserFacingError as exc:
        print('ERROR: ' + str(exc))
        sys.exit(1)
