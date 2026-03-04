---
name: consistency-auditor
description: Diagnose plot, setting, pacing, continuity, and style issues without defaulting to immediate rewriting. Use when the user wants critique, contradiction checks, weak-point analysis, or risk identification.
version: 0.1
---

# Purpose

設定、本文、章構成の問題点を洗い出し、修正優先度を整理する。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象シーン、章、または設定ファイル

# Required Inputs

- 監査対象
- 見てほしい観点

# Procedure

## 1. 範囲を固定する

- シーン単位か
- 章単位か
- 設定ファイル込みか

監査範囲を明確にしてから読む。

## 2. 問題を分類する

- 設定矛盾
- 因果の弱さ
- キャラ動機の弱さ
- 文体のぶれ
- 感情線の停滞
- テンポの悪さ
- 次話フックの弱さ

## 3. 影響度で並べる

- 高: 放置すると章や物語全体が破綻する
- 中: 読み味を損なうが局所修正で戻せる
- 低: 仕上げ段階で整えればよい

## 4. 修正先を提案する

- 設定修正が必要なら `SKILL_setting_creation.md`
- 本文改稿で足りるなら `SKILL_revision.md`
- 文体調整だけなら `SKILL_polish.md`

# Handoff

- 設定修正: `SKILL_setting_creation.md`
- 本文改稿: `SKILL_revision.md`
- 仕上げ調整: `SKILL_polish.md`

# Outputs

- 問題点一覧
- 優先度
- 推奨修正ルート

# Do Not

- 診断と改稿を同時に進めない
- 問題点を抽象論だけで済ませない
- 影響範囲を示さずに重大判定しない
