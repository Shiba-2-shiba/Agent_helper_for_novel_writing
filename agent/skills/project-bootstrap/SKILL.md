---
name: project-bootstrap
description: Initialize a new novel project from an agreed concept or logline. Use when the user wants to create the project shell, decide the project path/name, and prepare the first working state before deeper setting or scene planning. 日本語トリガー例: このログラインで案件作成して、プロジェクトを初期化したいとき。
---

# Purpose

合意済みの企画を、実作業に入れる案件として初期化する。

# Read First

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`
- `agent/state_schema_novel.yaml`
- 必要なら `agent/request_template.md`
- 必要なら `agent/naming_conventions.md`

# Required Inputs

- 合意済みログライン、または企画の核
- プロジェクト名、または命名ルール
- 保存先の親パス
- 必要なら `length_mode`

# Procedure

## 1. 初期条件を確定する

- 企画名、保存先、長さ目標、ジャンルを確認する
- `length_mode` を 1 つ決める
- まだ曖昧な要素と、いま固定してよい要素を分ける
- 既存案件を上書きしないことを先に確認する
- 生成先が「新規案件」なのか、「既存案件への agent 運用だけ追加」なのかを分ける
- `long_form_100k` の場合は、この段階では執筆前提を作らず、長編計画ゲートを通す前提で初期化する

## 2. 案件の箱を作る

- このリポジトリ標準の新規案件を作る場合は、まず以下を実行する
- `python scripts/init_project.py <project_name>`
- 既存案件に対して運用情報だけ整える場合は、初期化スクリプトを実行せず、必要な `agent/` 管理対象だけを整備する
- まだ未確定の設定は、空欄または保留として残す

実行後または既存案件整備時に、以下を確認する。

- 主要テンプレートが作成されているか
- 章フォルダと `body.md` が既定構成になっているか
- 運用上の正本がシーン単位 `txt` になる前提で進められるか

## 3. 初期状態を明文化する

- `current_mode` を次に使う正式モード名へセットする
- `next_action` と `files_to_check_first` を、次スキルが迷わない粒度で残す
- `recommended_skill` を 1 つだけ決める
- `long_form_100k` の場合は `planning_gate_status` を `blocked` で残す
- `long_form_100k` の場合は、`recommended_skill` を原則 `setting-creator` にする
- 直後に読むべきファイルを、最大 3 件までに絞る

## 4. 次スキルへ渡す

- `long_form_100k` で、章配分やシーン在庫が未確定なら `agent/skills/setting-creator/SKILL.md`
- 世界観や人物の骨格が薄いなら `agent/skills/setting-creator/SKILL.md`
- `long_form_100k` ではない、または計画ゲート通過済みで、次の章やシーンの段取りだけ必要なら `agent/skills/scene-planner/SKILL.md`

# Handoff

- 骨格設計: `agent/skills/setting-creator/SKILL.md`
- 執筆直前の段取り: `agent/skills/scene-planner/SKILL.md`

# Outputs

- 初期化済み案件、または既存案件を運用開始できる状態
- 初期状態の要約
- 長さモード
- 計画ゲート状態
- 次に呼ぶべきスキル
- 直後に読むべきファイル一覧

返答時は、以下の順で短く返す。

1. `Current State`: 初期化が完了したか、何が未確定か
2. `Length Mode`: 今回の運用モード
3. `Planning Gate`: `blocked` か `ready` か
4. `Next Skill`: 次に呼ぶ 1 スキル
5. `Read First`: 次スキルが最初に見るファイル

# Do Not

- この段階で本文執筆を始めない
- 未確定設定を勝手に確定扱いにしない
- 初期化と詳細な長編設計を同時に抱え込みすぎない
- 初期化結果の報告だけで終わらず、次の着手点を空欄のまま残さない
- `long_form_100k` 案件を、章配分とシーン在庫が未整理のまま `scene-planner` へ直接渡さない


