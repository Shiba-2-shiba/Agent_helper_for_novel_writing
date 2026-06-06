import json
import os

from prompt_utils import (
    UserFacingError,
    find_scene_file,
    parse_scene_reference,
    read_text_file,
    write_json_file,
)


def _split_values(raw_value):
    text = str(raw_value or "").strip()
    if not text or text == "-":
        return []
    parts = []
    for chunk in text.replace(" / ", "/").replace("、", "/").split("/"):
        cleaned = chunk.strip()
        if cleaned and cleaned != "-":
            parts.append(cleaned)
    return parts


def build_obligation_contract(scene_ref, scene_plan):
    scene_id = scene_ref["canonical_id"]
    if not scene_plan:
        return {
            "version": 1,
            "scene_id": scene_id,
            "must_hit_now": [],
            "must_preserve": [],
            "required_payoff_touches": [],
            "required_dependencies": [],
            "can_defer": [],
            "forbidden_crossings": [],
        }

    required_dependencies = []
    for dependency in _split_values(scene_plan.get("depends_on", "")):
        try:
            required_dependencies.append(parse_scene_reference(dependency)["canonical_id"])
        except UserFacingError:
            continue

    payoff_or_seed = scene_plan.get("payoff_or_seed", "")
    payoff_touches = []
    if payoff_or_seed and payoff_or_seed != "-":
        payoff_touches = _split_values(
            payoff_or_seed.replace("回収:", "").replace("種:", "").replace("種まき:", "")
        )

    return {
        "version": 1,
        "scene_id": scene_id,
        "must_hit_now": _split_values(scene_plan.get("purpose", "")),
        "must_preserve": [],
        "required_payoff_touches": payoff_touches,
        "required_dependencies": required_dependencies,
        "can_defer": [],
        "forbidden_crossings": [],
    }


def write_obligation_contract(path, contract):
    write_json_file(path, contract)
    return path


def load_obligation_contract(path):
    if not os.path.isfile(path):
        return None
    try:
        payload = json.loads(read_text_file(path))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    payload.setdefault("required_dependencies", [])
    payload.setdefault("must_hit_now", [])
    payload.setdefault("required_payoff_touches", [])
    payload.setdefault("forbidden_crossings", [])
    return payload


def format_obligation_contract(contract):
    def values(name):
        items = contract.get(name, [])
        return ", ".join(items) if items else "-"

    return "\n".join(
        [
            "## Obligation Contract",
            f"- must_hit_now: {values('must_hit_now')}",
            f"- must_preserve: {values('must_preserve')}",
            f"- required_payoff_touches: {values('required_payoff_touches')}",
            f"- required_dependencies: {values('required_dependencies')}",
            f"- can_defer: {values('can_defer')}",
            f"- forbidden_crossings: {values('forbidden_crossings')}",
        ]
    )


def check_obligations(project_dir, contract, scene_type=""):
    if not contract:
        return {
            "status": "not_available",
            "blocking_issues": [],
            "warnings": [],
        }

    blocking = []
    warnings = []
    for dependency in contract.get("required_dependencies", []) or []:
        dependency_ref = parse_scene_reference(dependency)
        dependency_path = find_scene_file(project_dir, dependency_ref)
        if not dependency_path:
            blocking.append(
                {
                    "type": "missing_required_dependency",
                    "message": "required dependency scene text is missing",
                    "dependency": dependency,
                }
            )

    if scene_type in {"anchor", "climax"} and not contract.get("must_hit_now"):
        warnings.append(
            {
                "type": "empty_must_hit_now",
                "message": "anchor/climax scene has no explicit must_hit_now obligation",
            }
        )

    if blocking:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    return {
        "status": status,
        "blocking_issues": blocking,
        "warnings": warnings,
    }

