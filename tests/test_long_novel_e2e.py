"""Real-command regression tests, not evaluations of an LLM's writing ability."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def cli(name, *args, ok=True):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if ok:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
    return result


def fixture_at(path, **kwargs):
    from helpers.long_novel_fixture import make_long_novel
    return make_long_novel(str(path), **kwargs)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def runtime(project, scene_id, mode="draft"):
    return project / "runtime" / "scenes" / scene_id / mode


def prepare(project, scene_id, mode="draft", pov=None):
    args = ["--project", project, "--chapter", scene_id.split("-")[0],
            "--scene", scene_id, "--mode", mode]
    if pov:
        args += ["--pov-character", pov]
    cli("build_runtime_context.py", *args)
    return runtime(project, scene_id, mode)


def prompt(project, scene_id, directory=None):
    args = ["--project", project, "--scene", scene_id]
    if directory:
        args += ["--runtime_dir", directory]
    cli("build_draft_prompt.py", *args)
    return (directory or runtime(project, scene_id)) / "draft_prompt.txt"


def check_approve(project, scene):
    directory = prepare(project, scene["scene_id"])
    cli("check_scene_output.py", "--project", project, "--text", project / scene["path"],
        "--runtime_dir", directory)
    report = read_json(directory / "check_report.json")
    assert report["version"] == 2
    assert report["scene_id"] == scene["scene_id"]
    assert report["source_hash"] == hashlib.sha256(
        (project / scene["path"]).read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()
    assert report["actual_chars"] == scene["chars"]
    assert report["status"] in ("pass", "warning"), report
    assert report["blocking_issues"] == []
    # Warnings are not relabeled pass; explicit acceptance is required.
    cli("approve_scene.py", "--project", project, "--scene", scene["scene_id"],
        *(["--allow-warnings"] if report["status"] == "warning" else []))
    return report


def approve_sources(project, manifest):
    ids = {source["scene_id"] for source in manifest["memory_sources"]}
    for scene in manifest["scenes"]:
        if scene["scene_id"] in ids:
            check_approve(project, scene)


def accept_memory(project, manifest):
    path = project / "fixture_proposal.json"
    path.write_text(json.dumps(manifest["proposal"], ensure_ascii=False, indent=2), encoding="utf-8")
    cli("import_story_memory.py", "--project", project, "--input", path, "--validate-only")
    assert not (project / "story_memory" / "accepted.json").exists()
    cli("import_story_memory.py", "--project", project, "--input", path)
    assert not (project / "story_memory" / "accepted.json").exists()
    cli("review_story_memory.py", "--project", project, "--batch", manifest["proposal"]["batch_id"])
    cli("review_story_memory.py", "--project", project, "--batch", manifest["proposal"]["batch_id"],
        "--accept", "--expected-revision", "0")
    accepted = read_json(project / "story_memory" / "accepted.json")
    assert accepted["revision"] == 1
    assert {r["id"] for r in accepted["records"]} == {r["id"] for r in manifest["proposal"]["records"]}
    return accepted


def test_fixture_is_exact_deterministic_and_has_real_source_hashes(tmp_path):
    first = fixture_at(tmp_path / "日本語の作品")
    second = fixture_at(tmp_path / "other")
    assert first == second
    assert first["total_chars"] == 200000
    assert len(first["scenes"]) == 100
    assert first["planned_total_min_chars"] == 160000
    assert first["planned_total_target_chars"] == 200000
    assert len({s["content_hash"] for s in first["scenes"]}) == 100
    for scene in first["scenes"]:
        text = (tmp_path / "日本語の作品" / scene["path"]).read_text(encoding="utf-8")
        assert len(text) == 2000
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == scene["content_hash"]
    assert first["expected_knowledge"]["character:b"] == []
    assert first["future_secret"] not in first["facts"]["past_fact"]


def test_200k_roundtrip_with_100_scenes(tmp_path):
    project = tmp_path / "roundtrip"
    manifest = fixture_at(project)
    assert sum(s["chars"] for s in manifest["scenes"]) == 200000
    assert manifest["planned_total_min_chars"] == 160000
    assert manifest["planned_total_target_chars"] == 200000
    reports = [check_approve(project, scene) for scene in manifest["scenes"]]
    cli("export_manuscript.py", "--project", project, "--include-warnings")
    exported = (project / "exports" / "manuscript.md").read_text(encoding="utf-8")
    offsets = [exported.index((project / s["path"]).read_text(encoding="utf-8").strip())
               for s in manifest["scenes"]]
    assert offsets == sorted(offsets), "Chapters 10–20 must be numerically ordered"
    assert len(set(offsets)) == 100
    ledger = read_json(project / "runtime" / "approval_ledger.json")["scenes"]
    assert len(ledger) == 100
    assert all(record["status"] == "approved" for record in ledger.values())
    from novel_agent.scene_status import collect_project_status
    progress = collect_project_status(str(project))["progress"]
    assert progress["written_scene_count"] == 100
    assert progress["checked_scene_count"] == 100
    assert progress["completed_scene_count"] == sum(r["status"] == "pass" for r in reports)
    assert progress["approved_scene_count"] == 100
    assert progress["total_chars_written"] == 200000


def test_late_scene_resume_and_context_budget(tmp_path):
    project = tmp_path / "late"
    manifest = fixture_at(project)
    approve_sources(project, manifest)
    accept_memory(project, manifest)
    target = manifest["late_target"]
    prepare(project, target, mode="resume", pov="character:b")
    directory = prepare(project, target, pov="character:b")
    text = prompt(project, target, directory).read_text(encoding="utf-8")
    assert len(text) <= 16000
    assert manifest["facts"]["past_fact"] in text
    assert manifest["future_secret"] not in text
    assert (runtime(project, target, "resume") / "resume_brief.md").is_file()
    assert (directory / "story_memory_pack.md").is_file()
    context = read_json(directory / "context_selection.json")
    records = context["memory"]["author_records"] + context["memory"]["pov_records"]
    selected_ids = {record_id for section in context["final_prompt"]["selected"]
                    if section["name"].startswith("memory:")
                    for record_id in section["source_ids"]}
    # The bounded prompt may render records independently instead of inserting
    # the pack as one block. This small memory set must fit without omissions.
    assert selected_ids == {record["id"] for record in records}
    assert "fact:key" in selected_ids
    for record in records:
        assert record["id"] in text
        assert record["text"] in text
        for source in record["sources"]:
            assert "{}:{}-{}".format(source["path"], source["line_start"], source["line_end"]) in text
    assert "POV: character:b" in text
    assert context["memory"]["pov_records"] == []
    from novel_agent.memory_context import select_memory
    selection = select_memory(str(project), target_scene_id=target, pov_character_id="character:b",
                              entity_ids=[], thread_ids=[])
    assert selection["pov_records"] == [], "B never inherits A's explicit knowledge"
    selected = json.dumps(selection["author_records"] + selection["pov_records"], ensure_ascii=False)
    assert manifest["future_secret"] not in selected
    assert not any((project / s["path"]).read_text(encoding="utf-8") in text
                   for s in manifest["scenes"][:10]), "Do not inject the novel wholesale"


def test_early_rewrite_stales_late_memory_and_approval(tmp_path):
    project = tmp_path / "rewrite"
    manifest = fixture_at(project, chapters=3, scenes_per_chapter=3)
    approve_sources(project, manifest)
    accept_memory(project, manifest)
    target = next(s for s in manifest["scenes"] if s["scene_id"] == manifest["late_target"])
    unrelated = manifest["scenes"][2]
    check_approve(project, unrelated)
    report = check_approve(project, target)
    early_path = manifest["scenes"][0]["path"]
    assert early_path in json.dumps(report["check_inputs"], ensure_ascii=False), "The changed source is an actual check dependency"
    accepted_path = project / "story_memory" / "accepted.json"
    before = accepted_path.read_bytes()
    path = project / early_path
    path.write_text(path.read_text(encoding="utf-8").replace("青銅の鍵", "銀色の鍵"), encoding="utf-8")
    from novel_agent.approvals import refresh_approval_statuses
    ledger = refresh_approval_statuses(str(project))["scenes"]
    assert ledger[target["scene_id"]]["status"] == "stale"
    assert ledger[unrelated["scene_id"]]["status"] == "approved"
    cli("export_manuscript.py", "--project", project, "--include-warnings", ok=False)
    directory = prepare(project, target["scene_id"], pov="character:a")
    text = prompt(project, target["scene_id"], directory).read_text(encoding="utf-8")
    assert manifest["facts"]["past_fact"] not in text
    assert accepted_path.read_bytes() == before, "Stale detection must not rewrite accepted evidence"


def test_migrate_100k_fixture_without_prose_changes(tmp_path):
    project = tmp_path / "migration"
    manifest = fixture_at(project, chapters=10)
    state = project / "agent" / "state_schema_novel.yaml"
    state.write_text(state.read_text(encoding="utf-8").replace("200000", "100000").replace("novel_200k", "novel_100k").replace("160000", "80000"), encoding="utf-8")
    outline = project / "05_chapter_outline.md"
    outline.write_text(outline.read_text(encoding="utf-8").replace("200000", "100000").replace("160000", "80000"), encoding="utf-8")
    prose_before = {s["path"]: (project / s["path"]).read_bytes() for s in manifest["scenes"]}
    state_before, outline_before = state.read_bytes(), outline.read_bytes()
    cli("migrate_project_state.py", "--project", project, "--target-total-chars", "200000", "--dry-run")
    assert (state.read_bytes(), outline.read_bytes()) == (state_before, outline_before)
    plans = list((project / "runtime" / "migrations").glob("*/plan.json"))
    assert len(plans) == 1
    plan = read_json(plans[0])
    assert plan["conflicts"] == []
    cli("migrate_project_state.py", "--project", project, "--apply-plan", plans[0],
        "--expected-plan-hash", plan["plan_hash"])
    assert "target_total_chars: 200000" in state.read_text(encoding="utf-8")
    assert "planning_gate_min_chars: 160000" in state.read_text(encoding="utf-8")
    assert prose_before == {p: (project / p).read_bytes() for p in prose_before}
    cli("migrate_project_state.py", "--project", project, "--rollback", plan["migration_id"])
    assert (state.read_bytes(), outline.read_bytes()) == (state_before, outline_before)


def test_corrupt_store_recovery_never_discards_records(tmp_path):
    project = tmp_path / "corrupt"
    manifest = fixture_at(project, chapters=3, scenes_per_chapter=3)
    approve_sources(project, manifest)
    accept_memory(project, manifest)
    store = project / "story_memory" / "accepted.json"
    good = store.read_bytes()
    corrupt = good[:-9]
    store.write_bytes(corrupt)
    cli("sync_project_health.py", "--project", project, "--fix-safe", "--json")
    assert store.read_bytes() == corrupt
    health = read_json(project / "runtime" / "health_report.json")
    assert "accepted.json" in json.dumps(health)
    assert health["blocking_issues"], health
    # Restore a known-good backup explicitly; health must never invent empty memory.
    store.write_bytes(good)
    directory = prepare(project, manifest["late_target"])
    assert manifest["facts"]["past_fact"] in prompt(project, manifest["late_target"], directory).read_text(encoding="utf-8")
    assert store.read_bytes() == good


def test_old_project_without_memory_works(tmp_path):
    project = tmp_path / "legacy"
    manifest = fixture_at(project, chapters=2, scenes_per_chapter=3)
    assert not (project / "story_memory").exists()
    state = project / "agent" / "state_schema_novel.yaml"
    state.write_text(state.read_text(encoding="utf-8").replace("200000", "100000").replace("novel_200k", "novel_100k").replace("160000", "80000"), encoding="utf-8")
    target = manifest["late_target"]
    directory = prepare(project, target)
    text = prompt(project, target, directory).read_text(encoding="utf-8")
    assert 0 < len(text) <= 16000
    assert manifest["future_secret"] not in text
    assert (directory / "related_context_pack.md").is_file()
    assert not (project / "story_memory" / "accepted.json").exists()


def test_memory_cli_propose_validate_accept_prompt_then_edit_invalidates(tmp_path):
    project = tmp_path / "memory_cli"
    manifest = fixture_at(project, chapters=3, scenes_per_chapter=3)
    approve_sources(project, manifest)
    accept_memory(project, manifest)
    target = manifest["late_target"]
    directory = prepare(project, target, pov="character:a")
    assert manifest["facts"]["past_fact"] in prompt(project, target, directory).read_text(encoding="utf-8")
    source = project / manifest["scenes"][0]["path"]
    source.write_text(source.read_text(encoding="utf-8").replace("青銅の鍵", "木製の鍵"), encoding="utf-8")
    cli("build_draft_prompt.py", "--project", project, "--scene", target, "--runtime_dir", directory, ok=False)
    cli("approve_scene.py", "--project", project, "--scene", "1-1", "--allow-warnings", ok=False)
    directory = prepare(project, target, pov="character:a")
    assert manifest["facts"]["past_fact"] not in prompt(project, target, directory).read_text(encoding="utf-8")


def test_runtime_evaluator_records_measured_metrics_without_mutating_project(tmp_path):
    project = tmp_path / "measure"
    fixture_at(project, chapters=2, scenes_per_chapter=3)
    before = {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    out = tmp_path / "metrics.json"
    cli("eval_long_novel_runtime.py", "--project", project, "--json-out", out)
    report = read_json(out)
    assert report["evaluation_kind"] == "deterministic_runtime_regression"
    assert report["agent_evaluation"]["status"] == "not_run"
    assert report["status"] == "pass"
    assert report["candidate_scene_count"] == 6
    assert 0 < report["prompt_chars"] <= 16000
    assert report["export"]["scene_count"] == 1
    assert report["stale_detection"]["detected"] is True
    assert len(report["commands"]) >= 5
    for result in report["commands"]:
        assert result["elapsed_seconds"] >= 0
        assert result["read_open_events"] > 0
        assert result["unique_project_files_read"] > 0
        assert not any(path.endswith(".tmp") for path in result["project_files_read"]), "Atomic write temp creations are not source reads"
    assert before == {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}


def test_result_template_never_claims_unrun_agent_success():
    result = read_json(ROOT / "agent" / "evals" / "templates" / "long_novel_agent_result.json")
    assert result["status"] == "not_run"
    assert len(result["runs"]) == 12
    assert {r["case_id"] for r in result["runs"]} == {
        "early_draft", "middle_draft", "late_draft", "chapter_resume", "pov_boundary", "stale_recovery"}
    for run in result["runs"]:
        assert run["status"] == "not_run"
        assert run["scores"] is None
        assert run["critical_failures"] is None
        assert run["output_path"] is None
