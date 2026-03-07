import os
import re
import sys
import argparse

from prompt_utils import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    load_target_length_profile,
    resolve_outline_path,
    resolve_project_path,
)

# スクリプトの場所を基準にプロジェクトルートを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# 簡易トークン推定（日本語: 文字数÷2、英語/記号: 文字数÷4程度）
def estimate_tokens(text):
    return max(1, len(text) // 2)

TOKEN_WARN_LIMIT = 27_000  # 3万トークン上限の90%で警告
CHAPTER_DIR_HINTS = {
    "1": "chapter_1_introduction",
    "2": "chapter_2_rising_action",
    "3": "chapter_3_complication",
    "4": "chapter_4_climax",
    "5": "chapter_5_resolution",
}

# -------------------------------------------------------------------
# Lorebook (Dynamic Context Extraction) Logic
# -------------------------------------------------------------------
def extract_lorebook_entries(text):
    """
    CharactersやWorld-Buildingなどのマークダウンテキストから、
    見出し（## または ###）単位でブロックを分割し、エントリーとして抽出する。
    """
    entries = []
    # 見出し行（## xxx または ### xxx）で分割する正規表現
    lines = text.splitlines()
    current_heading = ""
    current_content = []

    for line in lines:
        if re.match(r"^#{2,3}\s+", line):
            # 前のブロックを保存
            if current_heading or current_content:
                entries.append({"heading": current_heading, "content": "\n".join(current_content).strip()})
            current_heading = line.strip()
            current_content = []
        else:
            current_content.append(line)

    # 最後のブロックを保存
    if current_heading or current_content:
         entries.append({"heading": current_heading, "content": "\n".join(current_content).strip()})

    return entries

def filter_lorebook_entries(entries, context_text, always_on_keywords=None):
    """
    コンテキスト（現在の章ブロックや直前テキスト）に含まれるキーワードに基づいて、
    関連するエントリーのみをフィルタリングする。
    always_on_keywords にマッチする見出しは常に含める。
    """
    if always_on_keywords is None:
        always_on_keywords = ["主人公", "基本設定", "メインキャラ"]

    filtered = []
    context_text_lower = context_text.lower()

    for entry in entries:
        heading = entry.get("heading", "")
        content = entry.get("content", "")
        heading_lower = heading.lower()
        
        # 1. Always On (常時オン) の判定
        is_always_on = any(k.lower() in heading_lower for k in always_on_keywords)
        if is_always_on:
            filtered.append(f"{heading}\n{content}")
            continue

        # 2. キーワード抽出（見出しから不要な記号を除いた単語）
        # 例: "## アリス (魔法使い)" -> ["アリス", "魔法使い"]
        heading_clean = re.sub(r"^#{2,3}\s+", "", heading)
        # 括弧などで分割してキーワード化
        keywords = [k.strip() for k in re.split(r"[\(\)（）\s]+", heading_clean) if k.strip()]
        
        # 3. コンテキストとのマッチング判定 (Weaver的連鎖は省略したシンプルな判定)
        is_matched = False
        for kw in keywords:
            if len(kw) >= 2 and kw.lower() in context_text_lower: # 1文字の誤爆を防ぐため2文字以上
                is_matched = True
                break
        
        # キーワードなし（全体概要など）やマッチした場合は含める
        if not keywords or is_matched:
            filtered.append(f"{heading}\n{content}")

    return "\n\n".join(filtered) if filtered else "(関連エントリーなし)"

# -------------------------------------------------------------------


def read_file_safe(path):
    if not os.path.exists(path):
        return f"[Error: {os.path.basename(path)} is missing]"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_chapter_block(outline_text, chapter_num):
    """
    フェーズ3: --chapter に対応した選択的ブロック抽出。
    対象章のブロックのみ返す（見つからなければ全文返す）。
    """
    # 「## 第{N}章」形式のヘッダーを探す
    import re
    pattern = rf"(## 第{chapter_num}章.+?)(?=\n## 第\d+章|\Z)"
    match = re.search(pattern, outline_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return outline_text  # フォールバック: 全文


def parse_chapter_target_chars(chapter_block):
    match = re.search(r"(?:想定目標字数|目標)[:：]?\s*約?\s*([\d,]+)\s*(?:字)?", chapter_block)
    if not match:
        return 0
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return 0


def _chapter_scene_sort_key(path, chapter_num):
    filename = os.path.basename(path)
    if re.match(rf"chapter_{chapter_num}_introduction\.txt$", filename):
        return (0, 0, filename)
    match = re.search(r"scene_(\d+)\.txt$", filename)
    if match:
        return (1, int(match.group(1)), filename)
    return (2, 0, filename)


def collect_chapter_scene_files(project_dir, chapter_num):
    scene_paths = []
    root_files = os.listdir(project_dir)
    for name in root_files:
        if re.match(rf"chapter_{chapter_num}_scene_\d+\.txt$", name) or re.match(
            rf"chapter_{chapter_num}_introduction\.txt$", name
        ):
            scene_paths.append(os.path.join(project_dir, name))

    chapter_dir_hint = CHAPTER_DIR_HINTS.get(str(chapter_num), "")
    chapter_dir = os.path.join(project_dir, chapter_dir_hint) if chapter_dir_hint else ""
    if chapter_dir and os.path.isdir(chapter_dir):
        for name in os.listdir(chapter_dir):
            if re.match(rf"chapter_{chapter_num}_scene_\d+\.txt$", name):
                scene_paths.append(os.path.join(chapter_dir, name))

    unique = sorted(set(scene_paths), key=lambda p: _chapter_scene_sort_key(p, chapter_num))
    return unique


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_excerpt(text, max_chars=240):
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "..."


def auto_load_previous_context(project_dir, chapter_num, explicit_previous_path):
    if explicit_previous_path:
        if os.path.exists(explicit_previous_path):
            text = read_text(explicit_previous_path)
            return [
                {
                    "path": explicit_previous_path,
                    "text": text,
                    "source": "explicit",
                }
            ]
        return []

    scene_files = collect_chapter_scene_files(project_dir, chapter_num)
    if not scene_files:
        return []

    # フェーズ4改修 (Hybrid Memory): 直近1話は全文、それより前は要約(Excerpt)にする
    recent_count = 2  # 一度に読み込む数
    tail = scene_files[-recent_count:]
    result = []
    
    for i, path in enumerate(tail):
        raw_text = read_text(path)
        # 最後のファイル（直近）以外は要約圧縮する
        if i < len(tail) - 1:
            processed_text = "【要約圧縮枠】\n" + build_excerpt(raw_text, max_chars=800)
        else:
            processed_text = raw_text

        result.append(
            {
                "path": path,
                "text": processed_text,
                "source": "auto_hybrid",
            }
        )
    return result


def load_style_contract(project_dir):
    global_notes_path = os.path.join(project_dir, "agent", "memory", "global_notes.md")
    if not os.path.exists(global_notes_path):
        return (
            "- 視点: 一人称/三人称を固定する\n"
            "- 語尾: 主人公と主要キャラの語尾を固定する\n"
            "- 地の文: 過去形/現在形を統一する\n"
            "- メモ: agent/memory/global_notes.md が未検出のため既定契約を適用"
        )

    text = read_text(global_notes_path)
    match = re.search(r"(##\s*文体契約.+?)(?=\n##\s|\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    style_lines = []
    for line in text.splitlines():
        if any(key in line for key in ("一人称", "三人称", "口調", "語尾", "文体", "敬語", "視点")):
            style_lines.append(line.strip())

    if style_lines:
        return "\n".join(style_lines)

    return (
        "- 視点: 一人称/三人称を固定する\n"
        "- 語尾: 主人公と主要キャラの語尾を固定する\n"
        "- 地の文: 過去形/現在形を統一する\n"
        "- メモ: global_notes.md に明示契約がないため既定契約を適用"
    )


def count_chapter_written_chars(project_dir, chapter_num):
    total = 0
    for path in collect_chapter_scene_files(project_dir, chapter_num):
        total += len(read_text(path))

    chapter_dir_hint = CHAPTER_DIR_HINTS.get(str(chapter_num), "")
    body_path = os.path.join(project_dir, chapter_dir_hint, "body.md") if chapter_dir_hint else ""
    if body_path and os.path.exists(body_path):
        total += len(read_text(body_path))

    return total


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def compute_recommended_chars(chapter_target, chapter_written, min_chars, target_chars, max_chars):
    if chapter_target <= 0:
        return clamp(target_chars, min_chars, max_chars), 0

    remaining = max(0, chapter_target - chapter_written)
    if remaining <= 0:
        return min_chars, 0

    # 残量に応じて1話ぶんを保守的に配分する
    planned = target_chars
    if remaining < min_chars:
        planned = min_chars
    elif remaining < target_chars:
        planned = remaining

    return clamp(planned, min_chars, max_chars), remaining


def parse_batch_scenes(raw):
    if not raw.strip():
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Build a legacy full-context LLM prompt. Prefer the runtime flow for routine drafting."
    )
    parser.add_argument("--project",       required=True, help="Path to the novel project directory")
    parser.add_argument("--chapter",       default="1",   help="Current chapter you are writing (1-5)")
    parser.add_argument("--previous_text", default="",    help="Path to the text file containing the immediately preceding scene")
    parser.add_argument("--mode",          default="prose", choices=["prose", "idea"], help="Prompt output mode: prose or idea")
    parser.add_argument("--scene",         default="", help="Scene identifier (e.g. 2-4)")
    parser.add_argument("--min_chars",     type=int, default=DEFAULT_MIN_CHARS, help="Minimum characters for prose output")
    parser.add_argument("--target_chars",  type=int, default=DEFAULT_TARGET_CHARS, help="Target characters for prose output")
    parser.add_argument("--max_chars",     type=int, default=DEFAULT_MAX_CHARS, help="Maximum characters for prose output")
    parser.add_argument("--batch_scenes",  default="", help="Comma-separated scene IDs for sequential drafting")
    parser.add_argument("--strict_length", action="store_true", help="Require the model to self-extend output if shorter than min_chars")
    args = parser.parse_args()
    batch_scenes = parse_batch_scenes(args.batch_scenes)

    print("WARN: build_llm_prompt.py is the legacy full-context path.")
    print("WARN: For routine drafting, prefer `build_runtime_context.py` + `build_draft_prompt.py`.")

    if args.min_chars <= 0 or args.target_chars <= 0 or args.max_chars <= 0:
        print("Error: min/target/max chars must be positive integers.")
        sys.exit(1)
    if args.min_chars > args.target_chars or args.target_chars > args.max_chars:
        print("Error: expected min_chars <= target_chars <= max_chars.")
        sys.exit(1)

    project_dir = resolve_project_path(args.project)

    if not os.path.exists(project_dir):
        print(f"Error: Project directory '{project_dir}' not found.")
        print(f"Tip: Run `python scripts/init_project.py {args.project}` to create it.")
        sys.exit(1)

    # File paths
    concept_path  = os.path.join(project_dir, "01_concept_sheet.md")
    char_path     = os.path.join(project_dir, "02_character_sheet.md")
    # S4修正: world と plot を追加
    world_path    = os.path.join(project_dir, "03_world_building.md")
    plot_path     = os.path.join(project_dir, "04_plot_outline.md")
    outline_path  = resolve_outline_path(project_dir)

    # Read files
    concept_text  = read_file_safe(concept_path)
    char_text_raw = read_file_safe(char_path)
    world_text_raw = read_file_safe(world_path)   # S4
    plot_text     = read_file_safe(plot_path)     # S4
    outline_text  = read_file_safe(outline_path)
    target_profile = load_target_length_profile(project_dir)

    # フェーズ3: 対象章のブロックのみ抽出
    chapter_block = extract_chapter_block(outline_text, args.chapter)

    style_contract = load_style_contract(project_dir)
    chapter_target_chars = parse_chapter_target_chars(chapter_block)
    chapter_written_chars = count_chapter_written_chars(project_dir, args.chapter)
    recommended_chars, chapter_remaining_chars = compute_recommended_chars(
        chapter_target=chapter_target_chars,
        chapter_written=chapter_written_chars,
        min_chars=args.min_chars,
        target_chars=args.target_chars,
        max_chars=args.max_chars,
    )

    previous_contexts = auto_load_previous_context(project_dir, args.chapter, args.previous_text)
    prev_full_text = "\n\n".join(
        f"[Source: {item['path']}]\n{item['text']}"
        for item in previous_contexts
    )
    continuity_summary = "\n".join(
        (
            f"- Source ({item['source']}): {item['path']}"
            f" / chars={len(item['text'])}\n"
            f"  Summary: {build_excerpt(item['text'])}"
        )
        for item in previous_contexts
    ) or "- 直近本文は未検出。冒頭で文体を安定化させる導入段落を必ず置くこと。"

    # フェーズ4: Lorebook 動的コンテキスト抽出
    # 抽出のキーとするテキストを結合（現在の章計画 + 直前本文）
    search_context = chapter_block + "\n" + prev_full_text
    
    char_entries = extract_lorebook_entries(char_text_raw)
    char_text_filtered = filter_lorebook_entries(char_entries, search_context, always_on_keywords=["主人公", "ヒロイン", "基本設定"])

    world_entries = extract_lorebook_entries(world_text_raw)
    world_text_filtered = filter_lorebook_entries(world_entries, search_context, always_on_keywords=["基本ルール", "世界観の前提", "魔法システム"])

    if batch_scenes:
        batch_target = ", ".join(batch_scenes)
        batch_instruction = (
            f"- 複数話指定: {batch_target}\n"
            f"- 逐次生成ルール: 今回は先頭の `{batch_scenes[0]}` のみ本文を完成させる。\n"
            "- 残りは次リクエストで、直前出力を引き継いで1話ずつ生成する。"
        )
    else:
        batch_instruction = "- 複数話指定なし: 現在指定の1話のみ生成する。"

    chapter_target_display = f"{chapter_target_chars:,}" if chapter_target_chars else "未設定"
    chapter_remaining_display = f"{chapter_remaining_chars:,}" if chapter_target_chars else "未設定"

    # Construct Prompt（S4修正: world/plot を追加）
    prompt = f"""あなたはプロのライトノベル編集者・執筆アシスタントです。
以下の情報を元に、これから執筆するシーンの出力に集中してください。
全体のコンテキスト制限（3万トークン）を考慮し、情報が圧縮されています。

### 1. 物語のコア設定 (Concept)
```
{concept_text}
```

### 2. キャラクター情報 (Characters - 動的抽出済)
```
# 現在のシーンに関連するキャラクター設定のみを抽出しています
{char_text_filtered}
```

### 3. 世界観 (World-Building - 動的抽出済)
```
{world_text_filtered}
```

### 4. プロット概要 (Plot Outline)
```
{plot_text}
```

### 5. 現在の章のシーン構成 (Chapter {args.chapter} Outline)
あなたは現在「第{args.chapter}章」の執筆をサポートしています。
```
{chapter_block}
```

### 6. 文字数契約 (Length Contract)
- target_total_chars: {target_profile['target_total_chars']:,}
- target_length_profile: {target_profile['target_length_profile']}
- chapter_target_chars: {chapter_target_display}
- chapter_written_chars: {chapter_written_chars:,}
- chapter_remaining_chars: {chapter_remaining_display}
- scene_min_chars: {args.min_chars:,}
- scene_target_chars: {recommended_chars:,}
- scene_max_chars: {args.max_chars:,}

### 7. 文体契約 (Style Contract)
```
{style_contract}
```

### 8. 連続性要約（直近話）
{continuity_summary}

### 9. 出力フォーマット契約 (Output Contract)
- 本文のみを出力する（見出し、箇条書き、注釈、メタ解説は禁止）
- 視点・口調・語尾は文体契約を優先する
- シーン境界は自然な改段落で表現する
- 未解決の伏線を1つ以上維持する
- 不足時は描写・会話・内面を追加して文字数を満たす
{batch_instruction}
"""

    if prev_full_text:
        prompt += f"""
### 10. 直前シーン本文（参照原文）
以下は直前に執筆された本文です。この文体や雰囲気を引き継いでください。
```
{prev_full_text}
```
"""

    prompt += f"\n\n### 指示 (Instruction)\n"
    scene_label = args.scene if args.scene else f"第{args.chapter}章の次シーン"
    if args.mode == "idea":
        prompt += (
            f"{scene_label} の展開アイデアを5案提示してください。"
            "各案は100〜180文字、目的・障害・感情変化を必ず含めてください。"
            "本文は出力しないでください。\n"
        )
    else:
        prompt += (
            f"{scene_label} の本文を生成してください。"
            f"最終出力は {args.min_chars:,}〜{args.max_chars:,}文字、目標 {recommended_chars:,}文字。"
            "本文以外は出力しないこと。\n"
        )
        if args.strict_length:
            prompt += (
                f"最終文字数が {args.min_chars:,} 未満の場合、評価者(Evaluator)からリテイクが要求されます。"
                "提出前に必ず自身で文字数を確認し、不足している場合は、新情報の矛盾を作らず、感情描写と行動描写を増やして調整してください。\n"
            )

        prompt += (
            "※注意: 最終出力後、別の評価プロセスが「1)文字数下限 2)視点統一 3)主要キャラ口調 4)前話接続」を厳密にチェックします。"
            "一発で通過できるよう、丁寧に執筆してください。\n"
        )

    # フェーズ3: トークン推定と警告
    estimated_tokens = estimate_tokens(prompt)
    print(f"\n推定トークン数: {estimated_tokens:,} / 30,000")
    if estimated_tokens > TOKEN_WARN_LIMIT:
        print(f"\n⚠️  警告: 推定トークン数 ({estimated_tokens:,}) が上限の90% ({TOKEN_WARN_LIMIT:,}) を超えています。")
        parts = {
            "コンセプト": estimate_tokens(concept_text),
            "キャラクター(Filtered)": estimate_tokens(char_text_filtered),
            "世界観(Filtered)": estimate_tokens(world_text_filtered),
            "プロット": estimate_tokens(plot_text),
            "章アウトライン": estimate_tokens(chapter_block),
            "文体契約": estimate_tokens(style_contract),
            "連続性要約": estimate_tokens(continuity_summary),
            "直前テキスト": estimate_tokens(prev_full_text),
        }
        print("各ファイルの推定トークン数:")
        for name, tok in sorted(parts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {tok:,}")
        print("→ 大きなファイルを手動で削減してください。\n")

    # Define output
    out_path = os.path.join(project_dir, "llm_prompt_output.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"LLM prompt successfully generated: {out_path}")
    print("You can copy the contents of this file and paste it into your local LLM (e.g., Llama.cpp, LM Studio, etc).")

if __name__ == "__main__":
    main()
