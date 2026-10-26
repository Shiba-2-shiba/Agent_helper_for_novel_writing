# 会話の人物別文脈

会話を語尾だけで書き分けず、返答で何をしようとするか、語彙・リズム、相手との距離から組み立てるための任意の入力。全発話に内面説明を付ける仕組みではない。本文生成・文学的な品質判定はエージェントが担う。

## 入力と選択

プロジェクト直下に `dialogue_voice.json` を置く。ひな型は [`templates/dialogue_voice.json`](../templates/dialogue_voice.json)。既存の自由記述式 `02_character_sheet.md` はそのまま使える。

```json
{
  "version": 1,
  "characters": {
    "mira": {
      "name": "ミラ",
      "response_goal": "曖昧な返事には、相手が引き受ける範囲を確かめようとする。",
      "word_choice": "身近な具体語を選び、抽象語には言い換えを求める。",
      "rhythm": "短い問いを置き、答えを待つ。",
      "relationship_stance": "レンには遠慮なく聞くが、答えを決めつけない。"
    },
    "ren": {
      "name": "レン",
      "response_goal": "即答を避け、まず条件を揃えようとする。",
      "word_choice": "条件や範囲を示す語を選ぶ。",
      "rhythm": "一度受け止めてから、短く留保を足す。",
      "relationship_stance": "ミラの問いを軽く扱わず、約束できる範囲だけ答える。"
    }
  },
  "scenes": {
    "1-2": {
      "participants": ["mira", "ren"],
      "pov_character_id": "mira"
    }
  }
}
```

- `characters` のキーは空白を含まない80文字以内の安定した人物ID。各項目は改行のない文字列で簡潔に書く。`name` と、4つの話し方項目のうち少なくとも1つの空でない値が必要。根拠のない任意項目は省略できる。
- `participants` はそのシーンの会話参加者ID、`pov_character_id` は知覚・解釈の基準となる視点人物ID。別の指定であり、参加者の先頭を自動的にPOVとはみなさない。
- 選択された参加者とPOVのカードだけを使用する。POVの指定からほかの参加者を推測しない。POVは聞き手・観察者でもよい。
- 会話参加者がいないシーンは `participants: []` と明示できる。POVを指定しなければ不明として扱い、人物の内心を勝手に割り当てない。
- `response_goal` は会話で何を確かめる・避ける・引き出す傾向があるか。物語全体の目標や予定展開を書く欄ではない。

## prepare

登録済みのシーン設定を使う場合:

```sh
python scripts/run_scene_pipeline.py prepare --project my_novel --chapter 1 --scene 1-2
python scripts/run_scene_pipeline.py keyframe-prompt --project my_novel --scene 1-2 --output keyframe_proposal.json
# 外部エージェントがproposalを完成させる（既存outputは上書きしない）
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json
python scripts/run_scene_pipeline.py prompt --project my_novel --scene 1-2
```

今回の参加者・POVを明示する場合:

```sh
python scripts/run_scene_pipeline.py prepare --project my_novel --chapter 1 --scene 1-2 --participant mira --participant ren --pov-character mira
python scripts/run_scene_pipeline.py keyframe-prompt --project my_novel --scene 1-2 --output keyframe_proposal.json
# 外部エージェントがproposalを完成させる（既存outputは上書きしない）
python scripts/run_scene_pipeline.py register-keyframes --project my_novel --scene 1-2 --input keyframe_proposal.json
python scripts/run_scene_pipeline.py prompt --project my_novel --scene 1-2
```

`--participant` は繰り返せる。明示した参加者リストがそのシーンの既定リストを置き換え、`--pov-character` はPOVの既定値だけを上書きする。両者を混同しない。直接 `build_runtime_context.py` を使う場合も同じオプションと `--mode draft` を指定し、`build_keyframe_prompt.py` → 外部proposal作成 → `register_keyframes.py` → `build_draft_prompt.py --project my_novel --scene 1-2` と進める。

対象sceneの `runtime/scenes/1-2/draft/dialogue_context_pack.md` を確認する。これは `draft_prompt.txt` の必須入力で、カード未設定の旧案件でも生成される。欠損・stale・対象不一致なら同じシーンでprepareをやり直す。

packは最大3,000文字。超過時はエラーで止まり、黙ってカードや指針を切り捨てない。選択が正しいか確認し、意味を保ってカードを短くしてから再prepareする。選択された参加者・POVと会話方針を依存追跡する。選択外人物だけの編集は既存runtimeを無効にせず、選択されたカードの変更・削除や選択変更では対象sceneを再prepareする。

設定やCLIで参加者・POVを変更した場合も、対象sceneを再prepareし、変更後の条件で本文を再check・再approveしてから採用・書き出す。以前の検査・承認をそのまま流用しない。増補用 `expand_prompt.txt` も同じpackを参照するが、心理説明を自動的に足す指示ではない。文字数不足は局所差分で扱い、既存の省略や会話の速度を保つ。

## 安全なカードと旧案件

カードは安全な話し方情報だけの入力にする。未来の経歴・結末・成長予定・未開示の秘密・他者の内心や知識を入れない。未定義フィールドはエラーになるが、JSONの形式検証だけでは許可された文字列に混入したネタバレを検出できないため、作成時に内容を確認する。人物の知識や既成事実は既存の時点別記憶の規則で扱う。

ユーザーが毎回すべて手入力する必要はない。導入を依頼されたエージェントは、承認済みの設定・本文に根拠のある話し方を短いカード案に整理し、解釈による提案は確定情報と分ける。根拠のない口調・関係・POVを作らず、不明点だけ確認する。自由記述の人物紹介を機械的に解析したり、全人物の経歴を丸ごとコピーしたりしない。

`dialogue_voice.json` は任意。存在しなくても既存の `agent/memory/global_notes.md` の「会話」を含む文体契約を保持して従来どおりprepareできる。参加者未指定や選択人物のカード欠落は、追加するID・カードを確認できるwarningとして読む。warningを隠すために人物を自動補完せず、必要なら設定を整えて再prepareする。旧案件の本文・自由記述シートを書き換える移行は不要。

manifestのない旧runtimeやkeyframing契約のないruntimeから、新規draft/check/expand/approveへ進めない。同じsceneを再prepareする。現行manifestで管理されたpackの欠損・変更もエラーになり、旧互換fallbackで隠さない。過去の承認履歴をこの新規作成ゲートで遡及無効化するものではない。

## 執筆・改稿・監査の共通ルーブリック

1. **返答の目的**: 発言は単なる情報伝達ではなく、その場で確かめたいこと・かわしたいこと・相手への働きかけに合うか。常に目的を地の文で説明する必要はない。
2. **語彙とリズム**: 語の選び方、文の長短、間や言い直しに人物らしさがあるか。決め台詞や語尾の反復だけで区別しない。
3. **関係と場面**: 同じ人物でも相手・緊張・立場で返し方は変わる。カードを固定台詞の型にせず、既存本文と場面の根拠を優先して読む。
4. **選択的な主観**: 誤解・ためらい・距離の変化など、次の返答や読者の読みを変える要所では、POVが声の調子や言葉の印象を受け取り、推測や考え直しを経て返す流れを検討する。相手の意図を全知の事実にせず、「そう聞こえた」等の不確かな解釈として扱う。選んだ素材は主に台詞／地の文へ反映し、両方が不自然・冗長・テンポを損なう場合だけ両経路の具体的理由を残して省略する。
5. **省略と余白**: 台詞だけで伝わる応酬、速度が必要な場面、読者に判断を委ねる箇所はそのまま残す。全発話への心理説明・仕草の挿入、内面描写の回数ノルマ、機械的な言い換えを要求しない。

監査では具体的な台詞・返答と読者への影響を根拠にする。カード不足や解釈の相違は、人物崩壊の断定と分ける。「内面がない」だけを欠陥にせず、有効な省略も評価する。checkのpassやwarningの解消は、このルーブリックの達成や文学的な合格を保証しない。

## 本文に結び付いた会話レビュー

新しいcheckは、均衡した最上位の `「…」` / `『…』` が4発話以上続く範囲を候補として示す。空白だけ、または引用符を含まない80非空白文字以内の短い地の文を橋渡しし、最大の連鎖を一件にする。改行折り返しは発話を分割しない。これらは抽出versionに固定した検索上の目安であり、4行ごとに心理を足す規則でも、候補数による欠陥判定でもない。引用されない発話や短い応酬も、担当者が本文を読む対象から外れない。

候補のあるsceneを新たにapproveする前に、次のJSONを出力して本文を読み、全候補へ根拠を記入する。

```sh
python scripts/review_scene_dialogue.py --project my_novel --scene 1-2 --output review-input.json
python scripts/review_scene_dialogue.py --project my_novel --scene 1-2 --input review-input.json --reviewer-type agent --reviewer-id codex
```

pipelineでは `review-dialogue` を使う。同じsceneの `--runtime_dir` も指定できる。出力しただけではレビューされず、空欄・TODOのままのひな型は提出できない。

- 各候補に `keep|revise|uncertain` を一件ずつ指定する。`evidence` は候補内の正確な非空範囲、`reason` は具体的な判断理由、`reader_effect` は読みの効果。revise/uncertainには `next_action` も必要。
- `reason` / `reader_effect` では、①定型的な情報だけの問答を間接叙述へ圧縮すべきか、②特定の問い・声・距離の受け取りが次の返答・ためらい・省略を変えるため選択的なPOVの受け止めが必要か、を分けて検討する。不該当なら本文の具体的な理由を書く。
- 軽妙な言い直し、笑いの種明かし、意図した省略を保つkeepも正当な結論。台詞間に仕草を増やして連続を切ることを改善と数えない。他者の内心は事実として補わない。
- 文字位置はデコード後のUnicode文字の0始まり・半開区間、行は1始まり。quote/quote_hash/行番号を本文と厳密照合する。抜粋の省略記号や曖昧検索は使わない。テンプレートの全候補を勝手に削って網羅したことにしない。
- 改稿したら再checkし、新しいテンプレートへ再レビューする。前回の変更範囲、revise/uncertainには保存済みbeforeと現本文のafterの正確な比較が必要。問答を圧縮して候補が0件になっても比較義務は消えない。削除は残った置換文・文脈をafterに選ぶ。無変更の再考は理由に再考と明記し、改稿済みとは呼ばない。
- 記録はscene-scopedの平坦な台帳に追記する。revise/uncertainの記録成功は承認成功ではなく、非keepが一件でもあれば新規approveを止める。`--allow-warnings` とautomationにも免除はない。

新規承認ではcheckの旧新を問わず正本から候補を再抽出する。既存v1/v2承認の読み込み・exportへ新しい作成時ゲートを遡及適用しないが、従来どおり本文・有効な依存の変更はstaleになる。新規承認は検証済みレビューと必要なbeforeの平坦なスナップショットを保持し、後のレビュー台帳の削除や同じ本文への未解決レビューだけでは、保存済み承認を取り消さない。

これは根拠・網羅・鮮度が揃ったレビューであり、本人認証、正直に読んだこと、文学的品質、全会話の意味的網羅性の機械保証ではない。引用の多い地の文や未知の発話表記には過不足がある。過去の編集が記録前なら、beforeの出典検証はできない。参考の比較を検証済み履歴として捏造しない。

## 基本有効の主観素材との接続

[選択的主観素材](narrative_keyframing.md)は会話カードとは別の創作素材で、明示POVを共有する。カードがなくても明示POVで進められるが、POVが不明なら生成を止める。選んだ要所は主に台詞／地の文へ反映し、両方が不自然・冗長・テンポを損なう場合だけ両経路の理由を残して省略する。素材を逐語転記する必要はない。

候補に関係する素材と本文のexact spanを比較し、言い直し・留保への暗示的反映も具体的な読者効果で判断する。既存のkeep/revise/uncertainとbefore/afterゲートを保つ。4発話未満や地の文も自己評価するが、候補抽出による網羅性を主張しない。省略へ変更するならproposalを更新し、再登録・prompt再生成・再checkを行う。
