# Template Refactor Specification

Status: draft
Date: 2026-03-09
Owner: Codex review memo
Target Repository: `C:\Users\inott\Downloads\Agent_helper_for_novel_writing-main`
Primary Scope: `templates/01_concept_sheet.md` - `templates/05_chapter_outline.md`

## 1. Purpose

本仕様は、`templates/` の内容を「特定ジャンルへ寄せる雛形」から「planning で決定した方針を柔軟に反映できる雛形」へ段階的にリファクタリングするための実行計画を定義する。

今回の主目的は以下。

1. `01` から `04` をジャンル非依存の汎用テンプレートへ再設計する
2. `05` は script 互換を維持したまま、planning 反映力を高める最小拡張に留める
3. Phase ごとに検証ゲートを設け、互換性破壊や運用導線の後退を防ぐ
4. 次チャット以降で Phase 単位に安全に実装着手できる状態にする

## 2. Background

現状のプロジェクトは、全体としては `runtime-first` の執筆運用が整理されている一方、`templates/` 側に以下の偏りがある。

1. `01_concept_sheet.md` が「コメディ/ラブコメのトーン」「笑いの核」などを中心軸として持つ
2. `02_character_sheet.md` が「ボケ/ツッコミ」「ラブコメ関係図」などの前提を広く要求する
3. `03_world_building.md` と `04_plot_outline.md` がコメディ/ラブコメの補助導線を強く持つ
4. その結果、planning 時点で未確定のはずの演出レンズが、テンプレート入力の都合で先に固定されやすい

一方で、`05_chapter_outline.md` は既に `scene_type` / `Length Band` / planning gate を中核にした、比較的汎用的な運用テンプレートになっている。

## 3. Scope

対象:

1. `templates/01_concept_sheet.md`
2. `templates/02_character_sheet.md`
3. `templates/03_world_building.md`
4. `templates/04_plot_outline.md`
5. `templates/05_chapter_outline.md`
6. 必要に応じて `templates/05_chapter_outline_100k.md`
7. README や agent 文書のうち、テンプレート説明と整合が必要な箇所

非対象:

1. `scripts/` の修正
2. `prompt_utils.py` の parser 変更
3. `agent/skills/` のロジック改修
4. `runtime/` artifact 仕様変更
5. テンプレート以外の本文生成品質改善

## 4. Hard Compatibility Constraints

今回の refactor は「コード互換を保ったまま」進めるため、以下を破ってはならない。

### 4.1 File-level constraints

1. `templates/01_concept_sheet.md` から `templates/05_chapter_outline.md` のファイル名は維持する
2. `templates/05_chapter_outline.md` は canonical outline のままとする
3. `templates/05_chapter_outline_100k.md` は legacy fallback として当面維持する

### 4.2 Structural constraints for `05`

以下は parser と runtime が依存しているため、維持または後方互換にする。

1. `## 第N章 Chapter Card` の章見出し
2. `### Scene Ledger` 見出し
3. `Scene Ledger` 表の列名
4. `- 想定目標字数:` など既存の chapter card ラベル
5. `## Planning Totals` 見出し

### 4.3 Operational constraints

1. `scripts/init_project.py` は `templates/` の Markdown 一式をそのままコピーする
2. `scripts/build_llm_prompt.py` は `01` から `05` の固定ファイル名を読む
3. `scripts/prompt_utils.py` は `05` の章見出し、`Scene Ledger`、表列名を直接パースする
4. 実装 Phase では、script 非変更の時点で既存テストが落ちる構造変更を入れない

## 5. Design Principles

### 5.1 Decision-first

テンプレートは「最初から書くべき内容」を指定するのではなく、「planning で決まった方針をどこへ反映するか」を支援する。

### 5.2 Core plus optional modules

各テンプレートは、全作品で必要な core 項目と、方針次第で使う optional 項目を分離する。

### 5.3 Genre-neutral wording

ラブコメ、コメディ、バトル、ミステリ、政治劇、日常系など、任意のジャンルへ展開できる言い回しにする。

### 5.4 Minimal noise for prompts

`build_llm_prompt.py` がテンプレート全体を読むことを前提に、不要なジャンル誘導を減らし、空欄であってもノイズになりにくい見出し設計にする。

### 5.5 Backward-compatible chapter planning

`05` は自由度を増やすが、scene inventory と planning gate の責務は維持する。

## 6. Target End State

最終状態では、テンプレート群は以下の役割に整理される。

### 6.1 `01_concept_sheet.md`

役割:

1. 作品の核
2. 読者に約束する体験
3. planning で採用するレンズ
4. 非採用のレンズ
5. 作品全体の優先順位

必須の core 項目例:

1. タイトル仮案
2. ターゲット読者
3. ログライン
4. テーマ
5. 作品の売り
6. 物語の主軸 / 副軸 / 補助軸
7. 今回の planning で採用する重点レンズ
8. 今回は採用しない要素

optional 項目例:

1. 関係性レンズ
2. ユーモアレンズ
3. 謎 / サスペンスレンズ
4. 戦闘 / 競技レンズ
5. 社会 / 制度レンズ

### 6.2 `02_character_sheet.md`

役割:

1. 登場人物の欲求、恐れ、変化、関係圧力を整理する
2. キャラを「ジャンル役割」ではなく「物語機能」で捉える

必須の core 項目例:

1. 名前
2. 役割
3. 目的
4. 動機
5. 弱点 / 盲点
6. 変化の起点と着地点
7. 他者に与える圧力
8. 秘密 / 未認識の問題

optional 項目例:

1. 恋愛距離
2. ユーモア相性
3. バディ相性
4. 対立関係図
5. 会話テンポの役割

### 6.3 `03_world_building.md`

役割:

1. 世界設定の情報量を増やすことではなく、物語を動かす制約と発生装置を整理する

必須の core 項目例:

1. 舞台
2. 特別な力 / 技術 / 制度
3. できることとできないこと
4. コスト / 代償 / リスク
5. 社会状況
6. 主な行動舞台
7. 物語が自然発生する環境要因

optional 項目例:

1. 関係性イベント装置
2. コメディ発生装置
3. 捜査 / 陰謀 / 競技のルール
4. 歴史 / 伝承

### 6.4 `04_plot_outline.md`

役割:

1. 「起承転結のテンプレ記入」ではなく、各フェーズで何を前進、悪化、回収、保留するかを整理する

必須の core 項目例:

1. フェーズの目的
2. 主な出来事
3. 主人公の判断
4. 事態の悪化 / 反転
5. 関係性または対立の変化
6. 回収する要素
7. 次フェーズへ残す未解決
8. 軸の配分

optional 項目例:

1. ロマンス進展
2. ユーモアの使い方
3. 謎の提示 / 回収
4. バトル / 競技の段階設計

### 6.5 `05_chapter_outline.md`

役割:

1. canonical outline としての責務を維持する
2. chapter / scene 単位で planning 方針を執筆運用へ橋渡しする

追加可能な最小拡張:

1. `全体方針` に「今回の重点レンズ」欄を追加
2. 各 `Chapter Card` に「この章で強める要素」「避ける要素」を追加
3. `Scene Ledger` の外側に「scene_type では表現しない演出方針」メモ欄を追加
4. `Notes` に planning 由来の判断ログ欄を追加

`Scene Ledger` 表そのものの列追加は、script 非変更 Phase では行わない。

## 7. Refactor Strategy

今回の改修戦略は以下とする。

1. Phase 0 で依存境界と基準を固定する
2. Phase 1 で `01` から `04` の wording を汎用化する
3. Phase 2 で `01` から `04` に core / optional 構造を導入する
4. Phase 3 で `05` に最小拡張を入れる
5. Phase 4 で README と agent 文書の説明を同期する
6. Phase 5 で互換確認と内容レビューを実施し、残課題を確定する

各 Phase は、それ単体で revert 可能であること。

## 8. Phase Execution Plan

## Phase 0: Baseline Freeze

### Purpose

改修前の基準を固定し、以降の差分を評価可能にする。

### Tasks

1. 現行テンプレートの偏り箇所を一覧化する
2. `05` の互換必須構造を明文化する
3. 関連 script / test の依存ポイントを記録する
4. README と request template の説明方針を控える

### Deliverables

1. 本仕様書
2. 依存メモ
3. Baseline の判断基準

### Validation Gate

1. `01` から `04` の偏りが、具体的な見出し単位で列挙されている
2. `05` の parser 依存箇所が章見出し、ledger、totals 単位で識別されている
3. `init_project.py` / `build_llm_prompt.py` / `prompt_utils.py` の依存境界が記録されている

### Rollback

読み取り中心の Phase のため不要。記録が不十分なら再採取する。

### Exit Criteria

後続 Phase が本仕様書だけで開始できる。

## Phase 1: `01` から `04` の文言汎用化

### Purpose

ラブコメ / コメディ前提の wording を、汎用作品でも自然に使える wording へ置き換える。

### Tasks

1. `01` の「コメディ/ラブコメ」中心表現を「重点レンズ」中心へ置換する
2. `02` の「ボケ/ツッコミ」「ラブコメ関係図」を optional 項目へ格下げする
3. `03` の「コメディが生まれる仕掛け」「ラブコメのイベント装置」を一般化する
4. `04` の各幕の固定質問を、ユーモア前提ではない設問へ置換する

### Validation Gate

1. `01` から `04` の本文に、ラブコメまたはコメディを前提とする必須設問が残っていない
2. ラブコメ向けの活用余地は optional として残っている
3. 各ファイルの主見出し数が極端に増えず、初見で埋めやすい
4. 既存のファイル名と大枠の責務は維持されている

### Suggested Review Questions

1. このテンプレートはミステリでも違和感なく使えるか
2. 政治劇や日常系でも空欄を無理に埋めさせないか
3. ラブコメ案件でも情報不足になっていないか

### Rollback

対象テンプレートを Phase 0 時点の内容に戻す。

### Exit Criteria

`01` から `04` が「特定ジャンル向け」ではなく「企画方針の器」になっている。

## Phase 2: Core / Optional 構造の導入

### Purpose

planning の方針反映力を高めるため、各テンプレートに core 項目と optional 項目の境界を持たせる。

### Tasks

1. 各テンプレートの冒頭に「最低限ここまで埋めれば動ける」案内を追加する
2. optional 項目を `必要な場合のみ` と明記する
3. 作品ごとの planning 方針を記入する「採用レンズ」欄を `01` に追加する
4. `02` `03` `04` でも optional ブロックを明確化する

### Validation Gate

1. 各ファイルで core 項目が識別できる
2. optional 項目が、未採用時にノイズになりにくい見出し名になっている
3. planning 時に「何を決めたか」「何をまだ決めていないか」を切り分けられる
4. `build_llm_prompt.py` が全体を読んでも、不要な方向づけが過剰に残らない

### Rollback

Phase 1 版へ戻す。

### Exit Criteria

テンプレートが「全部埋めるもの」ではなく「必要な論点だけ拾えるもの」になっている。

## Phase 3: `05` の最小拡張

### Purpose

script 互換を守りつつ、planning で決まった方針を chapter / scene 運用へ落としやすくする。

### Tasks

1. `全体方針` に planning 由来の重点レンズ欄を追加する
2. 各 `Chapter Card` に「この章で強める要素」「抑える要素」などの補助欄を追加する
3. `Scene Ledger` の外側に運用メモ欄を追加する
4. `Notes` に planning 上の判断や保留事項を書ける欄を追加する
5. `05_chapter_outline_100k.md` にも必要最小限の同期を行う

### Forbidden Changes

1. `Scene Ledger` の列名変更
2. `Scene Ledger` の列順変更
3. 章見出し形式の変更
4. `Planning Totals` 見出し削除
5. `想定目標字数` など parser が読むラベルの改名

### Validation Gate

1. `prompt_utils.py` の parser 前提を壊していない
2. `05` を読んだ人間が、chapter 単位で planning 方針を判断しやすくなっている
3. `05_chapter_outline_100k.md` との責務差が拡大していない
4. 既存の `scene_type` / `Length Band` 運用と競合しない

### Rollback

`05` と legacy `05` を Phase 2 時点へ戻す。

### Exit Criteria

`05` が canonical outline のまま、planning 反映の不足を補えている。

## Phase 4: Documentation Sync

### Purpose

README と agent 補助文書の説明を、新テンプレート思想に合わせる。

### Tasks

1. README のテンプレート説明を更新する
2. 必要なら `agent/request_template.md` の「設定・骨格設計用」の補助文言を更新する
3. 必要なら `agent/skills/setting-creator/SKILL.md` の注意書きを更新する
4. 旧説明のうち、ラブコメ偏重のサンプルがあれば調整する

### Validation Gate

1. README が旧テンプレート思想を説明したままになっていない
2. request template が新テンプレート設計と矛盾しない
3. setting-creator の手順が、core / optional 構造と矛盾しない

### Rollback

文書差分を Phase 3 時点へ戻す。

### Exit Criteria

利用者が README だけ読んでも、新しいテンプレート思想を誤解しない。

## Phase 5: Final Review and Acceptance

### Purpose

テンプレート改修が、運用上の柔軟性と互換性を両立しているかを最終確認する。

### Tasks

1. ラブコメ案件、ミステリ案件、バトル案件の 3 パターンで机上レビューする
2. `05` の構造互換を最終確認する
3. テスト実行または parser 依存確認を行う
4. 未解決論点を `Open Questions` として整理する

### Validation Gate

1. 3 パターンの作品タイプで記入不能な必須項目がない
2. `05` 互換が保たれている
3. 既存の script / test に対して破壊的差分がない
4. README と templates の説明に齟齬がない

### Rollback

Phase 4 完了時点へ戻す。

### Exit Criteria

テンプレート refactor を mainline に乗せてよいと判断できる。

## 9. Validation Matrix

各 Phase で最低限確認する。

### 9.1 Structural validation

1. 対象 Markdown の見出し構造が意図どおりか
2. `05` の章見出し、ledger、totals が残っているか
3. legacy `05` と canonical `05` の責務が崩れていないか

### 9.2 Script compatibility validation

最低限、以下を基準に確認する。

1. `scripts/init_project.py` のテンプレートコピー前提を壊していない
2. `scripts/build_llm_prompt.py` の固定ファイル読込前提を壊していない
3. `scripts/prompt_utils.py` の `extract_chapter_block`, `parse_scene_ledger`, `compute_planned_totals` が依存する `05` 構造を壊していない

### 9.3 Content validation

1. ラブコメ案件で必要情報が取れるか
2. ミステリ案件でコメディ前提の違和感がないか
3. バトル / 冒険案件で関係性偏重になりすぎないか
4. 日常系案件で大仰な conflict を必須化しすぎないか

### 9.4 Prompt noise validation

`build_llm_prompt.py` がテンプレート全文を読む前提で、以下を確認する。

1. optional セクションが未記入でも過剰な誘導にならない
2. 見出しだけで特定ジャンルの圧を生まない
3. 例示文が偏りすぎず、複数ジャンルを想像できる

## 10. Suggested Test and Review Procedure

実装 Phase ごとに、以下を推奨する。

1. 差分レビューで `templates/` を確認する
2. `rg -n "コメディ|ラブコメ|ヒロイン|ボケ|ツッコミ" templates` で偏り語の残存を確認する
3. `05` 変更 Phase では `rg -n "Scene Ledger|Planning Totals|想定目標字数|第1章 Chapter Card" templates\\05_chapter_outline.md scripts\\prompt_utils.py tests\\test_scripts.py` を確認する
4. 可能なら `pytest tests/test_scripts.py` を実行して互換確認する

注記:

1. 今回の仕様時点では script 修正は含まない
2. 実装時に test が失敗した場合、Phase を進めず `05` の構造変更を見直す

## 11. Acceptance Criteria

以下をすべて満たしたら、本 refactor は完了とみなす。

1. `01` から `04` が特定ジャンル前提でなくなる
2. `01` から `04` に core / optional の境界がある
3. `05` は parser 互換を保ったまま planning 反映力が増している
4. README と関連文書が新方針を説明している
5. ラブコメ、ミステリ、バトルの 3 タイプで実用的に使える
6. 既存の script / test に対して、少なくともテンプレート構造起因の破壊がない

## 12. Risks

1. 汎用化しすぎて、逆に何を書けばよいかわかりにくくなる
2. optional 項目を増やしすぎると、`build_llm_prompt.py` でノイズが増える
3. `05` の補助欄を入れすぎると chapter card の可読性が落ちる
4. legacy `05` への追随が不足すると、canonical と legacy の説明差が広がる

## 13. Open Questions

1. `04_plot_outline.md` は起承転結ベースを維持するか、より抽象的な phase 設計へ寄せるか
2. `02_character_sheet.md` の optional 項目に、相関図をどこまで残すか
3. `05` の補助欄は chapter card の bullet に入れるか、別見出しへ分離するか
4. README の記入例は 1 ジャンルだけでなく複数出すべきか

## 14. Recommended Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5

各 Phase は validation gate を通過した場合のみ次へ進むこと。

## 15. Phase Handoff Template

別チャットまたは別作業単位で進める場合、各 Phase の開始時に以下を貼る。

```text
このチャットでは template_refactor_spec_2026-03-09.md に従って、
Phase N のみ実行してください。
変更は Phase N の範囲に限定し、終了時に以下を報告してください。
1) 変更ファイル一覧
2) 実施した検証
3) 互換性リスク
4) 次 Phase に進めるかの判定
```

## 16. Completion Record

完了日: 2026-03-09

実施 Phase:

1. Phase 1: `01` から `04` の文言汎用化
2. Phase 2: `01` から `04` の core / optional 化
3. Phase 3: `05` と legacy `05` の最小拡張
4. Phase 4: README / agent 文書同期
5. Phase 5: 最終レビューと受け入れ判定

実施した検証:

1. `rg -n "コメディ|ラブコメ|ヒロイン|ボケ|ツッコミ" templates\\01_concept_sheet.md templates\\02_character_sheet.md templates\\03_world_building.md templates\\04_plot_outline.md`
2. `rg -n "^## 第[1-5]章 Chapter Card|^### Scene Ledger|^## Planning Totals|^\\- 想定目標字数:" templates\\05_chapter_outline.md templates\\05_chapter_outline_100k.md`
3. `rg -n "extract_chapter_block|parse_scene_ledger|compute_planned_totals|想定目標字数|### Scene Ledger" scripts\\prompt_utils.py tests\\test_scripts.py`
4. `pytest -q tests/test_scripts.py` (`61 passed`)
5. ラブコメ / ミステリ / バトル案件の机上レビュー

残課題:

1. `build_llm_prompt.py` の実案件ベースの prompt noise spot check は未実施
2. `04_plot_outline.md` を将来さらに抽象的な phase 設計へ寄せるかは別判断
3. genre-neutral な記入例を README に追加するかは保留
