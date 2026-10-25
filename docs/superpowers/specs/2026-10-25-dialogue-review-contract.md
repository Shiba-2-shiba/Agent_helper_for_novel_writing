# Evidence-bound dialogue review contract

Read-only implementation recommendation, 2026-10-25. No repository source was edited for this review.

## Recommendation in brief

Keep check and approval record version 2. Add a versioned dialogue extension to newly generated checks and require an evidence-complete, current review before any *new* approval of a candidate-bearing scene. At new approval, recompute extraction from canonical source regardless of whether the check contains the new field. Do not apply this new gate retrospectively when validating saved approvals.

Use one pure candidate extractor, one review module, one review CLI, and one scene-scoped flat review ledger. A candidate is an invitation to judge, never a defect. A reviewer can keep fast/comic dialogue, revise information-only Q&A, or remain uncertain. Only keep/resolved outcomes permit new approval. Machines guarantee identities, coverage, binding and declared process, not honest or correct literary judgment.

Important edge case: after Q&A is compressed into indirect narration, the current candidate list may be empty. A recorded revision obligation must still receive an exact before/after comparison; deleting the visible symptom must not silently erase the obligation.

## Existing integration points and compatibility facts

- `check_scene_output.py` produces v2 reports, computes source identity using the text returned by `read_text_file`, snapshots policy dependencies, revalidates under `project_lock`, writes `check_report.json`, then registers the artifact.
- `approvals.validate_check_identity` verifies source/path/scope/hash/check dependencies. `approve_scene` then gates mechanical status and writes a selected report-field snapshot, not a reference to the live report.
- `validate_approval_current` independently checks the saved approval snapshot. Existing v1 approvals are hash-only historical guarantees; existing v2 approvals include dependency validation.
- `test_approval_identity.setup_checked` and numerous callers intentionally make small v2 records without new extension fields. Their body is `日本語本文。`; preserving this is straightforward.
- The long-novel fixture contains occasional isolated `「ここで待とう」` lines separated by substantially more than 80 narration characters. It is not a continuous Q&A fixture. Preserve `version == 2`, actual CLI execution, automation attribution and `agent_evaluation.status = not_run`.
- Existing `anti_ai_style.dialogue_as_exposition` finds long explanatory utterances, not the short repeated Q&A that motivated this change. Keep it separate.
- Task 1 owns `dependencies.py`, `ledgers.py`, `runtime_paths.py`, dialogue scope selection, and the small `check_inputs[0]['value']` access replacement. This proposal does not require changing those modules.

## Scope and rejected alternatives

Chosen: heuristic extraction plus explicit source-bound semantic review at the approval boundary.

Rejected: lower dialogue-ratio thresholds, declaring every candidate a warning/failure, mandatory prose/psychology every N lines, auto-inserting gestures, or a self-report Boolean such as `dialogue_reviewed: true`. Those mistake rhythm for quality or permit empty evidence.

Do not add a model service, NLP dependencies, an automatic rewrite, a new approval type, global policy version changes, or implicit historical approval promotion. No original manuscript edits. Real examples must be disposable copies.

## Exact source-span representation

A `Span` is the same everywhere:

    {
      "start_char": 100,
      "end_char": 132,
      "start_line": 4,
      "end_line": 6,
      "quote": "the exact substring, including internal whitespace",
      "quote_hash": "sha256(quote encoded as UTF-8)"
    }

Character offsets are Python Unicode-string offsets, 0-based and half-open. Lines are 1-based, inclusive, counted in the decoded source; `end_line` is the line containing the final included character. Source is decoded with the same universal-newline behavior already used by `read_text_file`/`text_content_hash`; do not mix raw-byte offsets or separately normalize whitespace/BOMs. Empty spans are not accepted as evidence.

Verify integer types strictly, rejecting booleans; `0 <= start_char < end_char <= len(text)`; exact substring equality; exact line numbers; and exact hash. No trimming, excerpts-with-ellipses, quote searching, or fuzzy matching during validation. Duplicate source text at different offsets remains distinguishable.

## Candidate extraction v1

Suggested public API in `text_quality.py`:

    extract_dialogue_candidates(text) -> list[dict]

Python 3.8 implementation uses normal dict/list annotations or no modern generic annotation syntax.

Algorithm:

1. Scan balanced top-level Japanese quote spans `「…」` and `『…』` with a small stack, allowing nested opposite-style quotes. A top-level pair is one utterance. Do not split an utterance at punctuation or physical line wrapping. Unbalanced quotations are not silently repaired; existing blocking format checks remain authoritative.
2. Link adjacent utterances when the source gap is either only whitespace (`direct`) or contains at most 80 non-whitespace characters and no unmatched quote delimiter (`short_narration`). This deliberately over-inclusive short-narration heuristic catches a nod, glance, or brief physical beat but does **not** claim to identify its semantics. Preserve the raw gap as part of the candidate.
3. Return maximal linked chains containing at least four utterances. No question mark is necessary: Japanese questions may omit it. A longer narration gap splits chains. No requirement is placed on how much prose the writer must add or retain.
4. Preserve chains in source order without overlaps. For a direct link followed by a short beat link, emit one maximal candidate, not overlapping pair/triple candidates. Never cap the candidate list silently.

Candidate:

    {
      "candidate_id": "d-<full SHA-256 described below>",
      "span": <Span covering the first opening through final closing quote>,
      "utterances": [<Span>, <Span>],
      "link_kinds": ["direct"],
      "kind": "direct"
    }

`kind` is `direct`, `short_narration` or `mixed`; its semantics are only extraction provenance. `link_kinds` length is utterance count minus one. Candidate ID is SHA-256 of canonical JSON containing extractor version, start/end offsets and span quote hash, prefixed `d-`. Use full hash, not a positional sequence number. Candidate identity intentionally changes after a source edit moving its range.

Canonical JSON for all digests: `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)` encoded UTF-8, then SHA-256. Candidate digest covers the ordered complete candidate objects plus extractor version. File paths, timestamps, decisions, and reviewer identity are not candidate inputs.

The 80-character bridge and minimum four utterances are *retrieval heuristics*, not literary pass/fail thresholds. Document them as tunable only through a future extractor version. False positives are handled with a justified keep decision. Quote-heavy prose, nested quotation, and unrecognized dialogue forms remain acknowledged limitations.

## Check report extension

Newly generated scene and standalone checks add:

    "dialogue_review_contract": {
      "version": 1,
      "extractor_version": "dialogue-candidates-v1",
      "candidate_digest": "...",
      "candidates": [...],
      "review_required": true
    }

`review_required` is true for scene checks with any candidates or a recorded unresolved revision obligation; standalone checks expose candidates as advisory and cannot approve a scene. Keep the main report's source fields and mechanical `status` unchanged. A mechanically passing scene can still require review. Emit an explicit next step; do not call this literary pass.

If the extension is present, validate all of it against recomputation. If absent in an old v2 check, retain read compatibility. Crucially, `approve_scene` always extracts current canonical text itself and never treats extension absence, `review_required: false`, `candidates: []`, or an edited digest as a waiver. A missing extension on an old check is not automatically an error when a valid current review can supply the new evidence; no-dialogue legacy API fixtures need no review at all.

Do not add extractor version to `current_check_policy`: this would retroactively stale historical v2 approvals during dependency verification.

## Review storage and exact schema

Module: `scripts/novel_agent/dialogue_review.py`. Path: `runtime/scenes/<canonical-scene-id>/dialogue_review_ledger.json`, outside the draft/resume mode directory so a re-prepare or custom runtime does not lose review history. Ledger is one atomic JSON file, version 1, scene ID, and a flat `records` list. No recursive previous-record payloads and no global dependency-ledger changes.

Each accepted record is constructed and hashed by the CLI/module after validating input; submitted JSON does not get to claim successful validation. It contains:

    {
      "version": 1,
      "scene_id": "3-1",
      "source_path": "chapter_3/chapter_3_scene_1.txt",
      "source_hash": "...",
      "hash_algorithm": "sha256-utf8-text-v1",
      "check_inputs_digest": "...",
      "extractor_version": "dialogue-candidates-v1",
      "candidate_digest": "...",
      "candidates": [... exact recomputed snapshot ...],
      "reviewer_type": "agent",
      "reviewer_id": "codex",
      "decisions": [...],
      "previous_review_id": null,
      "comparisons": [],
      "recorded_at": "UTC ISO timestamp",
      "review_id": "sha256 of all fields except review_id"
    }

Review attribution requires existing `human|agent|automation` and a nonblank ID. Do not add `unknown` as a valid *new dialogue reviewer*. This does not change compatibility behavior of the old approval API. Review and final scene approver may be different people; preserve both identities.

A decision:

    {
      "candidate_id": "d-...",
      "judgment": "keep",
      "evidence": [<exact nonempty Span contained within that candidate>],
      "reason": "Specific explanation linking this exchange to its purpose or weakness.",
      "reader_effect": "What the pacing, inference, relationship, or POV reception does here.",
      "next_action": ""
    }

Exactly one decision for every current candidate, with no duplicates, unknown IDs or omissions. At least one exact bounded evidence span per decision. `judgment` is exactly `keep|revise|uncertain`; `reason` and `reader_effect` are mandatory nonblank strings; `next_action` is additionally mandatory for revise/uncertain. Reject exact placeholders such as TODO/TBD and empty structures. Tags, counts, `reviewed: true`, or a bare approval note do not substitute for these fields. Do not claim a word-count minimum proves meaningfulness. Templates contain empty reasons and therefore cannot be submitted unchanged.

The reviewer must explicitly distinguish two semantic axes in `reason`/`reader_effect`: (1) whether routine information-only Q&A should be compressed into indirect narration, and (2) whether a particular response needs selective POV reception because the impression, hesitation, misunderstanding, or relationship changes the next reply. A keep reason may say an axis is not applicable, with the concrete textual reason. These are review questions, not automatic classifier outputs or compulsory prose insertions.

`keep` means deliberate retention, not defect denial. A useful keep reason can explain a withheld answer, changed relationship, comic timing, deliberate omission, or how the actual wording already conveys reception. `revise` identifies a localized weakness and change, such as compressing repeated information into indirect narration. `uncertain` states missing contextual evidence or an unresolved interpretation and remains blocking.

## Revision comparisons and obligation persistence

A recorded review is not overwritten by recheck. When the source hash differs from the latest recorded review, the new review names that record with `previous_review_id`. Before-side snapshots are validated against that stored record, not accepted merely because arbitrary caller-supplied text hashes itself. If a stored approval has a newer review snapshot than the sidecar ledger, use that snapshot as the baseline or report a consistency error; never silently downgrade.

For each previous candidate whose exact span is no longer identical at its old source offsets, require a comparison. Also require a resolution for every previous revise/uncertain decision, even if the current extractor finds nothing. This conservative rule may ask for comparison after an offset-only shift; it avoids fuzzy matching and can explicitly record unchanged wording moved by surrounding edits. Current candidates still all receive fresh decisions because the whole-source hash changed.

Comparison:

    {
      "before_review_id": "...",
      "before_candidate_id": "d-...",
      "before_source_hash": "...",
      "before": <exact prior candidate Span snapshot>,
      "after": <exact nonempty current-source Span>,
      "change_type": "compressed_information",
      "judgment": "keep",
      "reason": "What changed or why wording was retained after reconsideration.",
      "reader_effect": "How the concrete difference addresses the original issue."
    }

`change_type` accepts `compressed_information|pov_reception|retained_pace|other`. It describes the reviewer's claim, not a machine-classified result. The after span can be an indirect summary or include added POV reception and need not itself be a current candidate. For deletion, select the surviving replacement/context span and explain the deletion; do not use an uncheckable empty quote.

Both snapshot hashes/ranges must validate against their respective known evidence. Before must match the stored baseline candidate in full. After is validated against canonical current text. Require one comparison per changed baseline candidate; no invented/duplicate references. Comparison judgments are also keep/revise/uncertain, and any non-keep blocks finalization.

A prior revise can be changed to keep without prose changes only as an explicit *reconsideration*, with a new evidence-grounded reason and reader-effect explanation; never label this a completed rewrite. If implementing this distinction adds unnecessary branching, keep it blocking and require reviewer resubmission of a superseding review with an explicit reconsideration note rather than silently promoting it.

If a source edit predates the first captured review and no trusted before snapshot exists, do not manufacture a verified comparison from hashes. Current review can still be performed, but disclose `before evidence unavailable`; supplied loose comparison files must be labelled illustrative, not provenance-verified. This system cannot prove every unrecorded edit in a project's history.

## Public module API

Keep extraction pure and the locking boundary unambiguous:

    build_dialogue_contract(text, *, scene_bound, unresolved=False) -> dict
    read_dialogue_review_ledger(project_dir, scene_id) -> dict
    build_review_template(project_dir, scene_ref, scene_path, check_report) -> dict
    record_dialogue_review(project_dir, scene_raw, review_input,
                           *, reviewer_type, reviewer_id, runtime_dir_arg='') -> dict
    validate_dialogue_review(text, check_report, review_record,
                             *, baseline_record=None) -> None
    require_dialogue_review(project_dir, scene_ref, scene_path, check_report) -> dict|None

The final annotation above is conceptual; use Python 3.8-compatible Optional[dict] or no annotation. `record_dialogue_review` owns a project lock; `require_dialogue_review` is read-only and called under `approve_scene`'s existing lock. Helpers it calls must not acquire nested locks. Report corrupt explicit ledgers as `DataCorruptionError`, missing/stale/incomplete review as actionable `UserFacingError`.

`require_dialogue_review` independently computes current candidates and checks recorded obligations, selects a current source+check-inputs-bound record, revalidates its complete schema/coverage/evidence/comparisons, and returns the selected validated snapshot. It returns None only if no candidates and no recorded obligations exist. It must not create automatic keep decisions or rewrite review history.

## CLI and approval integration

New CLI:

    python scripts/review_scene_dialogue.py --project P --scene 3-1 --output review-input.json
    python scripts/review_scene_dialogue.py --project P --scene 3-1 --input review-input.json --reviewer-type agent --reviewer-id codex

`--output` emits a source-bound review template including exact candidates and baseline IDs; it does not record review success. `--input` validates and appends a record atomically, displaying counts and whether all judgments permit approval. Recording revise/uncertain is successful recording, not approval. Support existing `--runtime_dir` resolution without another scene's latest fallback. A read-only inspection without `--output` can print candidates and current state; never assume a human read it.

Add `review-dialogue` to `run_scene_pipeline.py` as a thin passthrough. Update `check`'s NEXT message to review candidates before approve when required. `--allow-warnings` remains exclusively a mechanical-warning override and cannot waive dialogue review. There is no `--skip-dialogue-review` or blanket automation exemption.

In `approve_scene`, after current check identity/status validation and before the ledger write, call the new requirement validator. Copy a validated review snapshot into optional `dialogue_review` and its digest into `dialogue_review_digest` on the approval record. Include the contract version/digest as well. Re-read the source hash/check identity immediately before persisting approval; fail if an external editor changed it during review validation. The lock coordinates repository writers but does not stop an editor.

For future validation, if saved approval has the explicit new review extension, validate the embedded digest/schema/bindings and its keep-only outcome. Do not require the transient current check file or review sidecar to remain unchanged. The approval is its own evidence snapshot, consistent with the current design. A later pending review does not itself revoke an already approved unchanged scene.

Most importantly, `validate_approval_current` must not run the new *creation* gate for older approvals lacking the extension. Existing source/dependency changes still stale them. A recheck alone does not revoke an unchanged historical approval; a new approve operation must meet the current evidence gate. This preserves validity, not a claim of prior literary review.

## Exact migration matrix

- Old v1 approval, same source: historical approved, no rewrite on read.
- Old v2 approval, same source/conditions: historical approved, no rewrite on read.
- Either old approval, changed source or old v2 conditions: existing stale rules apply.
- Old v2 check, no candidates/obligations: old approve API continues, including unknown attribution.
- Old v2 check, candidates: new approval needs a current valid review; absence of the extension does not waive it.
- New check with candidate field removed/false/empty: approval recomputes actual source and still requires review. If extension is present but falsified, reject it rather than silently regenerate it.
- New check with candidates, missing/stale review: mechanically checked but new approval blocked with the exact review command.
- New valid review, any revise/uncertain: record can exist; approval blocked.
- New valid current keep review: approval allowed subject to all old protections and warnings policy.
- Changed source removes candidates but earlier revision is recorded: require comparison/resolution.
- No dialogue_voice.json: extraction and review still work; never invent POV/participants.
- Standalone check: advisory extraction only; cannot become a scene approval.
- Reviewer automation: no waiver; if fixture truly has candidates, provide explicitly labelled fixture review through the real CLI or assert expected review-required blocking. Never relabel a deterministic fixture as literary review.

## Required red/green and actual-command tests

1. Pure extraction: adjacent quotes; same-line quotes; blank lines; Japanese indentation; CRLF through source reader; nested opposite quote style; short nod/glance gap; longer gap splitting; Q&A without question marks; comic rapid exchange retained as a candidate; duplicate identical exchanges at different offsets; exact quote/hash/ranges and no overlaps.
2. Contract: stable extraction digest; source edit alters identities; wrong offsets/line numbers/quote/hash rejected; candidate list deletion or false `review_required` cannot bypass approval; unknown extractor/schema fails closed.
3. Review: missing/empty/template review; unknown, duplicate or omitted decisions; placeholder reasons; mismatched scene/path/source/check inputs; partial evidence; stale source; invalid reviewer; wrong before baseline; invented after text; revise and uncertain blocking; keep permitted. Assert no ledger/approval writes after validation failure.
4. Revision: record revise on repeated Q&A, rewrite to indirect narration yielding no candidate, recheck, verify approval still blocked until exact comparison; same for selective reception; retained comic exchange explicitly kept; source mutation between validation and persistence rejected.
5. Compatibility: all existing identity/attribution tests; old v1/v2 historical approval read/export unchanged byte-for-byte; old no-dialogue v2 check API still works; do not add a policy projection field that stales old approvals.
6. Real subprocess flow for both direct entry points and pipeline: prepare -> check -> approve blocked -> emit/fill/record review -> approve -> export -> edit -> stale export refusal. Include `--allow-warnings` on a candidate scene and verify it does not waive review. Run a custom-runtime and non-ASCII project-path case.
7. Existing 200k synthetic CLI/evaluator tests remain measured, version 2, no LLM invoked; no silent canned literary keep injection.
8. Copied real 3-1: quote exact before passage, demonstrate information compression; copied 5-2: demonstrate selective reception rather than arbitrary thoughts; one comic rapid exchange: keep with concrete reason. Save before/after source hashes, review JSON, actual CLI commands/exit codes and exported source inclusion. Do not alter the original project or generalize these examples into an all-scene quality guarantee.
9. Run targeted tests, full pytest and compileall on Python 3.8/3.12. This document itself is a design review, not evidence that these tests have been run.

## Limited implementation file set

Production: `scripts/novel_agent/text_quality.py` (pure extractor only), new `scripts/novel_agent/dialogue_review.py`, new `scripts/review_scene_dialogue.py`, `scripts/check_scene_output.py` (report extension/next-step only), `scripts/novel_agent/approvals.py`, `scripts/run_scene_pipeline.py`. `approve_scene.py` needs no new flag if review selection is deterministic and scene-scoped; only help text may change.

Tests: new `tests/test_dialogue_review.py`, plus focused additions to `test_approval_identity.py`, `test_approval_attribution.py`, and CLI integration tests. Do not rewrite the shared synthetic fixture unless a reproduced extractor false positive makes a fixture-specific, honest review necessary.

Docs: `docs/dialogue_context.md`, `docs/long_novel_workflow.md`, `agent/skills/novel-writer/SKILL.md`, `agent/skills/revision-editor/SKILL.md`, `agent/skills/consistency-auditor/SKILL.md`. State the creation-vs-historical-validation split, template/submit commands, selective reception vs information compression, and that check is mechanical.

## Integrity and truthfulness boundary

Hashes and strict schemas detect stale source, missing coverage, altered quotes/ranges, inconsistent binding, wrong comparisons and unchanged empty templates. They do not authenticate a human identity, prove the reviewer read the passage, prove a literary judgment true, or stop someone intentionally forging an entire compatible historical ledger and all hashes. A generic or dishonest reason can satisfy syntactic requirements; name the resulting state evidence-complete review, not machine-certified literary quality. Never promise tamper-proofness or a guarantee that all dialogue weaknesses are found. Registered artifact integrity may further detect accidental edits, but do not introduce signing/authentication or weaken legacy compatibility in this fix.

## Coordinator ruling
Use at least four utterances for automatic candidate extraction, not two: this bounds routine review overhead while catching the observed failures. The short-narration bridge remains at most80 non-whitespace chars. This is candidate retrieval, never a prose requirement. Reviewer must still read non-extracted exchanges. Optional manual exact-span observations may supplement the automatic candidates; they must never replace automatic coverage or weaken source binding. No claim of semantic completeness.
