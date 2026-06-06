import argparse
import os
import re
import sys

from novel_agent.text_quality import (
    META_PATTERNS,
    classify_quality,
    collect_format_violations,
    detect_format_violations,
    dialogue_ratio_hint,
    paragraph_count,
)
from novel_agent.story_state import update_story_state_from_check
from novel_agent.trace import append_trace_event
from prompt_utils import (
    count_completed_scene_files,
    count_total_written_chars,
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    UserFacingError,
    infer_scene_ref_from_path,
    extract_forbidden_terms,
    read_text_file,
    resolve_project_path,
    resolve_relative_path,
    resolve_runtime_dir,
    sync_state_schema,
    update_scene_ledger_status,
    validate_char_bounds,
    write_json_file,
)


def parse_scene_brief_band(runtime_dir):
    scene_brief_path = os.path.join(runtime_dir, "scene_brief_compact.md")
    if not os.path.isfile(scene_brief_path):
        return None

    text = read_text_file(scene_brief_path)
    scene_type_match = re.search(r"(?m)^Scene Type:\s*(.+)$", text)
    band_match = re.search(r"(?m)^Length Band:\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)$", text)
    if not band_match:
        return None

    return {
        "scene_type": scene_type_match.group(1).strip() if scene_type_match else "default",
        "min": int(band_match.group(1)),
        "target": int(band_match.group(2)),
        "max": int(band_match.group(3)),
    }




def load_forbidden_terms(runtime_dir):
    style_path = os.path.join(runtime_dir, "style_contract_compact.md")
    if not os.path.isfile(style_path):
        return ["###", "```", "本文のみ出力", "生成しました"]

    terms = extract_forbidden_terms(read_text_file(style_path))
    return terms or ["###", "```", "本文のみ出力", "生成しました"]


def collect_forbidden_hits(text, runtime_dir):
    hits = []
    details = []
    for rule in load_forbidden_terms(runtime_dir):
        if "見出し" in rule and re.search(r"(?m)^\s*#+\s+", text):
            if "heading_rule" not in hits:
                hits.append("heading_rule")
            details.append(
                {
                    "rule": rule,
                    "type": "heading_rule",
                    "match": re.search(r"(?m)^\s*#+\s+.+$", text).group(0).strip(),
                }
            )
            continue
        if "箇条書き" in rule and re.search(r"(?m)^\s*(?:[-*]\s+|\d+\.\s+)", text):
            if "bullet_rule" not in hits:
                hits.append("bullet_rule")
            details.append(
                {
                    "rule": rule,
                    "type": "bullet_rule",
                    "match": re.search(r"(?m)^\s*(?:[-*]\s+|\d+\.\s+).+$", text).group(0).strip(),
                }
            )
            continue
        if ("メタ" in rule or "作者視点" in rule) and any(pattern.search(text) for _, pattern in META_PATTERNS):
            if "meta_rule" not in hits:
                hits.append("meta_rule")
            meta_match = next((pattern.search(text) for _, pattern in META_PATTERNS if pattern.search(text)), None)
            details.append(
                {
                    "rule": rule,
                    "type": "meta_rule",
                    "match": meta_match.group(0).strip() if meta_match else "",
                }
            )
            continue
        if len(rule) <= 24 and rule in text:
            hits.append(rule)
            details.append(
                {
                    "rule": rule,
                    "type": "literal_rule",
                    "match": rule,
                }
            )

    unique_hits = []
    seen = set()
    for item in hits:
        if item in seen:
            continue
        seen.add(item)
        unique_hits.append(item)
    return unique_hits, details


def main():
    parser = argparse.ArgumentParser(description="Check scene output without using an LLM.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--text", required=True, help="Text file to validate")
    parser.add_argument("--runtime_dir", default="", help="Optional runtime directory path")
    parser.add_argument("--min_chars", type=int, default=DEFAULT_MIN_CHARS, help="Minimum characters")
    parser.add_argument("--target_chars", type=int, default=DEFAULT_TARGET_CHARS, help="Target characters")
    parser.add_argument("--max_chars", type=int, default=DEFAULT_MAX_CHARS, help="Maximum characters")
    args = parser.parse_args()

    validate_char_bounds(args.min_chars, args.target_chars, args.max_chars)
    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    text_path = resolve_relative_path(args.text, base_dirs=[project_dir], must_exist=True)
    scene_ref = infer_scene_ref_from_path(text_path)
    runtime_dir = resolve_runtime_dir(
        project_dir,
        mode="draft",
        scene_ref=scene_ref,
        runtime_dir_arg=args.runtime_dir,
    )
    scene_band = parse_scene_brief_band(runtime_dir)
    effective_min = scene_band["min"] if scene_band else args.min_chars
    effective_target = scene_band["target"] if scene_band else args.target_chars
    effective_max = scene_band["max"] if scene_band else args.max_chars
    scene_type = scene_band["scene_type"] if scene_band else "default"
    validate_char_bounds(effective_min, effective_target, effective_max)

    body_text = read_text_file(text_path)
    actual_chars = len(body_text)
    violations, violation_details = collect_format_violations(body_text)
    forbidden_hits, forbidden_hit_details = collect_forbidden_hits(body_text, runtime_dir)
    paragraph_count_value = paragraph_count(body_text)
    dialogue_ratio = dialogue_ratio_hint(body_text)
    quality_assessment = classify_quality(
        actual_chars=actual_chars,
        min_chars=effective_min,
        max_chars=effective_max,
        format_details=violation_details,
        forbidden_hits=forbidden_hits,
        paragraph_count_value=paragraph_count_value,
        dialogue_ratio=dialogue_ratio,
    )

    report = {
        "target_file": text_path,
        "actual_chars": actual_chars,
        "scene_type": scene_type,
        "min_chars": effective_min,
        "target_chars": effective_target,
        "max_chars": effective_max,
        "expected_band": {
            "min": effective_min,
            "target": effective_target,
            "max": effective_max,
        },
        "char_delta_to_min": actual_chars - effective_min,
        "char_delta_to_target": actual_chars - effective_target,
        "needs_expand": actual_chars < effective_min,
        "under_min_for_type": actual_chars < effective_min,
        "within_max": actual_chars <= effective_max,
        "over_max_for_type": actual_chars > effective_max,
        "format_violations": violations,
        "format_violations_detail": violation_details,
        "forbidden_hits": forbidden_hits,
        "forbidden_hits_detail": forbidden_hit_details,
        "paragraph_count": paragraph_count_value,
        "dialogue_ratio_hint": dialogue_ratio,
        **quality_assessment,
    }

    output_path = os.path.join(runtime_dir, "check_report.json")
    write_json_file(output_path, report)
    update_story_state_from_check(project_dir, scene_ref, report)
    append_trace_event(
        project_dir,
        event_type="scene_checked",
        chapter=scene_ref["chapter"] if scene_ref else None,
        scene=scene_ref["canonical_id"] if scene_ref else "",
        summary=f"scene check status={report['status']} needs_expand={str(report['needs_expand']).lower()}",
        artifacts=[output_path],
        evidence=[f"blocking={len(report['blocking_issues'])}", f"warnings={len(report['warnings'])}"],
    )
    append_trace_event(
        project_dir,
        event_type="state_updated",
        chapter=scene_ref["chapter"] if scene_ref else None,
        scene=scene_ref["canonical_id"] if scene_ref else "",
        summary="story_state updated from scene check",
        artifacts=[os.path.join(project_dir, "runtime", "story_state.json")],
    )
    if scene_ref is not None:
        outline_status = (
            "completed"
            if (
                not report["needs_expand"]
                and not report["format_violations"]
                and not report["forbidden_hits"]
                and report["within_max"]
            )
            else "drafted"
        )
        update_scene_ledger_status(project_dir, scene_ref, outline_status)
        sync_state_schema(
            project_dir,
            {
                "active_work": {
                    "active_chapter": scene_ref["chapter"],
                    "active_scene": scene_ref["canonical_id"],
                },
                "progress": {
                    "current_chapter": scene_ref["chapter"],
                    "current_scene": scene_ref["canonical_id"],
                    "last_checked_scene": scene_ref["canonical_id"],
                    "last_completed_scene": scene_ref["canonical_id"],
                    "completed_scene_count": count_completed_scene_files(project_dir),
                    "total_chars_written": count_total_written_chars(project_dir),
                },
            },
        )
    print("OK: scene output checked")
    print(f"OK: needs_expand={str(report['needs_expand']).lower()} actual_chars={actual_chars}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while checking scene output")
        sys.exit(1)
