import json
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_MIN_CHARS = 1000
DEFAULT_TARGET_CHARS = 1250
DEFAULT_MAX_CHARS = 1500
RUNTIME_PROMPT_WARN_LIMIT = 8000
RUNTIME_CONTINUITY_WARN_LIMIT = 1500
SCENE_FILENAME_RE = re.compile(r"^chapter_?(\d+)_scene_?(\d+)\.txt$", re.IGNORECASE)


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


def extract_chapter_block(outline_text, chapter_num):
    pattern = rf"(?ms)^##\s*第{chapter_num}章[^\n]*\n.*?(?=^##\s*第\d+章|\Z)"
    match = re.search(pattern, outline_text)
    if match:
        return match.group(0).strip()
    return ""


def parse_chapter_target_chars(chapter_block):
    if not chapter_block:
        return 0
    match = re.search(r"目標[:：]\s*約?\s*([\d,]+)\s*字", chapter_block)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def extract_scene_description(chapter_block, scene_num):
    if not chapter_block:
        return ""

    pattern = rf"^\s*-\s*\[[ xX]?\]\s*シーン{scene_num}(?:（[^）]*）)?\s*:\s*(.*)$"
    match = re.search(pattern, chapter_block, re.MULTILINE)
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
            chapter_num = int(match.group(1))
            scene_num = int(match.group(2))
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


def _match_scene_tuple(path):
    name = os.path.basename(path)
    match = SCENE_FILENAME_RE.match(name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


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
