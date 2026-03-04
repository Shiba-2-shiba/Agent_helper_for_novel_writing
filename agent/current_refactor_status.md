# Current Refactor Status

## Status

- コアのリファクタリングは一巡完了
- 現行運用ブラッシュアップの主要項目も反映済み
- ルーティング語彙の正本化と、執筆前工程の再分割まで反映済み
- `runtime-first` の執筆・再開フロー統合まで反映済み
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

- `SKILL_project_bootstrap.md` を追加
- `SKILL_scene_planning.md` を追加
- `SKILL_novel.md` を新規執筆専用に整理
- `SKILL_revision.md` を追加
- `SKILL_consistency_audit.md` を追加
- `SKILL_polish.md` を追加
- `SKILL_resume_orchestrator.md` を追加
- `SKILL_setting_creation.md` を長編骨格設計へ絞り込み
- `SKILL_idea_generation.md` のハンドオフを初期化段階へ変更
- 既存スキル群を新構成へ揃えた
- `SKILL_novel.md` を `runtime-first` の執筆・機械チェック・不足時の局所差分拡張フローへ更新
- `SKILL_resume_orchestrator.md` を `runtime/resume_brief.md` 優先の再開フローへ更新

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
- `SKILL_project_bootstrap.md` と `SKILL_scene_planning.md` の実運用例を増やし、必要なら発火条件を微調整する
- `runtime-first` 運用の中で、追加の機械チェック（句読点連続、空行過多、視点ぶれヒント）が必要かを見極める
- 実運用の中で、記憶粒度やルーティングの違和感が出た場合のみ追加修正する
