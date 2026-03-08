import json
import os
import re
from datetime import datetime, timezone


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_MIN_CHARS = 1000
DEFAULT_TARGET_CHARS = 1250
DEFAULT_MAX_CHARS = 1500
RUNTIME_PROMPT_WARN_LIMIT = 8000
RUNTIME_CONTINUITY_WARN_LIMIT = 1500
SCENE_FILENAME_RE = re.compile(
    r"^(?:chapter_?(\d+)_scene_?(\d+)|scene_(\d+)-(\d+))\.txt$",
    re.IGNORECASE,
)
CANONICAL_OUTLINE_FILENAME = "05_chapter_outline.md"
LEGACY_OUTLINE_FILENAME = "05_chapter_outline_100k.md"
TARGET_PROFILE_SPECS = {
    30000: {
        "target_length_profile": "novel_30k",
        "planning_gate_min_chars": 24000,
    },
    50000: {
        "target_length_profile": "novel_50k",
        "planning_gate_min_chars": 40000,
    },
    100000: {
        "target_length_profile": "novel_100k",
        "planning_gate_min_chars": 80000,
    },
}
TARGET_TOTAL_CHARS_BY_PROFILE = {
    spec["target_length_profile"]: total_chars
    for total_chars, spec in TARGET_PROFILE_SPECS.items()
}
CHAPTER_DIR_HINTS = {
    1: "chapter_1_introduction",
    2: "chapter_2_rising_action",
    3: "chapter_3_complication",
    4: "chapter_4_climax",
    5: "chapter_5_resolution",
}


class UserFacingError(Exception):
    """Raised for expected CLI failures that should not print a traceback."""


def resolve_project_path(project_arg):
    if os.path.isabs(project_arg):
        return os.path.normpath(project_arg)

    cwd_path = os.path.abspath(project_arg)
    base_path = os.path.abspath(os.path.join(BASE_DIR, project_arg))
    if os.path.exists(cwd_path):
        return cwd_path
    if os.path.exists(base_path):
        return base_path
    return cwd_path


def resolve_relative_path(path_arg, base_dirs=None, must_exist=False):
    if not path_arg:
        raise UserFacingError("path value is empty")

    if os.path.isabs(path_arg):
        candidate = os.path.normpath(path_arg)
        if must_exist and not os.path.exists(candidate):
            raise UserFacingError(f"path not found: {candidate}")
        return candidate

    bases = [os.getcwd()]
    if base_dirs:
        bases.extend(base_dirs)
    bases.append(BASE_DIR)

    candidates = []
    for base in bases:
        candidate = os.path.abspath(os.path.join(base, path_arg))
        candidates.append(candidate)
        if os.path.exists(candidate):
            return candidate

    if must_exist:
        raise UserFacingError(f"path not found: {candidates[0]}")
    return candidates[0]


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def read_text_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def read_optional_text(path):
    if not os.path.exists(path):
        return ""
    return read_text_file(path)


def write_text_file(path, content):
    directory = os.path.dirname(path)
    if directory:
        ensure_directory(directory)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def write_json_file(path, payload):
    directory = os.path.dirname(path)
    if directory:
        ensure_directory(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def estimate_tokens(text):
    if not text:
        return 0
    return max(1, len(text) // 2)


def require_existing_file(path, label=None):
    if not os.path.isfile(path):
        target = label or path
        raise UserFacingError(f"{target} not found")
    return path


def validate_positive_int(name, value):
    if value <= 0:
        raise UserFacingError(f"{name} must be a positive integer")


def validate_char_bounds(min_chars, target_chars, max_chars):
    validate_positive_int("min_chars", min_chars)
    validate_positive_int("target_chars", target_chars)
    validate_positive_int("max_chars", max_chars)
    if not (min_chars <= target_chars <= max_chars):
        raise UserFacingError("expected min_chars <= target_chars <= max_chars")


def compute_target_length_profile(target_total_chars: int) -> str:
    spec = TARGET_PROFILE_SPECS.get(target_total_chars)
    if spec is None:
        raise UserFacingError(f"unsupported target_total_chars: {target_total_chars}")
    return spec["target_length_profile"]


def compute_gate_threshold(target_total_chars: int) -> int:
    spec = TARGET_PROFILE_SPECS.get(target_total_chars)
    if spec is None:
        raise UserFacingError(f"unsupported target_total_chars: {target_total_chars}")
    return spec["planning_gate_min_chars"]


def _compute_target_total_chars_from_profile(target_length_profile: str) -> int:
    total_chars = TARGET_TOTAL_CHARS_BY_PROFILE.get(target_length_profile)
    if total_chars is None:
        raise UserFacingError(f"unsupported target_length_profile: {target_length_profile}")
    return total_chars


def build_target_profile_payload(target_total_chars: int, *, source: str, planning_gate_enabled: bool = True) -> dict:
    return {
        "target_total_chars": target_total_chars,
        "target_length_profile": compute_target_length_profile(target_total_chars),
        "planning_gate_enabled": bool(planning_gate_enabled),
        "planning_gate_min_chars": compute_gate_threshold(target_total_chars),
        "planning_target_total_chars": target_total_chars,
        "source": source,
    }


def parse_scene_reference(scene_raw):
    cleaned = scene_raw.strip()
    match = re.fullmatch(r"(\d+)-(\d+)", cleaned)
    if match:
        chapter_num = int(match.group(1))
        scene_num = int(match.group(2))
    else:
        match = re.fullmatch(r"chapter_(\d+)_scene_(\d+)", cleaned, re.IGNORECASE)
        if not match:
            raise UserFacingError(f"unable to parse scene: {scene_raw}")
        chapter_num = int(match.group(1))
        scene_num = int(match.group(2))

    if chapter_num <= 0 or scene_num <= 0:
        raise UserFacingError(f"unable to parse scene: {scene_raw}")

    return {
        "chapter": chapter_num,
        "scene": scene_num,
        "canonical_id": f"{chapter_num}-{scene_num}",
        "scene_token": f"chapter_{chapter_num}_scene_{scene_num}",
        "filename": f"chapter_{chapter_num}_scene_{scene_num}.txt",
    }


def runtime_scene_key(scene_ref):
    return scene_ref["canonical_id"]


def runtime_scene_dir(project_dir, scene_ref, mode):
    return os.path.join(project_dir, "runtime", "scenes", runtime_scene_key(scene_ref), mode)


def runtime_root_dir(project_dir):
    return os.path.join(project_dir, "runtime")


def runtime_index_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "runtime_index.json")


def read_runtime_index(project_dir):
    path = runtime_index_path(project_dir)
    if not os.path.isfile(path):
        return {"latest_by_mode": {}}
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return {"latest_by_mode": {}}
    if not isinstance(payload, dict):
        return {"latest_by_mode": {}}
    payload.setdefault("latest_by_mode", {})
    return payload


def write_runtime_index(project_dir, payload):
    payload.setdefault("latest_by_mode", {})
    write_json_file(runtime_index_path(project_dir), payload)


def update_runtime_index(project_dir, *, mode, scene_ref, runtime_dir):
    payload = read_runtime_index(project_dir)
    payload["latest_by_mode"][mode] = {
        "chapter": scene_ref["chapter"],
        "scene": scene_ref["scene"],
        "scene_id": scene_ref["canonical_id"],
        "runtime_dir": runtime_dir,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_runtime_index(project_dir, payload)
    return payload


def resolve_runtime_dir(project_dir, *, mode="", scene_ref=None, runtime_dir_arg=""):
    if runtime_dir_arg:
        return resolve_relative_path(runtime_dir_arg, base_dirs=[project_dir], must_exist=True)

    if scene_ref is not None:
        candidate = runtime_scene_dir(project_dir, scene_ref, mode or "draft")
        if os.path.isdir(candidate):
            return candidate

    payload = read_runtime_index(project_dir)
    if mode:
        latest = payload.get("latest_by_mode", {}).get(mode)
        if latest:
            candidate = latest.get("runtime_dir", "")
            if candidate and os.path.isdir(candidate):
                return candidate

    return runtime_root_dir(project_dir)


def extract_chapter_block(outline_text, chapter_num):
    pattern = rf"(?ms)^#{{1,6}}\s*第{chapter_num}章[^\n]*\n.*?(?=^#{{1,6}}\s*第\d+章|\Z)"
    match = re.search(pattern, outline_text)
    if match:
        return match.group(0).strip()
    return ""


def parse_chapter_target_chars(chapter_block):
    if not chapter_block:
        return 0
    chapter_card_target = extract_chapter_card_value(chapter_block, "想定目標字数")
    parsed_target = _parse_int_from_text(chapter_card_target)
    if parsed_target:
        return parsed_target
    match = re.search(r"目標[:：]\s*約?\s*([\d,]+)\s*字", chapter_block)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def extract_chapter_card_value(chapter_block, label):
    if not chapter_block:
        return ""
    pattern = rf"(?m)^\s*-\s*{re.escape(label)}:\s*(.*)$"
    match = re.search(pattern, chapter_block)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_int_from_text(raw_text):
    if not raw_text:
        return 0
    match = re.search(r"([\d,]+)", raw_text)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _split_markdown_table_row(line):
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _normalize_scene_id(raw_scene_id, default_chapter=None):
    if not raw_scene_id:
        return None
    cleaned = raw_scene_id.strip()
    match = re.fullmatch(r"(\d+)-(\d+)", cleaned)
    if match:
        return {
            "chapter": int(match.group(1)),
            "scene": int(match.group(2)),
            "canonical_id": f"{int(match.group(1))}-{int(match.group(2))}",
        }
    match = re.fullmatch(r"(\d+)", cleaned)
    if match and default_chapter is not None:
        return {
            "chapter": int(default_chapter),
            "scene": int(match.group(1)),
            "canonical_id": f"{int(default_chapter)}-{int(match.group(1))}",
        }
    return None


def parse_scene_ledger(chapter_block):
    if not chapter_block:
        return []

    chapter_heading = re.search(r"(?m)^#{1,6}\s*第(\d+)章", chapter_block)
    default_chapter = int(chapter_heading.group(1)) if chapter_heading else None
    lines = chapter_block.splitlines()
    in_ledger = False
    header_cells = []
    rows = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("### Scene Ledger"):
            in_ledger = True
            header_cells = []
            continue
        if not in_ledger:
            continue
        if not stripped:
            if header_cells:
                break
            continue
        if stripped.startswith("### ") and not stripped.startswith("### Scene Ledger"):
            break
        if stripped.startswith("## ") and not stripped.startswith("## 第"):
            break
        if stripped.startswith("|---"):
            continue
        if stripped.startswith("|"):
            cells = _split_markdown_table_row(line)
            if not header_cells:
                header_cells = cells
                continue
            if not cells or len(cells) != len(header_cells):
                continue
            entry = dict(zip(header_cells, cells))
            scene_ref = _normalize_scene_id(entry.get("scene_id", ""), default_chapter=default_chapter)
            rows.append(
                {
                    "scene_id": entry.get("scene_id", "").strip(),
                    "chapter": scene_ref["chapter"] if scene_ref else default_chapter or 0,
                    "scene": scene_ref["scene"] if scene_ref else 0,
                    "canonical_id": scene_ref["canonical_id"] if scene_ref else "",
                    "scene_type": entry.get("scene_type", "").strip(),
                    "purpose": entry.get("purpose", "").strip(),
                    "turn": entry.get("turn", "").strip(),
                    "payoff_or_seed": entry.get("payoff_or_seed", "").strip(),
                    "min_chars": _parse_int_from_text(entry.get("min", "")),
                    "target_chars": _parse_int_from_text(entry.get("target", "")),
                    "max_chars": _parse_int_from_text(entry.get("max", "")),
                    "depends_on": entry.get("depends_on", "").strip(),
                    "status": entry.get("status", "").strip().lower(),
                    "row_index": len(rows),
                }
            )
            continue
        if header_cells:
            break

    return rows


def find_scene_ledger_entry(chapter_block, scene_num, chapter_num=None):
    for entry in parse_scene_ledger(chapter_block):
        if chapter_num is not None and entry["chapter"] not in (0, chapter_num):
            continue
        if entry["scene"] == scene_num:
            return entry
    return None


def compute_planned_totals(outline_text):
    chapter_numbers = sorted({int(match.group(1)) for match in re.finditer(r"(?m)^#{1,6}\s*第(\d+)章", outline_text)})
    totals = {
        "planned_scene_count": 0,
        "planned_total_min_chars": 0,
        "planned_total_target_chars": 0,
        "planned_total_max_chars": 0,
        "chapter_planned_chars": {},
        "chapter_scene_counts": {},
    }

    for chapter_num in chapter_numbers:
        chapter_block = extract_chapter_block(outline_text, chapter_num)
        if not chapter_block:
            continue
        rows = parse_scene_ledger(chapter_block)
        chapter_target = parse_chapter_target_chars(chapter_block)
        if not chapter_target and rows:
            chapter_target = sum(row["target_chars"] for row in rows if row["target_chars"] > 0)

        totals["planned_scene_count"] += len(rows)
        totals["planned_total_min_chars"] += sum(row["min_chars"] for row in rows if row["min_chars"] > 0)
        totals["planned_total_target_chars"] += sum(row["target_chars"] for row in rows if row["target_chars"] > 0)
        totals["planned_total_max_chars"] += sum(row["max_chars"] for row in rows if row["max_chars"] > 0)
        if rows:
            totals["chapter_scene_counts"][str(chapter_num)] = len(rows)
        if chapter_target:
            totals["chapter_planned_chars"][str(chapter_num)] = chapter_target

    return totals


def _extract_state_schema_text(project_dir):
    state_schema_path = find_state_schema_path(project_dir)
    if state_schema_path is None:
        return ""
    return read_text_file(state_schema_path)


def find_state_schema_path(project_dir):
    return _find_first_existing(
        os.path.join(project_dir, "agent", "state_schema_novel.yaml"),
        os.path.join(project_dir, "state_schema_novel.yaml"),
        os.path.join(project_dir, "state", "state_schema_novel.yaml"),
    )


def _yaml_scalar_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def update_state_schema_text(text, updates_by_section):
    lines = text.splitlines()

    for section, values in updates_by_section.items():
        section_index = None
        for index, line in enumerate(lines):
            if line.strip() == f"{section}:":
                section_index = index
                break
        if section_index is None:
            continue

        section_end = len(lines)
        for index in range(section_index + 1, len(lines)):
            line = lines[index]
            if line and not line.startswith(" "):
                section_end = index
                break

        for key, value in values.items():
            key_line = f"  {key}: {_yaml_scalar_text(value)}"
            replaced = False
            for index in range(section_index + 1, section_end):
                if re.match(rf"^\s{{2}}{re.escape(key)}:\s*", lines[index]):
                    lines[index] = key_line
                    replaced = True
                    break
            if not replaced:
                lines.insert(section_end, key_line)
                section_end += 1

    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def sync_state_schema(project_dir, updates_by_section):
    path = find_state_schema_path(project_dir)
    if path is None:
        return ""
    original = read_text_file(path)
    updated = update_state_schema_text(original, updates_by_section)
    if updated != original:
        write_text_file(path, updated)
    return path


def _extract_state_scalar(text, key, default_value=""):
    if not text:
        return default_value
    pattern = rf"(?m)^\s*{re.escape(key)}:\s*(.+?)\s*(?:#.*)?$"
    match = re.search(pattern, text)
    if not match:
        return default_value
    return match.group(1).strip().strip('"').strip("'")


def _parse_bool_text(raw_value, default_value=None):
    if raw_value is None:
        return default_value
    cleaned = str(raw_value).strip().strip('"').strip("'").lower()
    if cleaned in {"true", "yes", "on", "1"}:
        return True
    if cleaned in {"false", "no", "off", "0"}:
        return False
    return default_value


def resolve_target_profile_from_state(state_schema_text: str, *, fallback_total_chars: int = 100000) -> dict:
    target_total_chars = _parse_int_from_text(_extract_state_scalar(state_schema_text, "target_total_chars", "0"))
    if target_total_chars:
        planning_gate_enabled = _parse_bool_text(
            _extract_state_scalar(state_schema_text, "planning_gate_enabled", ""),
            default_value=True,
        )
        return build_target_profile_payload(
            target_total_chars,
            source="canonical_state",
            planning_gate_enabled=planning_gate_enabled,
        )

    target_length_profile = _extract_state_scalar(state_schema_text, "target_length_profile", "")
    if target_length_profile:
        planning_gate_enabled = _parse_bool_text(
            _extract_state_scalar(state_schema_text, "planning_gate_enabled", ""),
            default_value=True,
        )
        return build_target_profile_payload(
            _compute_target_total_chars_from_profile(target_length_profile),
            source="canonical_state",
            planning_gate_enabled=planning_gate_enabled,
        )

    planning_target_total_chars = _parse_int_from_text(
        _extract_state_scalar(state_schema_text, "planning_target_total_chars", "0")
    )
    if planning_target_total_chars in TARGET_PROFILE_SPECS:
        return build_target_profile_payload(planning_target_total_chars, source="legacy_planning_target")

    total_chars = _parse_int_from_text(_extract_state_scalar(state_schema_text, "total_chars", "0"))
    if total_chars in TARGET_PROFILE_SPECS:
        return build_target_profile_payload(total_chars, source="legacy_total_chars")

    length_mode = _extract_state_scalar(state_schema_text, "length_mode", "")
    if length_mode == "long_form_100k":
        return build_target_profile_payload(100000, source="legacy_length_mode")

    return build_target_profile_payload(fallback_total_chars, source="fallback")


def resolve_outline_path(project_dir: str, *, require_exists: bool = False) -> str:
    candidates = [
        os.path.join(project_dir, CANONICAL_OUTLINE_FILENAME),
        os.path.join(project_dir, LEGACY_OUTLINE_FILENAME),
        os.path.join(project_dir, "plot", CANONICAL_OUTLINE_FILENAME),
        os.path.join(project_dir, "plot", LEGACY_OUTLINE_FILENAME),
        os.path.join(project_dir, "memory", CANONICAL_OUTLINE_FILENAME),
        os.path.join(project_dir, "memory", LEGACY_OUTLINE_FILENAME),
    ]
    resolved = _find_first_existing(*candidates)
    if resolved:
        return resolved
    if require_exists:
        raise UserFacingError(
            f"{CANONICAL_OUTLINE_FILENAME} or {LEGACY_OUTLINE_FILENAME} not found"
        )
    return candidates[0]


def load_target_length_profile(project_dir: str) -> dict:
    state_schema_text = _extract_state_schema_text(project_dir)
    return resolve_target_profile_from_state(state_schema_text)


def _parse_scene_type_bands_from_state(state_schema_text):
    if not state_schema_text:
        return {}

    lines = state_schema_text.splitlines()
    in_section = False
    current_band = ""
    current_indent = 0
    bands = {}

    for line in lines:
        if not in_section:
            if re.match(r"^\s*scene_type_bands:\s*$", line):
                in_section = True
            continue

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent <= 2 and not stripped.startswith("#"):
            break

        if indent == 4 and stripped.endswith(":"):
            current_band = stripped[:-1].strip()
            bands[current_band] = {}
            current_indent = indent
            continue

        if current_band and indent > current_indent and ":" in stripped:
            key, value = stripped.split(":", 1)
            bands[current_band][key.strip()] = _parse_int_from_text(value.strip())

    return bands


def load_planning_metadata(project_dir):
    state_schema_text = _extract_state_schema_text(project_dir)
    target_profile = resolve_target_profile_from_state(state_schema_text)
    planning_gate_enabled = _parse_bool_text(
        _extract_state_scalar(state_schema_text, "planning_gate_enabled", ""),
        default_value=target_profile["planning_gate_enabled"],
    )
    planning_gate_min_chars = _parse_int_from_text(
        _extract_state_scalar(state_schema_text, "planning_gate_min_chars", "0")
    ) or target_profile["planning_gate_min_chars"]
    planning_target_total_chars = _parse_int_from_text(
        _extract_state_scalar(state_schema_text, "planning_target_total_chars", "0")
    ) or target_profile["planning_target_total_chars"]
    legacy_length_mode = _extract_state_scalar(state_schema_text, "length_mode", "")
    if not legacy_length_mode and target_profile["target_length_profile"] == "novel_100k":
        legacy_length_mode = "long_form_100k"

    return {
        "state_schema_text": state_schema_text,
        "length_mode": legacy_length_mode,
        "target_total_chars": target_profile["target_total_chars"],
        "target_length_profile": target_profile["target_length_profile"],
        "planning_gate_enabled": planning_gate_enabled,
        "target_profile_source": target_profile["source"],
        "planning_gate_status": _extract_state_scalar(state_schema_text, "planning_gate_status", ""),
        "planning_gate_min_chars": planning_gate_min_chars,
        "planning_target_total_chars": planning_target_total_chars,
        "planned_total_min_chars": _parse_int_from_text(_extract_state_scalar(state_schema_text, "planned_total_min_chars", "0")),
        "planned_total_target_chars": _parse_int_from_text(_extract_state_scalar(state_schema_text, "planned_total_target_chars", "0")),
        "planned_scene_count": _parse_int_from_text(_extract_state_scalar(state_schema_text, "planned_scene_count", "0")),
        "scene_type_bands": _parse_scene_type_bands_from_state(state_schema_text),
    }


def resolve_scene_type_band(scene_type, project_dir="", state_schema_text="", min_chars=DEFAULT_MIN_CHARS, target_chars=DEFAULT_TARGET_CHARS, max_chars=DEFAULT_MAX_CHARS):
    if not state_schema_text and project_dir:
        state_schema_text = _extract_state_schema_text(project_dir)

    bands = _parse_scene_type_bands_from_state(state_schema_text)
    if scene_type and scene_type in bands:
        band = bands[scene_type]
        return {
            "scene_type": scene_type,
            "min": band.get("min", min_chars),
            "target": band.get("target", target_chars),
            "max": band.get("max", max_chars),
        }

    fallback_type = scene_type or "default"
    return {
        "scene_type": fallback_type,
        "min": min_chars,
        "target": target_chars,
        "max": max_chars,
    }


def extract_scene_description(chapter_block, scene_num):
    if not chapter_block:
        return ""

    ledger_entry = find_scene_ledger_entry(chapter_block, scene_num)
    if ledger_entry and ledger_entry["purpose"]:
        return ledger_entry["purpose"]

    pattern = rf"^\s*-\s*\[[ xX]?\]\s*シーン{scene_num}(?:（[^）]*）)?\s*:\s*(.*)$"
    match = re.search(pattern, chapter_block, re.MULTILINE)
    if match:
        return match.group(1).strip()
    heading_pattern = rf"^#{{1,6}}\s*シーン{scene_num}(?:（[^）]*）)?\s*[：:]\s*(.*)$"
    match = re.search(heading_pattern, chapter_block, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def extract_chapter_summary(chapter_block):
    if not chapter_block:
        return ""

    lines = [line.strip() for line in chapter_block.splitlines() if line.strip()]
    for line in lines[1:6]:
        if line.startswith(">"):
            return line.lstrip(">").strip()
    return ""


def build_excerpt(text, max_chars=220):
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars].rstrip() + "..."


def _collect_scene_metadata(project_dir):
    found = {}
    for root, _, files in os.walk(project_dir):
        for name in files:
            match = SCENE_FILENAME_RE.match(name)
            if not match:
                continue
            chapter_num = int(match.group(1) or match.group(3))
            scene_num = int(match.group(2) or match.group(4))
            path = os.path.join(root, name)
            key = (chapter_num, scene_num)
            current = found.get(key)
            if current is None or len(path) < len(current["path"]):
                found[key] = {
                    "chapter": chapter_num,
                    "scene": scene_num,
                    "path": path,
                }

    return sorted(found.values(), key=lambda item: (item["chapter"], item["scene"], item["path"]))


def collect_scene_metadata(project_dir):
    return _collect_scene_metadata(project_dir)


def count_chapter_written_chars(project_dir, chapter_num):
    total_chars = 0
    for item in _collect_scene_metadata(project_dir):
        if item["chapter"] != chapter_num:
            continue
        total_chars += len(read_text_file(item["path"]))
    return total_chars


def count_total_written_chars(project_dir):
    total_chars = 0
    for item in _collect_scene_metadata(project_dir):
        total_chars += len(read_text_file(item["path"]))
    return total_chars


def count_completed_scene_files(project_dir):
    return len(_collect_scene_metadata(project_dir))


def update_scene_ledger_status(project_dir, scene_ref, new_status):
    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if not os.path.isfile(outline_path):
        return ""

    lines = read_text_file(outline_path).splitlines()
    chapter_pattern = re.compile(rf"^#{{1,6}}\s*第{scene_ref['chapter']}章")
    any_chapter_pattern = re.compile(r"^#{1,6}\s*第\d+章")
    chapter_start = -1
    for index, line in enumerate(lines):
        if chapter_pattern.match(line.strip()):
            chapter_start = index
            break
    if chapter_start < 0:
        return ""

    chapter_end = len(lines)
    for index in range(chapter_start + 1, len(lines)):
        if any_chapter_pattern.match(lines[index].strip()):
            chapter_end = index
            break

    ledger_start = -1
    for index in range(chapter_start, chapter_end):
        if lines[index].strip().startswith("### Scene Ledger"):
            ledger_start = index
            break
    if ledger_start < 0:
        return ""

    header_index = -1
    header_cells = []
    for index in range(ledger_start + 1, chapter_end):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            header_cells = _split_markdown_table_row(lines[index])
            header_index = index
            break
        if stripped.startswith("### ") or stripped.startswith("## "):
            return ""
    if header_index < 0 or not header_cells:
        return ""
    if "scene_id" not in header_cells or "status" not in header_cells:
        return ""

    scene_id_index = header_cells.index("scene_id")
    status_index = header_cells.index("status")
    changed = False
    for index in range(header_index + 1, chapter_end):
        stripped = lines[index].strip()
        if not stripped:
            break
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = _split_markdown_table_row(lines[index])
        if len(cells) != len(header_cells):
            continue
        if cells[scene_id_index].strip() != scene_ref["canonical_id"]:
            continue
        cells[status_index] = new_status
        lines[index] = "| " + " | ".join(cells) + " |"
        changed = True
        break

    if changed:
        content = "\n".join(lines) + "\n"
        write_text_file(outline_path, content)
        return outline_path
    return ""


def collect_missing_dependencies(project_dir):
    outline_path = resolve_outline_path(project_dir, require_exists=False)
    if not os.path.exists(outline_path):
        return []
    outline_text = read_text_file(outline_path)
    chapter_numbers = sorted({int(match.group(1)) for match in re.finditer(r"(?m)^#{1,6}\s*第(\d+)章", outline_text)})
    missing = []
    for chapter_num in chapter_numbers:
        chapter_block = extract_chapter_block(outline_text, chapter_num)
        for row in parse_scene_ledger(chapter_block):
            if not row["depends_on"] or row["depends_on"] == "-":
                continue
            current_path = find_scene_file(project_dir, parse_scene_reference(row["canonical_id"]))
            depends_path = find_scene_file(project_dir, parse_scene_reference(row["depends_on"]))
            if current_path and not depends_path:
                missing.append(
                    {
                        "scene_id": row["canonical_id"],
                        "depends_on": row["depends_on"],
                    }
                )
    return missing


def find_missing_dependency_for_scene(project_dir, scene_ref):
    for item in collect_missing_dependencies(project_dir):
        if item["scene_id"] == scene_ref["canonical_id"]:
            return item
    return None


def _match_scene_tuple(path):
    name = os.path.basename(path)
    match = SCENE_FILENAME_RE.match(name)
    if not match:
        return None
    return int(match.group(1) or match.group(3)), int(match.group(2) or match.group(4))


def infer_scene_ref_from_path(path):
    matched = _match_scene_tuple(path)
    if matched is None:
        return None
    chapter_num, scene_num = matched
    return parse_scene_reference(f"{chapter_num}-{scene_num}")


def find_scene_file(project_dir, scene_ref):
    target_key = (scene_ref["chapter"], scene_ref["scene"])
    for item in _collect_scene_metadata(project_dir):
        if (item["chapter"], item["scene"]) == target_key:
            return item["path"]
    return ""


def find_chapter_directory(project_dir, chapter_num):
    hint = CHAPTER_DIR_HINTS.get(chapter_num, "")
    if hint:
        hinted_path = os.path.join(project_dir, hint)
        if os.path.isdir(hinted_path):
            return hinted_path

    candidates = []
    chapter_prefix = f"chapter_{chapter_num}_"
    for name in os.listdir(project_dir):
        candidate = os.path.join(project_dir, name)
        if os.path.isdir(candidate) and name.startswith(chapter_prefix):
            candidates.append(candidate)
    if not candidates:
        return ""
    return sorted(candidates, key=lambda path: (len(path), path.lower()))[0]


def suggest_scene_output_path(project_dir, scene_ref):
    existing_path = find_scene_file(project_dir, scene_ref)
    if existing_path:
        return existing_path

    chapter_items = [
        item for item in _collect_scene_metadata(project_dir) if item["chapter"] == scene_ref["chapter"]
    ]
    preferred_dir = ""
    if chapter_items:
        dir_counts = {}
        for item in chapter_items:
            directory = os.path.dirname(item["path"])
            dir_counts[directory] = dir_counts.get(directory, 0) + 1
        preferred_dir = sorted(
            dir_counts.items(),
            key=lambda pair: (-pair[1], len(pair[0]), pair[0].lower()),
        )[0][0]
    if not preferred_dir:
        preferred_dir = find_chapter_directory(project_dir, scene_ref["chapter"]) or project_dir

    style = "chapter_scene"
    style_candidates = [item for item in chapter_items if os.path.dirname(item["path"]) == preferred_dir] or chapter_items
    for item in style_candidates:
        basename = os.path.basename(item["path"])
        if re.fullmatch(rf"scene_{scene_ref['chapter']}-\d+\.txt", basename, re.IGNORECASE):
            style = "scene_hyphen"
            break
        if re.fullmatch(rf"chapter_?{scene_ref['chapter']}_scene_?\d+\.txt", basename, re.IGNORECASE):
            style = "chapter_scene"
            break

    filename = f"scene_{scene_ref['canonical_id']}.txt" if style == "scene_hyphen" else scene_ref["filename"]
    return os.path.join(preferred_dir, filename)


def find_latest_scene_file(project_dir):
    all_scenes = _collect_scene_metadata(project_dir)
    if not all_scenes:
        return None
    return max(all_scenes, key=lambda item: (os.path.getmtime(item["path"]), item["chapter"], item["scene"]))


def find_previous_scene_pack(project_dir, current_scene_ref, explicit_previous_path=""):
    all_scenes = _collect_scene_metadata(project_dir)
    current_key = (current_scene_ref["chapter"], current_scene_ref["scene"])

    if explicit_previous_path:
        previous_path = require_existing_file(explicit_previous_path, "previous_text")
        summary_item = None
        explicit_key = _match_scene_tuple(previous_path)
        if explicit_key is not None:
            for index, item in enumerate(all_scenes):
                if (item["chapter"], item["scene"]) == explicit_key and index > 0:
                    summary_item = all_scenes[index - 1]
                    break
        return {
            "full": {
                "path": previous_path,
                "text": read_text_file(previous_path),
                "source": "explicit",
            },
            "summary": _scene_summary_payload(summary_item),
        }

    previous_items = [item for item in all_scenes if (item["chapter"], item["scene"]) < current_key]
    if not previous_items:
        return {"full": None, "summary": None}

    full_item = previous_items[-1]
    summary_item = previous_items[-2] if len(previous_items) >= 2 else None
    return {
        "full": {
            "path": full_item["path"],
            "text": read_text_file(full_item["path"]),
            "source": "auto",
        },
        "summary": _scene_summary_payload(summary_item),
    }


def _scene_summary_payload(item):
    if item is None:
        return None
    text = read_text_file(item["path"])
    return {
        "path": item["path"],
        "text": text,
        "summary": build_excerpt(text),
        "source": "auto",
    }


def _find_labeled_value(text, labels, default_value):
    for label in labels:
        match = re.search(rf"{label}\s*[:：]\s*(.+)", text)
        if match:
            return match.group(1).strip()
    return default_value


def _collect_style_lines(text, keywords, default_lines):
    collected = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if any(keyword in stripped for keyword in keywords):
            collected.append(stripped.lstrip("- ").strip())
    if collected:
        return collected
    return list(default_lines)


def _find_first_existing(*candidates):
    """Return the first path that exists on disk, or None."""
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def build_style_contract(project_dir, min_chars=DEFAULT_MIN_CHARS, target_chars=DEFAULT_TARGET_CHARS, max_chars=DEFAULT_MAX_CHARS):
    warnings = []
    global_notes_path = _find_first_existing(
        os.path.join(project_dir, "agent", "memory", "global_notes.md"),
        os.path.join(project_dir, "memory", "global_notes.md"),
    )
    state_schema_path = _find_first_existing(
        os.path.join(project_dir, "agent", "state_schema_novel.yaml"),
        os.path.join(project_dir, "state_schema_novel.yaml"),
        os.path.join(project_dir, "state", "state_schema_novel.yaml"),
    )

    global_notes_text = ""
    state_schema_text = ""

    if global_notes_path:
        global_notes_text = read_text_file(global_notes_path)
    else:
        warnings.append("global_notes.md not found, using defaults")

    if state_schema_path:
        state_schema_text = read_text_file(state_schema_path)
    else:
        warnings.append("state_schema_novel.yaml not found, using defaults")

    combined_text = "\n".join(part for part in (global_notes_text, state_schema_text) if part)
    viewpoint = _find_labeled_value(
        combined_text,
        ["視点", "POV", "pov", "point_of_view"],
        "未指定（既定: 一人称または近接三人称を固定）",
    )
    tense = _find_labeled_value(
        combined_text,
        ["地の文時制", "時制", "tense", "narration_tense"],
        "未指定（既定: 地の文は過去形で統一）",
    )
    tone_rules = _collect_style_lines(
        combined_text,
        ["口調", "語尾", "敬語", "文体", "台詞"],
        [
            "主要キャラの語尾と話し方を固定する",
            "台詞と地の文で温度差を作りすぎない",
        ],
    )
    forbidden_rules = _collect_style_lines(
        combined_text,
        ["禁止", "avoid", "forbid"],
        [
            "見出しや箇条書きの混入",
            "作者視点のメタ説明",
            "直前シーンと矛盾する設定変更",
        ],
    )

    content = "\n".join(
        [
            "# Style Contract Compact",
            f"- 視点: {viewpoint}",
            f"- 地の文時制: {tense}",
            "- 口調ルール:",
            *[f"  - {line}" for line in tone_rules],
            "- 禁止表現:",
            *[f"  - {line}" for line in forbidden_rules],
            "- 文字数契約:",
            f"  - 初稿: {min_chars} / {target_chars} / {max_chars} 字（min/target/max）",
        ]
    )
    return content, warnings


def extract_forbidden_terms(style_contract_text):
    terms = []
    in_section = False
    for raw_line in style_contract_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- 禁止表現"):
            in_section = True
            continue
        if in_section and raw_line.startswith("- ") and not stripped.startswith("- 禁止表現"):
            break
        if in_section and raw_line.startswith("  - "):
            term = raw_line[4:].strip()
            if term:
                terms.append(term)
    return terms
