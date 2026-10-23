---
name: prose-polisher
description: Improve readability, tone consistency, density, and endings after the structure is already sound. Use when the user wants polishing rather than structural rewriting or diagnosis. 日本語トリガー例: 文体を整えて、読みやすく仕上げたいとき。
---

# Purpose

構造を崩さずに、文体、密度、テンポ、引きを整える。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象シーンまたは章本文
- 対象sceneの現行 `dialogue_context_pack.md` と `docs/dialogue_context.md`（会話を扱う場合。欠損・staleなら同じsceneで再prepare）
- 対象 scene の `runtime/check_report.json`（あれば）

# Required Inputs

- 対象テキスト
- 重点調整したい観点

# Procedure

## 1. 構造変更が必要か確認する

- 大きな矛盾や展開不全がある場合は、このスキルではなく監査または改稿へ回す

## 2. 表現を整える

- 語尾の揺れを減らす
- 冗長な説明を圧縮する
- 地の文と会話のリズムを整える
- 共通ルーブリックに沿い、人物ごとの返答の目的・語彙とリズム・関係を均して消さない。POVの印象や解釈は不確かさを保ち、返し方に効く部分を残す
- 台詞だけで伝わる心理の重複説明は圧縮する。沈黙・省略を欠落と決めつけず、心理や仕草を発話ごとに挿入しない
- 引きや締めを少し強くする

## 3. 契約違反を除去する

- メタ発言
- 見出し
- 箇条書き
- 不要な重複説明
- `anti_ai_style` warning の説明過多、三点列挙、同形段落、文末反復、会話の説明化

# Handoff

- 構造問題が見つかった: `agent/skills/consistency-auditor/SKILL.md`
- 大きく書き直す必要がある: `agent/skills/revision-editor/SKILL.md`

# Outputs

- 仕上げ後の本文
- 調整した観点
- 残った `anti_ai_style` warning がある場合の短い注記

# Do Not

- 章構成まで変えない
- キャラ解釈を勝手に変えない
- 表現整理の範囲を超えて大規模改稿しない
- 語尾や決め台詞のノルマを作らず、機械checkのpassを会話の文学的な合格と扱わない


