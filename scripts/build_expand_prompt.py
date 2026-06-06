import argparse
import json
import os
import re
import sys

from novel_agent.trace import append_trace_event
from prompt_utils import (
    RUNTIME_PROMPT_WARN_LIMIT,
    UserFacingError,
    estimate_tokens,
    infer_scene_ref_from_path,
    read_text_file,
    require_existing_file,
    resolve_project_path,
    resolve_relative_path,
    resolve_runtime_dir,
    write_text_file,
)


ANCHOR_EXCERPT_CHARS = 90


def build_anchor_excerpt(text, max_chars=ANCHOR_EXCERPT_CHARS):
    compact = text.strip()
    if len(compact) <= max_chars:
        return compact
    normalized = re.sub(r"\s+", " ", compact)
    if len(normalized) <= max_chars:
        return normalized
    edge = max(20, (max_chars - 5) // 2)
    return normalized[:edge].rstrip() + " ... " + normalized[-edge:].lstrip()


def split_paragraphs(text):
    return [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]


def build_paragraph_map(text):
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return "- P1: (本文なし)"

    return "\n".join(
        f"- P{index}: {build_anchor_excerpt(paragraph)}"
        for index, paragraph in enumerate(paragraphs, start=1)
    )


def recommend_edit_blocks(missing_chars):
    if missing_chars <= 180:
        return 1
    if missing_chars <= 450:
        return 2
    return 3


def build_response_template():
    return "\n".join(
        [
            "[EDIT 1]",
            "TARGET: after P2",
            "ANCHOR: <`- P2:` の右側をそのまま貼る>",
            "TEXT:",
            "<ここに新規本文1段落>",
        ]
    )


def build_expand_instruction(report):
    missing_chars = max(0, int(report["min_chars"]) - int(report["actual_chars"]))
    recommended_blocks = recommend_edit_blocks(missing_chars)
    lines = [
        "# Expand Instruction",
        f"Missing Chars: {missing_chars}",
        f"Recommended Edit Blocks: {recommended_blocks}",
        "Expansion Mode:",
        "- structured_local_insertions",
        "- 既存本文は保持し、局所的に差し込む差分だけを作る",
        "- 末尾追記だけでなく、途中への差し込みも可",
        "- 既存本文の全文再掲や冒頭からの書き直しは禁止",
        "Keep Fixed:",
        "- 初稿の出来事を維持する",
        "- 視点と口調を維持する",
        "- 結末とフックを維持する",
        "Allowed Additions:",
        "- 情景描写",
        "- 身体動作",
        "- 会話の間",
        "- 内面反応",
        "- 余韻",
        "Forbidden Changes:",
        "- 展開順序を変えない",
        "- 設定事実を変えない",
        "- 固有名詞を変えない",
        "- 既存本文を言い換えて全文再出力しない",
    ]
    return "\n".join(lines), missing_chars


def main():
    parser = argparse.ArgumentParser(description="Build an expansion prompt from a short draft.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--draft_text", required=True, help="Draft text file path")
    parser.add_argument("--runtime_dir", default="", help="Optional runtime directory path")
    parser.add_argument("--check_report", default="", help="Optional check report path")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    draft_path = resolve_relative_path(args.draft_text, base_dirs=[project_dir], must_exist=True)
    scene_ref = infer_scene_ref_from_path(draft_path)
    runtime_dir = resolve_runtime_dir(
        project_dir,
        mode="draft",
        scene_ref=scene_ref,
        runtime_dir_arg=args.runtime_dir,
    )
    report_path = (
        resolve_relative_path(args.check_report, base_dirs=[project_dir, runtime_dir], must_exist=True)
        if args.check_report
        else require_existing_file(os.path.join(runtime_dir, "check_report.json"), "runtime/check_report.json")
    )
    style_path = require_existing_file(os.path.join(runtime_dir, "style_contract_compact.md"), "runtime/style_contract_compact.md")

    draft_text = read_text_file(draft_path).strip()
    style_contract = read_text_file(style_path).strip()
    try:
        report = json.loads(read_text_file(report_path))
    except json.JSONDecodeError:
        raise UserFacingError("check_report.json is invalid")

    for key in ("actual_chars", "min_chars", "needs_expand"):
        if key not in report:
            raise UserFacingError("check_report.json is missing required keys")

    instruction_text, missing_chars = build_expand_instruction(report)
    paragraph_map = build_paragraph_map(draft_text)
    response_template = build_response_template()
    prompt = "\n\n".join(
        [
            "あなたは既存初稿を保持したまま不足分だけを増補します。",
            instruction_text,
            "## Style Contract",
            style_contract,
            "## Existing Paragraph Map",
            paragraph_map,
            "## Output Contract",
            "- 返答は局所差分ブロックのみ",
            "- 差分は 1〜3 ブロックまで",
            "- 説明文、前置き、見出し、補足、コードブロックは禁止",
            "- 最初の行は必ず `[EDIT 1]` から始める",
            "- 各ブロックは `TARGET:` `ANCHOR:` `TEXT:` の3項目で返す",
            "- `TARGET:` は `before Pn` / `after Pn` / `end_of_text` のいずれか",
            "- `ANCHOR:` には対応する既存抜粋、または `END` を書く",
            "- `ANCHOR:` は `Existing Paragraph Map` の `- Pn:` の右側をそのままコピペする",
            "- `ANCHOR:` を要約したり言い換えたりしない",
            "- `TARGET:` の `Pn` と `ANCHOR:` の参照先は必ず一致させる",
            "- `TEXT:` には、その位置へ挿入する新規本文だけを書く",
            "- 1ブロックあたり 1 段落を基本にする",
            "- `TEXT:` の中に `TARGET:` `ANCHOR:` `[EDIT` を含めない",
            "- 既存の出来事・順序・固有名詞は変えない",
            "- 足りない分だけ描写を局所追加する",
            "- 既存本文を再掲しない",
            "## Response Template",
            response_template,
            "## Good Rule",
            "- 迷ったら `after Pn` を優先し、因果が崩れる場合だけ `before Pn` を使う",
            "- 末尾追加は、既存の締めを壊さないときだけ `end_of_text` を使う",
            "## Bad Output Examples",
            "- `まず1か所だけ補います。` のような説明文を先頭に付ける",
            "- `ANCHOR:` を本文内容で言い換える",
            "- `TARGET: after P2` なのに `ANCHOR:` が `P3` の抜粋になっている",
        ]
    )
    estimated_tokens = estimate_tokens(prompt)
    part_estimates = {
        "expand_instruction": estimate_tokens(instruction_text),
        "style_contract": estimate_tokens(style_contract),
        "paragraph_map": estimate_tokens(paragraph_map),
        "response_template": estimate_tokens(response_template),
    }

    instruction_path = os.path.join(runtime_dir, "expand_instruction.md")
    prompt_path = os.path.join(runtime_dir, "expand_prompt.txt")
    write_text_file(instruction_path, instruction_text + "\n")
    write_text_file(prompt_path, prompt + "\n")
    append_trace_event(
        project_dir,
        event_type="patch_prompt_generated",
        chapter=scene_ref["chapter"] if scene_ref else None,
        scene=scene_ref["canonical_id"] if scene_ref else "",
        summary=f"expand prompt generated missing_chars={missing_chars}",
        artifacts=[instruction_path, prompt_path],
        tokens_estimate=estimated_tokens,
    )

    if not bool(report.get("needs_expand")):
        print("WARN: needs_expand=false but expand prompt requested")
    print("OK: expand prompt generated")
    print(f"OK: missing_chars={missing_chars}")
    print(f"OK: estimated_tokens={estimated_tokens} runtime_budget={RUNTIME_PROMPT_WARN_LIMIT}")
    if estimated_tokens > RUNTIME_PROMPT_WARN_LIMIT:
        print(
            "WARN: expand prompt is larger than the recommended runtime budget; "
            "prefer reducing paragraph-map size or trimming style notes before reuse"
        )
        for name, tokens in sorted(part_estimates.items(), key=lambda item: (-item[1], item[0])):
            print(f"WARN: part_tokens {name}={tokens}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while generating expand prompt")
        sys.exit(1)
