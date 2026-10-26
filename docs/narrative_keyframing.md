# 選択的な視点素材（Narrative Keyframing）

## 何が変わるか

**新しいprepareでは基本有効。設定ファイルがない既存案件も有効になる。** 視点人物が何を受け取り、どう解釈し、次にどう返す／動くかを外部エージェントが短い創作素材にして登録する。Pythonは生成サービスではなく、対象・形式・参照・鮮度を検査する。モデルAPIや追加のランタイム依存はない。

**選んだ素材は、台詞ににじませる／地の文に出すことを主とする。** `dialogue` / `narration` / `both` が通常の反映先。省略を同等の逃げ道にせず、両方が不自然・冗長・テンポを損なう場合だけ具体的な理由を記録する。全発話への心理説明、仕草や描写量のノルマではない。

発想の出典は Chao Zhang / Abe Davis の [Narrative Keyframing for Generative Creative Writing（2026）](https://arxiv.org/abs/2608.10337) と [公開プロトタイプ](https://github.com/zhangchaodesign/narrative-keyframing)。一人称の中間叙述を本文へつなぐ考えを参考にした、このリポジトリ向けの独立した限定実装である。論文全体・UI・生成サービスの再現でも、その研究の評価結果を本実装へ移したものでもない。

## 標準手順

以下はリポジトリルートからの例。既存のScene Ledger、文体、計画ゲートを先に整える。

```sh
python scripts/run_scene_pipeline.py prepare --project my_novel --chapter 1 --scene 1-2 --pov-character mira
python scripts/run_scene_pipeline.py keyframe-prompt --project my_novel --scene 1-2 --output keyframe_proposal.json
```

外部エージェントは対象の `runtime/scenes/1-2/draft/narrative_keyframe_prompt.txt` と `narrative_keyframe_request.json` を読み、作成された `keyframe_proposal.json` の未記入欄を完成させる。ユーザーの毎回のJSON手入力を前提にしない。requestの `generation_id` と採用された `sources` を使う。テンプレートのままでは登録できない。

```sh
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json --validate-only
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json
python scripts/run_scene_pipeline.py prompt --project my_novel --scene 1-2
```

外部エージェントが `draft_prompt.txt` から本文をscene txtへ書く。**登録は創作素材の受理であって本文承認ではない。**

```sh
python scripts/run_scene_pipeline.py check --project my_novel --text chapter_1_scene_2.txt
# checkが要求する場合は、本文のexact spanを読んでレビューの未記入欄を埋める
python scripts/run_scene_pipeline.py review-dialogue --project my_novel --scene 1-2 --output review-input.json
python scripts/run_scene_pipeline.py review-dialogue --project my_novel --scene 1-2 --input review-input.json --reviewer-type agent --reviewer-id codex
# 本文を確認し、明示的に承認する場合だけ実行
python scripts/run_scene_pipeline.py approve --project my_novel --scene 1-2 --reviewer-type agent --reviewer-id codex
```

checkの正常終了は本文passと同義ではない。reportのstatus、warning、未解決レビューを確認する。`--allow-warnings`、`--force`、automationでも中間工程と必要な本文レビューは免除されない。直接入口は `build_keyframe_prompt.py` と `register_keyframes.py`（どちらも `--project/--scene/--runtime_dir`）。

## POVと知識の境界

- POVは `--pov-character` または `dialogue_voice.json` の対象scene設定だけから選ぶ。参加者の先頭、自由記述の人物紹介から推測しない。
- POV不明でもprepareは点検資料を作り、`needs_pov` を示す。中間生成・draft・expand・check・新規approveは停止する。カードが欠けていても明示POVがあれば進められるが、性格を勝手に補作しない。
- `planning` はこれから書く場面の予定。`author_context` は作者用情報でPOVが知る証明ではない。`pov_context` は選択済みの人物知識、`continuity` は接続資料、`voice` は表現設計である。
- `source_refs` は採用された資料を参照できることだけを証明する。推測の正しさや、作者用の秘密をPOVが知ることは証明しない。
- 現在sceneの知覚・反応は創作提案であり、承認済みの過去事実ではない。他者の内心を断定せず、未来の予定を過去の記憶へ昇格しない。canon/fact/character_knowledgeは自動作成しない。記憶は承認済み本文から別途提案・採用する。

## proposalの形式

rootは `version: 1`, `scene_id`, `pov_character_id`, `generation_id`, `keyframes`, `scene_omission` のみ。各keyframeは以下の全項目を持つ。

| 項目 | 内容 |
|---|---|
| `id` | 一意な `kf1`〜`kf3` |
| `anchor` | 場面中の出来事・言葉・知覚の要所 |
| `source_refs` | requestにあるsource IDの非空配列 |
| `selection_reason` | その受け止めが返答・判断・読者の読みを変える理由 |
| `perception` / `interpretation` / `response` | POVとしての短い一人称創作素材。日本語の「私は」を強制しない |
| `realization` | 通常 `dialogue` / `narration` / `both`、例外のみ `omit` |
| `realization_note` | どの語感・返答・叙述へ反映するか |
| `omission` | 通常null。omitのみ下のobject |

```json
{
  "category": "tempo_damage",
  "dialogue_reason": "無言で通り過ぎる橋渡しに発話を足すと移動が止まる。",
  "narration_reason": "既に示した警戒を説明し直すと移動の速度を損なう。"
}
```

categoryは `unnatural` / `redundant` / `tempo_damage`。両経路の理由を必須とし、空欄・TODO・TBD・未記入は拒否する。理由の誠実さ・意味的妥当性はエージェント／人が評価する。

最大3件は**上限であってノルマではない**。`keyframes: []` だけでは提出できない。適した要所を選べない例外では `scene_omission` に `considered_anchor`, `source_refs`, `category`, `dialogue_reason`, `narration_reason` の5項目を入れる。keyframesがある場合scene_omissionはnull。全項目omitでも各項目に両経路の具体的理由が必要で、通常成功の代用品ではない。

自然文は各1〜240 Unicode文字、IDは80文字以内・空白なし。提出は65,536 bytesまで、本文へ渡す素材レンダリングは3,000文字まで。未知キー、重複キー、重複ID/source、未知source、異なるscene/POV/generationは拒否する。上限超過は黙って切らず、素材を短く整える。

## 本文への反映と既存レビュー

「責める口調に聞こえた。違うかもしれないので言い訳を引っ込める」という素材は、本文の「……何を先に知りたい？」という返答へ暗示的に反映してよい。一人称素材を三人称本文へ加工してよく、逐語転記は合格条件ではない。

既存の会話レビューは変わらず、候補ごとの `keep/revise/uncertain`、正確な本文範囲、読者への効果、改稿時のbefore/afterを残す。候補に関係する素材は実本文と比較する。単に心理の説明がないだけで欠陥とせず、台詞の選び直しに読み取れる反映を評価する。4発話未満の応酬や地の文も自己評価するが、候補抽出が全主観描写を網羅したとは言わない。

本文段階で予定した反映を省略へ変える場合は、proposalに両経路の理由を記し再登録する。必要なprompt再生成・再check・再レビューを行い、無記録で省略へ変更しない。同一proposalの再登録は冪等、別の妥当なproposalの明示登録は置換で、旧checkはstaleになる。

`repair` / `build_expand_prompt.py` は文字数不足への**局所増補のまま**。登録素材と参照資料を保持するが、既に反映済みの内容を重複説明しない。意味的改稿が必要ならrevisionへ戻る。本文を自動変更するコマンドではない。

## 設定と例外的な無効化

案件直下の任意ファイル `narrative_keyframing.json`:

```json
{
  "version": 1,
  "enabled": true,
  "scenes": {
    "1-2": {"enabled": false, "disable_reason": "この場面は視点人物のいない外的な年表として書く。"}
  }
}
```

優先順位はCLI → 対象scene → root → true。不明キー・不正型は停止する。無効化には具体的な理由が必要。有効時にはdisable_reasonを書かない。

```sh
python scripts/run_scene_pipeline.py prepare --project my_novel --chapter 1 --scene 1-2 --keyframing off --keyframing-reason "視点人物を持たない外的な記録として書く。"
```

CLI選択はそのprepareに記録されるだけで、次のprepareへ黙って引き継がれない。設定なしの次回prepareは再び有効。理由だけのCLI指定はエラー。`--mode resume` は状態確認用で、中間生成はできない。執筆時は同じsceneをdraftでprepareする。

## ファイルと鮮度

prepareが作る `narrative_keyframe_contract.json` は不変契約。`context_selection.json` の静的keyframing設定とともにmanifestで保護される。後生成するprompt/request/resultはこの契約を上書きせず、artifact台帳へ別登録する。

- 外部proposalを置いただけでは登録済みにならない。
- `narrative_keyframes.json` を手で書き換えたり、これ自身をinputにして自己登録したりできない。
- proposalのoutputは新規ファイルだけ。既存ファイル、scene本文、契約、登録先へ上書きしない。
- 入力・契約・request・prompt・結果が変わった／消えたら停止。同じsceneのprepareから解決する。検査時にruntimeを自動生成しても中間工程は飛ばせない。
- promptの上限は16,000文字。必須制約、POV・知識ラベル、登録素材、その参照sourceは予算で落とさない。必須だけで超過すれば明示エラー。
- 新規check/approveは現行登録と一致するbindingを要求。承認には平坦なsnapshotを保存し、承認台帳自身の更新で即staleにならない。後日のartifact台帳整理だけでは過去の承認を取り消さないが、適用policy・selection・contract・resultの変更はstaleとなる。
- keyframing拡張を持たない過去のv1/v2承認は従来の条件で読込・exportする。新しいゲートを過去承認へ遡及しない。旧runtimeから新しく執筆・check・approveする場合は再prepareが必要。

`build_llm_prompt.py` は旧フル文脈入口で、この中間生成・限定文脈の保証対象外。その入口で作った本文も、新規scene check/approveでは同じゲートを通す。

## 評価の範囲

合成fixtureの成功は形式・鮮度・CLI経路の検証であり、小説の品質改善ではない。短い日本語例の評価手順は [評価ケース](../agent/evals/narrative_keyframing_cases.md)。実施結果は別途記録し、未実施は未実施とする。agentの判断を人間承認と呼ばず、数件の例を一般的な効果の実証としない。既存作品の移行・本文一括書換えはしない。
