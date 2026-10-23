"""Draft and resume must describe the same requested scene's length contract."""
from pathlib import Path
import subprocess
import sys

import pytest

from novel_agent.errors import UserFacingError
from novel_agent.runtime_paths import require_runtime_current
from test_scripts import RUNTIME_OUTLINE_TEXT, SCRIPTS_DIR, create_runtime_project


def prepare(project, mode):
    result = subprocess.run(
        [sys.executable, str(Path(SCRIPTS_DIR) / "build_runtime_context.py"),
         "--project", str(project), "--chapter", "2", "--scene", "2-3", "--mode", mode],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return project / "runtime" / "scenes" / "2-3" / mode


def target_outline(band):
    return RUNTIME_OUTLINE_TEXT.replace(
        "| 1000 | 1250 | 1500 | 2-2 | planned |", band + " | 2-2 | planned |",
    )


@pytest.mark.parametrize("mode", ["draft", "resume"])
def test_runtime_uses_requested_scene_ledger_band(tmp_path, mode):
    project = Path(create_runtime_project(tmp_path, outline_text=target_outline("| 1600 | 2000 | 2400")))
    runtime = prepare(project, mode)
    assert "Target Band: 1600 / 2000 / 2400" in (runtime / "request_compact.md").read_text()
    assert "初稿: 1600 / 2000 / 2400 字" in (runtime / "style_contract_compact.md").read_text()
    require_runtime_current(str(project), str(runtime))


@pytest.mark.parametrize("mode", ["draft", "resume"])
def test_runtime_uses_requested_scene_type_when_ledger_band_missing(tmp_path, mode):
    project = Path(create_runtime_project(tmp_path, outline_text=target_outline("| - | - | -")))
    state = project / "agent" / "state_schema_novel.yaml"
    state.write_text(state.read_text().replace("targets:\n", "targets:\n  scene_type_bands:\n    standard:\n      min: 1700\n      target: 2100\n      max: 2500\n"))
    runtime = prepare(project, mode)
    assert "Target Band: 1700 / 2100 / 2500" in (runtime / "request_compact.md").read_text()
    assert "初稿: 1700 / 2100 / 2500 字" in (runtime / "style_contract_compact.md").read_text()


def test_resume_reports_missing_contract_without_refusing_recovery(tmp_path):
    project = Path(create_runtime_project(tmp_path, outline_text=""))
    runtime = prepare(project, "resume")
    for name in ("request_compact.md", "style_contract_compact.md"):
        text = (runtime / name).read_text()
        assert "unknown" in text
        assert "legacy fallback" in text
    assert (runtime / "resume_brief.md").is_file()


def test_resume_keeps_requested_band_when_missing_dependency_redirects_work(tmp_path):
    project = Path(create_runtime_project(tmp_path, outline_text=target_outline("| 1600 | 2000 | 2400")))
    (project / "chapter_1_scene_1.txt").write_text("導入の本文。\n")
    (project / "chapter_2_scene_3.txt").write_text("対象の本文。\n")
    (project / "chapter_2_scene_2.txt").unlink()
    runtime = prepare(project, "resume")
    assert "Target Band: 1600 / 2000 / 2400" in (runtime / "request_compact.md").read_text()
    assert "Reason: 2-3 depends_on 2-2" in (runtime / "resume_brief.md").read_text()


def test_changed_ledger_band_invalidates_resume(tmp_path):
    project = Path(create_runtime_project(tmp_path, outline_text=target_outline("| 1600 | 2000 | 2400")))
    runtime = prepare(project, "resume")
    require_runtime_current(str(project), str(runtime))
    outline = project / "05_chapter_outline_100k.md"
    outline.write_text(outline.read_text().replace("| 1600 | 2000 | 2400", "| 1800 | 2200 | 2600"))
    with pytest.raises(UserFacingError, match="stale"):
        require_runtime_current(str(project), str(runtime))
