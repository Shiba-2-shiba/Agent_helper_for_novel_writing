import argparse
import os
import sys

from prompt_utils import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    RUNTIME_CONTINUITY_WARN_LIMIT,
    UserFacingError,
    build_style_contract,
    estimate_tokens,
    ensure_directory,
    extract_chapter_block,
    extract_chapter_summary,
    extract_scene_description,
    find_previous_scene_pack,
    _find_first_existing,
    parse_scene_reference,
    read_optional_text,
    read_text_file,
    require_existing_file,
    resolve_project_path,
    resolve_relative_path,
    validate_positive_int,
    write_text_file,
)


def build_scene_brief(chapter_block, scene_ref):
    scene_desc = extract_scene_description(chapter_block, scene_ref["scene"])
    chapter_summary = extract_chapter_summary(chapter_block)
    next_desc = extract_scene_description(chapter_block, scene_ref["scene"] + 1)

    goal = scene_desc or chapter_summary or "章の流れを前進させる決定的な一手を置く"
    conflict = (
        f"{scene_desc}を進める際の抵抗や障害を最低1つ明示する"
        if scene_desc
        else "直前シーンからの因果を保ちつつ、主人公の選択に対する抵抗を置く"
    )
    emotion_shift = "観察・静止 -> 判断・行動" if scene_desc else "現状維持 -> 小さな変化"
    hook = next_desc or "次シーンで回収できる未解決要素を1つ残す"

    return "\n".join(
        [
            "# Scene Brief Compact",
            f"Goal: {goal}",
            f"Conflict: {conflict}",
            f"Emotion Shift: {emotion_shift}",
            f"Hook: {hook}",
            "Hard Constraints:",
            f"- Scene ID: {scene_ref['canonical_id']}",
            f"- Source Outline: {scene_ref['filename']} を起点に構成する",
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


def build_request_compact(mode, priority, scene_ref):
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

    return "\n".join(
        [
            "# Request Compact",
            f"Current Mode: {mode}",
            f"Purpose: {purpose}",
            "Deliverables:",
            *[f"- {item}" for item in deliverables],
            "Constraints:",
            "- フル文脈を再投入しない",
            "- 文体契約を優先する",
            f"- 対象シーン: {scene_ref['canonical_id']}",
            f"Priority: {priority}",
        ]
    )


def build_resume_brief(scene_ref, previous_pack, session_notes_text):
    full_item = previous_pack["full"]
    current_position = (
        f"chapter {scene_ref['chapter']} scene {scene_ref['scene']} の準備段階。"
        f" 直前参照: {os.path.basename(full_item['path']) if full_item else '未検出'}"
    )

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
        "runtime/style_contract_compact.md を確認する",
        "draft に進むか resume 継続かを判断する",
        f"{scene_ref['canonical_id']} の着手条件を1行で決める",
    ]
    read_first = [
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

    outline_path = _find_first_existing(
        os.path.join(project_dir, "05_chapter_outline_100k.md"),
        os.path.join(project_dir, "plot", "05_chapter_outline_100k.md"),
    )
    if outline_path is None:
        raise UserFacingError("05_chapter_outline_100k.md not found")
    scene_ref = parse_scene_reference(args.scene)
    if scene_ref["chapter"] != args.chapter:
        raise UserFacingError("chapter and scene arguments do not match")

    previous_path = ""
    if args.previous_text:
        previous_path = resolve_relative_path(args.previous_text, base_dirs=[project_dir], must_exist=True)

    runtime_dir = os.path.join(project_dir, "runtime")
    ensure_directory(runtime_dir)

    outline_text = read_text_file(outline_path)
    chapter_block = extract_chapter_block(outline_text, args.chapter)
    if not chapter_block:
        raise UserFacingError(f"chapter {args.chapter} block not found in outline")

    style_contract, warnings = build_style_contract(
        project_dir,
        min_chars=DEFAULT_MIN_CHARS,
        target_chars=DEFAULT_TARGET_CHARS,
        max_chars=DEFAULT_MAX_CHARS,
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

    style_path = os.path.join(runtime_dir, "style_contract_compact.md")
    write_text_file(style_path, style_contract + "\n")
    written_files.append(style_path)

    request_path = os.path.join(runtime_dir, "request_compact.md")
    write_text_file(request_path, build_request_compact(args.mode, args.priority, scene_ref) + "\n")
    written_files.append(request_path)

    if args.mode == "draft":
        scene_brief_path = os.path.join(runtime_dir, "scene_brief_compact.md")
        write_text_file(scene_brief_path, build_scene_brief(chapter_block, scene_ref) + "\n")
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
        write_text_file(resume_path, build_resume_brief(scene_ref, previous_pack, session_notes) + "\n")
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
