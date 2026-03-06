# Skill Refactor Rollback Runbook

## Scope
- Target: skill structure and routing docs (`agent/skills`, `agent/HUB.md`, `agent/AGENT_GUIDE.md`, `agent/evals/*`)
- Baseline snapshot: `agent/skills_inventory_snapshot_2026-03-05.txt`

## Preconditions
- Stop new edits while rollback is running.
- Keep a copy of current `agent/` before rollback.

## Rollback Level A (Docs only)
Use when eval docs or reports are the only issue.

1. Revert files under `agent/evals/prompts/`, `agent/evals/results/`, `agent/evals/templates/`, `agent/evals/README.md`.
2. Keep `agent/skills` and router docs unchanged.

## Rollback Level B (Router switch)
Use when routing behavior is incorrect after canonical path switch.

1. Restore previous versions of:
   - `agent/HUB.md`
   - `agent/AGENT_GUIDE.md`
2. Verify mappings point to valid skill files.
3. Re-run:
   - `python scripts/run_skill_eval_suite.py`

## Rollback Level C (Skill path migration)
Use when canonical `agent/skills/<skill-name>/SKILL.md` layout must be reverted.

1. For each file in `agent/skills/legacy/SKILL_*.md` (except `SKILL_planner.md`), restore full skill body from backup snapshot/state.
2. Move restored files back to `agent/skills/` root as `SKILL_*.md`.
3. Remove canonical subdirectories only after file-level verification.
4. Restore `agent/HUB.md` and `agent/AGENT_GUIDE.md` to root `SKILL_*.md` references.

## Verification After Any Rollback

1. Structural:
   - Required skill files exist on the selected structure.
2. Routing:
   - `agent/HUB.md` mappings all resolve to existing files.
3. Behavior:
   - `python scripts/run_skill_eval_suite.py` returns `overall_pass=True` for the active structure.

## Failure Handling

- If rollback breaks references, stop and restore `agent/` from the pre-rollback copy.
- Do not partially roll back `agent/HUB.md` without matching skill path structure.
