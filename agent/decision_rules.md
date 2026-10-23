# Decision Rules (Common)

## Safety
- Do not delete files unless explicitly requested.
- Do not overwrite user content without confirmation.
- Prefer additive changes and clear diffs.
- Treat scene-level `txt` files as the prose source of truth in normal novel workflow.
- Do not use `body.md` as a prose append target unless the task is specifically about chapter-direction notes or large-scale restructuring.

## Scope Control
- Ask for clarification if requirements are missing or conflicting.
- Keep outputs limited to requested scope.
- Prefer the single best-fit skill for the current task instead of mixing drafting, audit, and revision in one pass.
- When backlog state and file reality disagree, inspect the actual files before deciding the next action.

## Evidence
- If uncertain, mark assumptions explicitly.
- When changing behavior, record rationale in `decisions_log.md`.
- For resume decisions, check current state files (`state_schema`, `session_notes`, backlog docs) before acting on stale memory.

## Legacy Migration
- Distinguish between legacy project rules and the new default operating standard.
- Do not silently normalize old projects to a new Length Band; keep the existing scene contract unless a change is authorized.
- When migrating a legacy project, audit first, then revise high-impact scenes before broad consistency cleanup.

## Evidence-bound approval and memory
- Never use another scene's runtime or a stale report to approve prose.
- A mechanical pass is not a literary assessment or user acceptance.
- Proposed memory is not accepted memory. Only valid approved prose can support accepted facts; planning is separately labeled.
- Do not bypass revision/hash conflicts or discard corrupt ledgers. Review and repair the source first.
