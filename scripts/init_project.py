import argparse
import os
import re
import shutil
import sys

from prompt_utils import compute_gate_threshold, compute_target_length_profile


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CANONICAL_OUTLINE_TEMPLATE = "05_chapter_outline.md"
LEGACY_OUTLINE_TEMPLATE = "05_chapter_outline_100k.md"
TARGET_TOTAL_CHAR_CHOICES = (30000, 50000, 100000)


def resolve_new_project_dir(project_name):
    if os.path.isabs(project_name):
        return os.path.normpath(project_name)
    return os.path.normpath(os.path.join(BASE_DIR, project_name))


def render_outline_template(template_text, *, target_total_chars, planning_gate_min_chars):
    return (
        template_text
        .replace("{{TARGET_TOTAL_CHARS}}", str(target_total_chars))
        .replace("{{PLANNING_GATE_MIN_CHARS}}", str(planning_gate_min_chars))
    )


def build_project_state_schema(project_dir, *, target_total_chars):
    target_length_profile = compute_target_length_profile(target_total_chars)
    planning_gate_min_chars = compute_gate_threshold(target_total_chars)
    return f"""version: 3

project:
  name: "{os.path.basename(project_dir)}"
  path: "{project_dir}"
  status: "active"
  notes: ""

source_of_truth:
  prose_files: "scene txt files"
  chapter_notes_file: "body.md"
  backlog_files: []

profile:
  genre: ""
  target_audience: ""
  tone: ""
  pov_default: ""

targets:
  target_total_chars: {target_total_chars}
  target_length_profile: "{target_length_profile}"
  planning_gate_enabled: true
  planning_gate_min_chars: {planning_gate_min_chars}
  planning_target_total_chars: {target_total_chars}
  scene_default_chars: 1250
  scene_min_chars: 1000
  scene_max_chars: 1500
  scene_type_bands:
    bridge:
      min: 1200
      target: 1500
      max: 1800
    standard:
      min: 1600
      target: 2000
      max: 2400
    anchor:
      min: 2200
      target: 2700
      max: 3200
    climax:
      min: 2600
      target: 3200
      max: 3800

style_contract:
  pov: ""
  narration_tense: ""
  dialogue_rules: []
  lexical_rules: []
  tone_watch: []

characters: []

story_constraints:
  must_include: []
  must_avoid: []

continuity_watch:
  unresolved_threads: []
  upcoming_payoffs: []
  risk_flags: []
  planned_payoffs: []
  missing_payoffs: []

active_work:
  current_mode: ""
  recommended_skill: ""
  primary_scope: ""
  active_chapter: 0
  active_scene: ""
  next_action: ""
  files_to_check_first:
    - "05_chapter_outline.md"
  planning_gate_status: ""
  current_scene_type: ""

progress:
  total_chapters: 0
  completed_chapters: []
  current_chapter: 0
  current_scene: ""
  total_chars_written: 0
  chapter_chars_written: {{}}
  planned_total_min_chars: 0
  planned_total_target_chars: 0
  planned_scene_count: 0
  completed_scene_count: 0
  chapter_scene_counts: {{}}
  chapter_planned_chars: {{}}

recent_decisions: []
open_questions: []
"""


def initialize_project_memory(project_dir):
    agent_memory_dir = os.path.join(project_dir, "agent", "memory")
    os.makedirs(agent_memory_dir, exist_ok=True)
    with open(os.path.join(agent_memory_dir, "global_notes.md"), "w", encoding="utf-8") as handle:
        handle.write(
            "# Global Notes\n\n"
            "## 文体契約\n"
            "- 視点:\n"
            "- 地の文時制:\n"
            "- 口調:\n"
            "- 禁止:\n"
        )
    with open(os.path.join(agent_memory_dir, "session_notes.md"), "w", encoding="utf-8") as handle:
        handle.write("# Session Notes\n\n- 次に決めること:\n")


def main():
    parser = argparse.ArgumentParser(description="Initialize a new light novel project.")
    parser.add_argument("project_name", help="Name of the novel project (will be used as the directory name)")
    parser.add_argument(
        "--target-total-chars",
        type=int,
        choices=TARGET_TOTAL_CHAR_CHOICES,
        default=None,
        help="Canonical target total chars for the project (30000 / 50000 / 100000)",
    )
    parser.add_argument(
        "--from_ideas",
        action="store_true",
        help="If set, copies generated_ideas.md into the project and transfers the logline to 01_concept_sheet.md",
    )
    args = parser.parse_args()

    templates_dir = os.path.join(BASE_DIR, "templates")
    project_dir = resolve_new_project_dir(args.project_name)
    target_total_chars = args.target_total_chars or 100000
    planning_gate_min_chars = compute_gate_threshold(target_total_chars)

    print(f"Initializing new light novel project: '{args.project_name}'...")
    if args.target_total_chars is None:
        print("WARN: --target-total-chars was not provided; falling back to 100000 for compatibility.")

    if os.path.exists(project_dir):
        print(f"Error: Directory '{project_dir}' already exists. Aborting.")
        sys.exit(1)

    os.makedirs(project_dir)
    print(f" - Created directory: {project_dir}")

    for template_name in sorted(os.listdir(templates_dir)):
        if not template_name.endswith(".md") or template_name == LEGACY_OUTLINE_TEMPLATE:
            continue
        src = os.path.join(templates_dir, template_name)
        dst = os.path.join(project_dir, template_name)
        if template_name == CANONICAL_OUTLINE_TEMPLATE:
            with open(src, "r", encoding="utf-8") as handle:
                rendered = render_outline_template(
                    handle.read(),
                    target_total_chars=target_total_chars,
                    planning_gate_min_chars=planning_gate_min_chars,
                )
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            shutil.copy2(src, dst)
        print(f" - Copied template: {template_name}")

    chapters = [
        ("chapter_1_introduction", "第1章：起（導入）"),
        ("chapter_2_rising_action", "第2章：承・前半（試練）"),
        ("chapter_3_complication", "第3章：承・後半（複雑化）"),
        ("chapter_4_climax", "第4章：転（クライマックス）"),
        ("chapter_5_resolution", "第5章：結（解決）"),
    ]
    for ch_dir_name, ch_title_ja in chapters:
        ch_dir = os.path.join(project_dir, ch_dir_name)
        os.makedirs(ch_dir)
        with open(os.path.join(ch_dir, "body.md"), "w", encoding="utf-8") as handle:
            handle.write(f"# {ch_title_ja}\n\nここに本文を執筆します。\n\n---\n\n## シーンメモ\n\n")
        print(f" - Created chapter folder: {ch_dir_name}")

    os.makedirs(os.path.join(project_dir, "agent"), exist_ok=True)
    with open(os.path.join(project_dir, "agent", "state_schema_novel.yaml"), "w", encoding="utf-8") as handle:
        handle.write(build_project_state_schema(project_dir, target_total_chars=target_total_chars))
    print(" - Created project-local state schema")

    initialize_project_memory(project_dir)
    print(" - Created project-local agent memory stubs")

    if args.from_ideas:
        ideas_src = os.path.join(BASE_DIR, "generated_ideas.md")
        if os.path.exists(ideas_src):
            ideas_dst = os.path.join(project_dir, "generated_ideas.md")
            shutil.copy2(ideas_src, ideas_dst)
            print(" - Copied generated_ideas.md to project folder")

            with open(ideas_src, "r", encoding="utf-8") as handle:
                ideas_text = handle.read()

            logline_match = re.search(r"## ログライン\n>\s*(.+)", ideas_text)
            logline = logline_match.group(1).strip() if logline_match else ""

            if logline:
                concept_path = os.path.join(project_dir, "01_concept_sheet.md")
                with open(concept_path, "r", encoding="utf-8") as handle:
                    concept_text = handle.read()
                concept_text = concept_text.replace(
                    "> 物語全体を「1〜2文」で説明してください。\n> 例：「[主人公]が[目的]を達成するために、[障害]を乗り越える物語」",
                    f"> {logline}\n>\n> (idea_generator.py から自動転記)",
                )
                with open(concept_path, "w", encoding="utf-8") as handle:
                    handle.write(concept_text)
                print(" - Transferred logline to 01_concept_sheet.md")
        else:
            print(" - Warning: generated_ideas.md not found. Run `python scripts/idea_generator.py` first.")

    print("\nProject initialization complete!")
    print(f"Next step: Open the files in '{args.project_name}/' and start filling in the templates.")
    print(f"When ready to generate an LLM prompt: python scripts/build_llm_prompt.py --project {args.project_name} --chapter 1")


if __name__ == "__main__":
    main()
