---
name: setting-creator
description: Build setting documents, strengthen logic, and repair plot foundations. Use when the user wants to define characters, world rules, or outline structure, or when writing must pause for a core direction change. 日本語トリガー例: 設定構築や土台の見直しをしたいとき。
---

# Purpose

設定、動機、世界観、プロットの骨格を整え、破綻しにくい長編前提を作る。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象プロジェクトの設定ファイル群
- 対象プロジェクトの `05_chapter_outline.md`

# Required Inputs

- 既存ログライン、または現在の企画情報
- 対象プロジェクトのパス

# Procedure

## 1. 現在の前提を確認する

- 既存の設定ファイルを順に読む
- すでに確定している文体契約、禁止事項、進捗を確認する
- `target_total_chars` / `target_length_profile` / `planning_gate_enabled` を確認する

## 2. 設定を埋めながら弱点を突く

以下を順に進める。

1. `01_concept_sheet.md`
2. `02_character_sheet.md`
3. `03_world_building.md`
4. `04_plot_outline.md`
5. `05_chapter_outline.md`

進める際は、単なる転記ではなく以下を必ず確認する。

- 目的と性格が噛み合っているか
- 弱点が物語上の障害として機能しているか
- 世界観ルールに代償や制限があるか
- 解決策がご都合主義になっていないか
- 伏線が配置されているか

## 3. 長編計画ゲートを作る

- `planning_gate_enabled=true` の場合は `05_chapter_outline.md` を正本として必須とする
- legacy project では `05_chapter_outline_100k.md` を fallback として読んでよい
- 各章について、以下を最低限埋める
- 章の役割
- 章の感情線
- 章末フック
- 回収する伏線
- 新規に撒く伏線
- 想定シーン数
- 想定最小字数
- 想定目標字数
- 各シーンについて、以下を最低限埋める
- `scene_id`
- `scene_type`
- `purpose`
- `turn`
- `payoff_or_seed`
- `min / target / max`
- `depends_on`
- `status`
- `planned_total_min_chars` を算出する
- `planned_total_target_chars` を算出する
- `planned_total_min_chars` が `planning_gate_min_chars` 未満なら `planning_gate_status` を `blocked` とする
- `planned_total_min_chars` が `planning_gate_min_chars` 以上なら `planning_gate_status` を `ready` とする

## 4. 次の工程へ渡せる状態に整える

- `planning_gate_status=ready` なら、直近の章やシーンの具体段取りは `agent/skills/scene-planner/SKILL.md` へ渡す
- `planning_gate_status=blocked` なら、不足している章やシーン在庫を明示して、このスキル内で長編計画を詰める

# Handoff

- `planning_gate_status=ready` で、直近の章やシーンの段取りを詰める場合: `agent/skills/scene-planner/SKILL.md`
- `planning_gate_status=ready` で、章レベルの段取りが十分で、そのまま新規本文へ進める場合: `agent/skills/novel-writer/SKILL.md`
- 既存本文の大幅方向転換が必要な場合: `agent/skills/revision-editor/SKILL.md`

# Outputs

- 更新済みの設定ファイル
- 主要な矛盾点と解消内容
- `planned_total_min_chars`
- `planned_total_target_chars`
- `planning_gate_status`
- 章ごとの不足箇所、または直近で執筆可能なシーン範囲

返答時は、以下の順で返す。

1. `Setting Status`: 今回固めた前提
2. `Planning Verdict`: `blocked` / `ready`
3. `Planned Total Min`: 長編計画の最小想定文字数
4. `Planned Total Target`: 長編計画の目標想定文字数
5. `Chapter Coverage`: どの章が十分で、どの章が不足しているか
6. `Next Skill`: 次に渡す 1 スキル、またはこのスキル内で続ける理由

# Do Not

- ユーザーの案を無批判に転記しない
- 一度に大量の設定ファイルを見せない
- `planning_gate_enabled=true` なのに `05_chapter_outline.md` を optional 扱いしない
- legacy fallback を除き、`05_chapter_outline_100k.md` を canonical path のように扱わない
- 計画ゲート未通過のまま、直近シーンの段取りや本文執筆へ進めない

