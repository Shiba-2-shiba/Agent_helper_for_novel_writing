---
name: setting-creator
description: Build setting documents, strengthen logic, and repair plot foundations. Use when the user wants to define characters, world rules, or outline structure, or when writing must pause for a core direction change.
version: 0.2
---

# Purpose

設定、動機、世界観、プロットの骨格を整え、破綻しにくい長編前提を作る。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象プロジェクトの設定ファイル群

# Required Inputs

- 既存ログライン、または現在の企画情報
- 対象プロジェクトのパス

# Procedure

## 1. 現在の前提を確認する

- 既存の設定ファイルを順に読む
- すでに確定している文体契約、禁止事項、進捗を確認する

## 2. 設定を埋めながら弱点を突く

以下を順に進める。

1. `01_concept_sheet.md`
2. `02_character_sheet.md`
3. `03_world_building.md`
4. `04_plot_outline.md`
5. 必要なら `05_chapter_outline_100k.md` の章レベル方針

進める際は、単なる転記ではなく以下を必ず確認する。

- 目的と性格が噛み合っているか
- 弱点が物語上の障害として機能しているか
- 世界観ルールに代償や制限があるか
- 解決策がご都合主義になっていないか
- 伏線が配置されているか

## 3. 次の工程へ渡せる状態に整える

- 大枠の章方針までを固める
- 直近の章やシーンの具体段取りが必要なら、このスキルでは抱え込まず `SKILL_scene_planning.md` へ渡す

# Handoff

- 直近の章やシーンの段取りを詰める場合: `SKILL_scene_planning.md`
- 章レベルの段取りが十分で、そのまま新規本文へ進める場合: `SKILL_novel.md`
- 既存本文の大幅方向転換が必要な場合: `SKILL_revision.md`

# Outputs

- 更新済みの設定ファイル
- 主要な矛盾点と解消内容
- 直近で執筆可能なシーン範囲

# Do Not

- ユーザーの案を無批判に転記しない
- 一度に大量の設定ファイルを見せない
- 執筆作業や直近シーンの詳細設計まで同時に進めない
