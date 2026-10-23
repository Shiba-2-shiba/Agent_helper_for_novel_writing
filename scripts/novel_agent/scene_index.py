import json
import os
import re
from datetime import datetime, timezone

from novel_agent.context_blocks import build_excerpt
from novel_agent.ledgers import file_content_hash
from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.storage import atomic_write_text
from novel_agent.story_memory import memory_status, scene_key
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
    outcomes = _accepted_outcomes(project_dir)
    for item in collect_scene_metadata(project_dir):
        path = item["path"]
        text = read_text_file(path)
        scene_id = f"{item['chapter']}-{item['scene']}"
        outcome = outcomes.get(scene_id)
        summary = outcome["text"] if outcome else build_excerpt(text, max_chars=140)
        records.append(
            {
                "scene_id": scene_id,
                "chapter": item["chapter"],
                "scene": item["scene"],
                "path": os.path.relpath(path, project_dir),
                "summary": summary,
                "summary_kind": "scene_outcome" if outcome else "excerpt",
                "memory_record_id": outcome["id"] if outcome else "",
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
    atomic_write_text(path, "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))
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
                record = json.loads(line)
                if not isinstance(record, dict) or not isinstance(record.get("scene_id"), str) or not isinstance(record.get("path"), str):
                    raise ValueError("invalid scene summary record")
                scene_key(record["scene_id"])
                records.append(record)
            except (ValueError, UserFacingError) as exc:
                raise DataCorruptionError("invalid JSONL at %s: %s; rebuild the scene index" % (path, exc))
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


def _accepted_outcomes(project_dir, target_scene_id=None):
    outcomes = {}
    for record in memory_status(project_dir, as_of_scene_id=target_scene_id)["records"]:
        if record["status"] == "active" and record["kind"] == "scene_outcome":
            old = outcomes.get(record["scene_id"])
            if old is None or (scene_key(record["available_after_scene"]), record["id"]) > (scene_key(old["available_after_scene"]), old["id"]):
                outcomes[record["scene_id"]] = record
    return outcomes


def select_related_scenes(project_dir, *, target_scene_id, query_text, limit=3):
    records = read_scene_summaries(project_dir) or refresh_scene_summaries(project_dir)
    target_key = scene_key(target_scene_id)
    outcomes = _accepted_outcomes(project_dir, target_scene_id)
    target_keywords = extract_keywords(query_text)
    candidates = []
    for original in records:
        if scene_key(original["scene_id"]) >= target_key:
            continue
        record = dict(original)
        outcome = outcomes.get(record["scene_id"])
        # A globally active index entry may be unavailable at an earlier target.
        # Re-project accepted outcomes at T; otherwise label a fresh prose excerpt.
        text = read_text_file(os.path.join(project_dir, record["path"]))
        record["summary"] = outcome["text"] if outcome else build_excerpt(text, max_chars=140)
        record["summary_kind"] = "scene_outcome" if outcome else "excerpt"
        record["memory_record_id"] = outcome["id"] if outcome else ""
        record["keywords"] = extract_keywords(record["summary"])
        candidates.append(record)
    scored = [(_score_record(record, target_keywords, target_scene_id), record) for record in candidates]
    selected = [record for score, record in sorted(scored, key=lambda item: item[0], reverse=True) if score >= 0]
    return selected[:limit]


def render_related_context_pack(project_dir, *, target_scene_id, query_text, limit=3):
    selected = select_related_scenes(project_dir, target_scene_id=target_scene_id, query_text=query_text, limit=limit)
    lines = ["# Related Context Pack", "", "## Selected Context"]
    if not selected:
        lines.append("- No related scene summaries found.")
    for record in selected:
        source = f"{record['path']}:1-1"
        lines.append(f"- [scene {record['scene_id']} / {record['summary_kind']}] {record['summary']} (source: {source})")
    lines.extend(["", "## Pointers"])
    for record in selected:
        lines.append(f"- scene:{record['path']}:1-1")
    return "\n".join(lines).rstrip() + "\n"
