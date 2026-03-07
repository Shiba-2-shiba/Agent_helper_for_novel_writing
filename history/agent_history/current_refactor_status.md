# Current Refactor Status

## Status

- コアのリファクタリングは一巡完了
- 現行運用ブラッシュアップの主要項目も反映済み
- ルーティング語彙の正本化と、執筆前工程の再分割まで反映済み
- `runtime-first` の執筆・再開フロー統合まで反映済み
- handoff / session 系ドキュメントは、第 9 改善ループ時点まで同期済み
- 今後は、新しい依頼パターンに応じた微調整フェーズ

---

## Completed

### Routing

- `HUB.md` を 9 系統のスキルルーティングに拡張
- 曖昧依頼時の優先順位を追加
- 実運用向けの短文依頼判定ルールを追加
- `Mode` / `current_mode` の正式語彙を `HUB.md` に一本化
- `HUB.md` を新規執筆・再開整理で `runtime-first` 優先へ更新

### Shared Rules

- `AGENT_GUIDE.md` を新運用に同期
- `decision_rules.md` に新運用の判断基準を追加
- `compaction_policy.md` を Agent アプリ前提の品質重視へ変更
- 共通テンプレートから作品固有の文体前提を外し、中立な雛形へ寄せた

### Skills

- `agent/skills/project-bootstrap/SKILL.md` を追加
- `agent/skills/scene-planner/SKILL.md` を追加
- `agent/skills/novel-writer/SKILL.md` を新規執筆専用に整理
- `agent/skills/revision-editor/SKILL.md` を追加
- `agent/skills/consistency-auditor/SKILL.md` を追加
- `agent/skills/prose-polisher/SKILL.md` を追加
- `agent/skills/resume-orchestrator/SKILL.md` を追加
- `agent/skills/setting-creator/SKILL.md` を長編骨格設計へ絞り込み
- `agent/skills/idea-generator/SKILL.md` のハンドオフを初期化段階へ変更
- 既存スキル群を新構成へ揃えた
- `agent/skills/novel-writer/SKILL.md` を `runtime-first` の執筆・機械チェック・不足時の局所差分拡張フローへ更新
- `agent/skills/resume-orchestrator/SKILL.md` を `runtime/resume_brief.md` 優先の再開フローへ更新
- `agent/skills/resume-orchestrator/SKILL.md` に、推奨スキルを選ぶ条件分岐（初期化 / シーン設計 / 改稿 / 監査 / 執筆 / 設定再整理）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、対象一致でも `resume_brief.md` を stale とみなす条件（着手前記述 vs 実本文 / 検査結果）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、更新時刻ベースの補助 stale 判定を追加（ただし時刻だけでは断定しない）
- `agent/skills/resume-orchestrator/SKILL.md` に、`resume_brief.md` の文言パターン解釈（未着手 / 完了 / 監査寄り）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、`Open Items` / `Next Actions` の語彙解釈（前工程残り / 監査寄り / 未移行）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、`Read First` と `Next Actions` の整合確認（整合したまま古いスナップショット判定）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、`Recommended Skill` と最終 `Read First` の整合確認を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、スキル別の `Read First` 対応表（監査 / 改稿 / 段取り / 執筆 / 設定 / 初期化）を追加
- `agent/skills/resume-orchestrator/SKILL.md` に、`runtime/scene_brief_compact.md` 欠落時の `Read First` 優先順（`check_report` / 対象シーン / 直前シーン）を追加
- `agent/skills/scene-planner/SKILL.md` に、`Read First` の選定順（`runtime` / 章アウトライン / 対象 or 直前シーン / `global_notes`）を追加
- `agent/skills/scene-planner/SKILL.md` に、既存シーン複数時の「情報不足シーン」判定基準（`needs_expand` / 文字数不足 / `Scene ID` 不一致）を追加

### Runtime Flow

- `scripts/prompt_utils.py` を追加
- `scripts/build_runtime_context.py` を追加
- `scripts/build_draft_prompt.py` を追加
- `scripts/check_scene_output.py` を追加
- `scripts/build_expand_prompt.py` を追加
- `scripts/apply_expand_edits.py` を追加
- `check_scene_output.py` に詳細レポート、メタ誤検知低減、未閉じカギ括弧、重複段落の検出を追加
- `build_expand_prompt.py` を、途中差し込みと末尾追記の両方に使える局所差分ブロック出力へ更新
- `apply_expand_edits.py` で、`[EDIT n]` ブロックを既存本文へ安全に反映できるようにした
- `小説作成/scripts/` 側にも runtime 系スクリプト一式を同期
- `小説作成/tests/test_scripts.py` に runtime 系テストを追加し、20 件通過を確認

### State / Memory

- `state_schema_novel.yaml` を、案件ごとの可変状態テンプレートとして再設計
- `session_notes.md` を、最小限の再開メモへ整理
- `session_archive.md` を、低優先度の履歴保管先として運用

### Templates / Evals

- `request_template.md` を用途別テンプレートへ再編
- `Mode` を正式モード名へ統一
- 初期化用、設定・骨格設計用、シーン設計用のテンプレートを追加
- 最小依頼例を新構成へ更新
- `evals/README.md` に小説向けの実運用レビュー観点を追加
- `project bootstrap` / `scene planning` の観点を追加
- レビュー出力粒度と Practical Triage を追加
- `resume_orchestrator` / `scene_planning` の第 2 改善ループ向け観点を追加
- `ojiichan_mystery` で `scene_planning` / `resume_orchestrator` の第 2 改善ループ再評価結果を追加
- 別案件用の汎用比較テンプレート `agent/evals/templates/runtime_ready_project_comparison.md` を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 3 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 4 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 5 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 6 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 7 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 8 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 9 改善ループ結果を追加
- `ojiichan_mystery` で `resume_orchestrator` の第 10 改善ループ結果を追加（`runtime` 内対象不一致の stale 判定ケース）

### Planning Docs

- `refactor_proposal.md`
- `refactor_plan.md`
- `refactor_task_checklist.md`
- `legacy_project_migration.md`
- `README.md`

上記を整備済み

---

## Current Operating Rules

- 本文の正本はシーン単位 `txt`
- `body.md` は通常の本文追記先にしない
- 1 シーンの標準文字数契約は `1000-1500`
- 新規本文と再開整理は `runtime/` を優先参照する `runtime-first`
- 文字数不足時は、全文再生成ではなく局所差分ブロックで増補し、必要なら `apply_expand_edits.py` で反映する
- `state_schema_novel.yaml` を可変状態の正本として使う
- `Mode` / `current_mode` は `HUB.md` の正式モード名に揃える
- `session_notes.md` は最新の主タスクだけを短く保持する

---

## Legacy Projects

- 旧案件移行ルールは定義済み
- ただし今後の主軸ではなく、必要時のみ参照する補助方針
- `modern_isekai_40` をパイロットとして検証済み

---

## Remaining Work

- 現在は大きな未完了タスクより、運用しながらの微調整が中心
- 新しい依頼パターンが出たら、必要に応じて `HUB.md`、`request_template.md`、`evals/README.md` を調整する
- `agent/skills/project-bootstrap/SKILL.md` と `agent/skills/scene-planner/SKILL.md` の実運用例を増やし、必要なら発火条件を微調整する
- `resume_orchestrator` / `scene_planning` を、別案件でも同じ観点で再評価して再現性を確認する
- `resume_orchestrator` の stale 判定で、更新時刻と文言パターンをどこまで機械的に扱うかは未決定
- `resume_orchestrator` の文言解釈を、`Current Position` 以外の項目にも広げるかは未決定
- `resume_orchestrator` の次候補として、`Read First` と `Next Action` の整合まで機械的に見るかは未決定
- `resume_orchestrator` の次候補として、`Recommended Skill` と `Read First` の整合まで機械的に見るかは未決定
- `resume_orchestrator` の次候補として、スキル別の `Read First` 対応表をどこまで細かく持つかは未決定
- `resume_orchestrator` の次候補として、スキル別 `Read First` の優先順位テンプレートを共通化するかは未決定
- `runtime-first` 運用の中で、追加の機械チェック（句読点連続、空行過多、視点ぶれヒント）が必要かを見極める
- 実運用の中で、記憶粒度やルーティングの違和感が出た場合のみ追加修正する

---

## 2026-03-05 Skill Path Migration

- Active skills moved to canonical paths: `agent/skills/<skill-name>/SKILL.md`
- Legacy compatibility maintained in `agent/skills/legacy/` as redirect files
- Routing docs switched to canonical references (`agent/HUB.md`, `agent/AGENT_GUIDE.md`)
- Added baseline assets for migration QA:
  - `agent/skills_inventory_snapshot_2026-03-05.txt`
  - `agent/evals/prompts/skill_router_smoke_2026-03-05.md`
  - `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`
  - `agent/evals/prompts/skill_regression_minimum_2026-03-05.md`
  - `agent/evals/prompts/skill_regression_boundary_2026-03-05.md`
  - `agent/evals/results/skill_refactor_baseline_2026-03-05.md`
- Added evaluation automation:
  - `scripts/eval_skill_trigger_qa.py`
  - `scripts/eval_skill_regression_minimum.py`
  - `scripts/run_skill_eval_suite.py`
- Latest measured status:
  - trigger QA pass (`skills=9`, `recall=1.0`, `fp_rate=0.0`)
  - regression minimum pass (`9/9`)
  - regression boundary pass (`21/21`)
  - suite overall pass

## 2026-03-05 Phase 6 Completion

- Completion report: `agent/skill_refactor_phase6_completion_2026-03-05.md`
- Rollback runbook: `agent/skill_refactor_rollback_runbook.md`
- Final handoff: `agent/skill_refactor_handoff_final_2026-03-05.md`
- Final status:
  - document alignment: pass
  - routing alignment: pass
  - evaluation alignment: pass

## 2026-03-05 Resume Orchestrator Tenth Pass

- Added result: `agent/evals/results/resume_orchestrator_ojiichan_mystery_tenth_pass.md`
- Check focus:
  - runtime 内の `resume_brief` / `scene_brief` / `check_report` の対象不一致を stale 判定できるか
- Outcome:
  - `Recommended Skill`: `agent/skills/consistency-auditor/SKILL.md`
  - `Read First`: `runtime/check_report.json` + `chapter_06_scene_03.txt` + `chapter_06_scene_02.txt`
  - review score: `5/5` across all categories

