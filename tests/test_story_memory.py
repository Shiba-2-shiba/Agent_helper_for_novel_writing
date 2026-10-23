"""Explicit, source-grounded semantic memory, never inferred from prose."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def api():
    return importlib.import_module("novel_agent.story_memory")


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def approved_scene(project, scene_id="1-1", text="扉は青い。\nアキだけが鍵を持つ。\n"):
    chapter, scene = scene_id.split("-")
    legacy = project / ("chapter_%s_scene_%s.txt" % (chapter, scene))
    path = legacy if legacy.exists() else project / ("scene_%s.txt" % scene_id)
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ledger_path = project / "runtime" / "approval_ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"version": 1, "scenes": {}}
    ledger["scenes"][scene_id] = {"status": "approved", "scene_id": scene_id, "scene_path": path.name, "content_hash": digest}
    save_json(ledger_path, ledger)
    return {"path": path.name, "content_hash": digest, "line_start": 1, "line_end": len(text.splitlines())}


def fact(source, record_id="f1", scene="1-1", **overrides):
    return dict({"id": record_id, "kind": "fact", "text": "扉は青い", "entity_ids": ["aki"],
                 "available_after_scene": scene, "sources": [source], "supersedes": [],
                 "subject_id": "door", "predicate": "color"}, **overrides)


def proposal(*records, batch_id="batch-1"):
    return {"version": 1, "batch_id": batch_id, "records": list(records)}


def accept(project, payload, revision=0):
    api().import_proposal(str(project), payload)
    return api().accept_proposal(str(project), batch_id=payload["batch_id"], expected_revision=revision)


def test_valid_six_kinds_with_covered_sources(tmp_path):
    source = approved_scene(tmp_path)
    base = fact(source)
    records = [base,
        fact(source, "k1", kind="character_knowledge", character_id="aki", fact_id="f1"),
        fact(source, "t1", kind="thread_event", thread_id="door-mystery", event="opened"),
        fact(source, "o1", kind="scene_outcome", scene_id="1-1"),
        fact(source, "c1", kind="chapter_summary", chapter=1, covered_scenes=["1-1"]),
        fact(source, "p1", kind="part_summary", part_id="part-1", covered_scenes=["1-1"])]
    result = api().validate_proposal(str(tmp_path), proposal(*records))
    assert result["valid"], result["errors"]
    assert len(result["records"]) == 6
    assert result["records"][0]["sources"][0]["scene_id"] == "1-1"
    assert any("semantic" in warning for warning in result["warnings"])


@pytest.mark.parametrize("change", [
    {"kind": "thought"}, {"sources": []}, {"available_after_scene": "0-1"},
    {"entity_ids": "aki"}, {"supersedes": "f1"}, {"text": ""},
    {"kind": "character_knowledge", "character_id": "aki", "fact_id": "missing"},
    {"kind": "thread_event", "thread_id": "door", "event": "invented"},
    {"kind": "scene_outcome", "scene_id": "1-2"},
    {"kind": "chapter_summary", "chapter": 2, "covered_scenes": ["1-1"]},
    {"kind": "part_summary", "part_id": "p", "covered_scenes": ["1-1", "1-2"]},
])
def test_invalid_schema_and_references_rejected(tmp_path, change):
    result = api().validate_proposal(str(tmp_path), proposal(fact(approved_scene(tmp_path), **change)))
    assert not result["valid"]
    assert result["errors"]


@pytest.mark.parametrize("source_change", [
    {"content_hash": "0" * 64}, {"line_start": 0}, {"line_end": 100},
    {"line_start": 2, "line_end": 1}, {"line_start": True},
    {"path": "missing.txt"}, {"path": "../scene_1-1.txt"}, {"scene_id": "9-9"},
])
def test_invalid_sources_rejected(tmp_path, source_change):
    source = dict(approved_scene(tmp_path), **source_change)
    result = api().validate_proposal(str(tmp_path), proposal(fact(source)))
    assert not result["valid"]


def test_unapproved_scene_and_planning_markdown_rejected(tmp_path):
    source = approved_scene(tmp_path)
    (tmp_path / "runtime" / "approval_ledger.json").unlink()
    assert not api().validate_proposal(str(tmp_path), proposal(fact(source)))["valid"]
    path = tmp_path / "05_chapter_outline.md"
    path.write_text("扉は青い。", encoding="utf-8")
    source.update(path=path.name, content_hash=hashlib.sha256(path.read_bytes()).hexdigest(), line_end=1)
    assert not api().validate_proposal(str(tmp_path), proposal(fact(source)))["valid"]


def test_external_symlink_and_duplicate_scene_identity_rejected(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    source = approved_scene(project)
    original = project / source["path"]
    external = tmp_path / "outside.txt"
    external.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(external)
    assert not api().validate_proposal(str(project), proposal(fact(source)))["valid"]
    original.unlink()
    original.write_bytes(external.read_bytes())
    (project / "chapter_1_scene_1.txt").write_bytes(external.read_bytes())
    assert not api().validate_proposal(str(project), proposal(fact(source)))["valid"]


def test_duplicate_ids_cycles_and_early_availability_rejected(tmp_path):
    source = approved_scene(tmp_path)
    f1 = fact(source)
    f2 = fact(source, "f2", supersedes=["f1"])
    f1["supersedes"] = ["f2"]
    assert not api().validate_proposal(str(tmp_path), proposal(f1, f2))["valid"]
    assert not api().validate_proposal(str(tmp_path), proposal(f2, f2))["valid"]
    future = approved_scene(tmp_path, "2-1")
    assert not api().validate_proposal(str(tmp_path), proposal(fact(future)))["valid"]


def test_import_never_auto_accepts(tmp_path):
    payload = proposal(fact(approved_scene(tmp_path)))
    result = api().import_proposal(str(tmp_path), payload)
    assert result["batch_id"] == "batch-1"
    assert api().load_memory(str(tmp_path)) == {"version": 1, "revision": 0, "records": []}
    assert (tmp_path / "story_memory" / "proposals" / "batch-1.json").is_file()


def test_accept_checks_revision_and_batch_atomicity(tmp_path):
    from novel_agent.errors import ConflictError
    payload = proposal(fact(approved_scene(tmp_path)))
    api().import_proposal(str(tmp_path), payload)
    with pytest.raises(ConflictError):
        api().accept_proposal(str(tmp_path), batch_id="batch-1", expected_revision=1)
    assert not (tmp_path / "story_memory" / "accepted.json").exists()
    result = api().accept_proposal(str(tmp_path), batch_id="batch-1", expected_revision=0)
    assert result["revision"] == 1
    before = (tmp_path / "story_memory" / "accepted.json").read_bytes()
    with pytest.raises(ConflictError):
        api().accept_proposal(str(tmp_path), batch_id="batch-1", expected_revision=0)
    assert (tmp_path / "story_memory" / "accepted.json").read_bytes() == before


def test_source_edit_between_import_and_accept_rejected(tmp_path):
    from novel_agent.errors import UserFacingError
    payload = proposal(fact(approved_scene(tmp_path)))
    api().import_proposal(str(tmp_path), payload)
    (tmp_path / "scene_1-1.txt").write_text("変更", encoding="utf-8")
    with pytest.raises(UserFacingError):
        api().accept_proposal(str(tmp_path), batch_id="batch-1", expected_revision=0)
    assert api().load_memory(str(tmp_path))["revision"] == 0


def test_changed_source_invalidates_fact_knowledge_summary_without_rewriting(tmp_path):
    source = approved_scene(tmp_path)
    source2 = approved_scene(tmp_path, "1-2")
    payload = proposal(fact(source),
        fact(source2, "k1", scene="1-2", kind="character_knowledge", character_id="aki", fact_id="f1"),
        fact(source, "c1", kind="chapter_summary", chapter=1, covered_scenes=["1-1"]))
    accept(tmp_path, payload)
    accepted = tmp_path / "story_memory" / "accepted.json"
    before = accepted.read_bytes()
    (tmp_path / "scene_1-1.txt").write_text("扉は赤い。", encoding="utf-8")
    status = api().memory_status(str(tmp_path))
    assert {record["id"] for record in status["records"] if record["status"] == "stale"} == {"f1", "k1", "c1"}
    assert accepted.read_bytes() == before


def test_approval_revocation_invalidates_memory(tmp_path):
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    path = tmp_path / "runtime" / "approval_ledger.json"
    ledger = json.loads(path.read_text())
    ledger["scenes"]["1-1"]["status"] = "revoked"
    save_json(path, ledger)
    result = api().memory_status(str(tmp_path))["records"][0]
    assert result["status"] == "stale"
    assert any("approval" in reason for reason in result["reasons"])


def test_conflicting_batch_and_record_ids_never_overwritten(tmp_path):
    from novel_agent.errors import UserFacingError
    payload = proposal(fact(approved_scene(tmp_path)))
    accept(tmp_path, payload)
    before = (tmp_path / "story_memory" / "accepted.json").read_bytes()
    changed = copy.deepcopy(payload)
    changed["records"][0]["text"] = "別の意味"
    with pytest.raises(UserFacingError):
        api().import_proposal(str(tmp_path), changed)
    changed["batch_id"] = "other"
    with pytest.raises(UserFacingError):
        api().import_proposal(str(tmp_path), changed)
    assert (tmp_path / "story_memory" / "accepted.json").read_bytes() == before


def test_future_supersession_preserves_earlier_fact_as_of_target(tmp_path):
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    accept(tmp_path, proposal(fact(approved_scene(tmp_path, "3-1"), "f2", scene="3-1", supersedes=["f1"]), batch_id="later"), 1)
    current = {r["id"]: r for r in api().memory_status(str(tmp_path))["records"]}
    past = {r["id"]: r for r in api().memory_status(str(tmp_path), as_of_scene_id="2-1")["records"]}
    assert current["f1"]["status"] == "superseded"
    assert past["f1"]["status"] == "active"
    assert past["f2"]["status"] == "future"


def test_correction_does_not_inherit_old_source_staleness(tmp_path):
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    (tmp_path / "scene_1-1.txt").write_text("改稿済み", encoding="utf-8")
    accept(tmp_path, proposal(fact(approved_scene(tmp_path, "2-1"), "f2", scene="2-1", supersedes=["f1"]), batch_id="corrected"), 1)
    records = {r["id"]: r for r in api().memory_status(str(tmp_path))["records"]}
    assert records["f2"]["status"] == "active"


@pytest.mark.parametrize("payload", ["{", "[]", '{"version": 9,"revision":0,"records":[]}', '{"version":1,"revision":false,"records":[]}'])
def test_corrupt_memory_is_not_empty_or_rewritten(tmp_path, payload):
    from novel_agent.errors import DataCorruptionError
    path = tmp_path / "story_memory" / "accepted.json"
    path.parent.mkdir()
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(DataCorruptionError):
        api().load_memory(str(tmp_path))
    assert path.read_text() == payload


def test_memory_cli_import_review_accept(tmp_path):
    payload = proposal(fact(approved_scene(tmp_path)))
    source = tmp_path / "input.json"
    save_json(source, payload)
    def run(script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), "--project", str(tmp_path), *args], capture_output=True, text=True)
    imported = run("import_story_memory.py", "--input", str(source))
    assert imported.returncode == 0, imported.stdout + imported.stderr
    assert not (tmp_path / "story_memory" / "accepted.json").exists()
    reviewed = run("review_story_memory.py", "--batch", "batch-1")
    assert reviewed.returncode == 0, reviewed.stdout + reviewed.stderr
    assert not (tmp_path / "story_memory" / "accepted.json").exists()
    missing_revision = run("review_story_memory.py", "--batch", "batch-1", "--accept")
    assert missing_revision.returncode != 0
    accepted = run("review_story_memory.py", "--batch", "batch-1", "--accept", "--expected-revision", "0")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert api().load_memory(str(tmp_path))["revision"] == 1


def test_transitive_correction_hides_ancestor_even_if_intermediate_is_stale(tmp_path):
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    accept(tmp_path, proposal(fact(approved_scene(tmp_path, "2-1"), "f2", scene="2-1", supersedes=["f1"]), batch_id="second"), 1)
    accept(tmp_path, proposal(fact(approved_scene(tmp_path, "3-1"), "f3", scene="3-1", supersedes=["f2"]), batch_id="third"), 2)
    (tmp_path / "scene_2-1.txt").write_text("改稿", encoding="utf-8")
    states = {r["id"]: r["status"] for r in api().memory_status(str(tmp_path))["records"]}
    assert states == {"f1": "superseded", "f2": "stale", "f3": "active"}


def test_health_reports_memory_corruption_without_replacing_user_data(tmp_path):
    from novel_agent.health import build_health_report, run_safe_fixes
    path = tmp_path / "story_memory" / "accepted.json"
    path.parent.mkdir()
    path.write_text('{"version":1,', encoding="utf-8")
    before = path.read_bytes()
    report = build_health_report(str(tmp_path))
    assert report["status"] == "fail"
    assert any("accepted.json" in issue["path"] for issue in report["blocking_issues"])
    assert run_safe_fixes(str(tmp_path)) == []
    assert path.read_bytes() == before


def test_health_does_not_rewrite_accepted_memory_or_manual_story_state(tmp_path):
    from novel_agent.health import build_health_report
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    accepted = tmp_path / "story_memory" / "accepted.json"
    before = accepted.read_bytes()
    save_json(tmp_path / "runtime" / "story_state.json", {"version":1,"scenes":{},"manual_note":"手編集を保持","characters":{"aki":{"custom":"keep"}}})
    state_before = (tmp_path / "runtime" / "story_state.json").read_bytes()
    (tmp_path / "scene_1-1.txt").write_text("改稿", encoding="utf-8")
    report = build_health_report(str(tmp_path))
    assert any(issue["type"] == "story_memory_stale" for issue in report["warnings"])
    assert accepted.read_bytes() == before
    assert (tmp_path / "runtime" / "story_state.json").read_bytes() == state_before


def test_approval_policy_change_stales_memory_without_source_edit(tmp_path):
    from test_approval_identity import setup_checked
    from novel_agent.approvals import approve_scene
    from novel_agent.storage import text_content_hash
    path, _ = setup_checked(tmp_path)
    approve_scene(str(tmp_path), "1-1")
    source = {"path": path.name, "content_hash": text_content_hash(str(path)), "line_start": 1, "line_end": 1}
    accept(tmp_path, proposal(fact(source)))
    before = path.read_bytes()
    notes = tmp_path / "agent" / "memory" / "global_notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("- 禁止: 新たな禁止語\n", encoding="utf-8")
    status = api().memory_status(str(tmp_path))["records"][0]
    assert status["status"] == "stale"
    assert any("approval" in reason for reason in status["reasons"])
    assert path.read_bytes() == before


def test_new_knowledge_cannot_be_accepted_against_a_stale_fact(tmp_path):
    from novel_agent.errors import UserFacingError
    accept(tmp_path, proposal(fact(approved_scene(tmp_path))))
    (tmp_path / "scene_1-1.txt").write_text("変更", encoding="utf-8")
    current = approved_scene(tmp_path, "1-2")
    payload = proposal(fact(current, "new-knowledge", scene="1-2", kind="character_knowledge",
                            character_id="aki", fact_id="f1"), batch_id="knowledge")
    with pytest.raises(UserFacingError, match="stale"):
        api().import_proposal(str(tmp_path), payload)
    assert api().load_memory(str(tmp_path))["revision"] == 1


def test_chapter_summary_is_partial_when_planned_scene_is_not_yet_written(tmp_path):
    source = approved_scene(tmp_path)
    (tmp_path / "05_chapter_outline.md").write_text(
        "## 第1章 Chapter Card\n### Scene Ledger\n"
        "| scene_id | purpose |\n|---|---|\n| 1-1 | 導入 |\n| 1-2 | 結末 |\n", encoding="utf-8")
    accept(tmp_path, proposal(fact(source, "summary", kind="chapter_summary", chapter=1, covered_scenes=["1-1"])))
    status = api().memory_status(str(tmp_path))["records"][0]
    assert status["coverage"] == "partial"



@pytest.mark.parametrize("field,value", [
    ("known_fact", {"id": "future", "text": "FUTURE_UNAPPROVED_SENTINEL", "sources": [{"path":"scene_9-1.txt", "line_start":1, "line_end":1}]}),
    ("status", "active"), ("reasons", []), ("coverage", "complete"), ("context_priority", 0),
])
def test_proposal_rejects_reserved_derived_fields(tmp_path, field, value):
    from novel_agent.errors import UserFacingError
    payload = proposal(fact(approved_scene(tmp_path), **{field: value}))
    with pytest.raises(UserFacingError, match="reserved"):
        api().import_proposal(str(tmp_path), payload)
    assert not (tmp_path / "story_memory" / "accepted.json").exists()


@pytest.mark.parametrize("corruption", ["summary_missing_source", "outcome_wrong_source", "early_availability", "derived_payload"])
def test_stored_memory_structural_corruption_is_rejected_without_rewrite(tmp_path, corruption):
    from novel_agent.errors import DataCorruptionError
    source1 = approved_scene(tmp_path)
    source2 = approved_scene(tmp_path, "1-2")
    record = fact(source1, "summary", scene="1-2", kind="chapter_summary", chapter=1,
                  sources=[source1, source2], covered_scenes=["1-1", "1-2"])
    accept(tmp_path, proposal(record))
    path = tmp_path / "story_memory" / "accepted.json"
    payload = json.loads(path.read_text())
    stored = payload["records"][0]
    if corruption == "summary_missing_source":
        stored["sources"] = stored["sources"][:1]
    elif corruption == "outcome_wrong_source":
        stored.update(kind="scene_outcome", scene_id="9-1")
    elif corruption == "early_availability":
        stored["available_after_scene"] = "1-1"
    else:
        stored["known_fact"] = {"text": "UNAPPROVED_SENTINEL"}
    save_json(path, payload)
    before = path.read_bytes()
    with pytest.raises(DataCorruptionError):
        api().memory_status(str(tmp_path))
    assert path.read_bytes() == before
