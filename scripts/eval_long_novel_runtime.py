#!/usr/bin/env python3
"""Measure real CLI work on an isolated project copy; never call an LLM.

File-read metrics count Python audit read-capable ``open`` attempts on project
files, excluding create/truncate/append opens. They are not OS read syscalls,
cache misses, successful-read guarantees, or bytes. Wall time includes process
startup and audit instrumentation. Latency is diagnostic, never a quality gate.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from prompt_utils import UserFacingError, collect_scene_metadata

SCRIPT_DIR = Path(__file__).resolve().parent

# Run the actual script entry point in a fresh interpreter. The small audit
# wrapper observes I/O without replacing any application function or report.
AUDITED_ENTRY = r'''
import json, os, runpy, sys
project, metrics, script = sys.argv[1:4]
arguments = sys.argv[4:]
project = os.path.realpath(project)
reads = []
def audit(event, args):
    if event != "open" or not isinstance(args[0], (str, bytes)):
        return
    path, mode, flags = args
    path = os.path.realpath(os.fsdecode(path))
    if os.path.commonpath([project, path]) != project:
        return
    # os.open used by atomic writers may request O_RDWR while only writing.
    # Count existing-source read opens, not creation/truncation/append events.
    if isinstance(flags, int) and flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        return
    if isinstance(mode, str) and any(letter in mode for letter in "wax"):
        return
    readable = (isinstance(mode, str) and ("r" in mode or "+" in mode)) or (
        mode is None and isinstance(flags, int) and flags & os.O_ACCMODE != os.O_WRONLY)
    if readable:
        reads.append(os.path.relpath(path, project))
sys.addaudithook(audit)
sys.path.insert(0, os.path.dirname(script))
sys.argv = [script] + arguments
try:
    runpy.run_path(script, run_name="__main__")
finally:
    payload = {"read_open_events": len(reads), "project_files_read": sorted(set(reads)),
               "unique_project_files_read": len(set(reads))}
    with open(metrics, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
'''


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hashes(project):
    return {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(project.rglob("*")) if p.is_file()}


def evaluate(project_dir):
    source = Path(project_dir).resolve()
    if not source.is_dir():
        raise ValueError("project directory not found: {}".format(source))
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("evaluation copy refuses symlinks; use a self-contained scratch fixture")
    original_hashes = _hashes(source)
    report = {
        "version": 1, "evaluation_kind": "deterministic_runtime_regression",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "status": "fail", "project": str(source),
        "execution_scope": "isolated_temporary_copy", "commands": [],
        "metric_definitions": {
            "elapsed_seconds": "perf_counter wall time including interpreter startup and audit instrumentation",
            "read_open_events": "Python audit read-capable open attempts under the isolated project, excluding create/truncate/append opens; not kernel read syscalls",
            "unique_project_files_read": "Distinct project-relative paths in those read-capable open events",
            "candidate_scene_count": "All scene files returned by the real collect_scene_metadata API",
            "past_candidate_scene_count": "Discovered scene files numerically before the target; not selected-context count",
        },
        "candidate_scene_count": None, "past_candidate_scene_count": None, "prompt_chars": None,
        "export": {"scene_count": None}, "stale_detection": {"detected": False},
        "agent_evaluation": {"status": "not_run", "reason": "No model or external agent was invoked."},
    }
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="long-novel-eval-") as temporary:
        work = Path(temporary) / "project"
        shutil.copytree(str(source), str(work))

        def run(script, args, expect_success=True):
            stats = Path(temporary) / "io-{}.json".format(len(report["commands"]))
            command = [sys.executable, "-c", AUDITED_ENTRY, str(work), str(stats),
                       str(SCRIPT_DIR / script)] + [str(value) for value in args]
            before = time.perf_counter()
            result = subprocess.run(command, capture_output=True, text=True)
            elapsed = time.perf_counter() - before
            metrics = _json(stats) if stats.exists() else {
                "read_open_events": None, "project_files_read": [], "unique_project_files_read": None}
            entry = dict(metrics, script=script, arguments=[str(v).replace(str(work), "<isolated-project>") for v in args],
                         elapsed_seconds=elapsed, returncode=result.returncode,
                         expected_success=expect_success, stdout=result.stdout, stderr=result.stderr)
            report["commands"].append(entry)
            if (result.returncode == 0) != expect_success:
                raise RuntimeError("{} returned {}: {}{}".format(script, result.returncode, result.stdout, result.stderr))
            return result

        try:
            scenes = collect_scene_metadata(str(work))
            report["candidate_scene_count"] = len(scenes)
            if not scenes:
                raise ValueError("project has no scene text; generate a fixture first")
            target = sorted(scenes, key=lambda s: (s["chapter"], s["scene"]))[-1]
            target_id = "{}-{}".format(target["chapter"], target["scene"])
            report["target_scene_id"] = target_id
            report["past_candidate_scene_count"] = sum(
                (s["chapter"], s["scene"]) < (target["chapter"], target["scene"]) for s in scenes)
            directory = work / "runtime" / "scenes" / target_id / "draft"
            run("build_runtime_context.py", ["--project", work, "--chapter", target["chapter"], "--scene", target_id, "--mode", "draft"])
            run("build_draft_prompt.py", ["--project", work, "--scene", target_id, "--runtime_dir", directory])
            report["prompt_chars"] = len((directory / "draft_prompt.txt").read_text(encoding="utf-8"))
            if report["prompt_chars"] > 16000:
                raise RuntimeError("final prompt exceeds the 16000-character budget")
            target_path = Path(target["path"])
            run("check_scene_output.py", ["--project", work, "--text", target_path, "--runtime_dir", directory])
            checked = _json(directory / "check_report.json")
            expected_hash = hashlib.sha256(target_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            if checked.get("version") != 2 or checked.get("scene_id") != target_id or checked.get("source_hash") != expected_hash:
                raise RuntimeError("check report is not bound to the actual scene text")
            if checked.get("status") not in ("pass", "warning") or checked.get("blocking_issues"):
                raise RuntimeError("real scene check did not permit approval: {}".format(checked.get("status")))
            report["check_status"] = checked["status"]
            report["check_warnings"] = checked.get("warnings", [])
            approve_args = ["--project", work, "--scene", target_id,
                            "--reviewer-type", "automation", "--reviewer-id", "eval_long_novel_runtime",
                            "--notes", "Synthetic fixture evaluation; not human or semantic review."]
            if checked["status"] == "warning":
                approve_args.append("--allow-warnings")
            run("approve_scene.py", approve_args)
            exported = run("export_manuscript.py", ["--project", work, "--include-warnings"])
            count = re.search(r"manuscript exported scenes=(\d+)", exported.stdout)
            if not count:
                raise RuntimeError("export did not report its real scene count")
            manuscript = (work / "exports" / "manuscript.md").read_text(encoding="utf-8")
            if target_path.read_text(encoding="utf-8").strip() not in manuscript:
                raise RuntimeError("export is missing the checked source text")
            report["export"] = {"scene_count": int(count.group(1)), "chars": len(manuscript),
                                "sha256_utf8_text": hashlib.sha256(manuscript.encode("utf-8")).hexdigest()}
            # An intentional edit only in the disposable copy exercises actual
            # stale-approval detection. Never fabricate a stale flag in a ledger.
            target_path.write_text(target_path.read_text(encoding="utf-8") + "\n検証用の改稿。", encoding="utf-8")
            rejected = run("export_manuscript.py", ["--project", work, "--include-warnings"], expect_success=False)
            ledger = _json(work / "runtime" / "approval_ledger.json")
            stale = ledger.get("scenes", {}).get(target_id, {}).get("status") == "stale"
            report["stale_detection"] = {"detected": stale, "probe": "target text changed on isolated copy",
                                          "export_returncode": rejected.returncode}
            if not stale:
                raise RuntimeError("edited target approval was not marked stale")
            report["status"] = "pass"
        except (OSError, ValueError, RuntimeError, KeyError, UserFacingError) as exc:
            report["error"] = str(exc)
    report["elapsed_seconds"] = time.perf_counter() - started
    report["original_project_unchanged"] = original_hashes == _hashes(source)
    if not report["original_project_unchanged"]:
        report["status"] = "fail"
        report["error"] = "original project changed during evaluation (including possible concurrent edits)"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.project)
    except (ValueError, OSError) as exc:
        result = {"evaluation_kind": "deterministic_runtime_regression", "status": "fail", "error": str(exc),
                  "agent_evaluation": {"status": "not_run"}}
    destination = Path(args.json_out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("{}: runtime evaluation {}; agent evaluation not_run".format(
        "OK" if result["status"] == "pass" else "ERROR", result["status"]))
    print("Report: {}".format(destination))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
