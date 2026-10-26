"""Content-addressed dependencies on project originals, not mutable runtime views.

Specs use ``kind`` (``type`` is accepted as an input alias): file(path),
scene_set(target_scene_id, optional path), projection(selector, optional scene_id,
optional path), and artifact(path). Paths are project-relative POSIX paths in
snapshots. A projection's path is its diagnostic identity; the known selector
resolves its authoritative sources afresh. Snapshots themselves can be reused
as specs. No reader here changes a source or promotes a legacy artifact.
"""
import hashlib
import json
import os
import re

from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.storage import read_json, text_content_hash


_STATE_PATHS = ["agent/state_schema_novel.yaml", "state_schema_novel.yaml", "state/state_schema_novel.yaml"]
_OUTLINE_PATHS = [prefix + name for prefix in ("", "plot/", "memory/") for name in ("05_chapter_outline.md", "05_chapter_outline_100k.md")]
_GLOBAL_PATHS = ["agent/memory/global_notes.md", "memory/global_notes.md"]
_SESSION_PATHS = ["agent/memory/session_notes.md", "memory/session_notes.md"]
_SCENE_RE = re.compile(r"^(?:chapter_?(\d+)_scene_?(\d+)|scene_(\d+)-(\d+))\.txt$", re.IGNORECASE)
_SELECTORS = {"check_policy", "runtime_policy", "resume_progress", "memory_selection", "dialogue_selection", "keyframing_policy", "keyframing_selection"}
_HASH_ALGORITHM = "sha256-utf8-text-v1"


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def dependency_digest(records):
    """Hash a snapshot independent of caller order without mutating it."""
    if not isinstance(records, list):
        raise UserFacingError("dependency records must be a list")
    return _digest(sorted(records, key=_canonical_json))


def _path(project_dir, path):
    if not isinstance(path, str) or not path:
        raise UserFacingError("dependency path must be a nonempty string")
    root = os.path.realpath(project_dir)
    absolute = os.path.abspath(os.path.join(root, path))
    resolved = os.path.realpath(absolute)
    try:
        contained = os.path.commonpath([root, resolved]) == root
    except ValueError:
        contained = False
    if not contained:
        raise UserFacingError("dependency path escapes project: {}".format(path))
    return absolute, os.path.relpath(absolute, root).replace(os.sep, "/")


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _source(project_dir, candidates, *, skip_empty=False):
    for candidate in candidates:
        path, relative = _path(project_dir, candidate)
        if os.path.isfile(path):
            text = _read(path)
            if not skip_empty or text:
                return {"path": relative, "exists": True}, text
    if skip_empty:
        final_path, relative = _path(project_dir, candidates[-1])
        return {"path": relative, "exists": os.path.isfile(final_path)}, ""
    return {"path": candidates[0], "exists": False}, ""


def _scene_key(scene_id):
    if isinstance(scene_id, dict):
        scene_id = scene_id.get("canonical_id") or "{}-{}".format(scene_id.get("chapter"), scene_id.get("scene"))
    raw = str(scene_id or "")
    match = re.fullmatch(r"(\d+)-(\d+)", raw)
    if not match:
        match = re.fullmatch(r"(?:chapter_?)(\d+)_scene_?(\d+)(?:\.txt)?", raw, re.IGNORECASE)
    if not match or int(match.group(1)) < 1 or int(match.group(2)) < 1:
        raise UserFacingError("invalid dependency scene ID: {}".format(raw))
    return int(match.group(1)), int(match.group(2))


def _scene_id(key):
    return "{}-{}".format(*key)


def _scene_members(project_dir, directory=".", before=None, only=None):
    absolute, _ = _path(project_dir, directory)
    members = []
    seen = {}
    for root, dirs, files in os.walk(absolute):
        # Generated backups/indexes are not authored scene candidates.
        dirs[:] = sorted(name for name in dirs if name not in {".git", "runtime", "story_memory", "__pycache__"})
        for name in sorted(files):
            match = _SCENE_RE.match(name)
            if not match:
                continue
            key = (int(match.group(1) or match.group(3)), int(match.group(2) or match.group(4)))
            if (before is not None and key >= before) or (only is not None and key not in only):
                continue
            path, relative = _path(project_dir, os.path.join(root, name))
            if key in seen:
                raise UserFacingError("ambiguous duplicate scene {}: {}, {}".format(_scene_id(key), seen[key], relative))
            seen[key] = relative
            members.append({"scene_id": _scene_id(key), "path": relative, "content_hash": text_content_hash(path)})
    return sorted(members, key=lambda item: (_scene_key(item["scene_id"]), item["path"]))


def _state_sections(text):
    """Select bounded YAML sections without depending on a third-party parser.

    Keep nested values as text, since arbitrary user YAML must not be rewritten
    or guessed. Comments and blank lines do not affect these projections.
    """
    sections = {}
    current = ""
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][\w-]*):", line)
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
        if current:
            sections[current].append(line.rstrip())
    return {key: "\n".join(lines) for key, lines in sections.items()}


def _integer(value):
    match = re.search(r"[\d,]+", str(value or ""))
    return int(match.group(0).replace(",", "")) if match else 0


def _scene_plan(outline, key):
    match = re.search(r"(?ms)^#{1,6}\s*第" + str(key[0]) + r"章[^\n]*\n.*?(?=^#{1,6}\s*第\d+章|\Z)", outline)
    if not match:
        return {}
    header = None
    in_ledger = False
    for line in match.group(0).splitlines():
        stripped = line.strip()
        if stripped.startswith("### Scene Ledger"):
            in_ledger, header = True, None
            continue
        if not in_ledger:
            continue
        if not stripped:
            if header:
                break
            continue
        if stripped.startswith("#"):
            break
        if not stripped.startswith("|") or not stripped.endswith("|"):
            if header:
                break
            continue
        cells = [part.strip() for part in stripped.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if header is None:
            header = cells
            continue
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        raw_id = row.get("scene_id", "")
        if raw_id.isdigit():
            raw_id = "{}-{}".format(key[0], raw_id)
        try:
            row_key = _scene_key(raw_id)
        except UserFacingError:
            continue
        if row_key == key:
            return row
    return {}


def _length_band(plan, state):
    scene_type = plan.get("scene_type", "") or "default"
    band = {"scene_type": scene_type, "min": 1000, "target": 1250, "max": 1500}
    explicit = {name: _integer(plan.get(name)) for name in ("min", "target", "max")}
    if all(explicit.values()):
        band.update(explicit)
        return band
    in_bands = False
    current = ""
    for line in state.splitlines():
        if not in_bands:
            if re.match(r"^\s*scene_type_bands:\s*$", line):
                in_bands = True
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= 2:
            break
        if indent == 4 and line.strip().endswith(":"):
            current = line.strip()[:-1]
        elif current == scene_type and indent > 4 and ":" in line:
            name, value = line.strip().split(":", 1)
            if name in ("min", "target", "max"):
                band[name] = _integer(value)
    return band


def _style_contract(global_notes, state, band):
    # State projections must not depend on the progress/status they produce.
    ignored = {"active_work", "progress", "project", "recent_decisions", "open_questions", "continuity_watch"}
    state_text = "\n".join(value for key, value in _state_sections(state).items() if key not in ignored)
    combined = "\n".join(part for part in (global_notes, state_text) if part)

    def labeled(labels, default):
        for label in labels:
            match = re.search(label + r"\s*[:：]\s*(.+)", combined)
            if match:
                return match.group(1).strip()
        return default

    def matching(keywords, defaults):
        result = [line.strip().lstrip("- ").strip() for line in combined.splitlines()
                  if line.strip() and not line.strip().startswith("#") and any(word in line for word in keywords)]
        return result or defaults

    viewpoint = labeled(["視点", "POV", "pov", "point_of_view"], "未指定（既定: 一人称または近接三人称を固定）")
    tense = labeled(["地の文時制", "時制", "tense", "narration_tense"], "未指定（既定: 地の文は過去形で統一）")
    tone = matching(["口調", "語尾", "敬語", "文体", "台詞", "会話"], ["主要キャラの語尾と話し方を固定する", "台詞と地の文で温度差を作りすぎない"])
    forbidden = matching(["禁止", "avoid", "forbid"], ["見出しや箇条書きの混入", "作者視点のメタ説明", "直前シーンと矛盾する設定変更"])
    return "\n".join(["# Style Contract Compact", "- 視点: " + viewpoint, "- 地の文時制: " + tense,
                      "- 口調ルール:"] + ["  - " + item for item in tone] + ["- 禁止表現:"] +
                     ["  - " + item for item in forbidden] + ["- 文字数契約:",
                      "  - 初稿: {min} / {target} / {max} 字（min/target/max）".format(**band)])


def _split_values(raw):
    return [part.strip() for part in str(raw or "").replace(" / ", "/").replace("、", "/").split("/") if part.strip() and part.strip() != "-"]


def current_check_policy(project_dir, scene_id, *, participants=None, pov_character_id=None, _legacy=False):
    """Recompute effective checking conditions from outline/state/style originals.

    ``style_contract`` is compact text, ``length_band`` has scene_type/min/target/
    max, and ``obligation_contract`` follows the existing version-1 contract.
    Required scene sources include content and membership (including absence).
    """
    key = _scene_key(scene_id)
    scene_id = _scene_id(key)
    outline_source, outline = _source(project_dir, _OUTLINE_PATHS)
    state_source, state = _source(project_dir, _STATE_PATHS)
    global_source, global_notes = _source(project_dir, _GLOBAL_PATHS)
    plan = _scene_plan(outline, key)
    band = _length_band(plan, state)
    dependencies = []
    for raw in _split_values(plan.get("depends_on")):
        try:
            normalized = _scene_id(_scene_key(raw))
        except UserFacingError:
            continue
        dependencies.append(normalized)
    payoff = plan.get("payoff_or_seed", "").replace("回収:", "").replace("種:", "").replace("種まき:", "")
    contract = {"version": 1, "scene_id": scene_id, "must_hit_now": _split_values(plan.get("purpose")),
                "must_preserve": [], "required_payoff_touches": _split_values(payoff),
                "required_dependencies": dependencies, "can_defer": [], "forbidden_crossings": []}
    members = _scene_members(project_dir, only={_scene_key(value) for value in dependencies}) if dependencies else []
    voice_source, voice_text = _source(project_dir, ["dialogue_voice.json"])
    sources = [outline_source, state_source, global_source] + ([voice_source] if voice_source["exists"] else [])
    return {**({"dialogue_voice_hash": _voice_hash(project_dir, scene_id, voice_text, legacy=_legacy, participants=participants, pov_character_id=pov_character_id)} if voice_source["exists"] else {}),
            "scene_id": scene_id, "length_band": band,
            "style_contract": _style_contract(global_notes, state, band),
            "state_style_contract": _state_sections(state).get("style_contract", ""),
            "obligation_contract": contract,
            "required_dependencies": [{"scene_id": value, "members": [member for member in members if member["scene_id"] == value]} for value in dependencies],
            "source_paths": [source["path"] for source in sources], "sources": sources}


def _outline_policy(outline):
    """Keep original planning prose and columns except derived ledger status."""
    lines = []
    in_ledger = False
    header = None
    for line in outline.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Scene Ledger"):
            in_ledger, header = True, None
        elif stripped.startswith("#") or (not stripped and header):
            in_ledger, header = False, None
        if in_ledger and stripped.startswith("|") and stripped.endswith("|"):
            cells = [part.strip() for part in stripped.strip("|").split("|")]
            if header is None:
                header = cells
            elif len(cells) == len(header) and "status" in header:
                cells[header.index("status")] = ""
                line = "| " + " | ".join(cells) + " |"
        lines.append(line)
    return "\n".join(lines)


def _planning_scalars(state):
    fields = ("planning_gate_status", "planned_total_min_chars", "planned_total_target_chars", "planned_scene_count")
    result = {}
    for field in fields:
        match = re.search(r"(?m)^[ \t]*" + field + r":[ \t]*(.*)$", state)
        result[field] = match.group(1).strip() if match else ""
    return result


def _voice_hash(project_dir, scene_id, voice_text, *, legacy=False, participants=None, pov_character_id=None):
    if legacy:
        return _digest(voice_text)
    from novel_agent.dialogue_context import dialogue_dependency_value
    return _digest(dialogue_dependency_value(project_dir, scene_id=scene_id,
                   participants=participants, pov_character_id=pov_character_id))


def _projection(project_dir, selector, scene_id, path=None, *, legacy=True, participants=None, pov_character_id=None,
                projection_version=2, enabled_override=None, reason_override=None):
    if selector == "keyframing_policy":
        from novel_agent.narrative_keyframes import keyframing_policy_value
        return keyframing_policy_value(project_dir, scene_id=scene_id,
                                      enabled_override=enabled_override, disable_reason=reason_override)
    if selector == "keyframing_selection":
        absolute, relative = _path(project_dir, path)
        payload = read_json(absolute, default_factory=dict)
        return {"exists": os.path.isfile(absolute), "selection": {key: payload.get(key) for key in
                ("version", "config", "dialogue", "keyframing")}, "source_paths": [relative]}
    if selector == "dialogue_selection":
        absolute, relative = _path(project_dir, path)
        payload = read_json(absolute, default_factory=dict)
        return {"exists": os.path.isfile(absolute), "dialogue": payload.get("dialogue"),
                "source_paths": [relative]}
    if selector == "memory_selection":
        absolute, relative = _path(project_dir, path)
        payload = read_json(absolute, default_factory=dict)
        # Final prompt reports are derived output; they must not change inputs.
        return {"exists": os.path.isfile(absolute),
                "selection": {key: payload.get(key) for key in
                              (("version", "config", "memory", "dialogue", "keyframing") if projection_version == 3 else
                               ("version", "config", "memory", "dialogue") if "dialogue" in payload
                               else ("version", "config", "memory"))},
                "source_paths": [relative]}
    if selector == "check_policy":
        return current_check_policy(project_dir, scene_id, participants=participants, pov_character_id=pov_character_id, _legacy=legacy)
    state_source, state = _source(project_dir, _STATE_PATHS)
    sections = _state_sections(state)
    if selector == "resume_progress":
        return {"progress": sections.get("progress", ""), "active_work": sections.get("active_work", ""),
                "sources": [state_source], "source_paths": [state_source["path"]]}
    global_source, global_notes = _source(project_dir, _GLOBAL_PATHS)
    session_source, session_notes = _source(project_dir, _SESSION_PATHS, skip_empty=True)
    outline_source, outline = _source(project_dir, _OUTLINE_PATHS)
    voice_source, voice_text = _source(project_dir, ["dialogue_voice.json"])
    sources = [state_source, global_source, session_source, outline_source] + ([voice_source] if voice_source["exists"] else [])
    return {**({"dialogue_voice_hash": _voice_hash(project_dir, scene_id, voice_text, legacy=legacy, participants=participants, pov_character_id=pov_character_id)} if voice_source["exists"] else {}),
            "outline": _outline_policy(outline), "planning": _planning_scalars(state),
            "state": {name: sections.get(name, "") for name in ("targets", "profile", "style_contract", "story_constraints")},
            "global_notes": global_notes, "session_notes": session_notes,
            "sources": sources, "source_paths": [source["path"] for source in sources]}


class _Operation:
    """Read-only caches scoped to one snapshot/verification, never publication.

    Each public verify call starts afresh, including the final pre-write check.
    Expected records are never cached by path: distinct historical guards must
    each compare against current evidence. Only current observations are shared.
    """
    def __init__(self):
        self.artifacts = None
        self.snapshots = {}
        self.digests = {}
        self.fallbacks = {}

    def artifact_index(self, project_dir):
        if self.artifacts is None:
            ledger_path = os.path.join(project_dir, "runtime", "artifact_ledger.json")
            ledger = read_json(ledger_path, default_factory=lambda: {"artifacts": []})
            if not isinstance(ledger, dict):
                raise DataCorruptionError("invalid artifact ledger at {}".format(ledger_path))
            artifacts = ledger.get("artifacts", [])
            if not isinstance(artifacts, list) or any(not isinstance(item, dict) for item in artifacts):
                raise DataCorruptionError("invalid artifacts at {}".format(ledger_path))
            index = {}
            for item in artifacts:
                path = item.get("path")
                if not isinstance(path, str):
                    raise DataCorruptionError("invalid artifact path at {}".format(ledger_path))
                if path in index:
                    raise DataCorruptionError("duplicate artifact path at {}: {}".format(ledger_path, path))
                index[path] = item
            self.artifacts = index
        return self.artifacts

    def digest(self, inputs):
        key = id(inputs)
        if key not in self.digests:
            # Retain inputs: compact snapshots no longer keep fallback lists
            # alive, so id-only entries can alias a later decoded list.
            self.digests[key] = (inputs, dependency_digest(inputs))
        return self.digests[key][1]


def _artifact_dependencies(project_dir, relative, absolute, operation):
    payload = operation.artifact_index(project_dir).get(relative)
    if payload is None and relative.endswith(".json") and os.path.isfile(absolute):
        if relative not in operation.fallbacks:
            operation.fallbacks[relative] = read_json(absolute, default_factory=dict)
        payload = operation.fallbacks[relative]
    if payload is None:
        return None, None
    inputs = payload.get("dependencies", payload.get("inputs", payload.get("check_inputs")))
    digest = payload.get("dependency_digest", payload.get("inputs_digest", payload.get("check_inputs_digest")))
    if inputs is not None and not isinstance(inputs, list):
        raise DataCorruptionError("invalid artifact dependencies: {}".format(relative))
    if inputs is not None and digest is None:
        digest = operation.digest(inputs)
    return inputs, digest


def _snapshot_one(project_dir, spec, operation=None, *, legacy=False):
    operation = operation or _Operation()
    if not isinstance(spec, dict):
        raise UserFacingError("dependency spec must be an object")
    kind = spec.get("kind", spec.get("type"))
    if kind not in {"file", "scene_set", "projection", "artifact"}:
        raise UserFacingError("unknown dependency kind: {}".format(kind))
    default_path = "." if kind in {"scene_set", "projection"} else ""
    absolute, relative = _path(project_dir, spec.get("path", default_path))
    # Include every selector/scope field, but not historical snapshot values.
    cache_key = _canonical_json([kind, relative, spec.get("scope", "prior"),
                           spec.get("selector"), spec.get("scene_id"), spec.get("target_scene_id"), legacy,
                           spec.get("projection_version"), spec.get("participants"), spec.get("pov_character_id"),
                           spec.get("enabled_override"), spec.get("reason_override")])
    if cache_key in operation.snapshots:
        return operation.snapshots[cache_key]
    result = {"kind": kind, "path": relative}
    if kind in {"file", "artifact"}:
        if os.path.exists(absolute) and not os.path.isfile(absolute):
            raise UserFacingError("dependency is not a file: {}".format(relative))
        result.update({"exists": os.path.isfile(absolute), "content_hash": text_content_hash(absolute), "hash_algorithm": _HASH_ALGORITHM})
    if kind == "artifact":
        inputs, digest = _artifact_dependencies(project_dir, relative, absolute, operation)
        result.update({"dependency_digest": digest})
        if legacy:
            result["dependencies"] = inputs
        else:
            result["guard_version"] = 2
    elif kind == "scene_set":
        scope = spec.get("scope", "prior")
        if scope == "all":
            # Resume position depends on target existence and the global latest
            # scene, unlike past-only drafting context.
            result.update({"scope": "all", "members": _scene_members(project_dir, relative)})
        elif scope == "prior":
            key = _scene_key(spec.get("target_scene_id"))
            result.update({"target_scene_id": _scene_id(key), "members": _scene_members(project_dir, relative, before=key)})
        else:
            raise UserFacingError("unknown scene_set scope: {}".format(scope))
    elif kind == "projection":
        selector = spec.get("selector")
        if selector not in _SELECTORS:
            raise UserFacingError("unknown dependency projection: {}".format(selector))
        scene_id = spec.get("scene_id", spec.get("target_scene_id"))
        result["selector"] = selector
        if scene_id:
            result["scene_id"] = _scene_id(_scene_key(scene_id))
        projection_version = 1 if legacy else spec.get("projection_version", 2)
        if type(projection_version) is not int or projection_version not in (1, 2, 3):
            raise UserFacingError("unsupported projection version: {}".format(projection_version))
        if projection_version == 3 and selector not in {"memory_selection", "keyframing_policy", "keyframing_selection"}:
            raise UserFacingError("projection version 3 is only defined for keyframing inputs")
        if selector in {"keyframing_policy", "keyframing_selection"} and projection_version != 3:
            raise UserFacingError("keyframing projections require version 3")
        for field in ("participants", "pov_character_id", "enabled_override", "reason_override"):
            if field in spec:
                result[field] = spec[field]
        value = _projection(project_dir, selector, scene_id, path=relative,
                            legacy=projection_version == 1, participants=spec.get("participants"),
                            pov_character_id=spec.get("pov_character_id"), projection_version=projection_version,
                            enabled_override=spec.get("enabled_override"), reason_override=spec.get("reason_override"))
        result.update({"source_paths": value["source_paths"], "projection_hash": _digest(value)})
        if legacy:
            result["value"] = value
        else:
            result.update({"guard_version": 2, "projection_version": projection_version})
    operation.snapshots[cache_key] = result
    return result


def snapshot_dependencies(project_dir, specs):
    """Capture explicit source specs, including absent optional sources."""
    if not isinstance(specs, list):
        raise UserFacingError("dependency specs must be a list")
    operation = _Operation()
    unique = {}
    for spec in specs:
        record = _snapshot_one(project_dir, spec, operation)
        unique[_canonical_json(record)] = record
    return [unique[key] for key in sorted(unique)]



def compact_dependencies(records):
    """Remove redundant source values without resnapshotting or blessing changes.

    Legacy projections keep version-1 projection semantics. Artifact references
    retain the exact historical upstream digest and are verified via its ledger.
    """
    if not isinstance(records, list):
        raise UserFacingError("dependency records must be a list")
    result = []
    for record in records:
        if not isinstance(record, dict):
            raise UserFacingError("dependency record must be an object")
        item = dict(record)
        version = item.get("guard_version", 1)
        if type(version) is not int or version not in (1, 2):
            raise DataCorruptionError("unsupported dependency guard version")
        if version == 1 and ("guard_version" in item or "projection_version" in item):
            raise DataCorruptionError("noncanonical legacy dependency version")
        if item.get("kind") == "projection":
            projection_version = item.get("projection_version", 1 if version == 1 else 2)
            if type(projection_version) is not int or projection_version not in (1, 2, 3):
                raise DataCorruptionError("unsupported projection version")
            if projection_version == 3 and item.get("selector") not in {"memory_selection", "keyframing_policy", "keyframing_selection"}:
                raise DataCorruptionError("projection version 3 is only defined for keyframing inputs")
            if item.get("selector") in {"keyframing_policy", "keyframing_selection"} and projection_version != 3:
                raise DataCorruptionError("keyframing projections require version 3")
            if version == 2 and "value" in item:
                raise DataCorruptionError("unexpected value in compact projection")
            if "value" in item and _digest(item["value"]) != item.get("projection_hash"):
                raise DataCorruptionError("invalid legacy projection hash")
            item.pop("value", None)
            item.setdefault("projection_version", 1 if "guard_version" not in item else 2)
            item["guard_version"] = 2
        elif item.get("kind") == "artifact":
            if version == 2 and "dependencies" in item:
                raise DataCorruptionError("unexpected dependencies in compact artifact")
            inputs = item.pop("dependencies", None)
            if inputs is not None and dependency_digest(inputs) != item.get("dependency_digest"):
                raise DataCorruptionError("invalid legacy artifact dependency digest")
            item["guard_version"] = 2
        result.append(item)
    return result


def snapshot_check_policy(project_dir, scene_id, *, participants=None, pov_character_id=None):
    """Capture the effective policy and its compact guard from the same read."""
    scene_id = _scene_id(_scene_key(scene_id))
    value = current_check_policy(project_dir, scene_id, participants=participants, pov_character_id=pov_character_id)
    record = {"kind": "projection", "path": ".", "selector": "check_policy", "scene_id": scene_id,
              "guard_version": 2, "projection_version": 2,
              "source_paths": value["source_paths"], "projection_hash": _digest(value)}
    if participants is not None:
        record["participants"] = participants
    if pov_character_id is not None:
        record["pov_character_id"] = pov_character_id
    return record, value


def _verify(project_dir, records, ancestors, operation):
    if not isinstance(records, list):
        return [{"path": "", "reason": "invalid_dependency_records"}]
    changes = []
    for record in records:
        if not isinstance(record, dict):
            changes.append({"path": "", "reason": "invalid_dependency_record"})
            continue
        path = record.get("path", "")
        kind = record.get("kind", record.get("type"))
        identity = {"kind": kind, "path": path}
        try:
            guard_version = record.get("guard_version", 1)
            if type(guard_version) is not int or guard_version not in (1, 2):
                raise UserFacingError("unsupported dependency guard version")
            current = _snapshot_one(project_dir, record, operation, legacy=guard_version == 1)
        except UserFacingError as exc:
            changes.append(dict(identity, reason="dependency_unavailable", detail=str(exc)))
            continue
        if current != record:
            changes.append(dict(identity, reason="dependency_changed"))
        if kind == "artifact":
            if path in ancestors:
                changes.append(dict(identity, reason="cyclic_artifact_dependency"))
                continue
            absolute, relative = _path(project_dir, path)
            inputs, digest = _artifact_dependencies(project_dir, relative, absolute, operation)
            if inputs is None or digest is None:
                changes.append(dict(identity, reason="unverified_artifact_dependencies"))
            elif digest != operation.digest(inputs):
                changes.append(dict(identity, reason="invalid_artifact_dependency_digest"))
            else:
                for issue in _verify(project_dir, inputs, ancestors | {path}, operation):
                    changes.append(dict(identity, reason="artifact_dependency_changed", dependency=issue))
    return changes


def verify_dependencies(project_dir, records):
    """Return explicit stale/corrupt/unverified reasons; never hide bad evidence."""
    return _verify(project_dir, records, set(), _Operation())
