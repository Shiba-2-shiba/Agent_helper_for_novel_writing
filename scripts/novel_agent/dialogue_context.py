"""Explicit voice-only planning input; never mine freeform character biographies."""
import os
import re

from novel_agent.errors import UserFacingError
from novel_agent.storage import read_json

VOICE_PATH = "dialogue_voice.json"
MAX_DIALOGUE_CHARS = 3000
VOICE_FIELDS = ("response_goal", "word_choice", "rhythm", "relationship_stance")
GUIDANCE = """## Selective Dialogue / Limited POV
- 人物らしさは応答の目的、語の選び方、文のリズム、相手との距離から作る。口癖・語尾だけで代用しない。
- 意味のある応酬では、焦点人物が相手の声・言い方から何を受け取り、どう解釈し、迷い・言い直し・言わない選択が返答にどう影響するかを必要な分だけ描く。
- 相手の内心は断定しない。印象・推測・不確かさを焦点人物のものとして扱い、人物の知識と作者用設定を混ぜない。
- 選んだ主観素材は主に台詞ににじませる／地の文に出す。省略は両方が不自然・冗長・テンポを損なう場合だけ、両経路の具体的理由を残す。全ての台詞に心理説明を足さず、動作や描写量のノルマに置き換えない。
- カードは会話表現の設計資料であり、出来事・秘密・未来の展開を知っている証拠ではない。未設定の性格や関係を補作しない。"""


def _invalid(detail):
    raise UserFacingError("dialogue_voice.json: " + detail)


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 80 or any(c.isspace() for c in value):
        _invalid(label + " must be a nonempty ID (no whitespace, max 80 characters)")
    return value


def _participants(value, label):
    if not isinstance(value, list):
        _invalid(label + " must be a list of character IDs")
    return list(dict.fromkeys(_identifier(item, label) for item in value))


def _load(project_dir):
    payload = read_json(os.path.join(project_dir, VOICE_PATH), default_factory=lambda: {
        "version": 1, "characters": {}, "scenes": {}})
    if not isinstance(payload, dict) or set(payload) - {"version", "characters", "scenes"}:
        _invalid("expected version, characters, and optional scenes only")
    if type(payload.get("version")) is not int or payload["version"] != 1:
        _invalid("unsupported version (expected 1)")
    if not isinstance(payload.get("characters"), dict) or not isinstance(payload.get("scenes", {}), dict):
        _invalid("characters and scenes must be objects")
    for character_id, card in payload["characters"].items():
        _identifier(character_id, "character ID")
        if not isinstance(card, dict) or set(card) - set(("name",) + VOICE_FIELDS):
            _invalid("card " + character_id + ": only name and voice fields are permitted; no biography")
        if not isinstance(card.get("name"), str) or not card["name"].strip():
            _invalid("card " + character_id + ": name is required")
        for field, value in card.items():
            if not isinstance(value, str) or "\n" in value or "\r" in value:
                _invalid("card " + character_id + ": " + field + " must be single-line text")
        if not any(card.get(field, "").strip() for field in VOICE_FIELDS):
            _invalid("card " + character_id + ": at least one nonempty voice field is required")
    for scene_id, scene in payload.get("scenes", {}).items():
        if not re.fullmatch(r"[1-9]\d*-[1-9]\d*", scene_id):
            _invalid("invalid scene ID: " + scene_id)
        if not isinstance(scene, dict) or set(scene) - {"participants", "pov_character_id"}:
            _invalid("scene " + scene_id + ": expected participants and/or pov_character_id")
        if "participants" in scene:
            _participants(scene["participants"], "scene " + scene_id + " participants")
        if "pov_character_id" in scene and scene["pov_character_id"] is not None:
            _identifier(scene["pov_character_id"], "scene POV")
    return payload


def build_dialogue_context(project_dir, *, scene_id, participants=None, pov_character_id=None):
    """Return bounded text plus reproducible selection metadata and warnings.

    Explicit CLI participants replace scene participants, never infer them from
    POV, entity relevance or a full character sheet. A focal observer's own card
    is included even when they are not a speaking participant.
    """
    payload = _load(project_dir)
    scene = payload.get("scenes", {}).get(scene_id, {})
    selected = _participants(participants if participants is not None else scene.get("participants", []), "participants")
    pov = pov_character_id if pov_character_id is not None else scene.get("pov_character_id")
    if pov is not None:
        _identifier(pov, "POV")
    ids = list(dict.fromkeys(selected + ([pov] if pov else [])))
    warnings = []
    if participants is None and "participants" not in scene:
        warnings.append("dialogue participants not configured; set scenes.<scene>.participants or --participant (POV alone does not select interlocutors)")
    if pov is None:
        warnings.append("dialogue POV not configured; set pov_character_id or --pov-character; do not infer private knowledge")
    lines = ["# Dialogue Context Pack", "Scene ID: " + scene_id,
             "Participants: " + (", ".join(selected) or "(none selected)"),
             "POV: " + (pov or "unknown"), "", GUIDANCE, "", "## Selected voice cards (planning, not knowledge)"]
    for character_id in ids:
        card = payload["characters"].get(character_id)
        if card is None:
            warnings.append("dialogue voice card missing for " + character_id + "; add established voice facts to dialogue_voice.json; do not invent traits")
            continue
        lines.append("- " + character_id + " / " + card["name"])
        lines.extend("  " + field + ": " + card[field] for field in VOICE_FIELDS if card.get(field, "").strip())
    if not ids:
        lines.append("- No character cards selected; use existing explicit style notes only.")
    lines.extend("WARN: " + warning for warning in warnings)
    text = "\n".join(lines) + "\n"
    if len(text) > MAX_DIALOGUE_CHARS:
        raise UserFacingError("dialogue voice budget exceeded ({} > {} characters); shorten selected cards or review participants; no cards were silently dropped".format(len(text), MAX_DIALOGUE_CHARS))
    return {"text": text, "participants": selected, "pov_character_id": pov,
            "selected_character_ids": ids, "warnings": warnings,
            "source_path": VOICE_PATH, "max_chars": MAX_DIALOGUE_CHARS,
            "participants_source": "cli" if participants is not None else ("scene" if "participants" in scene else "missing"),
            "pov_source": "cli" if pov_character_id is not None else ("scene" if pov else "missing")}



def dialogue_dependency_value(project_dir, *, scene_id, participants=None, pov_character_id=None):
    """Project only the selected scene/voices, including missing selected cards.

    CLI overrides replace defaults in exactly the same way as the writer pack.
    Full config validation still rejects malformed explicit planning data.
    """
    payload = _load(project_dir)
    scene = payload.get("scenes", {}).get(scene_id, {})
    selected = _participants(participants if participants is not None else scene.get("participants", []), "participants")
    pov = pov_character_id if pov_character_id is not None else scene.get("pov_character_id")
    if pov is not None:
        _identifier(pov, "POV")
    ids = list(dict.fromkeys(selected + ([pov] if pov else [])))
    return {"exists": os.path.isfile(os.path.join(project_dir, VOICE_PATH)),
            "scene_configuration": payload.get("scenes", {}).get(scene_id),
            "participants": selected, "pov_character_id": pov,
            "participants_source": "cli" if participants is not None else ("scene" if "participants" in scene else "missing"),
            "pov_source": "cli" if pov_character_id is not None else ("scene" if pov else "missing"),
            "cards": {character_id: payload["characters"].get(character_id) for character_id in ids}}


def read_dialogue_pack(runtime_dir):
    """Legacy runtimes keep working, but cannot silently imply configured voices."""
    path = os.path.join(runtime_dir, "dialogue_context_pack.md")
    if not os.path.isfile(path):
        warning = "dialogue context pack missing (legacy runtime); prepare the same scene to route voice cards and participants"
        return GUIDANCE + "\nWARN: " + warning, warning
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if not text.strip():
        raise UserFacingError("dialogue context pack is empty; prepare the same scene")
    if len(text) > MAX_DIALOGUE_CHARS:
        raise UserFacingError("dialogue context pack exceeds budget; prepare with shorter selected cards")
    return text, ""
