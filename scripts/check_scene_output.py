import argparse
import os
import re
import sys

from prompt_utils import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MIN_CHARS,
    DEFAULT_TARGET_CHARS,
    UserFacingError,
    extract_forbidden_terms,
    read_text_file,
    resolve_project_path,
    resolve_relative_path,
    validate_char_bounds,
    write_json_file,
)


META_PATTERNS = [
    ("meta_preface_detected", re.compile(r"(?m)^\s*(?:以下に|以下、|それでは|承知しました|了解しました)")),
    ("meta_output_notice_detected", re.compile(r"(?:生成しました|出力します|出力しました|修正版|補足|注:)")),
]


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


def detect_unclosed_dialogue(text):
    open_count = text.count("「")
    close_count = text.count("」")
    if open_count == close_count:
        return None

    for line in text.splitlines():
        if line.count("「") != line.count("」"):
            return {
                "type": "unclosed_dialogue_detected",
                "match": line.strip()[:80],
                "open_count": open_count,
                "close_count": close_count,
            }

    return {
        "type": "unclosed_dialogue_detected",
        "match": "dialogue quote count mismatch",
        "open_count": open_count,
        "close_count": close_count,
    }


def detect_duplicate_paragraphs(text):
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    seen = {}
    duplicates = []

    for index, paragraph in enumerate(paragraphs, start=1):
        normalized = re.sub(r"\s+", " ", paragraph)
        if len(normalized) < 20:
            continue
        if normalized in seen:
            duplicates.append(
                {
                    "type": "duplicate_paragraph_detected",
                    "match": normalized[:80],
                    "first_paragraph": seen[normalized],
                    "duplicate_paragraph": index,
                }
            )
            continue
        seen[normalized] = index

    return duplicates


def collect_format_violations(text):
    violations = []
    details = []

    heading_match = re.search(r"(?m)^\s*#+\s+(.+)$", text)
    if heading_match:
        violations.append("heading_detected")
        details.append(
            {
                "type": "heading_detected",
                "match": heading_match.group(0).strip(),
            }
        )

    bullet_match = re.search(r"(?m)^\s*(?:[-*]\s+|\d+\.\s+)(.+)$", text)
    if bullet_match:
        violations.append("bullet_list_detected")
        details.append(
            {
                "type": "bullet_list_detected",
                "match": bullet_match.group(0).strip(),
            }
        )

    for violation_type, pattern in META_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if "meta_commentary_detected" not in violations:
            violations.append("meta_commentary_detected")
        details.append(
            {
                "type": violation_type,
                "match": match.group(0).strip(),
            }
        )

    unclosed_dialogue = detect_unclosed_dialogue(text)
    if unclosed_dialogue:
        violations.append("unclosed_dialogue_detected")
        details.append(unclosed_dialogue)

    duplicate_paragraphs = detect_duplicate_paragraphs(text)
    if duplicate_paragraphs:
        violations.append("duplicate_paragraph_detected")
        details.extend(duplicate_paragraphs)

    return violations, details


def detect_format_violations(text):
    violations, _ = collect_format_violations(text)
    return violations


def paragraph_count(text):
    blocks = [block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    return len(blocks)


def dialogue_ratio_hint(text):
    if not text:
        return 0.0
    dialogue_chars = sum(len(match.group(0)) for match in re.finditer(r"「[^」]*」", text, re.DOTALL))
    return round(dialogue_chars / len(text), 3)


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
    runtime_dir = (
        resolve_relative_path(args.runtime_dir, base_dirs=[project_dir], must_exist=False)
        if args.runtime_dir
        else os.path.join(project_dir, "runtime")
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
        "paragraph_count": paragraph_count(body_text),
        "dialogue_ratio_hint": dialogue_ratio_hint(body_text),
    }

    output_path = os.path.join(runtime_dir, "check_report.json")
    write_json_file(output_path, report)
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
