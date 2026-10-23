import argparse
import os
import re
import sys

from novel_agent.ledgers import append_token_ledger, find_artifact_by_path
from novel_agent.trace import append_trace_event
from novel_agent.memory_context import assemble_prompt, memory_prompt_sections
from novel_agent.storage import read_json, atomic_write_json
from prompt_utils import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    RUNTIME_PROMPT_WARN_LIMIT,
    UserFacingError,
    estimate_tokens,
    read_optional_text,
    require_existing_file,
    read_text_file,
    resolve_project_path,
    resolve_runtime_dir,
    parse_scene_reference,
    validate_char_bounds,
    write_text_file,
)


def parse_scene_brief_metadata(scene_brief):
    scene_type_match = re.search(r"(?m)^Scene Type:\s*(.+)$", scene_brief)
    length_band_match = re.search(r"(?m)^Length Band:\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)$", scene_brief)

    metadata = {
        "scene_type": scene_type_match.group(1).strip() if scene_type_match else "",
        "min_chars": 0,
        "target_chars": 0,
        "max_chars": 0,
    }
    if length_band_match:
        metadata["min_chars"] = int(length_band_match.group(1))
        metadata["target_chars"] = int(length_band_match.group(2))
        metadata["max_chars"] = int(length_band_match.group(3))
    return metadata


def parse_request_compact_metadata(request_compact):
    planning_gate_match = re.search(r"(?m)^- Planning Gate:\s*(.+)$", request_compact)
    planning_gate_enabled_match = re.search(r"(?m)^- Planning Gate Enabled:\s*(.+)$", request_compact)
    length_mode_match = re.search(r"(?m)^- Length Mode:\s*(.+)$", request_compact)
    return {
        "planning_gate_status": planning_gate_match.group(1).strip().lower() if planning_gate_match else "",
        "planning_gate_enabled": _parse_bool_text(
            planning_gate_enabled_match.group(1).strip() if planning_gate_enabled_match else ""
        ),
        "length_mode": length_mode_match.group(1).strip() if length_mode_match else "",
    }


def parse_planning_gate_brief_metadata(planning_gate_brief):
    planning_gate_match = re.search(r"(?m)^Planning Gate:\s*(.+)$", planning_gate_brief)
    planning_gate_enabled_match = re.search(r"(?m)^Planning Gate Enabled:\s*(.+)$", planning_gate_brief)
    return {
        "planning_gate_status": planning_gate_match.group(1).strip().lower() if planning_gate_match else "",
        "planning_gate_enabled": _parse_bool_text(
            planning_gate_enabled_match.group(1).strip() if planning_gate_enabled_match else ""
        ),
    }


def _parse_bool_text(raw_value):
    cleaned = str(raw_value or "").strip().lower()
    if cleaned in {"true", "yes", "on", "1"}:
        return True
    if cleaned in {"false", "no", "off", "0"}:
        return False
    return None


def main():
    parser = argparse.ArgumentParser(description="Build a draft-only prompt from compact runtime files.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--scene", default="", help="Explicit scene ID")
    parser.add_argument("--runtime_dir", default="", help="Optional runtime directory path")
    parser.add_argument("--min_chars", type=int, default=DEFAULT_MIN_CHARS, help="Minimum target characters")
    parser.add_argument("--target_chars", type=int, default=DEFAULT_TARGET_CHARS, help="Preferred target characters")
    parser.add_argument("--max_chars", type=int, default=DEFAULT_MAX_CHARS, help="Maximum target characters")
    args = parser.parse_args()

    validate_char_bounds(args.min_chars, args.target_chars, args.max_chars)
    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    runtime_dir = resolve_runtime_dir(project_dir, mode="draft", scene_ref=parse_scene_reference(args.scene) if args.scene else None, runtime_dir_arg=args.runtime_dir)
    from novel_agent.runtime_paths import require_runtime_current
    require_runtime_current(project_dir, runtime_dir)

    style_path = require_existing_file(os.path.join(runtime_dir, "style_contract_compact.md"), "runtime/style_contract_compact.md")
    brief_path = require_existing_file(os.path.join(runtime_dir, "scene_brief_compact.md"), "runtime/scene_brief_compact.md")
    continuity_path = require_existing_file(os.path.join(runtime_dir, "continuity_pack.md"), "runtime/continuity_pack.md")
    request_path = require_existing_file(os.path.join(runtime_dir, "request_compact.md"), "runtime/request_compact.md")

    from novel_agent.dependencies import snapshot_dependencies, verify_dependencies
    prompt_inputs = snapshot_dependencies(project_dir, [
        {"kind": "artifact", "path": path} for path in
        (style_path, brief_path, continuity_path, request_path, os.path.join(runtime_dir, "planning_gate_brief.md"),
         os.path.join(runtime_dir, "story_memory_pack.md"), os.path.join(runtime_dir, "related_context_pack.md"))
    ] + ([{"kind": "projection", "selector": "memory_selection", "path": os.path.join(runtime_dir, "context_selection.json")}]
         if os.path.isfile(os.path.join(runtime_dir, "context_selection.json")) else []))
    style_contract = read_text_file(style_path).strip()
    scene_brief = read_text_file(brief_path).strip()
    continuity_pack = read_text_file(continuity_path).strip()
    request_compact = read_text_file(request_path).strip()
    planning_gate_brief = read_optional_text(os.path.join(runtime_dir, "planning_gate_brief.md")).strip()
    for required_path in (style_path, brief_path, continuity_path, request_path):
        artifact = find_artifact_by_path(project_dir, required_path)
        if artifact and artifact.get("status") == "stale":
            print(f"WARN: stale runtime artifact detected: {artifact.get('path')}")
    scene_brief_meta = parse_scene_brief_metadata(scene_brief)
    request_meta = parse_request_compact_metadata(request_compact)
    planning_gate_meta = parse_planning_gate_brief_metadata(planning_gate_brief)

    planning_gate_status = planning_gate_meta["planning_gate_status"] or request_meta["planning_gate_status"]
    planning_gate_enabled = planning_gate_meta["planning_gate_enabled"]
    if planning_gate_enabled is None:
        planning_gate_enabled = request_meta["planning_gate_enabled"]
    if planning_gate_enabled is None:
        planning_gate_enabled = request_meta["length_mode"] == "long_form_100k" or bool(planning_gate_status)

    if planning_gate_enabled and planning_gate_status and planning_gate_status not in {"ready", "unknown"}:
        raise UserFacingError(
            "planning_gate_status is not ready; complete long-form planning before generating draft_prompt.txt"
        )

    effective_min = scene_brief_meta["min_chars"] or args.min_chars
    effective_target = scene_brief_meta["target_chars"] or args.target_chars
    effective_max = scene_brief_meta["max_chars"] or args.max_chars
    validate_char_bounds(effective_min, effective_target, effective_max)
    scene_type = scene_brief_meta["scene_type"] or "default"

    prompt = "\n\n".join(
        [
            "あなたは初稿専用の執筆エージェントです。",
            "圧縮済みのランタイム文脈だけを使い、最初の骨格を安定して作ってください。",
            "## Style Contract",
            style_contract,
            "## Scene Brief (planning)",
            scene_brief,
            "## Request Compact",
            request_compact,
            *(
                ["## Planning Gate Brief", planning_gate_brief]
                if planning_gate_brief
                else []
            ),
            "## Output Contract",
            f"- Scene Type: {scene_type}",
            f"- 目安文字数: {effective_min} / {effective_target} / {effective_max} 字（min/target/max）",
            "- 初稿は1回目の骨格生成として扱う",
            "- 文字数が min 未満なら、後段で expand 候補として扱われる",
            "- ただし構造・文体・前後接続を優先する",
            "- bridge シーンは無理に膨らませない",
            "- anchor / climax シーンは感情変化と意思決定を厚くする",
            "- 本文のみ出力",
        ]
    )
    selection_path = os.path.join(runtime_dir, "context_selection.json")
    context_selection = read_json(selection_path, default_factory=dict)
    related_context = read_optional_text(os.path.join(runtime_dir, "related_context_pack.md")).strip()
    memory_pack = read_optional_text(os.path.join(runtime_dir, "story_memory_pack.md")).strip()
    prompt, output_contract = prompt.split("\n\n## Output Contract\n\n", 1)
    sections = [{"name": "required_constraints_and_planning", "text": prompt, "required": True,
                 "priority": 0, "source_ids": []},
                {"name": "output_contract", "text": "## Output Contract\n" + output_contract, "required": True,
                 "priority": 100, "source_ids": []}]
    if context_selection.get("memory"):
        sections.extend(memory_prompt_sections(context_selection["memory"]))
    elif memory_pack:
        sections.append({"name": "story_memory", "text": memory_pack, "required": False,
                         "priority": 2, "source_ids": []})
    sections.extend([
        {"name": "continuity", "text": "## Continuity Pack\n" + continuity_pack, "required": False,
         "priority": 8, "source_ids": ["continuity_pack.md"]},
        {"name": "related_context", "text": related_context, "required": False,
         "priority": 9, "source_ids": ["related_context_pack.md"]},
    ])
    assembled = assemble_prompt(sections)
    prompt = assembled["prompt"]
    context_selection["final_prompt"] = {key: value for key, value in assembled.items() if key != "prompt"}
    atomic_write_json(selection_path, context_selection)
    estimated_tokens = estimate_tokens(prompt)
    part_estimates = {
        "style_contract": estimate_tokens(style_contract),
        "scene_brief": estimate_tokens(scene_brief),
        "continuity_pack": estimate_tokens(continuity_pack),
        "request_compact": estimate_tokens(request_compact),
        "planning_gate_brief": estimate_tokens(planning_gate_brief),
    }

    output_path = os.path.join(runtime_dir, "draft_prompt.txt")
    if verify_dependencies(project_dir, prompt_inputs) and os.path.isfile(os.path.join(runtime_dir, "runtime_manifest.json")):
        raise UserFacingError("runtime changed during prompt generation; prepare again")
    write_text_file(output_path, prompt)
    from novel_agent.dependencies import snapshot_dependencies
    from novel_agent.ledgers import register_artifact
    register_artifact(project_dir, artifact_id="draft_prompt", artifact_type="draft_prompt", path=output_path, dependencies=prompt_inputs)
    append_token_ledger(
        project_dir,
        {
            "command": "build_draft_prompt",
            "projection": "draft",
            "chapter": None,
            "scene": None,
            "runtime_dir": runtime_dir,
            "total_estimated_tokens": estimated_tokens,
            "sections": part_estimates,
            "budget": RUNTIME_PROMPT_WARN_LIMIT,
            "status": "over_budget" if estimated_tokens > RUNTIME_PROMPT_WARN_LIMIT else "within_budget",
        },
    )
    append_trace_event(
        project_dir,
        event_type="draft_prompt_generated",
        summary="draft prompt generated from compact runtime files",
        artifacts=[output_path],
        tokens_estimate=estimated_tokens,
    )
    print(f"OK: draft prompt generated at {output_path}")
    print(f"OK: estimated_tokens={estimated_tokens} runtime_budget={RUNTIME_PROMPT_WARN_LIMIT}")
    if estimated_tokens > RUNTIME_PROMPT_WARN_LIMIT:
        print(
            "WARN: draft prompt is larger than the recommended runtime budget; "
            "prefer trimming the largest runtime section before sending it to the model"
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
        print("ERROR: unexpected failure while generating draft prompt")
        sys.exit(1)
