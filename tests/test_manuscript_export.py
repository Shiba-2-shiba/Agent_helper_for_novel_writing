from pathlib import Path
import subprocess
import sys

import pytest

from novel_agent.exports import export_manuscript
from novel_agent.storage import atomic_write_json, text_content_hash
from prompt_utils import UserFacingError


def approved_project(tmp_path, scene_texts):
    """Use real hash-bound legacy approvals, without fabricating current checks."""
    project = tmp_path / "project"
    project.mkdir()
    records = {}
    for scene_id, text in scene_texts.items():
        scene_path = project / f"scene_{scene_id}.txt"
        scene_path.write_text(text, encoding="utf-8")
        records[scene_id] = {
            "status": "approved",
            "scene_path": scene_path.name,
            "content_hash": text_content_hash(str(scene_path)),
            "check_status": "pass",
        }
    atomic_write_json(str(project / "runtime" / "approval_ledger.json"), {"version": 1, "scenes": records})
    return project


def test_export_retains_scene_boundary_whitespace_and_fullwidth_indentation(tmp_path):
    first = "\n　最初の場面。　 \n\n"
    second = "　次の場面。\t "
    project = approved_project(tmp_path, {"1-1": first, "1-2": second})
    originals = {path: path.read_bytes() for path in project.glob("scene_*.txt")}

    result = export_manuscript(str(project))

    manuscript = Path(result["output_path"]).read_text(encoding="utf-8")
    assert manuscript == "# project\n\n## 第1章\n\n" + first + "\n\n" + second + "\n\n"
    assert result["scenes"] == ["1-1", "1-2"]
    assert {path: path.read_bytes() for path in originals} == originals


def test_export_cli_uses_explicit_title_instead_of_directory_name(tmp_path):
    project = approved_project(tmp_path, {"1-1": "　本文。"})
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_manuscript.py"

    result = subprocess.run([sys.executable, str(script), "--project", str(project), "--title", "買ってないコロッケ"], capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "exports" / "manuscript.md").read_text(encoding="utf-8").startswith("# 買ってないコロッケ\n\n")


def test_export_preserves_original_scene_line_endings(tmp_path):
    text = "　最初の行。\r\n　次の行。\r\n\r\n"
    project = approved_project(tmp_path, {"1-1": text})

    result = export_manuscript(str(project))

    assert text.encode("utf-8") in Path(result["output_path"]).read_bytes()


@pytest.mark.parametrize("title", ["", "　 ", "作品名\n## 偽の章"])
def test_export_rejects_empty_or_multiline_explicit_title(tmp_path, title):
    project = approved_project(tmp_path, {"1-1": "　本文。"})

    with pytest.raises(UserFacingError, match="title"):
        export_manuscript(str(project), title=title)

    assert not (project / "exports" / "manuscript.md").exists()
