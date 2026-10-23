"""Validated, explicitly accepted story memory. No semantic extraction is performed."""
import copy
import os
import re

from novel_agent.approvals import read_approval_ledger, validate_approval_current
from novel_agent.errors import ConflictError, DataCorruptionError, UserFacingError
from novel_agent.storage import atomic_write_json, atomic_write_text, project_lock, read_json, text_content_hash

KINDS = {"fact", "character_knowledge", "thread_event", "scene_outcome", "chapter_summary", "part_summary"}
SCENE_NAME = re.compile(r"^(?:chapter_?(\d+)_scene_?(\d+)|scene_(\d+)-(\d+))\.txt$", re.IGNORECASE)
BATCH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def scene_key(scene_id):
    if not isinstance(scene_id, str) or not re.fullmatch(r"[1-9]\d*-[1-9]\d*", scene_id):
        raise UserFacingError("invalid canonical scene ID: %r" % scene_id)
    return tuple(int(part) for part in scene_id.split("-"))


def memory_path(project_dir):
    return os.path.join(project_dir, "story_memory", "accepted.json")


def _proposal_path(project_dir, batch_id):
    if not isinstance(batch_id, str) or not BATCH_ID.fullmatch(batch_id):
        raise UserFacingError("batch_id must contain only letters, digits, hyphens and underscores")
    return os.path.join(project_dir, "story_memory", "proposals", batch_id + ".json")


def _string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise UserFacingError("%s must be a nonempty string" % field)


def _strings(value, field, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise UserFacingError("%s must be %sa list" % (field, "a nonempty " if nonempty else ""))
    for item in value:
        _string(item, field)
    if len(set(value)) != len(value):
        raise UserFacingError("%s contains duplicates" % field)


def _schema(record):
    if not isinstance(record, dict):
        raise UserFacingError("record must be an object")
    reserved = {"known_fact", "status", "reasons", "coverage", "context_priority"}.intersection(record)
    if reserved:
        raise UserFacingError("reserved derived memory fields are not accepted: %s" % ", ".join(sorted(reserved)))
    for key in ("id", "kind", "text"):
        _string(record.get(key), key)
    kind = record["kind"]
    if kind not in KINDS:
        raise UserFacingError("unknown memory kind: %s" % kind)
    _strings(record.get("entity_ids"), "entity_ids")
    _strings(record.get("supersedes"), "supersedes")
    scene_key(record.get("available_after_scene"))
    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        raise UserFacingError("sources must be a nonempty list")
    for source in sources:
        if not isinstance(source, dict):
            raise UserFacingError("source must be an object")
        _string(source.get("path"), "source.path")
        digest = source.get("content_hash")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise UserFacingError("source.content_hash must be a SHA-256 hex digest")
        start, end = source.get("line_start"), source.get("line_end")
        if type(start) is not int or type(end) is not int or start < 1 or end < start:
            raise UserFacingError("invalid source line range")
    required = {"fact": ("subject_id", "predicate"), "character_knowledge": ("character_id", "fact_id"),
                "thread_event": ("thread_id", "event"), "scene_outcome": ("scene_id",),
                "chapter_summary": (), "part_summary": ("part_id",)}[kind]
    for key in required:
        _string(record.get(key), key)
    if kind == "thread_event" and record["event"] not in {"opened", "progressed", "resolved", "abandoned"}:
        raise UserFacingError("invalid thread event")
    if kind == "scene_outcome":
        scene_key(record["scene_id"])
    if kind in {"chapter_summary", "part_summary"}:
        _strings(record.get("covered_scenes"), "covered_scenes", nonempty=True)
        for scene_id in record["covered_scenes"]:
            scene_key(scene_id)
    if kind == "chapter_summary":
        if type(record.get("chapter")) is not int or record["chapter"] < 1:
            raise UserFacingError("chapter must be a positive integer")
        if any(scene_key(s)[0] != record["chapter"] for s in record["covered_scenes"]):
            raise UserFacingError("covered_scenes does not belong to chapter")
    _validate_source_structure(record)


def _validate_source_structure(record):
    """Stored and proposed records share structural rules, never freshness checks."""
    source_scenes = set()
    for source in record["sources"]:
        scene_id = _scene_from_path(source["path"])
        if source.get("scene_id", scene_id) != scene_id:
            raise UserFacingError("source scene_id does not match canonical path")
        source_scenes.add(scene_id)
    if scene_key(record["available_after_scene"]) < max(scene_key(s) for s in source_scenes):
        raise UserFacingError("available_after_scene precedes source scene")
    if record["kind"] == "scene_outcome" and record["scene_id"] not in source_scenes:
        raise UserFacingError("scene_outcome must cite its scene")
    if record["kind"] in {"chapter_summary", "part_summary"}:
        if not set(record["covered_scenes"]).issubset(source_scenes):
            raise UserFacingError("summary requires a source for every covered scene")


def _scene_from_path(path):
    match = SCENE_NAME.fullmatch(os.path.basename(path))
    if not match:
        raise UserFacingError("source must be canonical scene txt, not planning or setting material: %s" % path)
    result = "%s-%s" % (int(match.group(1) or match.group(3)), int(match.group(2) or match.group(4)))
    scene_key(result)
    return result


def _safe_source_path(project_dir, path):
    if "\\" in path or ".." in path.split("/"):
        raise UserFacingError("source path traversal is not allowed: %s" % path)
    root = os.path.realpath(project_dir)
    full = os.path.realpath(os.path.join(root, path))
    if os.path.commonpath([root, full]) != root or full == root:
        raise UserFacingError("source is outside project: %s" % path)
    return full, os.path.relpath(full, root).replace(os.sep, "/")


def _scene_paths(project_dir):
    paths = {}
    for root, _, files in os.walk(project_dir):
        for name in files:
            if SCENE_NAME.fullmatch(name):
                scene_id = _scene_from_path(name)
                paths.setdefault(scene_id, []).append(os.path.join(root, name))
    return paths


def _chapter_expected_scenes(project_dir, chapter, scene_paths):
    # Coverage is structural, never a semantic claim about the planned content.
    expected = {scene_id for scene_id in scene_paths if scene_key(scene_id)[0] == chapter}
    candidates = [os.path.join(project_dir, prefix, name)
                  for prefix in ("", "plot", "memory")
                  for name in ("05_chapter_outline.md", "05_chapter_outline_100k.md")]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for match in re.finditer(r"(?m)^\s*\|\s*([1-9]\d*-[1-9]\d*)\s*\|", text):
                scene_id = match.group(1)
                if scene_key(scene_id)[0] == chapter:
                    expected.add(scene_id)
            break
    return expected


def _validate_source(project_dir, source, scene_paths, approvals):
    full, relative = _safe_source_path(project_dir, source["path"])
    scene_id = _scene_from_path(relative)
    if source.get("scene_id", scene_id) != scene_id:
        raise UserFacingError("source scene_id does not match canonical path")
    if len(scene_paths.get(scene_id, [])) != 1:
        raise UserFacingError("source scene identity is missing or ambiguous: %s" % scene_id)
    if not os.path.isfile(full):
        raise UserFacingError("source does not exist: %s" % relative)
    if text_content_hash(full) != source["content_hash"]:
        raise UserFacingError("source hash changed: %s" % relative)
    with open(full, encoding="utf-8") as handle:
        line_count = len(handle.read().splitlines())
    if source["line_end"] > line_count:
        raise UserFacingError("source line range exceeds text: %s" % relative)
    approval = approvals.get(scene_id)
    if not isinstance(approval, dict):
        raise UserFacingError("source approval is missing: %s" % scene_id)
    approval_path = approval.get("source_path", approval.get("scene_path", ""))
    approved_full, _ = _safe_source_path(project_dir, approval_path)
    if approved_full != full:
        raise UserFacingError("source approval path does not match: %s" % scene_id)
    current = validate_approval_current(project_dir, approval)
    if current.get("status") != "approved":
        raise UserFacingError("source approval is not current: %s (%s)" % (scene_id, "; ".join(current.get("reasons", []))))
    return dict(source, path=relative, scene_id=scene_id)


def _references(record, include_supersedes=True):
    refs = list(record["supersedes"]) if include_supersedes else []
    if record["kind"] == "character_knowledge":
        refs.append(record["fact_id"])
    return refs


def _validate_graph(records):
    visiting, finished = set(), set()
    def visit(record_id):
        if record_id in visiting:
            raise UserFacingError("memory reference/supersedes cycle: %s" % record_id)
        if record_id in finished:
            return
        visiting.add(record_id)
        record = records[record_id]
        for ref in _references(record):
            if ref not in records:
                raise UserFacingError("unknown memory reference: %s -> %s" % (record_id, ref))
            visit(ref)
        if record["kind"] == "character_knowledge" and records[record["fact_id"]]["kind"] != "fact":
            raise UserFacingError("character_knowledge fact_id must reference a fact")
        visiting.remove(record_id)
        finished.add(record_id)
    for record_id in records:
        visit(record_id)


def _temporal_max(record_id, records, cache):
    if record_id not in cache:
        record = records[record_id]
        keys = [scene_key(record["available_after_scene"])]
        keys += [scene_key(_scene_from_path(source["path"])) for source in record["sources"]]
        keys += [scene_key(scene_id) for scene_id in record.get("covered_scenes", [])]
        keys += [_temporal_max(ref, records, cache) for ref in _references(record)]
        cache[record_id] = max(keys)
    return cache[record_id]


def load_memory(project_dir):
    path = memory_path(project_dir)
    payload = read_json(path, default_factory=lambda: {"version": 1, "revision": 0, "records": []})
    try:
        if type(payload.get("version")) is not int or payload["version"] != 1:
            raise UserFacingError("unsupported memory version")
        if type(payload.get("revision")) is not int or payload["revision"] < 0 or not isinstance(payload.get("records"), list):
            raise UserFacingError("invalid memory revision/records")
        records = {}
        for record in payload["records"]:
            _schema(record)
            if record["id"] in records:
                raise UserFacingError("duplicate memory ID: %s" % record["id"])
            records[record["id"]] = record
        _validate_graph(records)
    except UserFacingError as exc:
        raise DataCorruptionError("invalid memory %s: %s; restore or repair this file" % (path, exc))
    return payload


def validate_proposal(project_dir, payload):
    errors, warnings, normalized = [], ["Pointers and approval validated only; semantic support requires human/agent review."], []
    try:
        if not isinstance(payload, dict) or type(payload.get("version")) is not int or payload["version"] != 1:
            raise UserFacingError("unsupported proposal version")
        _proposal_path(project_dir, payload.get("batch_id"))
        if not isinstance(payload.get("records"), list) or not payload["records"]:
            raise UserFacingError("proposal records must be a nonempty list")
        existing = {r["id"]: r for r in load_memory(project_dir)["records"]}
        paths = _scene_paths(project_dir)
        approvals = read_approval_ledger(project_dir)["scenes"]
        seen = set()
        for original in payload["records"]:
            _schema(original)
            record = copy.deepcopy(original)
            record_id = record["id"]
            if record_id in seen:
                raise UserFacingError("duplicate proposal ID: %s" % record_id)
            seen.add(record_id)
            record["sources"] = [_validate_source(project_dir, s, paths, approvals) for s in record["sources"]]
            source_scenes = {s["scene_id"] for s in record["sources"]}
            if record["kind"] == "scene_outcome" and record["scene_id"] not in source_scenes:
                raise UserFacingError("scene_outcome must cite its scene")
            if record["kind"] in {"chapter_summary", "part_summary"}:
                if not set(record["covered_scenes"]).issubset(source_scenes):
                    raise UserFacingError("summary requires a source for every covered scene")
                if record["kind"] == "chapter_summary":
                    expected = _chapter_expected_scenes(project_dir, record["chapter"], paths)
                    if expected - set(record["covered_scenes"]):
                        warnings.append("%s: partial chapter summary" % record_id)
                else:
                    warnings.append("%s: partial part summary; full part membership is not asserted" % record_id)
            if record_id in existing and record != existing[record_id]:
                raise ConflictError("memory ID already has different content: %s; use a new ID and supersedes" % record_id)
            normalized.append(record)
        all_records = dict(existing)
        all_records.update({r["id"]: r for r in normalized})
        _validate_graph(all_records)
        temporal = {}
        for record in normalized:
            if record["kind"] == "character_knowledge":
                referenced_fact = all_records[record["fact_id"]]
                for source in referenced_fact["sources"]:
                    try:
                        _validate_source(project_dir, source, paths, approvals)
                    except (UserFacingError, OSError) as exc:
                        raise UserFacingError("referenced fact is stale: %s (%s)" % (record["fact_id"], exc))
            required = _temporal_max(record["id"], all_records, temporal)
            if scene_key(record["available_after_scene"]) < required:
                raise UserFacingError("available_after_scene precedes source or referenced memory: %s" % record["id"])
    except (UserFacingError, OSError) as exc:
        errors.append(str(exc))
    return {"valid": not errors, "errors": errors, "warnings": warnings, "records": normalized if not errors else []}


def _validated(project_dir, payload):
    result = validate_proposal(project_dir, payload)
    if not result["valid"]:
        raise UserFacingError("invalid memory proposal: " + "; ".join(result["errors"]))
    return dict(payload, records=result["records"])


def import_proposal(project_dir, payload):
    with project_lock(project_dir):
        normalized = _validated(project_dir, payload)
        path = _proposal_path(project_dir, normalized["batch_id"])
        if os.path.exists(path):
            existing = read_json(path, default_factory=dict)
            if existing != normalized:
                raise ConflictError("proposal batch already has different content: %s" % normalized["batch_id"])
        else:
            atomic_write_json(path, normalized)
        return {"batch_id": normalized["batch_id"], "status": "proposed", "path": path, "records": normalized["records"]}


def accept_proposal(project_dir, *, batch_id, expected_revision):
    # Public operations own one lock. CLIs deliberately do not acquire it again.
    with project_lock(project_dir):
        memory = load_memory(project_dir)
        if type(expected_revision) is not int or memory["revision"] != expected_revision:
            raise ConflictError("memory revision changed: expected %s, current %s" % (expected_revision, memory["revision"]))
        path = _proposal_path(project_dir, batch_id)
        if not os.path.isfile(path):
            raise UserFacingError("proposal batch not found: %s" % batch_id)
        proposal_payload = read_json(path, default_factory=dict)
        if proposal_payload.get("batch_id") != batch_id:
            raise UserFacingError("proposal batch identity mismatch")
        payload = _validated(project_dir, proposal_payload)
        ids = {r["id"] for r in memory["records"]}
        new_records = [r for r in payload["records"] if r["id"] not in ids]
        if not new_records:
            return memory
        updated = dict(memory, revision=memory["revision"] + 1, records=memory["records"] + new_records)
        atomic_write_json(memory_path(project_dir), updated)
        return updated


def memory_status(project_dir, *, as_of_scene_id=None):
    memory = load_memory(project_dir)
    records = {r["id"]: r for r in memory["records"]}
    paths = _scene_paths(project_dir)
    approvals = read_approval_ledger(project_dir)["scenes"] if records else {}
    temporal, status = {}, {}
    target_key = scene_key(as_of_scene_id) if as_of_scene_id else None
    def derive(record_id):
        if record_id in status:
            return status[record_id]
        record = records[record_id]
        reasons = []
        for source in record["sources"]:
            try:
                _validate_source(project_dir, source, paths, approvals)
            except (UserFacingError, OSError) as exc:
                reasons.append(str(exc))
        for ref in _references(record, include_supersedes=False):
            referenced = derive(ref)
            if referenced["status"] == "stale":
                reasons.append("referenced fact is stale: %s" % ref)
        state = "stale" if reasons else "active"
        if target_key and _temporal_max(record_id, records, temporal) >= target_key:
            state = "future"
            reasons.append("not available before target scene %s" % as_of_scene_id)
        item = dict(record, status=state, reasons=reasons)
        if record["kind"] in {"chapter_summary", "part_summary"}:
            expected = (_chapter_expected_scenes(project_dir, record["chapter"], paths)
                        if record["kind"] == "chapter_summary" else set())
            item["coverage"] = "complete" if expected and expected <= set(record["covered_scenes"]) else "partial"
        status[record_id] = item
        return item
    for record_id in records:
        derive(record_id)
    # Only replacements eligible at this time hide their predecessors. Staleness
    # of a corrected predecessor never invalidates the replacement itself.
    eligible = [item for item in status.values() if item["status"] == "active"]
    def predecessors(record_id):
        result = set(records[record_id]["supersedes"])
        for old_id in list(result):
            result.update(predecessors(old_id))
        return result
    for item in eligible:
        for old_id in predecessors(item["id"]):
            if status[old_id]["status"] == "active":
                status[old_id] = dict(status[old_id], status="superseded", reasons=["superseded by %s" % item["id"]])
    return {"version": 1, "revision": memory["revision"], "as_of_scene_id": as_of_scene_id,
            "records": [status[r["id"]] for r in memory["records"]]}


def write_memory_review(project_dir, *, batch_id=None):
    status = memory_status(project_dir)
    lines = ["# Story Memory Review", "", "Accepted revision: %s" % status["revision"],
             "Source pointers are checked, not semantic truth. Acceptance is explicit.", ""]
    if batch_id:
        path = _proposal_path(project_dir, batch_id)
        if not os.path.isfile(path):
            raise UserFacingError("proposal batch not found: %s" % batch_id)
        payload = read_json(path, default_factory=dict)
        validation = validate_proposal(project_dir, payload)
        lines += ["## Proposed batch: %s" % batch_id, "Valid: %s" % validation["valid"]]
        for record in payload.get("records", []):
            lines.append("- %s [%s]: %s" % (record.get("id"), record.get("kind"), record.get("text")))
        lines += ["- " + issue for issue in validation["errors"] + validation["warnings"]]
    lines.append("## Accepted records")
    for record in status["records"]:
        lines.append("- %s [%s]: %s" % (record["id"], record["status"], "; ".join(record["reasons"]) or record["text"]))
    runtime = os.path.join(project_dir, "runtime")
    atomic_write_json(os.path.join(runtime, "story_memory_status.json"), status)
    atomic_write_text(os.path.join(runtime, "memory_review.md"), "\n".join(lines) + "\n")
    return "\n".join(lines)
