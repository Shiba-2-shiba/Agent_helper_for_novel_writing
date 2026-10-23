# Selective dialogue context implementation plan

**Goal:** Carry character voice and selective limited-POV reception/reply nuance into real writing inputs, without imposing psychological narration on every line.

**Architecture:** Optional `dialogue_voice.json` contains only explicit compact voice cards and scene participant/POV routing. A bounded required runtime pack is consumed by the draft prompt; source and selection dependencies invalidate stale artifacts. Freeform character biographies remain out of the prompt to avoid future-knowledge leakage. Existing global conversation notes remain available.

**Tech stack:** Python 3.8+, standard library, pytest.
**Spec:** User-approved intent, documented in `docs/dialogue_context.md`.

## Constraints and review focus
- No manuscript changes, invented character facts, automatic biography extraction, prose quotas, or literary-quality pass claims.
- Missing/legacy configuration warns without blocking old projects; malformed explicit configuration fails clearly.
- Participants are explicit, separate from POV; selected POV is also available for response nuance.
- Voice pack is at most 3,000 characters and required in the existing 16,000-character prompt budget; overfull required context fails rather than silently dropping voices.
- Configuration creation, modification, removal and selection changes must invalidate generated context; unselected/future biography must never enter it.

## Implementation
- [x] Write failing regression tests for legacy 会話 routing, selected cards and POV, missing/invalid config, privacy and budget behavior.
- [x] Implement `novel_agent/dialogue_context.py` with validated schema, selection, rendering and warnings.
- [x] Write failing integration tests for prepare/prompt, selection recording and stale guards; integrate runtime, pipeline flags, draft and local expansion input.
- [x] Update writer/reviser/polisher/reviewer guidance and safe opt-in configuration documentation.
- [x] Run complete tests and compileall, test copied real scene 1-2 without modifying original project, get independent review and deliver local patch ZIP.

## Verification

- Untouched base: 390 tests passed. Final implementation: 416 tests passed on Python 3.12.14.
- `compileall` and Python 3.8 grammar parsing passed; Python 3.8 runtime was not available for this verification.
- Independent review findings were repaired with regressions: CLI selection invalidation, legacy internal callers, and downstream accepted-memory selection guards including races.
- Copied real scene 1-2 routing verified; all original project files remained unchanged. This is routing/safety verification, not a claim of literary-quality improvement.
