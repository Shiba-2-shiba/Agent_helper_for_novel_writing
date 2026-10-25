# 20万字の日本語小説: 共通運用手順

## 役割

Codex等の外部エージェントが設定・本文・意味要約を作成し、Pythonが対象識別、保存、文字数、依存、採用記録を検証する。機械検査は文学的な完成度や意味的な矛盾を保証しない。実エージェントによる長編執筆試験が未実施なら、そのまま未実施と記録する。

## 新規作品

リポジトリルートから実行する。`my_novel` は新規保存先の例。

```sh
python scripts/init_project.py my_novel --target-total-chars 200000 --chapter-count 20
```

目標は30,000/50,000/100,000/200,000字。20万字の計画ゲートは最小字数の計画合計160,000字。20章を強制せず、`--chapter-count` 未指定は既存の5章構成を維持する。章数を増やしても本文は生成されない。各Chapter Card/Scene Ledgerを作品に合わせて記入し、計画ゲートを満たす。1シーンのLength Bandは全体の長さに比例して引き延ばさない。

- bridge: 1200 / 1500 / 1800字
- standard: 1600 / 2000 / 2400字
- anchor: 2200 / 2700 / 3200字
- climax: 2600 / 3200 / 3800字

この値は既定。各シーンに明示された契約を優先する。20章×5シーン×平均2,000字は計算例であり、作品の必須構造ではない。

## 1シーンの執筆

```sh
python scripts/build_runtime_context.py --project my_novel --chapter 2 --scene 2-3 --mode draft --pov-character protagonist --entity protagonist --thread promise_01
python scripts/build_draft_prompt.py --project my_novel --scene 2-3
```

生成された対象sceneの `runtime/scenes/2-3/draft/draft_prompt.txt` を読む。planningがblocked、runtimeがstale・別対象なら先に修復する。初稿の本文はエージェントが書き、指定されたシーンtxtへ保存する。続くコマンドの本文パスは実際の保存先へ置き換える。

```sh
python scripts/check_scene_output.py --project my_novel --text chapter_2_scene_3.txt
```

check_reportのstatusと根拠を読む。コマンドが正常終了しただけで本文がpassとは限らない。文字数不足だけであれば、既存の局所差分フローを使える。

```sh
python scripts/build_expand_prompt.py --project my_novel --draft_text chapter_2_scene_3.txt
python scripts/apply_expand_edits.py --project my_novel --text chapter_2_scene_3.txt --edits expand_response.txt
python scripts/check_scene_output.py --project my_novel --text chapter_2_scene_3.txt
```

`expand_response.txt` はエージェントがプロンプトに従って作成する差分。見出し混入や上限超過等を無理に増補しない。修復予算の超過を自動で `--force` により回避しない。

checkの `dialogue_review_contract.review_required` がtrueなら、`docs/dialogue_context.md` の本文に結び付いた会話レビューを先に行う。候補数は欠陥数ではない。情報だけの問答を圧縮する判断と、相手の印象が返し方を変える選択的な受け止めを分け、keepの理由も具体的に記録する。

```sh
python scripts/review_scene_dialogue.py --project my_novel --scene 2-3 --output review-input.json
python scripts/review_scene_dialogue.py --project my_novel --scene 2-3 --input review-input.json --reviewer-type agent --reviewer-id codex
```

ひな型の空欄は本文を確認して埋める。revise/uncertainは承認を止め、改稿後は再checkと正確なbefore/after比較を行う。候補を0件にしても未解決の比較は消えない。`--allow-warnings` はこのレビューを免除しない。旧承認の歴史的な有効性には遡及適用せず、新規approveは旧checkでも正本から再抽出する。

内容をレビューし、明示的に承認する場合だけ次を実行する。

```sh
python scripts/approve_scene.py --project my_novel --scene 2-3 --reviewer-type agent --reviewer-id codex
```

`--reviewer-type` と `--reviewer-id` は必須。種別は `human`（人間）、`agent`（AIエージェント）、`automation`（合成fixture等の自動評価）。IDは実際の確認者を識別する値に置き換える。人間が本文を確認していない場合は `human` やユーザー本人のIDを指定しない。これらは申告された主体の記録であり、本人認証や文学的品質の証明ではない。`--revoke` は確認者の再指定を必要とせず、元の承認者情報を保持する。

承認台帳には `reviewer_type` / `reviewer_id` と互換用の `approved_by`（明示IDと同じ値）を保存する。旧記録の `approved_by: user` 等から確認者を推定しない。読み込み時は `unknown` とし、元の値を `legacy_approved_by` に保持するが、読み込みだけではファイルを書き換えない。既存の本文hash・検査条件に基づく承認の有効性は別途検証する。旧Python APIで種別/IDを省略した場合も `unknown` となる。明示済みの種別/IDが欠損・不正・矛盾した台帳は破損として停止する。

warningの採用は根拠を確認し `--allow-warnings` を明示する。本文または有効な検査条件が変われば、新形式の承認はstaleとなる。承認済みの古い本文へhashだけを付け替えて再利用しない。

## 次のシーンへ残す記憶

承認済み本文から `docs/story_memory_format.md` に沿って、起きた事実・人物の知識・伏線の状態・シーン結果を提案する。検証成功だけでは採用されない。

```sh
python scripts/import_story_memory.py --project my_novel --input memory_proposal.json --validate-only
python scripts/import_story_memory.py --project my_novel --input memory_proposal.json
python scripts/review_story_memory.py --project my_novel --batch batch_001
python scripts/review_story_memory.py --project my_novel --batch batch_001 --accept --expected-revision 0
```

`batch_001` とrevisionは実際の提案・レビュー結果へ置き換える。revisionが変わったら再レビューし、最新値を機械的に埋めて競合を回避しない。章末にはchapter_summary、部末にはpart_summaryを提案する。未記入・未採用の記憶を完成済みと扱わない。

## 再開と改稿

```sh
python scripts/build_runtime_context.py --project my_novel --chapter 2 --scene 2-3 --mode resume
python scripts/sync_project_health.py --project my_novel --json
```

再開資料と現物を照合する。written、checked、completed（現在の本文がpass）、approvedを区別する。本文の過去章を直したら再check・再approveし、関連する記憶と要約を再提案する。意味の変化を検討せずsource hashだけを更新してはならない。

対象より未来の本文・記憶は通常draftの過去事実に使わない。人物Aの秘密を人物Bの知識として扱わない。作者の視点・人物の知識・今後の計画は別のラベルで読む。これらは入力の構造的制約であり、モデルが実際に守ったかは出力を評価する。

## 文脈予算

最終promptの既定上限16,000文字、記憶枠6,000文字、直前本文枠4,000文字。日本語の文字数と実トークン数は同じではなく、表示された推定トークンは概算。省略された記録とpointerはcontext_selectionに残る。必須情報だけで上限を超えたら、黙って重要項目を落とさず計画・文脈を整理する。

## 書き出しと復旧

```sh
python scripts/export_manuscript.py --project my_novel --require-complete
```

完成原稿の書き出しは `--require-complete` で予定された全sceneを要求する。省略すると従来互換の部分exportであり、omitted_scenesと理由を確認し、完成とは扱わない。対象は承認済み本文。warningを採用した本文の書き出しは `--include-warnings` を明示する。stale承認は先に解決する。未承認のシーンを黙って完成原稿として数えない。

壊れた台帳は空の記録として再生成しない。バックアップ・JSONの内容・エラーに示されたパスを確認する。ロック残存時は他の処理が実行中でないことを確認し、人間が復旧方針を判断する。healthの派生物再生成と、採用済み記憶の書換えは別操作である。

healthがfailならJSON報告を保存したうえで非0終了する。pipelineも先へ進まない。続き物の仮フックや部分exportの扱いは `docs/trial_cli_diagnostics.md` を参照する。
