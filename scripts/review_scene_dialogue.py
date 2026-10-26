"""Emit/record exact-span semantic review evidence without invoking an LLM."""
import argparse
import json
import os
import sys

from novel_agent.approvals import resolve_check_report_path, _load_check_report
from novel_agent.dialogue_review import (
    REVIEWER_TYPES, build_review_template, record_dialogue_review,
)
from novel_agent.storage import atomic_write_json, read_json
from prompt_utils import (
    UserFacingError, resolve_project_path, parse_scene_reference, find_scene_file,
)


def main():
    parser = argparse.ArgumentParser(description='Review dialogue candidates with exact source evidence. Counts are not defects.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--runtime_dir', default='')
    files = parser.add_mutually_exclusive_group()
    files.add_argument('--output', help='Write an incomplete review template, not a successful review')
    files.add_argument('--input', help='Validate and record a filled review JSON file')
    parser.add_argument('--reviewer-type', choices=REVIEWER_TYPES)
    parser.add_argument('--reviewer-id')
    args = parser.parse_args()
    project = resolve_project_path(args.project)
    if not os.path.isdir(project):
        raise UserFacingError('project directory not found: ' + project)
    ref = parse_scene_reference(args.scene)
    path = find_scene_file(project, ref)
    if not path:
        raise UserFacingError('scene text not found: ' + ref['canonical_id'])
    if args.input:
        if args.reviewer_type is None or not args.reviewer_id or not args.reviewer_id.strip():
            parser.error('--input requires --reviewer-type and nonblank --reviewer-id')
        input_path = os.path.abspath(args.input)
        if not os.path.isfile(input_path):
            raise UserFacingError('review input not found: ' + input_path)
        data = read_json(input_path, default_factory=dict)
        record = record_dialogue_review(project, args.scene, data, reviewer_type=args.reviewer_type,
                                        reviewer_id=args.reviewer_id, runtime_dir_arg=args.runtime_dir)
        ready = all(d['judgment'] == 'keep' for d in record['decisions'] + record['comparisons'])
        print('OK: dialogue review recorded candidates={} comparisons={} permits_approval={} reviewer={}:{}'.format(
            len(record['candidates']), len(record['comparisons']), str(ready).lower(), record['reviewer_type'], record['reviewer_id']))
        print('NOTE: evidence completeness is not a machine-certified literary judgment.')
        return
    report = _load_check_report(resolve_check_report_path(project, ref, args.runtime_dir))
    template = build_review_template(project, ref, path, report)
    if args.output:
        atomic_write_json(os.path.abspath(args.output), template)
        print('OK: incomplete dialogue review template written: ' + os.path.abspath(args.output))
    else:
        print(json.dumps(template, ensure_ascii=False, indent=2))
    print('NEXT: read the source; distinguish information-Q&A compression from selective POV reception. Fill exact evidence, reason and reader_effect, then submit with --input. Compare relevant registered keyframes with exact prose spans; implicit dialogue realization need not copy the material literally. Re-register justified omission changes and recheck. Empty templates are invalid.')


if __name__ == '__main__':
    try:
        main()
    except UserFacingError as exc:
        print('ERROR: ' + str(exc))
        sys.exit(1)
