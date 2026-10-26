# Narrative Keyframing 型の選択的主観生成 — 設計

- 対象: `22a2dba`（main）の外部エージェント + Python 標準ライブラリ構成。
- 状態: **承認済み・実装検証済み（2026-10-25 UTC）。実測結果は [検証報告](../../validation/2026-10-26-narrative-keyframing.md) を参照。既存作品の本文は変更しない。**
- 対応計画: `docs/superpowers/plans/2026-10-26-narrative-keyframing.md`
- 日付: 2026-10-26（作業環境の UTC 日付は 2026-10-25）。

## 1. 狙いと合意事項

選んだ要所で、視点人物が「何を受け取ったか → どう解釈したか → どう返す／動くか」を短い一人称の創作素材として先に作り、初稿へ渡す。単なる問答の往復を減らし、受け止め方が次の発言・ためらい・判断に影響する文章を作りやすくする。論文の完全再現や品質向上の実証を主張するものではない。

ユーザーが選択した方式は、現在の外部エージェント運用への統合である。最新の方針を以下に固定する。

1. **基本有効。設定ファイルがない案件も、新しく prepare する際は有効。**
2. **選んだ主観素材は、台詞ににじませる／地の文に出すことを主とする。省略を同等の通常選択肢にしない。**
3. そのどちらでも不自然・冗長・テンポを損なう場合だけ省略する。台詞と地の文の**両方**が適さない具体的な理由を残す。
4. 全発話に挿入しない。心理描写の回数・比率のノルマにしない。短い場面でも無理な描写を増やさない。
5. Python は対象、形式、参照、鮮度、登録を検査する。主観の意味的妥当性、理由の誠実さ、文学的品質は外部エージェント／人の判断である。

以下のファイル名、上限、CLI 名、例外の記録形式は、この方針を実装可能にする**実装側の提案**であり、ユーザーが個別に指定した数値ではない。

## 2. 方式比較

| 方式 | 長所 | 限界／判断 |
|---|---|---|
| 既存 runtime に中間生成・検証・登録を追加 | 現在の外部エージェント、依存追跡、本文レビューを利用できる | 手順が二段増える。**選択された方式** |
| draft prompt の注意書きだけ強化 | 最小の変更 | 中間素材を作ったか、どの入力に基づくかを追跡できないため今回の主方式には不足 |
| 内蔵 LLM/API による自動生成サービス | 人手の受け渡しを減らせる | API、認証、費用、再試行管理を持ち込み、現在の責務から外れるため採用しない |

## 3. 範囲と非目標

対象は `prepare → keyframe prompt → 外部生成 → validate/register → draft → check → 既存 review → approve` の一つの連続した機能。登録済み素材は文字数不足用の `expand` にも渡すが、`repair` は今後も文字数増補のみで、意味的改稿コマンドへ改称・拡張しない。

- 本文の正本は既存の scene txt。既存本文を自動書換えしない。過去作の一括再生成・移行はしない。
- API 呼出し、新規ランタイム依存、全人物の内心生成、自由記述からの POV 推測、canon への自動昇格はしない。
- 既存の会話候補抽出・exact-span レビューを置き換えない。別の全 keyframe 実現レビュー台帳は作らない。
- 中間素材の文を本文へそのまま転記する義務はない。一人称素材を三人称本文へ加工してよく、台詞の語彙・言い直し・返答選択に**暗示的に反映**してもよい。
- 外部エージェントが JSON を作成・提出する。ユーザーが毎回手入力する設計にしない。

## 4. 現行実装との接点

- `build_runtime_context.py` が scene-scoped runtime、`context_selection.json`、manifest、artifact 台帳を生成する。
- `dialogue_context.py` が明示参加者と POV を選ぶ。POV は参加者の先頭とは限らず、既存 `--pov-character`／scene 設定をそのまま唯一の指定元とする。
- `build_draft_prompt.py`／`build_expand_prompt.py` は `assemble_prompt` で最終 16,000 文字以内に組み立てる。
- `check_scene_output.py` は runtime がない場合に同一 scene を自動 prepare する。これで中間生成を迂回できてはならない。
- `approvals.py` は新規承認のゲートと、過去承認の読込検証を分離している。この境界を維持する。
- 依存 projection の現行 v1/v2 の意味は固定。`memory_selection` は現在 `version/config/memory/dialogue` のみを投影し、任意に新フィールドを追加するだけでは鮮度保護されない。
- prepare の manifest に記録したファイルを外部生成結果で上書きすると runtime 自体が stale になる。**不変の契約、未登録 proposal、登録済み結果を別ファイルにする。**

## 5. 方針設定と状態遷移

任意の案件ファイル `narrative_keyframing.json`:

```json
{
  "version": 1,
  "enabled": true,
  "scenes": {
    "1-2": {"enabled": false, "disable_reason": "この場面は視点人物を持たない外的記録として書く"}
  }
}
```

- 許可キーは root `version/enabled/disable_reason/scenes`、scene `enabled/disable_reason`。不明キー、不正型、未知 version を停止する。
- 優先順位は CLI `--keyframing on|off` → 対象 scene 設定 → root 設定 → `true`。
- 有効時 `disable_reason` は不要・空。無効時は具体的な非空の理由が必須。CLI off は `--keyframing-reason` を伴う。理由だけの CLI 指定はエラー。
- CLI 選択とその出典を runtime に保存する。次の prepare は指定・設定を改めて解決する。前回 off を黙って引き継がない。
- 対象外 scene の正常な設定変更だけで runtime を stale にしない。適用された設定、対象 scene 設定、ファイルの不在／存在を追跡する。
- 有効でも POV 不明なら prepare は点検用資料を作成できるが、`needs_pov` を明示し、中間生成・draft/check/expand/新規 approve は停止する。必要な `--pov-character` か、理由付き明示 off を案内する。POV カードの欠落と POV 未指定は別問題であり、カードがなくても明示 POV で進められる。
- `--mode resume` は状態確認を妨げない。方針と次の不足入力を示し、執筆時は draft prepare へ戻す。resume runtime から中間生成はしない。

```text
prepare(draft)
  ├─ enabled + POVあり → awaiting_keyframes
  ├─ enabled + POV不明 → needs_pov（生成停止）
  └─ explicit off + reason → disabled（記録して従来の本文工程へ）
awaiting_keyframes → keyframe-prompt → 外部 proposal → register-keyframes
registered → prompt → 外部本文 → check → 既存 review-dialogue → approve
入力変更／改変／欠損 → stale または不正として停止 → 同じ scene の prepare から解決
```

## 6. 成果物と所有者

scene draft runtime を `R = runtime/scenes/<scene>/draft/` と表す。

| ファイル | 作成・変更者 | 性質 |
|---|---|---|
| `R/narrative_keyframe_contract.json` | prepare | manifest 管理の不変契約。version、scene、POV、方針と出典、上限、schema version。生成結果は入れない |
| `R/narrative_keyframe_prompt.txt` | keyframe-prompt | 検証済み runtime だけから作る生成指示。artifact 台帳に登録 |
| `R/narrative_keyframe_request.json` | keyframe-prompt | generation ID、prompt hash、contract hash、compact inputs/digest、実際に prompt に採用した source ID と区分、未完成 proposal テンプレート。artifact 登録 |
| `keyframe_proposal.json`（任意の作業ファイル） | 外部エージェント | 未信頼の提出物。読んだだけで登録済みとはしない |
| `R/narrative_keyframes.json` | register-keyframes のみ | 検証済み proposal + 生成 provenance。artifact 台帳に登録。draft/expand が読む唯一の結果 |

`context_selection.json` は新規 prepare で version 2 とし、`keyframing` に方針、POV、contract の静的メタデータを保持する。登録結果や生成時刻はこの入力領域へ書き戻さない。`keyframe_prompt/final_prompt/expand_prompt` は派生レポート領域として依存 projection から除く。manifest version は 1 を保ち、`features.narrative_keyframing = 1` を付ける。契約ファイルは manifest.files に含めるが、後で生成する prompt/request/result は含めない。

登録は既存 `project_lock` 下で行う。対象、入力、prompt/request と登録済み ledger hash を検査し、書込直前にも再検査する。結果 JSON の atomic write と ledger 更新の間で失敗しても、次回読込は ledger 不在／hash 不一致を停止し、未登録結果を使わない。本文には触れない。

## 7. 提出 schema と省略の位置づけ

proposal の root キーは固定: `version` (1), `scene_id`, `pov_character_id`, `generation_id`, `keyframes`, `scene_omission`。

各 keyframe のキー:

- `id`: scene 内で一意、`kf1`〜`kf3`。
- `anchor`: 予定された出来事・言葉・知覚のどこを要所とするか。
- `source_refs`: request に存在する source ID の非空リスト。
- `selection_reason`: 返答・判断・読者の読みを変える理由。
- `perception`, `interpretation`, `response`: **視点人物としての短い一人称創作素材**。解釈は相手の内心の事実ではない。日本語の一人称代名詞の有無を機械判定しない。
- `realization`: `dialogue | narration | both | omit`。最初の三つを主とする。
- `realization_note`: どの返答・語感・叙述に反映するか。omit の場合も、何を残し何を見せないかを記す。
- `omission`: 通常 `null`。omit の場合だけ次の object を必須とする。

省略 object は `category` (`unnatural | redundant | tempo_damage`), `dialogue_reason`, `narration_reason` の三キー。**両経路の理由を必須**とし、空欄や `TODO/TBD/未記入` のテンプレートは拒否する。機械は理由の意味的妥当性を認定しない。

keyframe は最大 3 件で、これは上限であって描写数のノルマではない。`keyframes: []` 単独は禁止。適した要所を選べない例外は、`scene_omission` に `considered_anchor/source_refs` と上の省略 object の三キーを持つ具体的な場面検討を提出する。keyframes がある場合 `scene_omission` は必ず null。全 keyframe が omit でも各項目の両経路理由は必要で、通常成功の代用品としない。

各自然文フィールドは 1〜240 Unicode 文字、ID は 80 文字以内・空白なし。source_refs の重複・未知 ID、未知キー、bool を version とする値、過剰件数を拒否する。提出 JSON は最大 65,536 bytes、本文に渡すレンダリングは最大 3,000 Unicode 文字。超過は明示エラーで、黙って項目・注意書きを削らない。テンプレートは未完成のまま提出すると失敗する。

例として「私は問いを責める口調に聞いた。違うかもしれないが、まず言い訳を引っ込めよう」という素材は、本文の「……何を先に知りたい？」という返答にも反映しうる。説明文への逐語転記を要求しない。最終レビューでは、その**正確な本文範囲**と読みの効果によって判断する。

## 8. 入力の安全な区分と文脈予算

keyframe prompt に入れるのは、同じ scene の必須 style/brief/request/planning gate/dialogue と、既存の選択済み memory/continuity/related context だけ。全 outline、全人物紹介、manifest 内の生データへ読み広げない。

source registry は、最終組立てで実際に採用された section の ID と `planning/author_context/pov_context/continuity/voice` の区分を記録する。未来情報・不採用 memory を ID だけで復活させない。`source_refs` は参照可能性を証明するだけで、当該解釈が正しいことや、作者用情報を POV が知っていることの証明ではない。

**対象 scene 内の知覚・反応は、これから書く創作提案である。承認済み過去の出来事ではない。** planning の予定と accepted memory を明示的に分ける。推測を canon/fact/character_knowledge に登録しない。story_memory の既存「承認済み本文から別途提案→採用」を維持する。

中間 prompt、draft、expand は既存 `assemble_prompt` と 16,000 文字上限を使用する。style、scene、planning gate、出力契約、POV/知識ラベル、keyframing の規則・登録素材を required とする。必須だけで超過すれば停止する。省略対象の任意 memory/continuity/related は既存の優先度で扱い、採否を selection レポートに残す。素材が参照した source section は draft/expand でも必須として保持し、参照先が予算落ちしたまま主観だけ残さない。

## 9. 鮮度と互換性

1. 新 selector `keyframing_policy` は設定正本から毎回再計算し、CLI override と理由のスコープを記録する。`keyframing_selection` は対象 context_selection の静的 keyframing と POV/config を守る。
2. 上記 selector と新 `memory_selection` を projection v3 とする。新 memory projection は `version/config/memory/dialogue/keyframing` を含む。v1/v2 の出力と hash 意味は変更しない。古い記録を最新 v3 として読み替えない。
3. prepare は新 policy、selection を inputs に含める。prompt/request/result は compact artifact dependency を使い、過去入力の再 snapshot で stale を正当化しない。
4. draft/expand/check/新規 approve は共通の `require_keyframing_current` を使う。各経路で現在の policy・selection・contract・登録結果を確認し、保存直前にも captured guards を検証する。`--force`、`--allow-warnings`、automation は免除にならない。
5. 新 check は `keyframing` binding と**安定した検査依存**を保存する: policy/selection の v3 projection、contract と登録結果の `kind=file` hash。登録 artifact の推移的依存を check_inputs に入れない。prepare は approval_ledger 全体を参照するため、それを承認へ継承すると approve 自身の台帳更新で即 stale になる。作成時の full runtime/登録鮮度検査と、承認後の履歴検証を分離する。新 approve は同じ現在 binding を要求し、旧 check をそのまま通さない。新 approval に binding と平坦な `keyframing_snapshot`（proposal、source 区分、contract/prompt/request/registration hash、generation ID、inputs digest、snapshot digest）をコピーする。無効時 snapshot は null とする。snapshot に推移的 dependencies や台帳履歴は埋め込まない。過去承認の証跡確認は保存済み snapshot を使い、artifact 台帳の後日削除・整理だけでは取り消さない。有効な policy/selection/contract/result の変更は引き続き stale とする。
6. **既存の keyframing 拡張を持たない v1/v2 approval は従来の条件だけで読込・exportする。** 新規承認ゲートを過去承認検証から呼ばない。従来の本文・依存変更に伴う stale は残す。
7. 旧 runtime の新規 draft/expand/check は同じ scene の再 prepare を案内して停止する。古い「keyframing がなければ互換 fallback」で新しい既定値を回避しない。standalone 機械 check は従来どおりだが、scene 承認や keyframing 済みを主張できない。
8. accepted memory の出典となる**過去 scene**に新 keyframing binding がある場合、その source approval の安定した policy/selection/contract/result guards も新 runtime に引き継ぐ。target／未来の自己参照と再帰的な provenance 複製を避ける。承認履歴の検証では登録当時の全 runtime graph を再実行しない。素材の参照妥当性・鮮度は登録／check／新規 approve 時点の保証であり、過去の創作工程を後から意味的に再認定するものではない。既存の compact guard・性能検査を維持する。

## 10. CLI と担当者の手順

```sh
python scripts/run_scene_pipeline.py prepare --project my_novel --chapter 1 --scene 1-2 --pov-character mira
python scripts/run_scene_pipeline.py keyframe-prompt --project my_novel --scene 1-2 --output keyframe_proposal.json
# 外部エージェントが narrative_keyframe_prompt.txt を読み、proposal の未記入欄を完成する。
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json --validate-only
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json
python scripts/run_scene_pipeline.py prompt --project my_novel --scene 1-2
# 外部エージェントが scene txt を執筆。以後 check → 必要な review-dialogue → 明示 approve。
```

直接入口は `build_keyframe_prompt.py` と `register_keyframes.py`。両方 `--project/--scene/--runtime_dir`、前者は `--output`、後者は `--input/--validate-only` を受ける。output は外部 proposal 用で、manifest 管理ファイル・登録先・既存本文との同一 realpath は拒否し、既存ファイルは上書きしない。input を登録先そのものにして自己承認しない。

新規 prepare の NEXT は中間生成を示し、明示 off の場合だけ従来 prompt を示す。不足 POV、stale、missing、budget はそれぞれ修正すべき対象と次のコマンドを出す。prepare と validate-only は本文・accepted memory・承認を変更しない。

## 11. 文章への反映と既存レビュー

登録は創作素材の受理であって本文承認ではない。draft/expand は素材を機械的にコピペせず、既存の文体・長さ・場面目的を優先し、選んだ要所の受け止めを主に台詞／地の文へ反映する。expand は既に反映された内容を重複説明せず、必要な局所差分だけにする。意味的修正が必要なら既存 revision 手順へ戻る。本文作成中に予定していた反映を省略へ変える場合は、両経路の理由を proposal に記して再登録し、必要な prompt の再生成・再check を行う。無記録で省略へ変更しない。

既存 review の candidate、`keep/revise/uncertain`、exact span、before/after、非 keep の承認停止を保持する。候補に関係する keyframe は素材と本文を比較して、暗示的反映でも exact span と具体的理由を示せれば評価可能とする。台詞 4 発話未満の箇所や地の文もエージェントの自己評価対象だが、候補抽出が全主観を網羅したとは主張しない。

手動評価例は「誤解して返し方が変わる」「解釈を直接書かず台詞ににじませる」「短い橋渡しの例外省略」「POV 不明」「他者の秘密／未来の混入」「既存短文の局所増補」。実装後には、隔離した短い日本語 scene 3〜4 件を外部エージェントと実 CLI で実行し、素材から実本文へどう反映／省略したかを正確な本文範囲とともに示す。有料 API は使用せず、記録した agent 評価を人間承認や一般的な効果の実証と呼ばない。合成 JSON fixture の通過だけを実エージェントの文章品質改善と呼ばない。

## 12. 受入条件

- 設定なしで新 prepare が on、未登録の draft/check/expand/新規 approve は停止する。
- 明示 POV を共有し、他者の内心を事実化せず、未来の素材を過去の記憶へ昇格しない。
- 通常の台詞／地の文反映、両方を検討した理由付き省略、理由なし空提出の拒否を検証する。
- 別 scene、旧 generation、改変、欠損、入力変更、保存中の変更を全消費経路で拒否する。
- mandatory 制約と参照 source を落とさず 16,000 文字を守る。長すぎる場合は明示停止する。
- 旧承認の読込・export は byte-preserving。新規作成時の default-on ゲートと混同しない。
- `python -m pytest tests -q` と `python -m compileall -q scripts`。CI の Python 3.8/3.12 に合う標準ライブラリ実装とする。
- 実施していない実エージェント評価を成功と書かない。push・作品の一括書換えは範囲外。
