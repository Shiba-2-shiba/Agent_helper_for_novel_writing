---
name: scene-planner
description: Plan the next chapter or the next one to three scenes before drafting. Use when the user wants execution-ready scene beats, chapter segmentation, or immediate writing prep without rewriting core setting or drafting full prose.
version: 0.1
---

# Purpose

既存の設定と章方針を前提に、直近で書く章やシーンの段取りを固める。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象章の `05_chapter_outline_100k.md`
- 必要なら直前シーンの `txt`

# Required Inputs

- `project_path`
- 対象章、または対象シーン
- 直近で達成したい執筆目標

# Procedure

## 1. 現在地を確認する

- 直近で確定している章方針と未解決要素を確認する
- 直前シーンとの接続条件を確認する

## 2. 範囲を絞る

- 章全体か、次の 1〜3 シーンかを決める
- いま必要な範囲だけに絞り、長編全体の再設計に広げすぎない

## 3. 段取りを作る

- 各シーンの目的
- 衝突または障害
- 見せる情報と伏線
- シーン末尾の次フック

上記を、執筆に移れる粒度で整理する。

## 4. 執筆へ渡す

- 次に書くシーンと、先に読むべきファイルを明確にする
- 骨格不足が見つかった場合のみ `SKILL_setting_creation.md` へ戻す

# Handoff

- 新規本文: `SKILL_novel.md`
- 骨格再整理: `SKILL_setting_creation.md`

# Outputs

- 次章または次シーン群の段取り
- 直近で参照すべきファイル
- そのまま書き始めるべき対象

# Do Not

- 長編全体の骨格設計まで巻き取らない
- 本文初稿を書き始めない
- 監査や改稿の責務を混ぜない
