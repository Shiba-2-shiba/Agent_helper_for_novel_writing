"""Regression coverage for CLI diagnostics reproduced in the fantasy trial."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from build_runtime_context import build_request_compact, build_scene_brief
from novel_agent.exports import export_manuscript
from novel_agent.storage import atomic_write_json
from novel_agent.trace import append_trace_event
from prompt_utils import (
    UserFacingError,
    extract_chapter_block,
    load_planning_metadata,
    parse_scene_reference,
    suggest_scene_output_path,
)
from test_manuscript_export import approved_project
from test_scripts import RUNTIME_OUTLINE_TEXT, create_runtime_project


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def run_cli(script, project, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--project", str(project)] + list(args),
        capture_output=True, text=True,
    )


def write_outline(project, scene_ids):
    lines = ["# Outline"]
    for chapter in sorted({int(scene_id.split("-")[0]) for scene_id in scene_ids}):
        lines.extend([
            "", "## 第{}章".format(chapter), "", "### Scene Ledger",
            "| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |",
            "|---|---|---|---|---|---:|---:|---:|---|---|",
        ])
        for scene_id in scene_ids:
            if int(scene_id.split("-")[0]) == chapter:
                lines.append("| {} | standard | 場面の目的 | 変化 | - | 1000 | 1250 | 1500 | - | planned |".format(scene_id))
    (project / "05_chapter_outline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_warning_approval(project, scene_id):
    path = project / "runtime" / "approval_ledger.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scenes"][scene_id]["check_status"] = "warning"
    atomic_write_json(str(path), payload)


def test_health_corrupt_ledger_exits_nonzero_after_writing_valid_json(tmp_path):
    project = tmp_path / "project"
    ledger = project / "runtime" / "approval_ledger.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text('{"scenes": broken', encoding="utf-8")
    before = ledger.read_bytes()

    result = run_cli("sync_project_health.py", project, "--json", "--fix-safe")

    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert any(issue["type"] == "data_corruption" for issue in report["blocking_issues"])
    assert json.loads((project / "runtime" / "health_report.json").read_text(encoding="utf-8")) == report
    assert ledger.read_bytes() == before
    assert result.returncode != 0


@pytest.mark.parametrize("fix_safe, expected", [(False, "warning"), (True, "pass")])
def test_health_nonblocking_reports_keep_zero_exit(tmp_path, fix_safe, expected):
    project = tmp_path / "project"
    project.mkdir()
    write_outline(project, [])
    if fix_safe:
        append_trace_event(str(project), event_type="fixture_initialized", summary="Healthy empty project")

    result = run_cli("sync_project_health.py", project, "--json", *(["--fix-safe"] if fix_safe else []))

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == expected


def test_partial_export_preserves_api_and_reports_missing_and_unapproved_ids(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    write_outline(project, ["1-1", "1-2", "1-3"])
    (project / "scene_1-3.txt").write_text("　未検査・未承認。", encoding="utf-8")
    output = project / "partial.md"

    result = export_manuscript(str(project), output_path=str(output), title="試験作品")

    assert result["scenes"] == ["1-1"]
    assert result["scene_count"] == 1
    assert result["output_path"] == str(output)
    assert output.read_text(encoding="utf-8").startswith("# 試験作品\n")
    assert "未検査" not in output.read_text(encoding="utf-8")
    assert result["complete"] is False
    assert result["omitted_scenes"] == [
        {"scene_id": "1-2", "reason": "scene_missing"},
        {"scene_id": "1-3", "reason": "not_approved"},
    ]


def test_warning_exclusion_is_an_explicit_omission(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　通常承認。", "1-2": "　警告付き承認。"})
    write_outline(project, ["1-1", "1-2"])
    set_warning_approval(project, "1-2")

    result = export_manuscript(str(project))

    assert result["scenes"] == ["1-1"]
    assert result["complete"] is False
    assert result["omitted_scenes"] == [{"scene_id": "1-2", "reason": "warning_excluded"}]


def test_partial_export_cli_discloses_all_omissions(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    write_outline(project, ["1-1", "1-2"])

    result = run_cli("export_manuscript.py", project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "complete=false" in result.stdout
    assert "1-2" in result.stdout and "scene_missing" in result.stdout
    assert "completed" not in result.stdout.lower()


@pytest.mark.parametrize("existing_output", [False, True])
def test_strict_export_rejects_partial_before_creating_or_overwriting_output(tmp_path, existing_output):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    write_outline(project, ["1-1", "1-2"])
    output = project / "strict" / "manuscript.md"
    if existing_output:
        output.parent.mkdir()
        output.write_bytes(b"previous complete manuscript\r\n")

    with pytest.raises(UserFacingError, match=r"incomplete.*1-2.*scene_missing"):
        export_manuscript(str(project), output_path=str(output), require_complete=True)

    if existing_output:
        assert output.read_bytes() == b"previous complete manuscript\r\n"
    else:
        assert not output.parent.exists()


def test_strict_export_rejects_warning_excluded_scene(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　通常承認。", "1-2": "　警告付き承認。"})
    write_outline(project, ["1-1", "1-2"])
    set_warning_approval(project, "1-2")

    with pytest.raises(UserFacingError, match=r"1-2.*warning_excluded"):
        export_manuscript(str(project), require_complete=True)

    assert not (project / "exports").exists()


def test_strict_export_rejects_existing_unchecked_scene(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    write_outline(project, ["1-1", "1-2"])
    (project / "scene_1-2.txt").write_text("　未検査・未承認。", encoding="utf-8")

    with pytest.raises(UserFacingError, match=r"1-2.*not_approved"):
        export_manuscript(str(project), require_complete=True)

    assert not (project / "exports").exists()


def test_complete_export_includes_explicitly_allowed_warnings(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　通常承認。", "1-2": "　警告付き承認。"})
    write_outline(project, ["1-1", "1-2"])
    set_warning_approval(project, "1-2")

    result = export_manuscript(str(project), include_warnings=True, require_complete=True)

    assert result["scenes"] == ["1-1", "1-2"]
    assert result["complete"] is True
    assert result["omitted_scenes"] == []


def test_strict_export_cli_rejects_missing_scene_without_writing(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    write_outline(project, ["1-1", "1-2"])

    result = run_cli("export_manuscript.py", project, "--require-complete")

    assert result.returncode != 0
    assert "1-2" in result.stdout and "scene_missing" in result.stdout
    assert not (project / "exports").exists()


def test_complete_export_cli_explicitly_includes_warning_approvals(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　警告付き承認。"})
    write_outline(project, ["1-1"])
    set_warning_approval(project, "1-1")

    result = run_cli("export_manuscript.py", project, "--require-complete", "--include-warnings")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "complete=true" in result.stdout and "omitted=0" in result.stdout
    assert "警告付き承認" in (project / "exports" / "manuscript.md").read_text(encoding="utf-8")


def test_export_with_no_selected_scenes_still_discloses_omissions(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    write_outline(project, ["1-1"])

    result = run_cli("export_manuscript.py", project)

    assert result.returncode != 0
    assert "1-1" in result.stdout and "scene_missing" in result.stdout
    assert not (project / "exports").exists()


def test_outlineless_export_uses_discovered_scene_inventory(tmp_path):
    project = approved_project(tmp_path, {"2-1": "　承認済み。"})
    (project / "scene_2-2.txt").write_text("　未承認。", encoding="utf-8")

    result = export_manuscript(str(project))

    assert result["scenes"] == ["2-1"]
    assert result["complete"] is False
    assert result["omitted_scenes"] == [{"scene_id": "2-2", "reason": "not_approved"}]


def test_outlineless_strict_export_can_complete_discovered_inventory(tmp_path):
    project = approved_project(tmp_path, {"2-1": "　承認済み。"})

    result = export_manuscript(str(project), require_complete=True)

    assert result["complete"] is True
    assert result["omitted_scenes"] == []


@pytest.mark.parametrize("require_complete", [False, True])
def test_export_stale_approval_remains_fatal(tmp_path, require_complete):
    project = approved_project(tmp_path, {"1-1": "　承認済み。"})
    (project / "scene_1-1.txt").write_text("　承認後に変更。", encoding="utf-8")

    with pytest.raises(UserFacingError, match="stale approval detected"):
        export_manuscript(str(project), require_complete=require_complete)

    assert not (project / "exports").exists()


def test_empty_new_chapter_adopts_consistent_global_scene_hyphen_style(tmp_path):
    previous = tmp_path / "chapter_1_opening"
    previous.mkdir()
    original = previous / "scene_1-1.txt"
    original.write_text("　既存本文。", encoding="utf-8")
    target = tmp_path / "chapter_2_ending"
    target.mkdir()

    result = suggest_scene_output_path(str(tmp_path), parse_scene_reference("2-1"))

    assert result == str(target / "scene_2-1.txt")
    assert original.read_text(encoding="utf-8") == "　既存本文。"
    assert list(target.iterdir()) == []


def test_empty_new_chapter_keeps_default_when_global_styles_are_mixed(tmp_path):
    (tmp_path / "scene_1-1.txt").write_text("一。", encoding="utf-8")
    (tmp_path / "chapter_2_scene_1.txt").write_text("二。", encoding="utf-8")

    result = suggest_scene_output_path(str(tmp_path), parse_scene_reference("3-1"))

    assert result == str(tmp_path / "chapter_3_scene_1.txt")


def test_scene_output_path_prefers_existing_target_over_global_style(tmp_path):
    (tmp_path / "scene_1-1.txt").write_text("一。", encoding="utf-8")
    target = tmp_path / "chapter_2_scene_1.txt"
    target.write_text("二。", encoding="utf-8")

    assert suggest_scene_output_path(str(tmp_path), parse_scene_reference("2-1")) == str(target)


def test_scene_output_path_rejects_ambiguous_new_chapter_directories(tmp_path):
    (tmp_path / "scene_1-1.txt").write_text("一。", encoding="utf-8")
    (tmp_path / "chapter_2_first").mkdir()
    (tmp_path / "chapter_2_second").mkdir()

    with pytest.raises(UserFacingError, match="ambiguous chapter directory"):
        suggest_scene_output_path(str(tmp_path), parse_scene_reference("2-1"))


def test_known_terminal_scene_brief_allows_closure_instead_of_forcing_unresolved_hook(tmp_path):
    project = Path(create_runtime_project(tmp_path))
    scene = parse_scene_reference("2-3")
    metadata = load_planning_metadata(str(project))

    brief = build_scene_brief(extract_chapter_block(RUNTIME_OUTLINE_TEXT, 2), scene, str(project), metadata)

    assert "Hook: 場面の決着と余韻（続きがある場合のみ接続）" in brief
    assert "次シーンで回収できる未解決要素を1つ残す" not in brief


def test_known_next_scene_purpose_is_preserved_in_scene_brief(tmp_path):
    project = Path(create_runtime_project(tmp_path))

    brief = build_scene_brief(
        extract_chapter_block(RUNTIME_OUTLINE_TEXT, 2), parse_scene_reference("2-2"),
        str(project), load_planning_metadata(str(project)),
    )

    assert "Hook: 障害を越えるために決断する" in brief


def test_draft_request_does_not_require_a_next_scene_hook(tmp_path):
    project = Path(create_runtime_project(tmp_path))
    request = build_request_compact(
        "draft", "balanced", parse_scene_reference("2-3"), load_planning_metadata(str(project)),
        {"min": 1000, "target": 1250, "max": 1500, "source": "Scene Ledger"},
    )

    assert "場面の決着と余韻（続きがある場合のみ接続）" in request
    assert "次シーンへ渡すフック" not in request
