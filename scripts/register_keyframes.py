"""Validate or explicitly register an external proposal; never generate prose."""
import argparse
import sys
from novel_agent.errors import UserFacingError
from novel_agent.keyframe_runtime import register_keyframes
from prompt_utils import resolve_project_path, parse_scene_reference


def main():
    parser = argparse.ArgumentParser(description='Validate/register selected POV creative material, not prose approval.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--runtime_dir', default='')
    parser.add_argument('--input', required=True)
    parser.add_argument('--validate-only', action='store_true', help='Validate without changing artifacts, ledgers or prose')
    args = parser.parse_args()
    register_keyframes(resolve_project_path(args.project), parse_scene_reference(args.scene)['canonical_id'], args.input,
                       runtime_dir_arg=args.runtime_dir, validate_only=args.validate_only)
    print('OK: proposal ' + ('validated without writes' if args.validate_only else 'registered; not prose approval'))
    print('NEXT: ' + ('register without --validate-only, then prompt' if args.validate_only else 'prompt, write prose, check and review before explicit approval'))


if __name__ == '__main__':
    try:
        main()
    except UserFacingError as exc:
        print('ERROR: ' + str(exc)); sys.exit(1)
