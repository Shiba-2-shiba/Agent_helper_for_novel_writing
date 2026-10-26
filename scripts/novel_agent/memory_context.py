"""Reading-order, explicit POV, and deterministic character-budget selection."""
from novel_agent.errors import UserFacingError
from novel_agent.story_memory import memory_status, scene_key

DEFAULT_PROMPT_CHARS = 16000
DEFAULT_MEMORY_CHARS = 6000
DEFAULT_PREVIOUS_CHARS = 4000


def _pointer(source):
    return "%s:%s-%s" % (source["path"], source["line_start"], source["line_end"])


def _record_text(record):
    coverage = " [%s]" % record["coverage"] if "coverage" in record else ""
    text = record["text"]
    sources = list(record["sources"])
    if record["kind"] == "character_knowledge" and record.get("known_fact"):
        known = record["known_fact"]
        text += "\n  Known fact [%s]: %s" % (known["id"], known["text"])
        sources.extend(known["sources"])
    return "- [%s / %s]%s %s\n  sources: %s" % (
        record["id"], record["kind"], coverage, text,
        "; ".join(dict.fromkeys(_pointer(source) for source in sources)))


def render_memory_pack(selection):
    lines = ["# Story Memory Pack", "", "Accepted, current sources before target scene only. Not planning.",
             "Author facts are not automatically known to the POV character.", "", "## author_context"]
    lines.extend(_record_text(record) for record in selection["author_records"])
    if not selection["author_records"]:
        lines.append("- No eligible accepted author records.")
    lines.extend(["", "## pov_context"])
    if selection.get("pov_character_id") is None:
        lines.append("- 知識未確定: POV character not specified; no character knowledge inferred.")
    else:
        lines.append("POV: " + selection["pov_character_id"])
        lines.extend(_record_text(record) for record in selection["pov_records"])
        if not selection["pov_records"]:
            lines.append("- No explicitly accepted knowledge for this POV.")
    return "\n".join(lines) + "\n"


def _omitted(record, reason):
    return {"id": record["id"], "source_ids": [record["id"]], "sources": record["sources"], "reason": reason}


def select_memory(project_dir, *, target_scene_id, pov_character_id, entity_ids, thread_ids, max_chars=DEFAULT_MEMORY_CHARS):
    if type(max_chars) is not int or max_chars < 1:
        raise UserFacingError("memory character budget must be positive")
    status = memory_status(project_dir, as_of_scene_id=target_scene_id)
    selection = {"target_scene_id": target_scene_id, "pov_character_id": pov_character_id,
                 "author_records": [], "pov_records": [], "omitted": [], "warnings": [],
                 "dependencies": ["story_memory/accepted.json", "runtime/approval_ledger.json"],
                 "max_chars": max_chars, "revision": status["revision"]}
    if pov_character_id is None:
        selection["warnings"].append("知識未確定: POV character not specified")
    if max(len(render_memory_pack(selection)), _memory_section_chars(selection)) > max_chars:
        raise UserFacingError("memory character budget cannot contain required labels")
    records = {r["id"]: r for r in status["records"]}
    latest_threads = {}
    for record in status["records"]:
        selection["dependencies"].extend(s["path"] for s in record["sources"])
        if record["status"] == "active" and record["kind"] == "thread_event":
            old = latest_threads.get(record["thread_id"])
            key = (scene_key(record["available_after_scene"]), record["id"])
            if old is None or key > (scene_key(old["available_after_scene"]), old["id"]):
                latest_threads[record["thread_id"]] = record
    candidates = []
    for record in status["records"]:
        reason, destination = None, "author_records"
        if record["status"] != "active":
            reason = record["status"] + ": " + "; ".join(record["reasons"])
        elif record["kind"] == "character_knowledge":
            destination = "pov_records"
            if record["character_id"] != pov_character_id:
                reason = "different or unspecified POV"
            elif records[record["fact_id"]]["status"] != "active":
                reason = "referenced fact is not active at target"
        elif record["kind"] == "thread_event":
            if latest_threads[record["thread_id"]]["id"] != record["id"]:
                reason = "earlier thread event"
            elif record["event"] in {"resolved", "abandoned"} and record["thread_id"] not in thread_ids:
                reason = "closed thread, not explicitly requested"
        if reason:
            selection["omitted"].append(_omitted(record, reason))
            continue
        explicit = bool(set(record["entity_ids"]) & set(entity_ids)) or record.get("thread_id") in thread_ids
        priority = 0 if explicit else {"character_knowledge": 1, "thread_event": 2, "scene_outcome": 3,
                                     "chapter_summary": 4, "part_summary": 4, "fact": 5}[record["kind"]]
        chapter, scene = scene_key(record["available_after_scene"])
        candidates.append((priority, -chapter, -scene, record["id"], destination, record))
    for priority, _, _, _, destination, record in sorted(candidates):
        record = dict(record, context_priority=priority)
        if destination == "pov_records":
            known = records[record["fact_id"]]
            record["known_fact"] = {key: known[key] for key in ("id", "text", "sources")}
        selection[destination].append(record)
        if max(len(render_memory_pack(selection)), _memory_section_chars(selection)) > max_chars:
            selection[destination].pop()
            selection["omitted"].append(_omitted(record, "memory character budget"))
    selection["dependencies"] = sorted(set(selection["dependencies"]))
    selection["chars"] = max(len(render_memory_pack(selection)), _memory_section_chars(selection))
    return selection


def _section_info(section, reason=None):
    result = {"name": section["name"], "source_ids": list(section.get("source_ids", [])),
              "sources": list(section.get("sources", [])), "chars": len(section["text"]),
              "required": bool(section.get("required"))}
    if reason:
        result["reason"] = reason
    return result


def assemble_prompt(sections, *, max_chars=DEFAULT_PROMPT_CHARS):
    if type(max_chars) is not int or max_chars < 1:
        raise UserFacingError("prompt character budget must be positive")
    ordered = sorted(enumerate(sections), key=lambda pair: (pair[1].get("priority", 0), pair[0]))
    def render(selected):
        selected_ids = {index for index, _ in selected}
        return "\n\n".join(section["text"] for index, section in ordered if index in selected_ids and section["text"]) + "\n"
    selected = [(index, section) for index, section in ordered if section.get("required")]
    required_chars = len(render(selected))
    if required_chars > max_chars:
        breakdown = ", ".join("%s=%s" % (s["name"], len(s["text"])) for _, s in selected)
        raise UserFacingError("required prompt sections exceed budget: %s > %s characters (%s)" % (required_chars, max_chars, breakdown))
    omitted = []
    for index, section in ordered:
        if section.get("required"):
            continue
        if len(render(selected + [(index, section)])) <= max_chars:
            selected.append((index, section))
        else:
            omitted.append(_section_info(section, "final prompt character budget"))
    prompt = render(selected)
    selected_ids = {index for index, _ in selected}
    return {"prompt": prompt, "selected": [_section_info(s) for i, s in ordered if i in selected_ids],
            "omitted": omitted, "chars": len(prompt), "max_chars": max_chars}


def memory_prompt_sections(selection):
    """Keep optional memories individually omittable in the final prompt."""
    header = "# Story Memory Pack\nAccepted, current sources before target only; not planning.\nAuthor facts are not automatically POV knowledge."
    header += "\n\n## author_context\nOnly records explicitly labeled author_context below are author facts."
    header += "\n\n## pov_context"
    if selection.get("pov_character_id") is None:
        header += "\n知識未確定: no POV knowledge inferred."
    else:
        header += "\nPOV: " + selection["pov_character_id"]
        if not selection["pov_records"]:
            header += "\nNo explicitly accepted knowledge for this POV."
        else:
            header += "\nOnly records explicitly labeled pov_context below are known to this POV."
    sections = [{"name": "story_memory_labels", "text": header.rstrip(), "required": True,
                 "priority": 1, "source_ids": []}]
    for group, label in (("pov_records", "pov_context"), ("author_records", "author_context")):
        for record in selection[group]:
            priority = 2 if group == "pov_records" else {"thread_event": 3, "scene_outcome": 4,
                         "chapter_summary": 5, "part_summary": 5, "fact": 2}.get(record["kind"], 5)
            sections.append({"name": "memory:" + record["id"], "text": "## " + label + "\n" + _record_text(record),
                             "required": False, "priority": record.get("context_priority", priority) + 2, "source_ids": [record["id"]],
                             "sources": record["sources"]})
    return sections


def _memory_section_chars(selection):
    sections = memory_prompt_sections(selection)
    return sum(len(s["text"]) for s in sections) + 2 * (len(sections) - 1) + 1
