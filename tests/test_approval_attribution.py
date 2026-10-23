import json
from pathlib import Path
import subprocess
import sys

import pytest

from novel_agent.approvals import approve_scene, read_approval_ledger, validate_approval_current
from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.exports import export_manuscript
from novel_agent.storage import text_content_hash
from test_approval_identity import setup_checked


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def run_approve(project, *args, pipeline=False):
    command = [sys.executable, str(SCRIPTS / ("run_scene_pipeline.py" if pipeline else "approve_scene.py"))]
    if pipeline:
        command.append("approve")
    return subprocess.run(command + ["--project", str(project), "--scene", "1-1", *args],
                          capture_output=True, text=True)


def test_compatibility_api_never_defaults_to_human_approval(tmp_path):
    setup_checked(tmp_path)
    record = approve_scene(str(tmp_path), "1-1")
    assert record["approved_by"] == "unknown"
    assert record["reviewer_type"] == "unknown"
    assert record["reviewer_id"] == "unknown"


@pytest.mark.parametrize("reviewer_type", ["human", "agent", "automation"])
def test_explicit_reviewer_identity_is_persisted(tmp_path, reviewer_type):
    setup_checked(tmp_path)
    record = approve_scene(str(tmp_path), "1-1", reviewer_type=reviewer_type,
                           reviewer_id="reviewer-42", notes="Reviewed the current scene.")
    saved = read_approval_ledger(str(tmp_path))["scenes"]["1-1"]
    assert saved == record
    assert saved["reviewer_type"] == reviewer_type
    assert saved["reviewer_id"] == "reviewer-42"
    assert saved["approved_by"] == "reviewer-42"
    assert validate_approval_current(str(tmp_path), saved)["status"] == "approved"


@pytest.mark.parametrize("identity", [
    {"reviewer_type": "agent"},
    {"reviewer_id": "reviewer-42"},
    {"reviewer_type": "user", "reviewer_id": "reviewer-42"},
    {"reviewer_type": "agent", "reviewer_id": "  "},
    {"reviewer_type": "human", "reviewer_id": None},
])
def test_incomplete_or_invalid_identity_cannot_write_approval(tmp_path, identity):
    setup_checked(tmp_path)
    with pytest.raises(UserFacingError, match="reviewer"):
        approve_scene(str(tmp_path), "1-1", **identity)
    assert not (tmp_path / "runtime/approval_ledger.json").exists()


@pytest.mark.parametrize("legacy_by", [None, "user", "old-agent"])
@pytest.mark.parametrize("version", [1, 2])
def test_legacy_attribution_is_unknown_without_rewriting_or_invalidating_approval(tmp_path, legacy_by, version):
    text, report_path = setup_checked(tmp_path)
    record = json.loads(report_path.read_text()) if version == 2 else {"version": 1}
    record.update(status="approved", scene_path="scene_1-1.txt",
                  content_hash=text_content_hash(str(text)), check_status="pass")
    if legacy_by is not None:
        record["approved_by"] = legacy_by
    ledger = tmp_path / "runtime/approval_ledger.json"
    ledger.write_text(json.dumps({"version": 1, "scenes": {"1-1": record}}))
    before = ledger.read_bytes()

    current = read_approval_ledger(str(tmp_path))["scenes"]["1-1"]
    assert current["reviewer_type"] == "unknown"
    assert current["reviewer_id"] == "unknown"
    assert current["approved_by"] == "unknown"
    assert current.get("legacy_approved_by") == legacy_by
    assert validate_approval_current(str(tmp_path), current)["status"] == "approved"
    assert export_manuscript(str(tmp_path))["scenes"] == ["1-1"]
    assert ledger.read_bytes() == before

    text.write_text("本文を改稿した。")
    assert validate_approval_current(str(tmp_path), current)["status"] == "stale"


def test_legacy_api_keyword_is_retained_as_unverified_evidence(tmp_path):
    setup_checked(tmp_path)
    record = approve_scene(str(tmp_path), "1-1", approved_by="user")
    assert record["approved_by"] == "unknown"
    assert record["legacy_approved_by"] == "user"
    assert record["reviewer_type"] == "unknown"


@pytest.mark.parametrize("attribution", [
    {"reviewer_type": "human", "approved_by": "user"},
    {"reviewer_id": "codex"},
    {"reviewer_type": "agent", "reviewer_id": "  "},
    {"reviewer_type": "user", "reviewer_id": "user"},
    {"reviewer_type": "unknown", "reviewer_id": "user"},
    {"reviewer_type": "agent", "reviewer_id": "codex", "approved_by": "user"},
])
def test_malformed_explicit_attribution_is_not_reported_as_known_reviewer(tmp_path, attribution):
    setup_checked(tmp_path)
    ledger = tmp_path / "runtime/approval_ledger.json"
    ledger.write_text(json.dumps({"version": 1, "scenes": {"1-1": attribution}}))
    before = ledger.read_bytes()
    with pytest.raises(DataCorruptionError, match="reviewer"):
        read_approval_ledger(str(tmp_path))
    assert ledger.read_bytes() == before


def test_later_ledger_write_keeps_original_legacy_attribution_evidence(tmp_path):
    setup_checked(tmp_path)
    ledger = tmp_path / "runtime/approval_ledger.json"
    ledger.write_text(json.dumps({"version": 1, "scenes": {"1-2": {"approved_by": "user"}}}))
    approve_scene(str(tmp_path), "1-1", reviewer_type="agent", reviewer_id="codex")
    old_record = json.loads(ledger.read_text())["scenes"]["1-2"]
    assert old_record["legacy_approved_by"] == "user"
    assert old_record["approved_by"] == "unknown"
    assert old_record["reviewer_type"] == "unknown"
    assert read_approval_ledger(str(tmp_path))["scenes"]["1-2"] == old_record


@pytest.mark.parametrize("pipeline", [False, True])
@pytest.mark.parametrize("args", [(), ("--reviewer-type", "agent"), ("--reviewer-id", "codex")])
def test_cli_requires_both_reviewer_fields_before_approval(tmp_path, pipeline, args):
    setup_checked(tmp_path)
    result = run_approve(tmp_path, *args, pipeline=pipeline)
    assert result.returncode != 0
    assert "reviewer" in result.stdout + result.stderr
    assert not (tmp_path / "runtime/approval_ledger.json").exists()


@pytest.mark.parametrize("pipeline", [False, True])
def test_cli_records_agent_not_user(tmp_path, pipeline):
    setup_checked(tmp_path)
    result = run_approve(tmp_path, "--reviewer-type", "agent", "--reviewer-id", "codex",
                         pipeline=pipeline)
    assert result.returncode == 0, result.stdout + result.stderr
    record = read_approval_ledger(str(tmp_path))["scenes"]["1-1"]
    assert record["reviewer_type"] == "agent"
    assert record["reviewer_id"] == "codex"
    assert record["approved_by"] == "codex"


def test_revoke_does_not_require_new_reviewer_or_rewrite_original_identity(tmp_path):
    setup_checked(tmp_path)
    approve_scene(str(tmp_path), "1-1", reviewer_type="agent", reviewer_id="codex")
    result = run_approve(tmp_path, "--revoke")
    assert result.returncode == 0, result.stdout + result.stderr
    record = read_approval_ledger(str(tmp_path))["scenes"]["1-1"]
    assert record["status"] == "revoked"
    assert record["reviewer_type"] == "agent"
    assert record["reviewer_id"] == "codex"
