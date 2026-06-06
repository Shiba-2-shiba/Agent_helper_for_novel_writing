---
name: consistency-auditor
description: Diagnose plot, setting, pacing, continuity, and style issues without defaulting to immediate rewriting. Use when the user wants critique, contradiction checks, weak-point analysis, or risk identification. 日本語トリガー例: 設定矛盾チェック、整合性監査、違和感診断をしたいとき。
---

# Purpose

設定、本文、章構成の問題点を洗い出し、修正優先度を整理する。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象シーン、章、または設定ファイル
- 必要なら `runtime/health_report.json`
- 必要なら対象 scene の `runtime/check_report.json` / `runtime/obligation_contract.json`

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
- obligation 未達
- anti-AI style warning

## 3. 影響度で並べる

- 高: 放置すると章や物語全体が破綻する
- 中: 読み味を損なうが局所修正で戻せる
- 低: 仕上げ段階で整えればよい

## 4. 修正先を提案する

- 設定修正が必要なら `agent/skills/setting-creator/SKILL.md`
- 本文改稿で足りるなら `agent/skills/revision-editor/SKILL.md`
- 文体調整だけなら `agent/skills/prose-polisher/SKILL.md`
- export 前診断では `approval_ledger.json` と `health_report.json` の stale / fail / warning も確認する

# Handoff

- 設定修正: `agent/skills/setting-creator/SKILL.md`
- 本文改稿: `agent/skills/revision-editor/SKILL.md`
- 仕上げ調整: `agent/skills/prose-polisher/SKILL.md`

# Outputs

- 問題点一覧
- 優先度
- 推奨修正ルート

# Do Not

- 診断と改稿を同時に進めない
- 問題点を抽象論だけで済ませない
- 影響範囲を示さずに重大判定しない


