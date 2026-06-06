# VCC Context Refactor Progress

Date: 2026-06-06

## Current State

- Overall Status: implemented
- Spec Status: drafted
- Implementation Status: phase_1_to_7_complete
- Validation Status: passing
- Handoff Status: ready_for_use

## Baseline

Latest validation:

```bash
python -m pytest tests/ -q
```

Result:

- `74 passed in 5.73s`

Baseline before implementation:

- `61 passed in 4.01s`

## Created Planning Artifacts

- `history/refactor_direction_reassessment_with_vcc_2026-06-06.md`
- `history/vcc_context_refactor_spec_2026-06-06.md`
- `history/vcc_context_refactor_progress_2026-06-06.md`
- `history/vcc_context_refactor_tasks_2026-06-06.md`

## Phase Status

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Behavior Lock | completed | Baseline was green before implementation. |
| 1 | Deterministic Quality Gate | completed | `status`, severity fields, and `text_quality.py` added. |
| 2 | Context Compiler MVP | completed | `compile_project_context.py` writes full/min/search views. |
| 3 | Runtime Stale Detection | completed | `artifact_ledger.json` and stale warning path added. |
| 4 | Token Ledger | completed | `token_ledger.jsonl` records prompt/projection estimates. |
| 5 | Story State MVP | completed | `story_state.json` updates from scene checks. |
| 6 | Related Context View | completed | `scene_summaries.jsonl` and `related_context_pack.md` added. |
| 7 | Agent Trace Compiler | completed | `trace.jsonl` and full/min/search trace views added. |

## Completed

- Local reference repositories were inspected from `../参考`.
- VCC was identified as the highest-leverage reference.
- Previous refactor direction was revised away from immediate RAG/DB adoption.
- Refactor direction now centers on source artifacts, projections, block pointers, deterministic gates, and ledgers.
- Detailed phase specification was written.
- Task checklist was prepared.
- Phase 1 implemented and validated.
- Phase 2 implemented and validated.
- Phase 3 implemented and validated.
- Phase 4 implemented and validated.
- Phase 5 implemented and validated.
- Phase 6 implemented and validated.
- Phase 7 implemented and validated.
- README, HUB, `novel-writer`, and `resume-orchestrator` docs updated with new context/trace references.

## In Progress

- None.

## Not Started

- Full quality budget ledger is not yet implemented; the numbered 1-7 phases did not require it directly, but the architecture notes still identify it as useful follow-up.

## Known Risks

- `prompt_utils.py` is already large; careless extraction can create circular imports.
- `build_runtime_context.py` owns too many responsibilities and should be changed incrementally.
- Existing tests are concentrated in `tests/test_scripts.py`; new tests may make the file harder to navigate unless grouped carefully.
- Stale detection via hash must not mark user-edited protected artifacts as disposable.
- Related context selection must avoid prompt bloat; pointer-first output is required.
- `story_state.json` must not become another free-form summary sink.
- Trace logging must not leak full generated prose into every event.
- Quality budget loop limiting remains a follow-up if repeated repair attempts become a real cost sink.

## Next Recommended Action

Use the new runtime helpers on a real project and inspect token/context reduction:

1. Run `build_runtime_context.py` and `build_draft_prompt.py` on an active scene.
2. Run `compile_project_context.py --grep <keyword>` to verify pointer recovery.
3. Check `runtime/token_ledger.jsonl` and `runtime/artifact_ledger.json`.
4. If repeated repair loops appear, implement the deferred quality budget ledger.

## Stop Conditions

Pause implementation if:

- Baseline tests fail before any code change.
- The new report schema requires removing existing fields.
- A phase requires a new dependency.
- Prompt size increases instead of decreasing.
- The implementation needs to rewrite project directory layout.

## Evidence Log

- 2026-06-06: Created this planning set.
- 2026-06-06: Implemented phases 1-7. Validation: `74 passed in 5.73s`.
