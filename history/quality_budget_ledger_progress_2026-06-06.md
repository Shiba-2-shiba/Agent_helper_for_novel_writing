# Quality Budget Ledger Progress

Date: 2026-06-06

## Current State

- Overall Status: implemented
- Spec Status: drafted
- Implementation Status: phase_0_to_5_complete
- Validation Status: passing
- Handoff Status: ready_for_use

## Baseline

Latest validation:

```bash
python -m pytest tests/ -q
```

Result:

- `79 passed in 6.88s`

Baseline before this feature:

- `74 passed in 5.58s`

## Created Planning Artifacts

- `history/quality_budget_ledger_implementation_plan_2026-06-06.md`
- `history/quality_budget_ledger_progress_2026-06-06.md`
- `history/quality_budget_ledger_tasks_2026-06-06.md`

## Phase Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Behavior Lock | completed | Baseline was green before implementation. |
| 1 | Ledger Helpers | completed | Quality budget helper functions added to `scripts/novel_agent/ledgers.py`. |
| 2 | Check Report Integration | completed | `check_scene_output.py` updates `quality_budget_ledger.json`. |
| 3 | Expand Prompt Budget Gate | completed | `build_expand_prompt.py` blocks repeated or inappropriate expansion and supports `--force`. |
| 4 | Apply Edit Action Tracking | completed | `apply_expand_edits.py` records applied expand edits. |
| 5 | Documentation / Reporting | completed | README/HUB/skill docs updated; optional report CLI deferred. |

## Completed

- Reviewed the existing VCC refactor docs.
- Identified current connection points:
  - `scripts/check_scene_output.py`
  - `scripts/build_expand_prompt.py`
  - `scripts/apply_expand_edits.py`
  - `scripts/novel_agent/ledgers.py`
- Chose JSON ledger design under `<project>/runtime/quality_budget_ledger.json`.
- Defined default budget policy:
  - max scene repair prompts: 3
  - max attempts per issue: 2
  - max expand without recheck: 1
  - block expansion for format / forbidden / over max failures
- Drafted implementation plan.
- Drafted task checklist.
- Implemented `runtime/quality_budget_ledger.json` helpers.
- Connected `check_scene_output.py` to update open/resolved issues.
- Connected `build_expand_prompt.py` to block repeated or inappropriate expansion before prompt generation.
- Added `--force` override with ledger recording.
- Connected `apply_expand_edits.py` to record local edit application.
- Updated README, HUB, `novel-writer`, and `revision-editor` docs.
- Added regression coverage for under-min issue tracking, pass resolution, repeated expand blocking, force override, format violation blocking, and apply action tracking.
- Validation completed: `python -m pytest tests/ -q` -> `79 passed in 6.88s`.

## In Progress

- None.

## Not Started

- Optional `report_quality_budget.py`.

## Known Risks

- `build_expand_prompt.py` now blocks `needs_expand=false` unless `--force` is used; this is intentional but stricter than the earlier warning-only behavior.
- `format_violations` and `forbidden_hits` are now blocked for expansion; users should route those cases to revision or manual repair.
- `tests/test_scripts.py` is already large; new tests should be grouped clearly.
- Ledger policy must not save full scene prose.
- Budget exhaustion must be easy to override intentionally, but not silently.

## Next Recommended Action

Use the new quality budget gate in a real scene repair loop:

1. Run `check_scene_output.py` on a short draft.
2. Run `build_expand_prompt.py`; confirm first under-min expansion is allowed.
3. Try a second expansion before recheck; confirm it is blocked.
4. Apply edits and rerun `check_scene_output.py`.
5. Inspect `runtime/quality_budget_ledger.json`.

## Stop Conditions

Pause implementation if:

- Existing tests fail before code changes.
- The plan requires removing existing `check_report.json` fields.
- A new dependency becomes necessary.
- Budget gate would block normal first-time expansion.
- Any implementation stores full scene prose in the ledger.

## Evidence Log

- 2026-06-06: Created quality budget ledger planning set.
- 2026-06-06: Implemented quality budget ledger. Validation: `79 passed in 6.88s`.
