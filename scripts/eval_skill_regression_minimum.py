#!/usr/bin/env python3
"""
Evaluate the minimum skill regression set.

Input format:
  ## <number>. <skill-slug>
  - Input: ...
  - Expected: ...
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

from eval_skill_trigger_qa import route_prompt


REQUIRED_SKILLS = [
    "idea-generator",
    "project-bootstrap",
    "setting-creator",
    "scene-planner",
    "novel-writer",
    "revision-editor",
    "consistency-auditor",
    "prose-polisher",
    "resume-orchestrator",
]


def parse_cases(path: Path) -> List[Dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cases: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m = re.match(r"^##\s+(?:\d+\.\s+)?([a-z\-]+)\s*$", line)
        if m:
            if current:
                cases.append(current)
            current = {"skill": m.group(1), "input": "", "expected": ""}
            continue

        if current is None:
            continue
        if line.startswith("- Input:"):
            current["input"] = line[len("- Input:") :].strip()
        elif line.startswith("- Expected:"):
            current["expected"] = line[len("- Expected:") :].strip()

    if current:
        cases.append(current)
    return cases


def evaluate(cases: List[Dict[str, str]]) -> Dict:
    evaluated = []
    passed = 0

    for idx, case in enumerate(cases, start=1):
        expected_skill = case["skill"]
        prompt = case["input"]
        predicted = route_prompt(prompt)
        is_pass = predicted == expected_skill
        status = "pass" if is_pass else "fail"
        if is_pass:
            passed += 1

        fail_trigger = None
        if not is_pass:
            fail_trigger = {
                "type": "UNKNOWN_ROUTE" if predicted == "unknown" else "ROUTER_MISMATCH",
                "repro_input": prompt,
                "expected_skill": expected_skill,
                "predicted_skill": predicted,
            }

        evaluated.append(
            {
                "case_id": idx,
                "skill": expected_skill,
                "input": prompt,
                "expected_behavior": case["expected"],
                "predicted_skill": predicted,
                "status": status,
                "fail_trigger": fail_trigger,
            }
        )

    covered = sorted({c["skill"] for c in cases})
    missing_required = [s for s in REQUIRED_SKILLS if s not in covered]

    failed_case_ids = [c["case_id"] for c in evaluated if c["status"] == "fail"]

    summary = {
        "total_cases": len(cases),
        "passed_cases": passed,
        "failed_cases": len(cases) - passed,
        "pass_rate": round(passed / len(cases), 4) if cases else 0.0,
        "skills_covered": len(covered),
        "covered_skill_list": covered,
        "missing_required_skills": missing_required,
        "failed_case_ids": failed_case_ids,
        "fail_trigger_record_fields": [
            "type",
            "repro_input",
            "expected_skill",
            "predicted_skill",
        ],
        "overall_pass": (len(cases) > 0) and (passed == len(cases)) and (len(missing_required) == 0),
    }
    return {"summary": summary, "cases": evaluated}


def write_markdown(report: Dict, out_path: Path) -> None:
    s = report["summary"]
    lines = [
        "# Skill Regression Minimum Report",
        "",
        "## Summary",
        f"- Total cases: {s['total_cases']}",
        f"- Passed: {s['passed_cases']}",
        f"- Failed: {s['failed_cases']}",
        f"- Pass rate: {s['pass_rate']}",
        f"- Skills covered: {s['skills_covered']}",
        f"- Missing required skills: {', '.join(s['missing_required_skills']) if s['missing_required_skills'] else 'none'}",
        f"- Failed case IDs: {', '.join(str(x) for x in s['failed_case_ids']) if s['failed_case_ids'] else 'none'}",
        f"- Overall pass: {s['overall_pass']}",
        "",
        "## Fail Trigger Reproduction",
        "- Re-run command:",
        "  - `python scripts/eval_skill_regression_minimum.py --input <dataset.md> --json_out <report.json> --md_out <report.md>`",
        "- Fail trigger fields:",
        f"  - {', '.join(s['fail_trigger_record_fields'])}",
        "",
        "## Case Results",
    ]

    for c in report["cases"]:
        lines.extend(
            [
                f"### Case {c['case_id']} - {c['skill']}",
                f"- Input: {c['input']}",
                f"- Expected: {c['expected_behavior']}",
                f"- Predicted Skill: {c['predicted_skill']}",
                f"- Status: {c['status']}",
            ]
        )
        if c["fail_trigger"]:
            ft = c["fail_trigger"]
            lines.extend(
                [
                    "- Fail Trigger:",
                    f"  - type={ft['type']}",
                    f"  - expected={ft['expected_skill']}",
                    f"  - predicted={ft['predicted_skill']}",
                    f"  - repro_input={ft['repro_input']}",
                ]
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate minimum skill regression set.")
    parser.add_argument("--input", required=True, help="Path to skill_regression_minimum markdown")
    parser.add_argument("--json_out", required=True, help="Path to output JSON report")
    parser.add_argument("--md_out", help="Optional path to output Markdown report")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        return 1

    cases = parse_cases(input_path)
    if not cases:
        print("ERROR: no regression cases found")
        return 1

    report = evaluate(cases)
    Path(args.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md_out:
        write_markdown(report, Path(args.md_out))

    print(f"OK: evaluated {report['summary']['total_cases']} regression cases")
    print(f"OK: wrote {args.json_out}")
    if args.md_out:
        print(f"OK: wrote {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
