import argparse
import os
import re
import sys

from prompt_utils import (
    UserFacingError,
    read_text_file,
    resolve_project_path,
    resolve_relative_path,
    write_text_file,
)


EDIT_HEADER_RE = re.compile(r"(?m)^\[EDIT\s+\d+\]\s*$")
TARGET_RE = re.compile(r"(?im)^TARGET:\s*(.+)\s*$")
ANCHOR_RE = re.compile(r"(?im)^ANCHOR:\s*(.+)\s*$")
TEXT_RE = re.compile(r"(?ims)^TEXT:\s*\n?(.*)$")
TARGET_VALUE_RE = re.compile(r"(?i)^(before|after)\s+P(\d+)$")


def split_paragraphs(text):
    return [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]


def parse_edit_blocks(text):
    if not EDIT_HEADER_RE.search(text):
        raise UserFacingError("no edit blocks found")

    blocks = [block.strip() for block in EDIT_HEADER_RE.split(text) if block.strip()]
    edits = []

    for index, block in enumerate(blocks, start=1):
        target_match = TARGET_RE.search(block)
        anchor_match = ANCHOR_RE.search(block)
        text_match = TEXT_RE.search(block)
        if not target_match or not anchor_match or not text_match:
            raise UserFacingError(f"edit block {index} is missing TARGET, ANCHOR, or TEXT")

        insert_text = text_match.group(1).strip()
        if not insert_text:
            raise UserFacingError(f"edit block {index} has empty TEXT")

        edits.append(
            {
                "target": target_match.group(1).strip(),
                "anchor": anchor_match.group(1).strip(),
                "text": insert_text,
            }
        )

    return edits


def _normalize(text):
    return re.sub(r"\s+", " ", text.strip())


def anchor_matches(paragraph, anchor):
    if not anchor:
        return False

    normalized_paragraph = _normalize(paragraph)
    normalized_anchor = _normalize(anchor)
    if normalized_anchor == normalized_paragraph:
        return True

    parts = [part.strip() for part in normalized_anchor.split(" ... ") if part.strip()]
    if not parts:
        return False

    cursor = 0
    for part in parts:
        next_index = normalized_paragraph.find(part, cursor)
        if next_index < 0:
            return False
        cursor = next_index + len(part)
    return True


def classify_target(target, paragraph_count):
    normalized = target.strip()
    if normalized.lower() == "end_of_text":
        return ("end", None)

    match = TARGET_VALUE_RE.fullmatch(normalized)
    if not match:
        raise UserFacingError(f"unsupported TARGET value: {target}")

    mode = match.group(1).lower()
    paragraph_number = int(match.group(2))
    if paragraph_number <= 0 or paragraph_number > paragraph_count:
        raise UserFacingError(f"TARGET references missing paragraph: P{paragraph_number}")

    return (mode, paragraph_number)


def apply_edits(source_text, edits):
    paragraphs = split_paragraphs(source_text)
    if not paragraphs:
        raise UserFacingError("source text has no paragraphs")

    before_map = {index: [] for index in range(1, len(paragraphs) + 1)}
    after_map = {index: [] for index in range(1, len(paragraphs) + 1)}
    end_blocks = []

    for edit in edits:
        target_mode, paragraph_number = classify_target(edit["target"], len(paragraphs))
        if target_mode == "end":
            if edit["anchor"].upper() != "END":
                raise UserFacingError("TARGET end_of_text requires ANCHOR: END")
            end_blocks.append(edit["text"])
            continue

        paragraph_text = paragraphs[paragraph_number - 1]
        if not anchor_matches(paragraph_text, edit["anchor"]):
            raise UserFacingError(f"ANCHOR does not match paragraph P{paragraph_number}")

        if target_mode == "before":
            before_map[paragraph_number].append(edit["text"])
        else:
            after_map[paragraph_number].append(edit["text"])

    assembled = []
    for index, paragraph in enumerate(paragraphs, start=1):
        assembled.extend(before_map[index])
        assembled.append(paragraph)
        assembled.extend(after_map[index])
    assembled.extend(end_blocks)
    return "\n\n".join(assembled).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Apply local expand-edit blocks to an existing draft.")
    parser.add_argument("--project", required=True, help="Path to the project directory")
    parser.add_argument("--text", required=True, help="Existing draft text file path")
    parser.add_argument("--edits", required=True, help="Edit-block response file path")
    parser.add_argument("--output", default="", help="Optional output path (defaults to overwriting --text)")
    args = parser.parse_args()

    project_dir = resolve_project_path(args.project)
    if not os.path.isdir(project_dir):
        raise UserFacingError(f"project directory not found: {project_dir}")

    text_path = resolve_relative_path(args.text, base_dirs=[project_dir], must_exist=True)
    edits_path = resolve_relative_path(args.edits, base_dirs=[project_dir], must_exist=True)
    output_path = (
        resolve_relative_path(args.output, base_dirs=[project_dir], must_exist=False)
        if args.output
        else text_path
    )

    source_text = read_text_file(text_path)
    edit_text = read_text_file(edits_path)
    edits = parse_edit_blocks(edit_text)
    updated_text = apply_edits(source_text, edits)

    write_text_file(output_path, updated_text)
    print(f"OK: applied {len(edits)} edit blocks")
    print(f"OK: output={output_path}")


if __name__ == "__main__":
    try:
        main()
    except UserFacingError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except Exception:
        print("ERROR: unexpected failure while applying expand edits")
        sys.exit(1)
