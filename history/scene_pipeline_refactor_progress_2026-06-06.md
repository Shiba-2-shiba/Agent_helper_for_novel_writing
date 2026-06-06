# Scene Pipeline Refactor Progress

Date: 2026-06-06

## Current State

- Overall Status: implemented
- Spec Status: drafted
- Implementation Status: phase_1_to_5_complete
- Validation Status: passing
- Handoff Status: ready_for_use

## Baseline

Before implementation:

```bash
python -m pytest tests/ -q
```

Result:

- `79 passed in 6.90s`

Latest validation:

```bash
python -m pytest tests/ -q
```

Result:

- `87 passed in 8.51s`

## Created Planning Artifacts

- `history/scene_pipeline_refactor_spec_2026-06-06.md`
- `history/scene_pipeline_refactor_progress_2026-06-06.md`
- `history/scene_pipeline_refactor_tasks_2026-06-06.md`

## Phase Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Behavior Lock | completed | Baseline was green. |
| 1 | Thin Integrated CLI / Orchestrator | completed | `run_scene_pipeline.py` wraps prepare/prompt/check/repair/approve/export/health. |
| 2 | Approval Gate and Export | completed | `approval_ledger.json`, `approve_scene.py`, and Markdown export added. |
| 3 | Scene Obligation Contract | completed | `obligation_contract.json` generated and dependency gaps become blocking check issues. |
| 4 | Memory Sync / Project Health Check | completed | `sync_project_health.py` writes `health_report.json` and supports `--fix-safe`. |
| 5 | Anti-AI Style Gate | completed | Conservative deterministic style warnings added to `check_report.json`. |
| 6 | Documentation Update | completed | README, HUB, and skill docs updated. |

## Completed

- Added `scripts/run_scene_pipeline.py`.
- Added `scripts/approve_scene.py`.
- Added `scripts/export_manuscript.py`.
- Added `scripts/sync_project_health.py`.
- Added `scripts/novel_agent/approvals.py`.
- Added `scripts/novel_agent/exports.py`.
- Added `scripts/novel_agent/obligations.py`.
- Added `scripts/novel_agent/health.py`.
- Added `scripts/novel_agent/anti_ai_style.py`.
- Updated `build_runtime_context.py` to write `obligation_contract.json` and include an obligation summary in `scene_brief_compact.md`.
- Updated `check_scene_output.py` to include `obligation_status`, `obligation_issues`, and `anti_ai_style`.
- Updated quality budget evaluation so obligation failures do not route into expansion.
- Added regression tests for approval gates, export, stale approval, pipeline wrapper, obligation contracts, health check, and anti-AI warnings.

## Known Risks

- The integrated CLI is intentionally thin and still delegates to existing scripts; deeper function extraction can be done later.
- Obligation checks are deterministic and conservative; creative semantic fulfillment remains a human/agent audit task.
- Anti-AI style checks can false-positive and are warning-only by design.
- Export currently supports Markdown only.
- Health `--fix-safe` regenerates derived artifacts only; it does not repair outline or prose.

## Next Recommended Action

Use the new pipeline on a real project:

```bash
python scripts/run_scene_pipeline.py prepare --project <project> --chapter 2 --scene 2-3
python scripts/run_scene_pipeline.py prompt --project <project>
python scripts/run_scene_pipeline.py check --project <project> --text <scene_txt>
python scripts/run_scene_pipeline.py approve --project <project> --scene 2-3
python scripts/run_scene_pipeline.py export --project <project>
python scripts/run_scene_pipeline.py health --project <project> --fix-safe
```

## Evidence Log

- 2026-06-06: Baseline verified: `79 passed in 6.90s`.
- 2026-06-06: Planning artifacts created.
- 2026-06-06: Scene pipeline refactor phases 1-5 implemented.
- 2026-06-06: Validation: `87 passed in 8.51s`.
