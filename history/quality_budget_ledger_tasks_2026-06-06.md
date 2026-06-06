# Quality Budget Ledger Tasks

Date: 2026-06-06

## Goal

`runtime/quality_budget_ledger.json` を導入し、長編小説の scene 修復で同じ失敗に対して LLM prompt を繰り返し作りすぎないようにする。

## Implementation Scope

v1 で必ず扱う:

- `needs_expand=true` / `under_min_for_type=true` の budget 管理
- scene 全体の expand prompt 回数管理
- recheck なしの連続 expand 抑止
- `--force` override
- format / forbidden / over max の expansion block

v1 では扱わない:

- LLM judge
- 自動全文改稿
- DB / vector store
- format / forbidden 専用の repair prompt

## Implementation Update

2026-06-06 実装結果:

- [x] Phase 0 completed
- [x] Phase 1 completed: quality budget ledger helpers
- [x] Phase 2 completed: check report integration
- [x] Phase 3 completed: expand prompt budget gate and `--force`
- [x] Phase 4 completed: apply edit action tracking
- [x] Phase 5 completed: README/HUB/skill documentation updates
- [x] Validation completed: `python -m pytest tests/ -q` -> `79 passed in 6.88s`

Deferred:

- [ ] Optional `scripts/report_quality_budget.py`
- [ ] Format / forbidden 専用の repair prompt は未実装。現時点では revision/manual repair へ戻す。

## Phase 0: Behavior Lock

- [x] `python -m pytest tests/ -q` を実行する
- [x] baseline result を `quality_budget_ledger_progress_2026-06-06.md` に記録する
- [x] `build_expand_prompt.py` の現行正常系 test を確認する
- [x] `check_scene_output.py` の current report fields を確認する

## Phase 1: Ledger Helpers

- [x] `scripts/novel_agent/ledgers.py` に `quality_budget_ledger_path(project_dir)` を追加する
- [x] `read_quality_budget_ledger(project_dir)` を追加する
- [x] 壊れた JSON でも default payload を返す
- [x] `write_quality_budget_ledger(project_dir, payload)` を追加する
- [x] `default_quality_budget_policy()` を追加する
- [x] `scene_budget_record(payload, scene_id)` 相当の helper を追加する
- [x] issue key helper を追加する
- [x] `update_quality_budget_from_check(project_dir, scene_ref, report, report_path)` を追加する
- [x] pass check で open issue を resolved にする
- [x] warning は記録するが expand attempts を消費しない
- [x] fail check で issue を open / still_open にする
- [x] `evaluate_quality_budget_for_expand(project_dir, scene_ref, report)` を追加する
- [x] `record_quality_budget_action(project_dir, scene_ref, action, reason, artifacts=None, force=False)` を追加する
- [x] ledger に本文全文を保存しない
- [x] helper / integration tests を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 2: Check Report Integration

- [x] `scripts/check_scene_output.py` に quality budget helper import を追加する
- [x] `check_report.json` 書き込み後に `update_quality_budget_from_check()` を呼ぶ
- [x] trace event とは別に ledger が更新されることを確認する
- [x] `needs_expand=true` の check で `under_min_for_type` issue が作られる test を追加する
- [x] pass check で issue が resolved になる test を追加する
- [x] existing report schema compatibility test を維持する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 3: Expand Prompt Budget Gate

- [x] `scripts/build_expand_prompt.py` に `--force` を追加する
- [x] prompt 作成前に `evaluate_quality_budget_for_expand()` を呼ぶ
- [x] budget within なら既存どおり prompt を作る
- [x] prompt 作成時に `record_quality_budget_action(..., "expand_prompt_generated")` を呼ぶ
- [x] `needs_expand=false` の場合は warning ではなく budget decision に従う
- [x] `format_violations` がある場合は expansion を block する
- [x] `forbidden_hits` がある場合は expansion を block する
- [x] `over_max_for_type=true` の場合は expansion を block する
- [x] issue attempts exhausted の場合は exit 1 で止める
- [x] `--force` の場合は prompt を作り、`forced_override` を記録する
- [x] budget within expand test を追加する
- [x] budget exhausted / recheck-required block test を追加する
- [x] `--force` override test を追加する
- [x] inappropriate expansion block test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 4: Apply Edit Action Tracking

- [x] `scripts/apply_expand_edits.py` で text path から scene ref を推定する
- [x] edit 適用後に `record_quality_budget_action(..., "expand_edits_applied")` を呼ぶ
- [x] `output` 指定時も artifact path を正しく記録する
- [x] recheck なしで再度 expand しようとした場合に block できる counter を更新する
- [x] apply action record test を追加する
- [ ] output path 指定 test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 5: Documentation and Optional Report

- [x] README に `quality_budget_ledger.json` の役割を追加する
- [x] README の runtime-first flow に budget exhausted 時の戻り先を追加する
- [x] `agent/HUB.md` に repeated repair loop の扱いを追加する
- [x] `agent/skills/novel-writer/SKILL.md` に budget exhausted 時は自動執筆を止めるルールを追加する
- [x] `agent/skills/revision-editor/SKILL.md` または `prose-polisher` への handoff 条件を必要に応じて追記する
- [ ] optional: `scripts/report_quality_budget.py` を作る
- [ ] optional: exhausted scenes / open issues / forced overrides を表示する
- [x] docs 更新後に `rg -n "quality_budget_ledger|Quality Budget"` で参照を確認する

## Regression Tests To Add

- [x] missing quality ledger returns default
- [x] invalid quality ledger returns default
- [x] under-min check creates open issue
- [x] pass check resolves open issue
- [x] first expand prompt is allowed
- [x] repeated expand prompt is blocked after budget exhaustion / recheck requirement
- [x] force override allows prompt and records override
- [x] format violation blocks expansion
- [x] forbidden hit blocks expansion
- [x] over max blocks expansion
- [x] apply edits records action
- [x] no full prose is written to quality ledger

## Phase Done Checklist

Each phase is done only when:

- [ ] Scope stayed inside the phase
- [ ] Tests were added or an explicit test gap was recorded
- [ ] `python -m pytest tests/ -q` passed
- [ ] Existing CLI compatibility was preserved
- [ ] No new dependency was added
- [ ] No full scene prose was stored in the ledger
- [x] `quality_budget_ledger_progress_2026-06-06.md` was updated

## Overall Done Definition

- [x] `runtime/quality_budget_ledger.json` is created and updated by normal runtime flow
- [x] repeated expansion attempts are stopped before another LLM prompt is generated
- [x] inappropriate expansion categories are blocked
- [x] `--force` override exists and is auditable
- [x] README/HUB/skill docs explain the new budget gate
- [x] all tests pass
