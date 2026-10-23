# Novel trial findings implementation plan

**Goal:** Correct reproducible workflow defects from the completed 25-scene evaluation without rewriting the novel.

**Architecture:** Retain the validated performance patch and existing provenance model. Add narrowly scoped regressions around CLI attribution, runtime contracts, source pointers, Japanese text segmentation and export; preserve existing stale/tamper guards.

**Constraints:** No publication; Python 3.8-compatible source; no destructive ledger compaction or modification of original evaluation data. All real-project tests use isolated copies.

## Independent changes
- [x] Approval attribution: approvals.py, approve_scene.py and pipeline integration. Test required CLI type/ID, agent identity, legacy unknown attribution and unchanged stale/tamper rejection before implementation.
- [x] Context contracts: build_runtime_context.py and scene_index.py. Test resume/draft 1600/2000/2400 equality and accepted multi-source ranges before implementation.
- [x] Japanese text/export: text quality/style modules and export API/CLI. Test ordinary Japanese LF paragraphs, dialogue boundaries, explicit title and exact source boundary whitespace before implementation.
- [x] Entry documentation: HUB must prioritize Scene Ledger Length Band rather than the historical 1000–1500 default; add executable documentation regression.

## Review focus
- Legacy approval attribution must not be silently upgraded to a known human identity.
- A changed source, dependency, approval or runtime identity must still fail closed.
- Multiple accepted sources and non-first-line evidence must survive context indexing.
- Japanese dialogue punctuation must not erase true style warnings or merge independent lines.
- Exports must preserve authored whitespace and retain compatible fallback titles.

## Verification and delivery
- [x] Run focused red/green tests per change; commit only each worker's files.
- [x] Inspect ledger growth and ID validation support; defer structural redesign where no authoritative registry/migration contract exists.
- [x] Run complete pytest suite and compileall after integration; use available Python interpreters and explicitly disclose unavailable versions.
- [x] Regenerate runtime on a copy of the real 25-scene project; verify length, sources, export, attribution, performance work counts and source hashes.
- [x] Obtain independent final review; resolve findings, repeat affected checks and full suite.
- [x] Produce local commits, patch, bundle, verification report and hashes; no push.

## Verification outcome

Final code f5f6a5b: 390 tests passed under Python 3.12; compileall passed. Real 25-scene copy: 13 pass, 12 warning, 0 fail, exact source export and accepted-source checks passed. All 395 original files remained unchanged. Python 3.8 runtime was unavailable; grammar-only compatibility was checked separately. Independent review found no actionable defects. Entity registry and history compaction were deliberately deferred.
