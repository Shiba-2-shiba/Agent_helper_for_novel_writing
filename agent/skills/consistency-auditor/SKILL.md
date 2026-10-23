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
- 対象sceneの現行 `dialogue_context_pack.md` と `docs/dialogue_context.md`（会話を扱う場合。欠損・staleなら同じsceneで再prepare）
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

会話は共通ルーブリックに沿って返答の目的、語彙・リズム、関係を確認する。POVの受け取りや考え直しが返答に効く要所を具体的な本文と読者への影響で診断し、相手の内心の断定と不確かな推測を分ける。心理の記載がないだけで欠陥とせず、速度や余白のための省略を評価する。カード不足・解釈の相違は人物崩壊の断定と分け、回数ノルマや全発話への仕草追加を修正条件にしない。機械checkのpassはこの評価の代わりにならない。

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



# Shared Long-Novel Contract

開始前に `docs/long_novel_workflow.md` の対象・鮮度・検査・承認契約を適用する。意味記憶を扱う場合は `docs/story_memory_format.md` に従う。共通規則をここへ複製せず、役割固有の手順だけを上記に記載する。
