# Fantasy Trial Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkboxes for tracking.

**Goal:** Fix the four confirmed real-manuscript failures without weakening provenance and knowledge boundaries.
**Architecture:** Compact dependency guards retain original-source verification; scene-scoped voice guards avoid unrelated invalidation; content-bound dialogue reviews complement mechanical checks.
**Tech Stack:** Python standard library; pytest development tests.
**Spec:** docs/superpowers/specs/2026-10-25-fantasy-trial-design.md

## Global Constraints
- Python 3.8 and 3.12; no new runtime dependency.
- No push, no original novel rewrite, no implicit legacy approval promotion.
- Tampered, missing, stale, cyclic dependency evidence remains blocking.
- Dialogue candidate count is not a literary pass/fail rule; preserve intentional comic/fast exchanges.

## Review Focus
- Mixed legacy/new artifacts and approvals survive safe reading, not silent evidence laundering.
- Relevant voice deletion/POV changes fail, irrelevant character edits remain valid.
- Future secrets cannot appear in normal writer manifest/bundle; original-source change remains detected.
- Stale/empty/quote-mismatched dialogue review records cannot satisfy a new review requirement; machine validation does not prove literary honesty.
- Interrupted writes remain atomic; source mutation between checks cannot be accepted.

### Task 1: Compact, scoped and safe dependency guards
Files: scripts/novel_agent/dependencies.py, ledgers.py, runtime_paths.py, dialogue_context.py as needed; targeted tests.
- [x] Reproduce size/latency and old voice invalidation with copied real project.
- [x] Add failing tests for compact guards, legacy compatibility, tamper/stale recursion, relevant vs irrelevant voice changes and safe manifest.
- [x] Implement bounded hash-based evidence without recursive full value copies; expose current writer-safe validation metadata.
- [x] Run targeted and full regression; compare fixture outputs and protections; commit and review.

### Task 2: Evidence-bound dialogue review
Files: new dialogue_review module/CLI, text_quality.py, approvals.py, check/approve entrypoints, tests, writer/reviser/auditor docs.
- [x] Add failing tests extracting consecutive and short-beat-separated candidates; preserve source ranges and hashes.
- [x] Add structured keep/revise/uncertain judgement, explicit evidence/reason, current content hash and revision comparison.
- [x] Enforce review where newly checked dialogue candidates require it; legacy approvals stay historical without being called literary pass.
- [x] Demonstrate 3-1 question compression, 5-2 reception nuance, and retained comic quick dialogue on copies.
- [x] Run targeted and full regression; commit and review.

### Task 3: Ancillary safe fixes and integration
Files: health/export/resume/prompt entrypoints and docs only where reproduced bugs warrant.
- [x] Reproduce before changing; add failing tests.
- [x] Fix health fail exit status and incomplete export handling without silently discarding existing workflows; clarify deferred UX/semantic features.
- [x] Integrate documentation, tests, representative prose comparisons, and real-project benchmark report.
- [x] Run Python3.8/3.12 full pytest and compileall; independent whole-branch review; fix and reverify.
- [x] Package patch/bundle/report with exact commit, source baseline and honest verification limits; no publication.

## Verified completion

- Code commit: `26e3ac95a100f93c0e9e73d8b04c93ddb5968192`.
- Full regression: Python 3.12.14 and 3.8.20 each **557 passed**; both compile checks passed.
- Independent final review findings resolved and scoped re-review passed.
- Real 25-scene replay: same 316 artifact paths, active ledger 132,801,332 → 8,064,512 bytes; original source/approval/memory hashes unchanged, 25 approvals and 97 accepted memories remain active.
- Copied prose: 36 CLI operations, seven rejected approvals leave ledger bytes unchanged; final-code revalidation and strict export pass for all three examples.
- Local patch and prerequisite-bound bundle verified. Deliverable ZIP/report/comparison TXT are saved separately; branch retained, no push or original novel rewrite.
- Limits: candidate extraction is heuristic; evidence validation is not a literary classifier; optional manual spans and automatic world/knowledge chronology remain deferred.
