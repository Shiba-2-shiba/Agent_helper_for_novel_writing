import os
import sys
import shutil
import argparse
import re

# スクリプトの場所を基準にプロジェクトルートを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

def main():
    parser = argparse.ArgumentParser(description="Initialize a new light novel project.")
    parser.add_argument("project_name", help="Name of the novel project (will be used as the directory name)")
    # S2修正: --from_ideas オプションを追加
    parser.add_argument(
        "--from_ideas",
        action="store_true",
        help="If set, copies generated_ideas.md into the project and transfers the logline to 01_concept_sheet.md"
    )
    args = parser.parse_args()

    templates_dir = os.path.join(BASE_DIR, "templates")
    project_dir   = os.path.join(BASE_DIR, args.project_name)

    print(f"Initializing new light novel project: '{args.project_name}'...")

    # S6修正: 既存ディレクトリの場合はエラーコード1で終了
    if os.path.exists(project_dir):
        print(f"Error: Directory '{project_dir}' already exists. Aborting.")
        sys.exit(1)

    # Create project structure
    os.makedirs(project_dir)
    print(f" - Created directory: {project_dir}")

    # Copy templates
    for template_name in sorted(os.listdir(templates_dir)):
        if template_name.endswith(".md"):
            src = os.path.join(templates_dir, template_name)
            dst = os.path.join(project_dir, template_name)
            shutil.copy2(src, dst)
            print(f" - Copied template: {template_name}")

    # Create chapter folders for 100k character target
    chapters = [
        ("chapter_1_introduction",  "第1章：起（導入）"),
        ("chapter_2_rising_action", "第2章：承・前半（試練）"),
        ("chapter_3_complication",  "第3章：承・後半（複雑化）"),
        ("chapter_4_climax",        "第4章：転（クライマックス）"),
        ("chapter_5_resolution",    "第5章：結（解決）"),
    ]
    for ch_dir_name, ch_title_ja in chapters:
        ch_dir = os.path.join(project_dir, ch_dir_name)
        os.makedirs(ch_dir)
        # W3修正: body.md の見出しを日本語に
        with open(os.path.join(ch_dir, "body.md"), "w", encoding="utf-8") as f:
            f.write(f"# {ch_title_ja}\n\nここに本文を執筆します。\n\n---\n\n## シーンメモ\n\n")
        print(f" - Created chapter folder: {ch_dir_name}")

    # S2修正: --from_ideas フラグの処理
    if args.from_ideas:
        ideas_src = os.path.join(BASE_DIR, "generated_ideas.md")
        if os.path.exists(ideas_src):
            # プロジェクトにコピー
            ideas_dst = os.path.join(project_dir, "generated_ideas.md")
            shutil.copy2(ideas_src, ideas_dst)
            print(f" - Copied generated_ideas.md to project folder")

            # ログラインを 01_concept_sheet.md に転記
            with open(ideas_src, "r", encoding="utf-8") as f:
                ideas_text = f.read()

            logline_match = re.search(r"## ログライン\n>\s*(.+)", ideas_text)
            logline = logline_match.group(1).strip() if logline_match else ""

            if logline:
                concept_path = os.path.join(project_dir, "01_concept_sheet.md")
                with open(concept_path, "r", encoding="utf-8") as f:
                    concept_text = f.read()
                # 「ここにタイトル案」より下のログライン欄に書き込む
                concept_text = concept_text.replace(
                    "> 物語全体を「1〜2文」で説明してください。\n> 例：「[主人公]が[目的]を達成するために、[障害]を乗り越える物語」",
                    f"> {logline}\n>\n> (idea_generator.py から自動転記)"
                )
                with open(concept_path, "w", encoding="utf-8") as f:
                    f.write(concept_text)
                print(f" - Transferred logline to 01_concept_sheet.md")
        else:
            print(" - Warning: generated_ideas.md not found. Run `python scripts/idea_generator.py` first.")

    print("\nProject initialization complete!")
    print(f"Next step: Open the files in '{args.project_name}/' and start filling in the templates.")
    print(f"When ready to generate an LLM prompt: python scripts/build_llm_prompt.py --project {args.project_name} --chapter 1")

if __name__ == "__main__":
    main()
