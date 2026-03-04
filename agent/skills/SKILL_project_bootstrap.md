---
name: project-bootstrap
description: Initialize a new novel project from an agreed concept or logline. Use when the user wants to create the project shell, decide the project path/name, and prepare the first working state before deeper setting or scene planning.
version: 0.1
---

# Purpose

合意済みの企画を、実作業に入れる案件として初期化する。

# Read First

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`
- 必要なら `agent/request_template.md`

# Required Inputs

- 合意済みログライン、または企画の核
- プロジェクト名、または命名ルール
- 保存先の親パス

# Procedure

## 1. 初期条件を確定する

- 企画名、保存先、長さ目標、ジャンルを確認する
- まだ曖昧な要素と、いま固定してよい要素を分ける

## 2. 案件の箱を作る

- プロジェクトフォルダ構成を決める
- `state_schema`、`memory`、設定ファイル群の初期配置を整える
- まだ未確定の設定は、空欄または保留として残す

## 3. 初期状態を明文化する

- `current_mode` を次に使う正式モード名へセットする
- `next_action` と `files_to_check_first` を、次スキルが迷わない粒度で残す

## 4. 次スキルへ渡す

- 世界観や人物の骨格が薄いなら `SKILL_setting_creation.md`
- 既に骨格があり、次の章やシーンの段取りだけ必要なら `SKILL_scene_planning.md`

# Handoff

- 骨格設計: `SKILL_setting_creation.md`
- 執筆直前の段取り: `SKILL_scene_planning.md`

# Outputs

- 初期化済み案件
- 初期状態の要約
- 次に呼ぶべきスキル

# Do Not

- この段階で本文執筆を始めない
- 未確定設定を勝手に確定扱いにしない
- 初期化と詳細な長編設計を同時に抱え込まない
