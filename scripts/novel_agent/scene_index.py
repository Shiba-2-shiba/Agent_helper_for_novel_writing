import json
import os
import re
from datetime import datetime, timezone

from novel_agent.context_blocks import build_excerpt
from novel_agent.ledgers import file_content_hash
from prompt_utils import collect_scene_metadata, read_text_file, runtime_root_dir


def scene_summaries_path(project_dir):
    return os.path.join(runtime_root_dir(project_dir), "scene_summaries.jsonl")


def extract_keywords(text):
    keywords = set()
    for match in re.finditer(r"[A-Za-z0-9_一-龯ぁ-んァ-ンー]{2,}", text or ""):
        token = match.group(0).strip()
        if len(token) > 40:
            # Long Japanese spans are still useful for substring lookup, but
            # shorter slices make overlap scoring less brittle.
            for index in range(0, max(0, len(token) - 1), 4):
                keywords.add(token[index:index + 6])
        else:
            keywords.add(token)
    return sorted(keyword for keyword in keywords if keyword)


def build_scene_summary_records(project_dir):
    records = []
    for item in collect_scene_metadata(project_dir):
        path = item["path"]
        text = read_text_file(path)
        scene_id = f"{item['chapter']}-{item['scene']}"
        summary = build_excerpt(text, max_chars=140)
        records.append(
            {
                "scene_id": scene_id,
                "chapter": item["chapter"],
                "scene": item["scene"],
                "path": os.path.relpath(path, project_dir),
                "summary": summary,
                "characters": [],
                "threads": [],
                "keywords": extract_keywords(summary),
                "content_hash": file_content_hash(path),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    return records


def write_scene_summaries(project_dir, records):
    path = scene_summaries_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_scene_summaries(project_dir):
    path = scene_summaries_path(project_dir)
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def refresh_scene_summaries(project_dir):
    records = build_scene_summary_records(project_dir)
    write_scene_summaries(project_dir, records)
    return records


def _score_record(record, target_keywords, target_scene_id):
    if record.get("scene_id") == target_scene_id:
        return -1
    haystack = " ".join([record.get("summary", ""), " ".join(record.get("keywords", []))])
    score = 0
    for keyword in target_keywords:
        if keyword and keyword in haystack:
            score += 1
    # Prefer recent prior scenes when lexical scores tie.
    try:
        chapter, scene = (int(part) for part in str(record.get("scene_id", "0-0")).split("-", 1))
    except ValueError:
        chapter, scene = 0, 0
    return score * 1000 + chapter * 100 + scene


def select_related_scenes(project_dir, *, target_scene_id, query_text, limit=3):
    records = read_scene_summaries(project_dir) or refresh_scene_summaries(project_dir)
    target_keywords = extract_keywords(query_text)
    scored = [
        (_score_record(record, target_keywords, target_scene_id), record)
        for record in records
    ]
    selected = [record for score, record in sorted(scored, key=lambda item: item[0], reverse=True) if score >= 0]
    return selected[:limit]


def render_related_context_pack(project_dir, *, target_scene_id, query_text, limit=3):
    selected = select_related_scenes(project_dir, target_scene_id=target_scene_id, query_text=query_text, limit=limit)
    lines = ["# Related Context Pack", "", "## Selected Context"]
    if not selected:
        lines.append("- No related scene summaries found.")
    for record in selected:
        source = f"{record['path']}:1-1"
        lines.append(f"- [scene {record['scene_id']}] {record['summary']} (source: {source})")
    lines.extend(["", "## Pointers"])
    for record in selected:
        lines.append(f"- scene:{record['path']}:1-1")
    return "\n".join(lines).rstrip() + "\n"
