# Template Refactor Final Review

Status: accepted with minor residual risks
Date: 2026-03-09
Scope: `templates/01_concept_sheet.md` - `templates/05_chapter_outline.md`

## 1. Validation Summary

実施した確認は以下。

1. `templates/01` から `04` の必須設問が、特定ジャンル前提でないことを目視確認
2. `templates/05_chapter_outline.md` と `templates/05_chapter_outline_100k.md` に対して、以下の互換アンカーが維持されていることを確認
   - `## 第N章 Chapter Card`
   - `### Scene Ledger`
   - `- 想定目標字数:`
   - `## Planning Totals`
3. `scripts/prompt_utils.py` の依存箇所が、今回の追加欄と競合していないことを確認
4. `pytest -q tests/test_scripts.py` を実行し、`61 passed` を確認

## 2. Desk Review by Story Type

### 2.1 ラブコメ案件

判定: usable

根拠:

1. `01` の重点レンズと作品体験の核で、関係性とユーモアを明示できる
2. `02` の補足メモ、関係図、相性・役割メモで恋愛距離や掛け合いを追加できる
3. `04` の補助メモで、各幕ごとにロマンス進展や緩急を入れられる

懸念:

1. 旧版よりラブコメ専用ガイドは薄いので、濃い関係イベント設計は optional 欄を自発的に使う前提になる

### 2.2 ミステリ案件

判定: usable

根拠:

1. `01` で重点レンズを「謎 / サスペンス」に寄せられる
2. `03` の制約、環境要因、イベント装置で捜査や制度の発火点を置ける
3. `04` の各幕設問が、提示・悪化・反転・回収ベースになっており、ユーモア前提の違和感がない

懸念:

1. `04` はまだ起承転結ベースなので、複雑な多重謎構造は個別に補助メモを厚くする必要がある

### 2.3 バトル / 冒険案件

判定: usable

根拠:

1. `01` の軸と重点レンズで成長、対立、戦闘を主軸に置ける
2. `03` の制約・代償・環境要因が、能力バランスや危険地帯の設計に向く
3. `05` の `scene_type` / `Length Band` と章ごとの強調要素が、見せ場配分にそのまま使える

懸念:

1. 競技ルールや戦術段階の詳細は `03` と `04` の optional 側に依存するため、作品ごとに書き足し前提

## 3. Acceptance Decision

判定: accept

受け入れ理由:

1. `01` から `04` は特定ジャンル前提の必須設問を外せている
2. `01` から `04` に core / optional の境界が入っている
3. `05` は parser 互換を保ったまま planning 反映欄を増やせている
4. README と agent 文書が新しいテンプレート思想に同期している
5. テスト上、今回のテンプレート変更に起因する破壊は確認されていない

## 4. Residual Risks

1. `build_llm_prompt.py` の実運用ノイズは、実案件での長文プロンプト確認をまだしていない
2. ラブコメ特化案件では、旧版より補助ガイドが薄いため、optional 欄の使い方が弱いと情報不足になる可能性がある
3. `04_plot_outline.md` は起承転結ベースを維持したため、非線形構成や複雑な群像構成では追加メモが必要

## 5. Recommended Follow-up

1. 実案件を1本使って `build_llm_prompt.py` のプロンプトノイズを spot check する
2. 必要なら README に genre-neutral な記入例を1本追加する
3. 将来 `04_plot_outline.md` をより抽象的な phase 設計へ寄せるかは別タスクで再検討する
