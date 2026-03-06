---
name: revision-editor
description: Rewrite an existing scene while preserving selected strengths and changing targeted weaknesses. Use when the user wants a scene rewritten, tightened, redirected, or partially restructured without switching into pure diagnostic mode. 日本語トリガー例: このシーンを改稿して、弱点を直したいとき。
---

# Purpose

既存シーンの問題点を、保持すべき要素を残しつつ改稿する。

# Read First

- `agent/HUB.md`
- `agent/state_schema_novel.yaml`
- `agent/memory/global_notes.md`
- 対象シーンの `txt`
- 必要なら直前、直後シーン
- 章の方向性変更が絡む場合のみ `body.md`

# Required Inputs

- 対象シーン
- 変えたい点
- 残したい点

# Procedure

## 1. 問題を分解する

- 現行テキストの弱点を整理する
- 残すべき要素と変える要素を分ける
- 変更が局所修正で足りるか、構成再設計が必要か判断する

## 2. 改稿方針を決める

- テンポ
- 感情線
- 説明密度
- 会話の温度
- 引きの強さ

上記のうち、どこを触るか明確にしてから書き直す。

## 3. 改稿する

- 原則 `1000-1500` の範囲に収める
- 文体契約と前後接続を維持する
- 明示的な差し替え依頼がある場合は対象シーンを更新する
- 差し替え範囲が曖昧なら、改稿案として別扱いで提示してから反映する

## 4. 影響を確認する

- 新しい矛盾を生んでいないか
- 直後シーンへの接続が崩れていないか
- 章方針まで変わるなら `body.md` の更新が必要か確認する

# Handoff

- 設定の根本変更が必要: `agent/skills/setting-creator/SKILL.md`
- 先に問題洗い出しが必要: `agent/skills/consistency-auditor/SKILL.md`
- 仕上げ調整だけが残る: `agent/skills/prose-polisher/SKILL.md`

# Outputs

- 改稿版本文
- 主な修正点
- 波及修正が必要な場合の指摘

# Do Not

- 何を残すか決めずに全面改稿しない
- 章方針変更と局所改稿を混同しない
- 前後の接続を無視しない


