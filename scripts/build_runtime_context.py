import argparse
import os
import re
import sys

from prompt_utils import (
    compute_planned_totals,
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    RUNTIME_CONTINUITY_WARN_LIMIT,
    UserFacingError,
    build_style_contract,
    count_chapter_written_chars,
    estimate_tokens,
    ensure_directory,
    extract_chapter_block,
    extract_chapter_summary,
    extract_scene_description,
    find_scene_ledger_entry,
    find_previous_scene_pack,
    _find_first_existing,
    load_planning_metadata,
    parse_scene_reference,
    parse_scene_ledger,
    parse_chapter_target_chars,
    read_optional_text,
    read_text_file,
    require_existing_file,
    resolve_outline_path,
    resolve_scene_type_band,
    resolve_project_path,
    resolve_relative_path,
    validate_positive_int,
    write_text_file,
)


def _extract_outline_chapter_numbers(outline_text):
    if not outline_text:
        return []
    return sorted({int(match.group(1)) for match in re.finditer(r"(?m)^#{1,6}\s*第(\d+)章", outline_text)})


def build_planning_gate_brief(planning_meta, outline_text):
    chapter_numbers = _extract_outline_chapter_numbers(outline_text)
    computed_totals = compute_planned_totals(outline_text) if outline_text else {}

    planned_scene_count = computed_totals.get("planned_scene_count", 0) or planning_meta["planned_scene_count"]
    planned_total_min_chars = computed_totals.get("planned_total_min_chars", 0) or planning_meta["planned_total_min_chars"]
    planned_total_target_chars = computed_totals.get("planned_total_target_chars", 0) or planning_meta["planned_total_target_chars"]
    gate_threshold = planning_meta["planning_gate_min_chars"]
    gate_enabled = planning_meta["planning_gate_enabled"]
    gate_status = planning_meta["planning_gate_status"] or "unknown"

    chapter_scene_counts = computed_totals.get("chapter_scene_counts", {})
    chapters_with_inventory = [str(chapter) for chapter in chapter_numbers if chapter_scene_counts.get(str(chapter), 0) > 0]
    chapters_missing_inventory = [str(chapter) for chapter in chapter_numbers if chapter_scene_counts.get(str(chapter), 0) == 0]
    gate_gap = max(0, gate_threshold - planned_total_min_chars) if gate_enabled and gate_threshold else 0

    if not gate_enabled:
        next_action = "planning gate は無効。通常の runtime-first 運用を続ける。"
    elif gate_status == "ready":
        next_action = "planning gate は通過済み。対象シーンの段取りまたは本文執筆へ進める。"
    elif chapters_missing_inventory:
        next_action = (
            "不足している章の Scene Ledger を先に埋める: "
            + ", ".join(f"第{chapter}章" for chapter in chapters_missing_inventory)
        )
    elif gate_gap > 0:
        next_action = f"Scene Ledger を増強し、planned_total_min_chars をあと {gate_gap} 字ぶん積み増す。"
    else:
        next_action = "planning gate 判定根拠を確認し、setting-creator で章配分と scene inventory を再点検する。"

    return "\n".join(
        [
            "# Planning Gate Brief",
            f"Target Total Chars: {planning_meta['target_total_chars']}",
            f"Target Length Profile: {planning_meta['target_length_profile']}",
            f"Planning Gate Enabled: {str(gate_enabled).lower()}",
            f"Planning Gate: {gate_status}",
            "Planning Totals:",
            f"- Planned Scene Count: {planned_scene_count}",
            f"- Planned Total Min Chars: {planned_total_min_chars}",
            f"- Planned Total Target Chars: {planned_total_target_chars}",
            f"- Planning Gate Min Chars: {gate_threshold}",
            f"- Planning Target Total Chars: {planning_meta['planning_target_total_chars']}",
            *([f"Length Mode: {planning_meta['length_mode']}"] if planning_meta["length_mode"] else []),
            "Coverage Snapshot:",
            f"- Outline Chapters Found: {len(chapter_numbers)}",
            f"- Chapters With Scene Inventory: {', '.join(chapters_with_inventory) if chapters_with_inventory else '-'}",
            f"- Chapters Missing Scene Inventory: {', '.join(chapters_missing_inventory) if chapters_missing_inventory else '-'}",
            f"- Gate Gap To Threshold: {gate_gap}",
            "Next Planning Action:",
            f"- {next_action}",
        ]
    )


def _split_payoff_seed(raw_value):
    if not raw_value:
        return "-", "-"

    text = raw_value.strip()
    payoff = "-"
    seed = "-"

    payoff_match = re.search(r"(?:回収|payoff)\s*[:：]\s*([^/;]+)", text, re.IGNORECASE)
    seed_match = re.search(r"(?:種|種まき|seed)\s*[:：]\s*([^/;]+)", text, re.IGNORECASE)
    if payoff_match:
        payoff = payoff_match.group(1).strip()
    if seed_match:
        seed = seed_match.group(1).strip()

    if payoff == "-" and any(token in text for token in ("回収", "payoff")):
        payoff = text
    if seed == "-" and any(token in text for token in ("種", "火種", "seed", "推進力")):
        seed = text

    if payoff == "-" and seed == "-":
        seed = text

    return payoff, seed


def _resolve_scene_length_band(scene_plan, planning_meta):
    if scene_plan and scene_plan["min_chars"] and scene_plan["target_chars"] and scene_plan["max_chars"]:
        return {
            "scene_type": scene_plan["scene_type"] or "default",
            "min": scene_plan["min_chars"],
            "target": scene_plan["target_chars"],
            "max": scene_plan["max_chars"],
        }

    return resolve_scene_type_band(
        scene_plan["scene_type"] if scene_plan else "",
        state_schema_text=planning_meta["state_schema_text"],
        min_chars=DEFAULT_MIN_CHARS,
        target_chars=DEFAULT_TARGET_CHARS,
        max_chars=DEFAULT_MAX_CHARS,
    )


def _count_planned_scenes_remaining(chapter_rows, scene_ref):
    if not chapter_rows:
        return 0

    remaining = 0
    for row in chapter_rows:
        if row["scene"] < scene_ref["scene"]:
            continue
        if row["status"] in {"done", "completed", "final"}:
            continue
        remaining += 1
    return remaining


def build_scene_brief(chapter_block, scene_ref, project_dir, planning_meta):
    scene_plan = find_scene_ledger_entry(chapter_block, scene_ref["scene"], chapter_num=scene_ref["chapter"])
    chapter_rows = parse_scene_ledger(chapter_block)
    scene_desc = extract_scene_description(chapter_block, scene_ref["scene"])
    chapter_summary = extract_chapter_summary(chapter_block)
    next_plan = find_scene_ledger_entry(chapter_block, scene_ref["scene"] + 1, chapter_num=scene_ref["chapter"])
    next_desc = extract_scene_description(chapter_block, scene_ref["scene"] + 1)
    length_band = _resolve_scene_length_band(scene_plan, planning_meta)

    chapter_target_chars = parse_chapter_target_chars(chapter_block)
    if not chapter_target_chars and chapter_rows:
        chapter_target_chars = sum(row["target_chars"] for row in chapter_rows if row["target_chars"] > 0)
    chapter_written_chars = count_chapter_written_chars(project_dir, scene_ref["chapter"])
    chapter_budget_remaining = max(0, chapter_target_chars - chapter_written_chars) if chapter_target_chars else 0
    chapter_planned_scenes_remaining = _count_planned_scenes_remaining(chapter_rows, scene_ref)

    goal = scene_desc or chapter_summary or "章の流れを前進させる決定的な一手を置く"
    if scene_plan and scene_plan["turn"]:
        conflict = f"{scene_plan['turn']} の変化を起こす際の抵抗や代償を最低1つ置く"
        emotion_shift = scene_plan["turn"]
    elif scene_desc:
        conflict = f"{scene_desc}を進める際の抵抗や障害を最低1つ明示する"
        emotion_shift = "観察・静止 -> 判断・行動"
    else:
        conflict = "直前シーンからの因果を保ちつつ、主人公の選択に対する抵抗を置く"
        emotion_shift = "現状維持 -> 小さな変化"

    hook = (
        next_plan["purpose"]
        if next_plan and next_plan["purpose"]
        else next_desc or "次シーンで回収できる未解決要素を1つ残す"
    )
    payoff, seed = _split_payoff_seed(scene_plan["payoff_or_seed"] if scene_plan else "")
    depends_on = scene_plan["depends_on"] if scene_plan and scene_plan["depends_on"] else "-"
    source_outline = "Scene Ledger" if scene_plan else scene_ref["filename"]

    return "\n".join(
        [
            "# Scene Brief Compact",
            f"Goal: {goal}",
            f"Conflict: {conflict}",
            f"Emotion Shift: {emotion_shift}",
            f"Hook: {hook}",
            f"Target Total Chars: {planning_meta['target_total_chars']}",
            f"Target Length Profile: {planning_meta['target_length_profile']}",
            f"Planning Gate Enabled: {str(planning_meta['planning_gate_enabled']).lower()}",
            f"Scene Type: {length_band['scene_type']}",
            f"Length Band: {length_band['min']} / {length_band['target']} / {length_band['max']}",
            f"Chapter Budget Remaining: {chapter_budget_remaining}",
            f"Chapter Planned Scenes Remaining: {chapter_planned_scenes_remaining}",
            f"This Scene Pays Off: {payoff}",
            f"This Scene Seeds: {seed}",
            f"Depends On: {depends_on}",
            "Hard Constraints:",
            f"- Scene ID: {scene_ref['canonical_id']}",
            f"- Source Outline: {source_outline} を起点に構成する",
            f"- Planning Gate: {planning_meta['planning_gate_status'] or 'unknown'}",
            "- 直前シーンとの接続を優先する",
            "- 新しい設定事実は必要最小限に留める",
        ]
    )


def build_continuity_pack(previous_pack):
    full_item = previous_pack["full"]
    summary_item = previous_pack["summary"]

    lines = ["# Continuity Pack"]
    if full_item:
        lines.extend(
            [
                "## Immediate Previous Scene (Full Text)",
                f"Source ({full_item['source']}): {full_item['path']}",
                "",
                full_item["text"].rstrip(),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Immediate Previous Scene (Full Text)",
                "前シーン本文は未検出。冒頭1段落で接続感を補強すること。",
                "",
            ]
        )

    if summary_item:
        lines.extend(
            [
                "## One Scene Earlier (Summary)",
                f"Source ({summary_item['source']}): {summary_item['path']}",
                f"Summary: {summary_item['summary']}",
            ]
        )
    else:
        lines.extend(
            [
                "## One Scene Earlier (Summary)",
                "要約対象の1つ前シーンは未検出。",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def build_request_compact(mode, priority, scene_ref, planning_meta, length_band):
    if mode == "draft":
        purpose = "圧縮済み文脈のみで初稿の骨格を作る"
        deliverables = [
            "自然な本文初稿",
            "直前シーンと接続した導入",
            "次シーンへ渡すフック",
        ]
    else:
        purpose = "現在位置を短く再把握し、次の作業モード判断につなげる"
        deliverables = [
            "再開判断に必要な要点整理",
            "次アクション候補",
        ]

    lines = [
        "# Request Compact",
        f"Current Mode: {mode}",
        f"Purpose: {purpose}",
        "Deliverables:",
        *[f"- {item}" for item in deliverables],
        "Constraints:",
        "- フル文脈を再投入しない",
        "- 文体契約を優先する",
        f"- 対象シーン: {scene_ref['canonical_id']}",
        f"- Target Total Chars: {planning_meta['target_total_chars']}",
        f"- Target Length Profile: {planning_meta['target_length_profile']}",
        f"- Planning Gate Enabled: {str(planning_meta['planning_gate_enabled']).lower()}",
        f"- Planning Gate: {planning_meta['planning_gate_status'] or 'unknown'}",
        f"- Target Band: {length_band['min']} / {length_band['target']} / {length_band['max']}",
        f"Priority: {priority}",
    ]
    if planning_meta["length_mode"]:
        lines.append(f"- Length Mode: {planning_meta['length_mode']}")
    return "\n".join(lines)


def build_resume_brief(scene_ref, previous_pack, session_notes_text, planning_meta):
    full_item = previous_pack["full"]
    current_position = (
        f"chapter {scene_ref['chapter']} scene {scene_ref['scene']} の準備段階。"
        f" 直前参照: {os.path.basename(full_item['path']) if full_item else '未検出'}"
    )
    if planning_meta["planning_gate_status"] and planning_meta["planning_gate_status"] != "ready":
        current_position += f" planning gate は {planning_meta['planning_gate_status']}。"

    open_items = []
    if session_notes_text:
        for line in session_notes_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(("- ", "* ", "- [", "* [")):
                open_items.append(stripped.lstrip("-* ").strip())
            if len(open_items) >= 3:
                break
    if not open_items:
        open_items.append("次シーンの具体的な衝突と着地を確定する")
        open_items.append("直前シーンの余韻をどう継続するか決める")

    next_actions = [
        "runtime/planning_gate_brief.md を確認する",
        "runtime/style_contract_compact.md を確認する",
        "draft に進むか resume 継続かを判断する",
        f"{scene_ref['canonical_id']} の着手条件を1行で決める",
    ]
    read_first = [
        "runtime/planning_gate_brief.md",
        "runtime/style_contract_compact.md",
        "runtime/request_compact.md",
    ]
    if full_item:
        read_first.append(full_item["path"])
    if session_notes_text:
        read_first.append("agent/memory/session_notes.md")

    return "\n".join(
        [
            "# Resume Brief",
            f"Current Position: {current_position}",
            "Open Items:",
            *[f"- {item}" for item in open_items],
            "Next Actions:",
            *[f"- {item}" for item in next_actions],
            "Read First:",
            *[f"- {item}" for item in read_first],
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Build compact runtime files for draft or resume mode.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--chapter", required=True, type=int, help="Current chapter number")
    parser.add_argument("--scene", required=True, help="Scene ID (3-2 or chapter_3_scene_2)")
    parser.add_argument("--mode", required=True, choices=["draft", "resume"], help="Runtime generation mode")
    parser.add_argument("--previous_text", default="", help="Optional previous scene text path")
    parser.add_argument(
        "--priority",
        default="balanced",
        choices=["speed", "balanced", "quality"],
        help="Runtime extraction priority",
    )
    parser.add_argument("--force", action="store_true", help="Accepted for compatibility; outputs are always refreshed")
    args = parser.parse_args()

    validate_positive_int("chapter", args.chapter)
    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    scene_ref = parse_scene_reference(args.scene)
    if scene_ref["chapter"] != args.chapter:
        raise UserFacingError("chapter and scene arguments do not match")

    previous_path = ""
    if args.previous_text:
        previous_path = resolve_relative_path(args.previous_text, base_dirs=[project_dir], must_exist=True)

    runtime_dir = os.path.join(project_dir, "runtime")
    ensure_directory(runtime_dir)

    outline_path = resolve_outline_path(project_dir)
    outline_text = read_text_file(outline_path) if os.path.exists(outline_path) else ""

    chapter_block = ""
    if args.mode == "draft":
        outline_path = resolve_outline_path(project_dir, require_exists=True)
        outline_text = read_text_file(outline_path)
        chapter_block = extract_chapter_block(outline_text, args.chapter)
        if not chapter_block:
            raise UserFacingError(f"chapter {args.chapter} block not found in outline")

    planning_meta = load_planning_metadata(project_dir)
    if args.mode == "draft":
        scene_plan = find_scene_ledger_entry(chapter_block, scene_ref["scene"], chapter_num=scene_ref["chapter"])
        length_band = _resolve_scene_length_band(scene_plan, planning_meta)
    else:
        length_band = resolve_scene_type_band(
            "",
            state_schema_text=planning_meta["state_schema_text"],
            min_chars=DEFAULT_MIN_CHARS,
            target_chars=DEFAULT_TARGET_CHARS,
            max_chars=DEFAULT_MAX_CHARS,
        )

    style_contract, warnings = build_style_contract(
        project_dir,
        min_chars=length_band["min"],
        target_chars=length_band["target"],
        max_chars=length_band["max"],
    )
    previous_pack = find_previous_scene_pack(project_dir, scene_ref, previous_path)
    written_files = []

    if not previous_pack["full"]:
        warnings.append("previous scene not found, continuity pack contains fallback note")
    else:
        continuity_tokens = estimate_tokens(previous_pack["full"]["text"])
        if continuity_tokens > RUNTIME_CONTINUITY_WARN_LIMIT:
            warnings.append(
                "previous scene is large and may inflate runtime prompts "
                f"(estimated_tokens={continuity_tokens}, target<={RUNTIME_CONTINUITY_WARN_LIMIT})"
            )
    if (
        args.mode == "draft"
        and planning_meta["planning_gate_enabled"]
        and planning_meta["planning_gate_status"]
        and planning_meta["planning_gate_status"] != "ready"
    ):
        warnings.append(
            "planning_gate_status is not ready; runtime was generated for inspection, "
            "but drafting should normally wait until planning is complete"
        )

    style_path = os.path.join(runtime_dir, "style_contract_compact.md")
    write_text_file(style_path, style_contract + "\n")
    written_files.append(style_path)

    request_path = os.path.join(runtime_dir, "request_compact.md")
    write_text_file(request_path, build_request_compact(args.mode, args.priority, scene_ref, planning_meta, length_band) + "\n")
    written_files.append(request_path)

    planning_gate_path = os.path.join(runtime_dir, "planning_gate_brief.md")
    write_text_file(planning_gate_path, build_planning_gate_brief(planning_meta, outline_text) + "\n")
    written_files.append(planning_gate_path)

    if args.mode == "draft":
        scene_brief_path = os.path.join(runtime_dir, "scene_brief_compact.md")
        write_text_file(scene_brief_path, build_scene_brief(chapter_block, scene_ref, project_dir, planning_meta) + "\n")
        written_files.append(scene_brief_path)

        continuity_path = os.path.join(runtime_dir, "continuity_pack.md")
        write_text_file(continuity_path, build_continuity_pack(previous_pack))
        written_files.append(continuity_path)
    else:
        session_notes = read_optional_text(
            os.path.join(project_dir, "agent", "memory", "session_notes.md")
        ) or read_optional_text(
            os.path.join(project_dir, "memory", "session_notes.md")
        )
        resume_path = os.path.join(runtime_dir, "resume_brief.md")
        write_text_file(resume_path, build_resume_brief(scene_ref, previous_pack, session_notes, planning_meta) + "\n")
        written_files.append(resume_path)

    for warning in warnings:
        print(f"WARN: {warning}")
    print(f"OK: runtime context generated for chapter {args.chapter} scene {scene_ref['scene']}")
    print(f"OK: wrote {len(written_files)} files into {runtime_dir}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while generating runtime context")
        sys.exit(1)
