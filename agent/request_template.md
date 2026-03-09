# Request Template (Common)

依頼を構造化することで、Agent が不要な確認なしに動けるようになります。
用途ごとに必要な情報が違うため、以下のテンプレートから近いものを選んで使ってください。

---

## 共通ルール

- `Purpose` と `Deliverables` は必須
- 本文の正本はシーン単位 `txt`
- 通常運用では `body.md` を本文追記先として指定しない
- `Target Total Chars` を最初に決める
- `Target Length Profile` は補助ラベルであり、本文長の正本は `Length Band`
- `planning_gate_enabled=true` の profile では固定 `1000-1500` ではなく、`scene_type` ごとの `Length Band` を使う
- 低クレジット運用では、`bridge` を短く保ち、`anchor` / `climax` だけを厚くする
- 必須項目だけで依頼してよい。細部は `Context` と `Notes` で補う
- `01_concept_sheet.md` から `04_plot_outline.md` は core と optional を分けて使う。未採用の optional 項目は空欄でよい
- `setting_creation` を頼むときは、今回の重点レンズと前面に出しすぎない要素を書くとズレが減る
- `Mode` を書く場合は、`HUB.md` の正式モード名をそのまま使う
- 正式モード名: `idea_generation` / `project_bootstrap` / `setting_creation` / `scene_planning` / `novel` / `revision` / `consistency_audit` / `polish` / `resume_orchestrator`

---

## 1. アイディア出し用

```md
## Purpose
どんな企画を立ち上げたいか

## Deliverables
- 出力: アイディア候補
- 出力: 仮ログライン

## Required Context
- ジャンル
- 好きな要素
- 避けたい要素

## Notes
- 迷っている点
```

---

## 2. プロジェクト初期化用

```md
## Purpose
合意済みの企画を、実作業用の案件として立ち上げたい

## Deliverables
- 出力: プロジェクト名
- 出力: 初期化対象パス
- 出力: 次に呼ぶべきスキル

## Required Context
- 確定済みログライン
- 保存したい親フォルダ

## Constraints
- 命名ルール
- `Target Total Chars`（`30000` / `50000` / `100000`）
- `Target Length Profile`（`novel_30k` / `novel_50k` / `novel_100k`）
- `Prefer Low Credit Mode`（yes / no）
```

---

## 3. 設定・骨格設計用

```md
## Purpose
どの設定や骨格を固めたいか

## Deliverables
- 更新対象: 設定ファイル
- 出力: 修正方針と反映内容

## Required Context
- 変えたい前提
- 重点レンズ、または強めたい要素
- 今回は前面に出しすぎない要素

## Current Issue
- いま起きている矛盾や不満

## Constraints
- 維持したい世界観
- 維持したい着地点
- 必須で埋めたいファイル（例: `01` と `05` だけ / `01` から `04` まで）
- `Planning Gate` を通したいか
- 重要シーンだけ厚くしたいか
```

---

## 4. シーン設計用

```md
## Purpose
次に書く章やシーンの段取りを固めたい

## Deliverables
- 出力: 次章または次シーン群の設計
- 出力: 直近で読むべきファイル

## Required Context
- 対象章または対象シーン
- 現在の章プロット

## Focus
- シーン順
- 目的
- 衝突
- 回収 / 種まき
- 次へのフック
- `Scene Type`
- `Length Band`
```

---

## 5. 新規執筆用

```md
## Purpose
何を新しく書くか

## Deliverables
- 対象: chapter_x_scene_y.txt
- `Scene Type`: `bridge` / `standard` / `anchor` / `climax`
- `Length Band`: 自動 または 明示
- 出力: 本文初稿

## Required Context
- 参照すべき章プロット
- `05_chapter_outline.md` の対象行
- 直前シーン

## Context
- シーンで達成したいこと
- 次に残したいフック

## Constraints
- 視点
- 禁止表現
- 残したいフック
- `Target Total Chars`
- `Target Length Profile`
- `Prefer Low Credit Mode`
```

---

## 6. 改稿用

```md
## Purpose
どのシーンを、何のために改稿するか

## Deliverables
- 対象: 既存の scene txt
- `Scene Type` と `Length Band` を維持または調整
- 出力: 改稿版

## Required Context
- どのファイルを直すか
- 何が問題か

## Keep
- 維持したい要素

## Change
- 変えたい要素

## Constraints
- 変えてはいけない設定
```

---

## 7. 整合性監査用

```md
## Purpose
何を診断したいか

## Deliverables
- 出力: 問題点一覧
- 出力: 修正方針

## Required Context
- どこを見ればよいか

## Scope
- 対象章
- 対象シーン
- 対象ファイル

## Focus
- 視点
- 設定矛盾
- 感情線
- テンポ
```

---

## 8. 再開整理用

```md
## Purpose
どこから再開すべきか整理したい

## Deliverables
- 出力: 現在地の要約
- 出力: 次に着手すべき作業

## Required Context
- 対象プロジェクト

## Context
- 前回の終了地点
```

---

## 9. 仕上げ・推敲用

```md
## Purpose
どの文章を、どう整えたいか

## Deliverables
- 対象: scene txt または章本文
- 出力: 仕上げ版

## Required Context
- 構造は変えるか変えないか

## Focus
- 語尾
- 読みやすさ
- 密度
- 引き
```

---

## 10. 共通補助項目

```md
## Priority（あれば）
速さ優先 / 品質優先 / バランス重視

## Target Total Chars（あれば）
30000 / 50000 / 100000

## Target Length Profile（あれば）
novel_30k / novel_50k / novel_100k

## Length Mode（legacy fallback のみ）
short / standard / long_form_100k

## Prefer Low Credit Mode（あれば）
yes / no

## Mode（あれば）
idea_generation / project_bootstrap / setting_creation / scene_planning / novel / revision / consistency_audit / polish / resume_orchestrator

## Notes（あれば）
特に気にしてほしいこと
```

---

## 最小依頼の書き方

短く頼む場合でも、以下のどれかに寄せると誤解が減ります。

```md
idea_generation: 学園ものの企画を壁打ちしたい。会話強めで考えたい。
project_bootstrap: このログラインで案件を立ち上げたい。保存先は novels 配下。Target Total Chars は 50000。
setting_creation: 主人公の動機と世界の制約を固めたい。重点レンズは関係性と謎。ご都合主義は避けたい。
scene_planning: 第3章の次の 2 シーンだけ段取りを決めたい。
novel: 第3章シーン2の初稿を書いて。直前は 3-1。
consistency_audit: 第4章の違和感を見て。感情線とテンポ重視。
revision: 2-4を書き直して。オチは残して、説明を減らして。
polish: 5-1を読みやすく整えて。構造は変えない。
resume_orchestrator: 今どこから再開すべきか整理して。
```

---

## 記入例（新規執筆）

```md
## Purpose
第2章シーン1の初稿を書いてほしい

## Deliverables
- 対象: chapter_2_scene_1.txt
- Scene Type: standard
- Length Band: 自動
- 出力: 本文初稿

## Context
- `05_chapter_outline.md` の第2章シーン1
- 直前は `chapter_1_scene_8.txt`

## Constraints
- 視点は三人称（主人公寄り）
- 見出しや箇条書きは本文に入れない
- Target Total Chars: 100000
- Target Length Profile: novel_100k
- Prefer Low Credit Mode: yes

## Notes
- シーン末尾に次の検証フックを残したい
```
