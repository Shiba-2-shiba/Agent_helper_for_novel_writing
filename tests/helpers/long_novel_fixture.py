"""Synthetic long-novel fixture. This is not a literary-quality writing sample.

There are no fabricated checks, approvals, or accepted memories. Call the real
CLIs to create those records. Hashes cover the actual UTF-8 text, not a label.
"""
import hashlib
import json
from pathlib import Path

FIXTURE_REVISION = "long-novel-v1"
PAST_FACT = "青銅の鍵は北門だけを開く。"
PRIVATE_SECRET = "地下室の合言葉は琥珀の灯であり、葵だけが知っている。"
FUTURE_SECRET = "終幕限定語彙スピネルの王冠"
THREAD = "鐘楼から届いた差出人不明の手紙の謎は未解決だ。"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _scene_text(chapter, scene, size, inserts):
    opening = "第{}章の{}番目の朝、葵は石畳の角で立ち止まった。\n".format(chapter, scene)
    text = opening + "\n".join(inserts) + ("\n" if inserts else "")
    if len(text) > size:
        raise ValueError("chars_per_scene cannot hold the fixture's evidence")
    # Different paragraph lengths/endings exercise the real style check without
    # hiding warnings. Each scene has a unique marker and independent content.
    paragraphs = [
        "靴の先で小石が転がる。遠くの窓に鳥の影が映り、葵は鞄の紐を握り直した。",
        "「ここで待とう」透が壁際を指した。返事の代わりに葵はうなずく。荷車の音が通りを渡り、二人の間にしばし静けさが戻った。",
        "戸口には乾いた泥が残っていた。指で触れると薄い欠片が落ちたが、拾おうとした手は途中で止まる。",
        "水売りが樽を下ろす。木の底が石を打つ低い音に、向かいの店から老人が顔を出した。葵は一歩脇へ寄った。",
    ]
    index = 0
    while len(text) < size:
        block = "\n\n{}度目の足音を数えた。{}".format(index + 1, paragraphs[(index + chapter + scene) % len(paragraphs)])
        remaining = size - len(text)
        if len(block) > remaining:
            # Finish with plain narration, never half an open dialogue quote.
            text += ("風が路地を抜ける。" * (remaining // 9 + 2))[:remaining]
        else:
            text += block
        index += 1
    return text


def make_long_novel(project_dir, *, chapters=20, scenes_per_chapter=5, chars_per_scene=2000):
    """Create an empty/new scratch project and return its deterministic manifest.

    Small variants require at least two scenes, so past and future evidence are
    distinct. The conventional 1600/2000/2400 standard band is never scaled.
    Existing nonempty destinations are refused to protect user prose.
    """
    for name, value in (("chapters", chapters), ("scenes_per_chapter", scenes_per_chapter), ("chars_per_scene", chars_per_scene)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("{} must be a positive integer".format(name))
    if chapters * scenes_per_chapter < 2:
        raise ValueError("fixture requires at least two scenes")
    project = Path(project_dir)
    if project.exists() and any(project.iterdir()):
        raise ValueError("fixture destination must be empty: {}".format(project))
    project.mkdir(parents=True, exist_ok=True)
    coordinates = [(c, s) for c in range(1, chapters + 1) for s in range(1, scenes_per_chapter + 1)]
    first_id = "{}-{}".format(*coordinates[0])
    secret_id = "{}-{}".format(*coordinates[min(1, len(coordinates) - 1)])
    future_id = "{}-{}".format(*coordinates[-1])
    late_target = "{}-{}".format(*coordinates[-2])
    scenes = []
    for chapter, scene in coordinates:
        scene_id = "{}-{}".format(chapter, scene)
        inserts = []
        if scene_id == first_id:
            inserts += [PAST_FACT, THREAD]
        if scene_id == secret_id:
            inserts += [PRIVATE_SECRET]
        if scene_id == future_id:
            inserts += [FUTURE_SECRET + "が初めて姿を現した。"]
        text = _scene_text(chapter, scene, chars_per_scene, inserts)
        path = "chapter_{}/scene_{}.txt".format(chapter, scene_id)
        _write(project / path, text)
        scenes.append({"scene_id": scene_id, "chapter": chapter, "scene": scene,
                       "path": path, "chars": len(text),
                       "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    minimum = len(scenes) * 1600
    target = len(scenes) * 2000
    outline = ["# 合成長編のアウトライン", "", "- 全体目標文字数: 200000", "- 計画ゲート下限: 160000", ""]
    for chapter in range(1, chapters + 1):
        outline += ["## 第{}章 Chapter Card".format(chapter), "- 章の役割: 街の探索", "- part_id: part:one" if chapter == 1 else "- part_id: part:later",
                    "- 想定シーン数: {}".format(scenes_per_chapter),
                    "- 想定最小字数: {}".format(scenes_per_chapter * 1600),
                    "- 想定目標字数: {}".format(scenes_per_chapter * 2000), "", "### Scene Ledger",
                    "| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |",
                    "|---|---|---|---|---|---:|---:|---:|---|---|"]
        for entry in (s for s in scenes if s["chapter"] == chapter):
            # Explicit distant dependency only for the late target. Independent
            # scenes let the rewrite test catch overbroad invalidation too.
            dependency = first_id if entry["scene_id"] == late_target and late_target != first_id else "-"
            outline.append("| {} | standard | 街で手掛かりを探す | 警戒 -> 決意 | - | 1600 | 2000 | 2400 | {} | planned |".format(entry["scene_id"], dependency))
        outline.append("")
        _write(project / "chapter_{}".format(chapter) / "body.md", "")
    _write(project / "05_chapter_outline.md", "\n".join(outline))
    state = "\n".join([
        "targets:", "  target_total_chars: 200000", "  target_length_profile: novel_200k",
        "  planning_gate_enabled: {}".format("true" if minimum >= 160000 else "false"),
        "  planning_gate_min_chars: 160000", "  planning_target_total_chars: 200000",
        "active_work:", "  planning_gate_status: ready", "progress:",
        "  planned_total_min_chars: {}".format(minimum), "  planned_total_target_chars: {}".format(target),
        "  planned_scene_count: {}".format(len(scenes)), "narration_tense: 過去形", "",
    ])
    _write(project / "agent" / "state_schema_novel.yaml", state)
    _write(project / "agent" / "memory" / "global_notes.md", "## 文体契約\n- 視点: 三人称一元\n- 地の文時制: 過去形\n- 禁止: メタ発言\n")
    _write(project / "agent" / "memory" / "session_notes.md", "合成回帰試験用。設定や人物の意味的な正しさは人間が別途評価する。\n")
    by_id = {s["scene_id"]: s for s in scenes}

    def sources(ids):
        return [{"path": by_id[i]["path"], "content_hash": by_id[i]["content_hash"],
                 "line_start": 1, "line_end": len((project / by_id[i]["path"]).read_text(encoding="utf-8").splitlines())} for i in ids]

    def record(record_id, kind, text, ids, **fields):
        return dict({"id": record_id, "kind": kind, "text": text,
                     "entity_ids": ["character:a"], "available_after_scene": ids[-1],
                     "sources": sources(ids), "supersedes": []}, **fields)

    first_chapter = [s["scene_id"] for s in scenes if s["chapter"] == 1]
    records = [
        record("fact:key", "fact", PAST_FACT, [first_id], subject_id="object:key", predicate="opens"),
        record("fact:secret", "fact", PRIVATE_SECRET, [secret_id], subject_id="place:cellar", predicate="password"),
        record("knowledge:a", "character_knowledge", "葵は地下室の合言葉を知った。", [secret_id], character_id="character:a", fact_id="fact:secret"),
        record("thread:letter:opened", "thread_event", THREAD, [first_id], thread_id="thread:letter", event="opened"),
        record("outcome:first", "scene_outcome", "葵は北門の鍵を手に入れ、手紙の謎を追い始めた。", [first_id], scene_id=first_id),
        record("summary:chapter:1", "chapter_summary", "葵たちは街で手掛かりを集めた。手紙の謎は未解決である。", first_chapter, chapter=1, covered_scenes=first_chapter),
        record("summary:part:one", "part_summary", "第一部では探索が始まり、差出人不明の手紙が残された。", first_chapter, part_id="part:one", covered_scenes=first_chapter),
        record("fact:future", "fact", FUTURE_SECRET, [future_id], subject_id="object:crown", predicate="revealed"),
    ]
    source_ids = {first_id, secret_id, future_id, *first_chapter}
    manifest = {
        "fixture_revision": FIXTURE_REVISION, "synthetic_not_literary_sample": True,
        "chapters": chapters, "scenes_per_chapter": scenes_per_chapter,
        "total_chars": sum(s["chars"] for s in scenes), "scenes": scenes,
        "planned_total_min_chars": minimum, "planned_total_target_chars": target,
        "late_target": late_target, "future_scene_id": future_id, "future_secret": FUTURE_SECRET,
        "facts": {"past_fact": PAST_FACT, "private_secret": PRIVATE_SECRET, "open_thread": THREAD},
        "expected_knowledge": {"character:a": ["fact:secret"], "character:b": []},
        "memory_sources": [s for s in scenes if s["scene_id"] in source_ids],
        "proposal": {"version": 1, "batch_id": "synthetic-evidence-v1", "records": records},
    }
    _write(project / "fixture_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest
