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
- 対象sceneの現行 `dialogue_context_pack.md` と `docs/dialogue_context.md`（会話を扱う場合。欠損・staleなら同じsceneで再prepare）
- 対象 scene の `runtime/check_report.json` と `runtime/quality_budget_ledger.json`（あれば）
- 対象 scene の `runtime/obligation_contract.json` と `runtime/health_report.json`（あれば）
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
- 会話では共通ルーブリックで、返答の目的・語彙とリズム・関係のどこが弱いか、具体的な応酬から特定する。主観の省略が効いている箇所は保持点に分ける
- `quality_budget_ledger.json` で同一 issue の修復予算が尽きている場合は、なぜ expansion では直らないかを先に特定する
- `obligation_status=fail` の場合は、依存欠落・必須到達点・回収義務のどれが原因かを先に切り分け、単純な文字数増補として扱わない

## 2. 改稿方針を決める

- テンポ
- 感情線
- 説明密度
- 会話の温度
- 引きの強さ

上記のうち、どこを触るか明確にしてから書き直す。

## 3. 改稿する

- 対象シーンのLength Bandを維持する。契約不明の旧案件だけ `1000-1500` をfallbackにする
- 文体契約と前後接続を維持する
- 返答の変化に根拠が足りない要所だけ、POVが受け取った調子・印象や不確かな解釈を局所的に補う。内面・仕草の一律追加でなく、既存の間や余白を残す
- 明示的な差し替え依頼がある場合は対象シーンを更新する
- 差し替え範囲が曖昧なら、改稿案として別扱いで提示してから反映する

## 4. 影響を確認する

- 新しい矛盾を生んでいないか
- 直後シーンへの接続が崩れていないか
- 章方針まで変わるなら `body.md` の更新が必要か確認する
- `anti_ai_style` warning が出ている場合は、説明過多・同形反復・会話の説明化を局所的に減らす

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



# Shared Long-Novel Contract

開始前に `docs/long_novel_workflow.md` の対象・鮮度・検査・承認契約を適用する。意味記憶を扱う場合は `docs/story_memory_format.md` に従う。共通規則をここへ複製せず、役割固有の手順だけを上記に記載する。

## Dialogue Review Gate

会話を改稿する前に現本文のreviewを記録する。revise/uncertainの範囲は再check後、保存済みbeforeと現本文afterを正確に比較する。間接叙述へ圧縮して候補0件でも比較義務は残る。相手の問いの受け取りが返答の省略を変える要所だけ選択的に補い、無変更の再考を改稿と偽らない。手順とCLIは `docs/dialogue_context.md` に従う。空欄のひな型はレビュー済みではなく、automationや `--allow-warnings` で免除しない。既存承認の歴史的検証と、新規承認のレビュー条件を区別する。

## 選択的主観素材と本文レビュー

`docs/narrative_keyframing.md` に従う。新prepareでは設定なしでも基本有効で、明示POVを共有する。選んだ素材は主に台詞ににじませる／地の文に出し、省略は両経路が不自然・冗長・テンポを損なう具体的理由がある場合だけ。全発話への心理・仕草の追加をノルマにしない。素材の一人称文を本文へ逐語転記する必要はない。相手の内心を断定せず、作者用情報や未来の予定をPOVの既知事実・canonへ昇格しない。

候補に関係する登録素材を本文のexact span・読者効果と照合し、台詞の言い直し等の暗示的反映も評価する。keep/revise/uncertainと改稿前後の正確な比較を維持する。候補外の短い台詞や地の文も自己評価するが、全主観を機械検査したとは主張しない。反映を省略へ変える場合は両経路の理由をproposalに記し再登録・prompt再生成・再checkする。expandは既に伝わる心理を重複説明せず文字数不足への局所増補のみ。
