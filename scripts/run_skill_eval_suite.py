#!/usr/bin/env python3
"""
Run the skill evaluation suite:
1) trigger QA
2) regression minimum
3) regression boundary
Then write a consolidated suite summary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def run_cmd(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_markdown(summary: Dict, out_path: Path) -> None:
    t = summary["trigger"]
    r1 = summary["regression_minimum"]
    r2 = summary["regression_boundary"]
    lines = [
        "# Skill Eval Suite Report",
        "",
        "## Summary",
        f"- Generated at (UTC): {summary['generated_at_utc']}",
        f"- Overall pass: {summary['overall_pass']}",
        "",
        "## Trigger QA",
        f"- pass: {t['pass']}",
        f"- skills_covered: {t['skills_covered']}",
        f"- should-trigger recall: {t['should_trigger_recall']}",
        f"- should-not-trigger false-positive-rate: {t['should_not_trigger_false_positive_rate']}",
        "",
        "## Regression Minimum",
        f"- pass: {r1['pass']}",
        f"- total_cases: {r1['total_cases']}",
        f"- failed_cases: {r1['failed_cases']}",
        f"- pass_rate: {r1['pass_rate']}",
        "",
        "## Regression Boundary",
        f"- pass: {r2['pass']}",
        f"- total_cases: {r2['total_cases']}",
        f"- failed_cases: {r2['failed_cases']}",
        f"- pass_rate: {r2['pass_rate']}",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full skill evaluation suite.")

    parser.add_argument(
        "--trigger_input",
        default="agent/evals/prompts/skill_trigger_qa_2026-03-05.md",
    )
    parser.add_argument(
        "--regression_min_input",
        default="agent/evals/prompts/skill_regression_minimum_2026-03-05.md",
    )
    parser.add_argument(
        "--regression_boundary_input",
        default="agent/evals/prompts/skill_regression_boundary_2026-03-05.md",
    )

    parser.add_argument(
        "--trigger_json_out",
        default="agent/evals/results/skill_trigger_qa_report_2026-03-05.json",
    )
    parser.add_argument(
        "--trigger_md_out",
        default="agent/evals/results/skill_trigger_qa_report_2026-03-05.md",
    )
    parser.add_argument(
        "--regression_min_json_out",
        default="agent/evals/results/skill_regression_minimum_report_2026-03-05.json",
    )
    parser.add_argument(
        "--regression_min_md_out",
        default="agent/evals/results/skill_regression_minimum_report_2026-03-05.md",
    )
    parser.add_argument(
        "--regression_boundary_json_out",
        default="agent/evals/results/skill_regression_boundary_report_2026-03-05.json",
    )
    parser.add_argument(
        "--regression_boundary_md_out",
        default="agent/evals/results/skill_regression_boundary_report_2026-03-05.md",
    )
    parser.add_argument(
        "--suite_json_out",
        default="agent/evals/results/skill_eval_suite_report_2026-03-05.json",
    )
    parser.add_argument(
        "--suite_md_out",
        default="agent/evals/results/skill_eval_suite_report_2026-03-05.md",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    trigger_script = script_dir / "eval_skill_trigger_qa.py"
    regression_script = script_dir / "eval_skill_regression_minimum.py"

    trigger_cmd = [
        sys.executable,
        str(trigger_script),
        "--input",
        args.trigger_input,
        "--json_out",
        args.trigger_json_out,
        "--md_out",
        args.trigger_md_out,
    ]
    res = run_cmd(trigger_cmd)
    if res.returncode != 0:
        print("ERROR: trigger QA run failed")
        print(res.stdout + res.stderr)
        return 1

    reg_min_cmd = [
        sys.executable,
        str(regression_script),
        "--input",
        args.regression_min_input,
        "--json_out",
        args.regression_min_json_out,
        "--md_out",
        args.regression_min_md_out,
    ]
    res = run_cmd(reg_min_cmd)
    if res.returncode != 0:
        print("ERROR: regression minimum run failed")
        print(res.stdout + res.stderr)
        return 1

    reg_boundary_cmd = [
        sys.executable,
        str(regression_script),
        "--input",
        args.regression_boundary_input,
        "--json_out",
        args.regression_boundary_json_out,
        "--md_out",
        args.regression_boundary_md_out,
    ]
    res = run_cmd(reg_boundary_cmd)
    if res.returncode != 0:
        print("ERROR: regression boundary run failed")
        print(res.stdout + res.stderr)
        return 1

    trigger = load_json(Path(args.trigger_json_out))
    reg_min = load_json(Path(args.regression_min_json_out))
    reg_boundary = load_json(Path(args.regression_boundary_json_out))

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trigger": {
            "pass": bool(trigger["summary"]["overall_pass"]),
            "skills_covered": int(trigger["summary"]["skills_covered"]),
            "should_trigger_recall": float(trigger["summary"]["should_trigger_recall"]),
            "should_not_trigger_false_positive_rate": float(
                trigger["summary"]["should_not_trigger_false_positive_rate"]
            ),
        },
        "regression_minimum": {
            "pass": bool(reg_min["summary"]["overall_pass"]),
            "total_cases": int(reg_min["summary"]["total_cases"]),
            "failed_cases": int(reg_min["summary"]["failed_cases"]),
            "pass_rate": float(reg_min["summary"]["pass_rate"]),
        },
        "regression_boundary": {
            "pass": bool(reg_boundary["summary"]["overall_pass"]),
            "total_cases": int(reg_boundary["summary"]["total_cases"]),
            "failed_cases": int(reg_boundary["summary"]["failed_cases"]),
            "pass_rate": float(reg_boundary["summary"]["pass_rate"]),
        },
    }
    summary["overall_pass"] = (
        summary["trigger"]["pass"]
        and summary["regression_minimum"]["pass"]
        and summary["regression_boundary"]["pass"]
    )

    suite_json_path = Path(args.suite_json_out)
    suite_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(summary, Path(args.suite_md_out))

    print(f"OK: wrote {args.suite_json_out}")
    print(f"OK: wrote {args.suite_md_out}")
    print(f"OK: overall_pass={summary['overall_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
