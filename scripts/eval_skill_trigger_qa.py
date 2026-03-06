#!/usr/bin/env python3
"""
Evaluate skill trigger QA prompts with deterministic routing heuristics.

Input format:
  ## <skill-slug>
  ### should-trigger
  - <prompt>
  ### should-not-trigger
  - <prompt>
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


SKILL_PRIORITY = [
    "consistency-auditor",
    "revision-editor",
    "novel-writer",
    "scene-planner",
    "setting-creator",
    "project-bootstrap",
    "resume-orchestrator",
    "idea-generator",
    "prose-polisher",
]


SKILL_PATTERNS = {
    "idea-generator": [
        r"アイディア|アイデア|ネタ出し|発想|壁打ち|ログライン候補|方向性",
        r"案を[0-9一二三四五六七八九十]+|案を増や",
        r"世界観は未定|設定を固めず|物語のフック",
        r"企画を広げ",
    ],
    "project-bootstrap": [
        r"案件作成|初期化|保存先|プロジェクト名|新規案件|箱を作",
        r"init_project|立ち上げ",
        r"agent 運用だけ追加|命名規則|作業フォルダ構成",
    ],
    "setting-creator": [
        r"設定|世界観|プロット|骨格|土台|動機|章方針",
        r"資料を作り直|再設計|見直し",
        r"04_plot_outline",
        r"因果を整え|因果関係",
        r"planning gate|計画ゲート|シーン在庫|scene inventory",
    ],
    "scene-planner": [
        r"段取り|シーン分解|シーン設計|Write Next|ビート",
        r"次の[0-9一二三四五六七八九十]+.?シーン|本文はまだ書かない",
        r"章全体の流れ|シーン候補を比較",
        r"情報不足.*シーン|シーンを選んで段取り",
    ],
    "novel-writer": [
        r"第[0-9]+章|chapter\s*[0-9]+|scene\s*[0-9]",
        r"シーンを書いて|新規本文|初稿|続きを執筆|draft_prompt",
        r"続きの本文|runtime[- ]first|新規執筆",
    ],
    "revision-editor": [
        r"改稿|書き直|リライト|再構成|差し替え|修正",
        r"保持点|弱点|テンポ.*改善|方向性維持",
    ],
    "consistency-auditor": [
        r"矛盾|監査|診断|違和感|洗い出し|問題点|チェック",
        r"感情線|因果の弱さ|優先度|因果の弱い部分",
    ],
    "prose-polisher": [
        r"推敲|文体|語尾|読みやす|冗長|密度|仕上げ|整えて",
        r"構造は変えず",
        r"引きの弱い締め|表現のノイズ",
    ],
    "resume-orchestrator": [
        r"再開|どこから|進捗|現在地|次アクション|Read First",
        r"中断後|resume_brief|推奨スキル",
    ],
}


@dataclass
class SkillCases:
    should_trigger: List[str] = field(default_factory=list)
    should_not_trigger: List[str] = field(default_factory=list)


def parse_dataset(path: Path) -> Dict[str, SkillCases]:
    lines = path.read_text(encoding="utf-8").splitlines()
    dataset: Dict[str, SkillCases] = {}
    current_skill = None
    current_bucket = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            current_skill = line[3:].strip()
            dataset.setdefault(current_skill, SkillCases())
            current_bucket = None
            continue
        if line == "### should-trigger":
            current_bucket = "should_trigger"
            continue
        if line == "### should-not-trigger":
            current_bucket = "should_not_trigger"
            continue
        if line.startswith("- ") and current_skill and current_bucket:
            prompt = line[2:].strip()
            getattr(dataset[current_skill], current_bucket).append(prompt)

    return dataset


def route_prompt(prompt: str) -> str:
    scores = {skill: 0 for skill in SKILL_PATTERNS}
    for skill, patterns in SKILL_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, prompt, flags=re.IGNORECASE):
                scores[skill] += 1

    # Context-aware overrides for common boundary conflicts.
    if re.search(r"本文はまだ書かない", prompt):
        scores["scene-planner"] += 2
        scores["novel-writer"] = max(0, scores["novel-writer"] - 2)

    if re.search(r"agent\s*運用だけ追加", prompt):
        scores["project-bootstrap"] += 3
        scores["scene-planner"] = max(0, scores["scene-planner"] - 1)
        scores["novel-writer"] = max(0, scores["novel-writer"] - 1)

    if re.search(r"設定はまだ白紙|企画の方向性", prompt):
        scores["idea-generator"] += 2
        scores["setting-creator"] = max(0, scores["setting-creator"] - 1)

    if re.search(r"世界観ルール.*整理し直", prompt):
        scores["setting-creator"] += 2
        scores["consistency-auditor"] = max(0, scores["consistency-auditor"] - 1)

    if re.search(r"04_plot_outline|因果をつなぎ直", prompt):
        scores["setting-creator"] += 2
        scores["revision-editor"] = max(0, scores["revision-editor"] - 1)

    if re.search(r"planning gate|計画ゲート|シーン在庫|scene inventory", prompt, flags=re.IGNORECASE):
        scores["setting-creator"] += 3
        scores["scene-planner"] = max(0, scores["scene-planner"] - 2)
        scores["novel-writer"] = max(0, scores["novel-writer"] - 2)

    if re.search(r"着手順|シーン候補を比較", prompt):
        scores["scene-planner"] += 2
        scores["novel-writer"] = max(0, scores["novel-writer"] - 1)

    if re.search(r"段取りだけ|情報不足.*シーン", prompt):
        scores["scene-planner"] += 2
        scores["novel-writer"] = max(0, scores["novel-writer"] - 1)

    best_score = max(scores.values()) if scores else 0
    if best_score == 0:
        return "unknown"

    candidates = [s for s, v in scores.items() if v == best_score]
    for skill in SKILL_PRIORITY:
        if skill in candidates:
            return skill
    return candidates[0]


def evaluate(dataset: Dict[str, SkillCases]) -> dict:
    report = {"skills": {}, "summary": {}}
    total_should = 0
    total_should_hit = 0
    total_should_not = 0
    total_should_not_true_negative = 0

    for skill, cases in dataset.items():
        should_total = len(cases.should_trigger)
        should_hit = 0
        false_negative = []
        for prompt in cases.should_trigger:
            predicted = route_prompt(prompt)
            if predicted == skill:
                should_hit += 1
            else:
                false_negative.append({"prompt": prompt, "predicted": predicted})

        should_not_total = len(cases.should_not_trigger)
        should_not_true_negative = 0
        false_positive = []
        for prompt in cases.should_not_trigger:
            predicted = route_prompt(prompt)
            if predicted != skill:
                should_not_true_negative += 1
            else:
                false_positive.append({"prompt": prompt, "predicted": predicted})

        total_should += should_total
        total_should_hit += should_hit
        total_should_not += should_not_total
        total_should_not_true_negative += should_not_true_negative

        report["skills"][skill] = {
            "should_trigger_total": should_total,
            "should_trigger_hit": should_hit,
            "should_trigger_recall": round(should_hit / should_total, 4) if should_total else 0.0,
            "should_not_trigger_total": should_not_total,
            "should_not_trigger_true_negative": should_not_true_negative,
            "should_not_trigger_true_negative_rate": round(
                should_not_true_negative / should_not_total, 4
            )
            if should_not_total
            else 0.0,
            "false_negative": false_negative,
            "false_positive": false_positive,
        }

    recall = (total_should_hit / total_should) if total_should else 0.0
    true_negative_rate = (
        total_should_not_true_negative / total_should_not if total_should_not else 0.0
    )
    false_positive_rate = 1.0 - true_negative_rate

    report["summary"] = {
        "skills_covered": len(dataset),
        "total_should_trigger": total_should,
        "total_should_trigger_hit": total_should_hit,
        "should_trigger_recall": round(recall, 4),
        "total_should_not_trigger": total_should_not,
        "total_should_not_trigger_true_negative": total_should_not_true_negative,
        "should_not_trigger_true_negative_rate": round(true_negative_rate, 4),
        "should_not_trigger_false_positive_rate": round(false_positive_rate, 4),
        "pass_threshold": {
            "should_trigger_recall_min": 0.9,
            "should_not_trigger_false_positive_rate_max": 0.1,
        },
        "overall_pass": (recall >= 0.9) and (false_positive_rate <= 0.1),
    }
    return report


def write_markdown(report: dict, out_path: Path) -> None:
    s = report["summary"]
    lines = [
        "# Skill Trigger QA Report",
        "",
        "## Summary",
        f"- Skills covered: {s['skills_covered']}",
        f"- should-trigger recall: {s['should_trigger_recall']}",
        f"- should-not-trigger false-positive-rate: {s['should_not_trigger_false_positive_rate']}",
        f"- Overall pass: {s['overall_pass']}",
        "",
        "## Per Skill",
    ]

    for skill, m in report["skills"].items():
        lines.extend(
            [
                f"### {skill}",
                f"- should-trigger: {m['should_trigger_hit']}/{m['should_trigger_total']} (recall={m['should_trigger_recall']})",
                f"- should-not-trigger: {m['should_not_trigger_true_negative']}/{m['should_not_trigger_total']} (tnr={m['should_not_trigger_true_negative_rate']})",
            ]
        )
        if m["false_negative"]:
            lines.append("- false negatives:")
            for fn in m["false_negative"][:3]:
                lines.append(f"  - predicted={fn['predicted']} prompt={fn['prompt']}")
        if m["false_positive"]:
            lines.append("- false positives:")
            for fp in m["false_positive"][:3]:
                lines.append(f"  - predicted={fp['predicted']} prompt={fp['prompt']}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate skill trigger QA markdown dataset.")
    parser.add_argument("--input", required=True, help="Path to trigger QA markdown")
    parser.add_argument("--json_out", required=True, help="Path to output JSON report")
    parser.add_argument("--md_out", help="Optional path to output markdown summary")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        return 1

    dataset = parse_dataset(input_path)
    if not dataset:
        print("ERROR: dataset parse failed or empty")
        return 1

    report = evaluate(dataset)
    Path(args.json_out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.md_out:
        write_markdown(report, Path(args.md_out))

    print(f"OK: evaluated {len(dataset)} skills")
    print(f"OK: wrote {args.json_out}")
    if args.md_out:
        print(f"OK: wrote {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
