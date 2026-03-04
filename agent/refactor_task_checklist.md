# Refactor Task Checklist

## Phase 1: Operating Rules

- [x] `body.md` を通常本文の追記先から外す
- [x] シーン単位 `txt` を本文の正本として明記する
- [x] `body.md` 更新条件を限定する
- [x] `global_notes.md` の文字数契約を `2000-2500` に更新する（当時。現行は `1000-1500` へ再更新済み）
- [x] `state_schema_novel.yaml` の `scene_*_chars` を更新する
- [x] `compaction_policy.md` を Agent アプリ前提へ更新する

## Phase 2: Routing

- [x] `HUB.md` のスキル一覧を拡張する
- [x] 各スキルの発動条件を具体化する
- [x] 曖昧依頼時の優先順位を追加する
- [x] スキル間ハンドオフ条件を追加する
- [x] `Mode` / `current_mode` の正式語彙を `HUB.md` へ集約する

## Phase 3: Skills

- [x] `SKILL_idea_generation.md` を新構成に寄せる
- [x] `SKILL_setting_creation.md` を新構成に寄せる
- [x] `SKILL_project_bootstrap.md` を追加する
- [x] `SKILL_scene_planning.md` を追加する
- [x] `SKILL_novel.md` を新規執筆専用へ再定義する
- [x] `SKILL_revision.md` を追加する
- [x] `SKILL_consistency_audit.md` を追加する
- [x] `SKILL_polish.md` を追加する
- [x] `SKILL_resume_orchestrator.md` を追加する
- [x] `SKILL_setting_creation.md` から執筆直前の段取り責務を分離する

## Phase 4: Templates and Evals

- [x] `request_template.md` を用途別テンプレートへ更新する
- [x] `evals/README.md` を小説向け評価へ更新する
- [x] リトライ条件を明文化する
- [x] `request_template.md` の `Mode` を正式モード名へ統一する
- [x] 初期化用 / シーン設計用テンプレートを追加する
- [x] `evals/README.md` に `project bootstrap` / `scene planning` の評価観点を追加する

## Phase 5: Guide and Logs

- [x] `AGENT_GUIDE.md` の説明を新運用に合わせる
- [x] `decisions_log.md` に今回の設計判断を追記する
- [x] `change_log.md` に今回の変更を追記する
- [x] `current_refactor_status.md` を新しい 9 スキル構成へ同期する

## Validation

- [x] `body.md` が通常運用から外れている
- [x] 文字数契約が `2000-2500` に統一されている（当時。現行は `1000-1500`）
- [x] 再開方針が Agent アプリ前提になっている
- [x] 改稿、監査、仕上げ、再開のスキルが追加されている
- [x] 初期化とシーン設計のスキルが追加されている
- [x] 依頼テンプレートが現在の運用をカバーしている
- [x] 共通テンプレートから作品固有の文体前提が除去されている
- [x] `HUB.md` 参照の執筆開始・再開で `runtime-first` 運用へ入れる
- [x] `小説作成/scripts/` でも runtime 系コマンドが実行できる

## Phase 6: Current Operations Hardening

- [x] `HUB.md` の曖昧依頼ルーティングを実運用寄りに再点検する
- [x] `state_schema_novel.yaml` を現行運用向けに再設計する
- [x] `session_notes.md` / `session_archive.md` の運用粒度を再点検する
- [x] `request_template.md` の入力粒度を実依頼に合わせて再調整する
- [x] `evals/README.md` の実運用レビュー観点を追加調整する

## Phase 7: Runtime-First Integration

- [x] `HUB.md` を新規執筆・再開整理で `runtime-first` 優先へ更新する
- [x] `SKILL_novel.md` を `runtime-first` の執筆・機械チェック・拡張フローへ更新する
- [x] `SKILL_resume_orchestrator.md` を `runtime/resume_brief.md` 優先へ更新する
- [x] `README.md` の Antigravity 運用説明を `runtime-first` に同期する
- [x] `scripts/` に runtime 系スクリプト一式を追加する
- [x] `小説作成/scripts/` に runtime 系スクリプト一式を同期する
- [x] `check_scene_output.py` の機械判定を強化する
- [x] `小説作成/tests/test_scripts.py` に runtime 系テストを追加する
- [x] `小説作成/tests/test_scripts.py` の runtime 系テスト 19 件通過を確認する

## Legacy Projects (Low Priority)

- [x] 必要時のみ参照する旧案件移行ルールを定義する
