---
name: resume-orchestrator
description: Recover project state, identify the correct next step, and route back into the right writing skill. Use when the user wants to resume after a pause, understand current progress, or decide what to do next.
version: 0.2
---

# Purpose

中断後の現在地を整理し、`runtime-first` で次に着手すべき作業と呼び出すべきスキルを決める。

# Read First

- `agent/HUB.md`
- 対象プロジェクトの `runtime/resume_brief.md`（あれば最優先）
- `runtime/resume_brief.md` がない場合は `runtime/style_contract_compact.md`
- `runtime/request_compact.md`
- `runtime/` に不足がある場合のみ `agent/state_schema_novel.yaml`
- `runtime/` に不足がある場合のみ `agent/memory/global_notes.md`
- `runtime/` に不足がある場合のみ `agent/memory/session_notes.md`
- 必要なら `agent/memory/session_archive.md`
- 必要なら最新の進捗ファイル

# Required Inputs

- 対象プロジェクト
- 前回の作業範囲が分かる手がかり
- 可能なら `chapter` と `scene`

# Procedure

## 1. `runtime/` を準備する

- 対象の `runtime/resume_brief.md` があり、現在の再開対象と矛盾しないなら再利用する
- `runtime/resume_brief.md` がない、古い、または対象シーンと不一致なら、先に以下を実行して更新する
- `python scripts/build_runtime_context.py --project <project_path> --chapter <chapter> --scene <scene> --mode resume`
- `chapter` / `scene` が明示されていない場合は、最新のシーン `txt`、`state_schema_novel.yaml`、`session_notes.md` から最も妥当な再開地点を推定する
- `runtime/` が使えない場合のみ、従来の広い文脈参照へフォールバックする

## 2. 現在地を確認する

- まず `runtime/resume_brief.md` を読み、そこに書かれた `Current Position`、`Open Items`、`Next Actions` を優先する
- `runtime/resume_brief.md` がない場合のみ、状態ファイルやメモから現在地を再構築する

- 完了済みの章、シーン
- 直近の未解決事項
- 次回着手点
- 直近の重要な方向転換

## 3. 次の最適行動を決める

- まだ案件の箱がないなら初期化が先か
- 新規執筆に進めるか
- 執筆前にシーン設計が先か
- 改稿が先か
- 監査が先か
- 設定再整理が必要か
- 新規執筆に進む場合は、`SKILL_novel.md` の `runtime-first` ループへ渡す

## 4. 必要なスキルへ渡す

- 次に呼ぶべきスキルを 1 つに絞る
- 参照すべきファイルを短く案内する
- 新規執筆へ渡す場合は、`runtime/resume_brief.md` と、必要なら再生成した `runtime/` の参照を明示する

# Handoff

- 新規執筆: `SKILL_novel.md`
- 初期化: `SKILL_project_bootstrap.md`
- シーン設計: `SKILL_scene_planning.md`
- 改稿: `SKILL_revision.md`
- 監査: `SKILL_consistency_audit.md`
- 設定整理: `SKILL_setting_creation.md`

# Outputs

- 現在地の要約
- 次に着手すべきタスク
- 推奨スキル
- 必要なら `runtime/resume_brief.md` の更新案内

# Do Not

- いきなり本文執筆に入らない
- 古い履歴を無制限に読み込み続けない
- 次の優先タスクを曖昧なまま終えない
- `runtime/resume_brief.md` が使えるのに、先にフル文脈を読み直さない
