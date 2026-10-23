# 日本語20万字: 実エージェント評価プロトコル

これは実際の外部エージェントを対象とする、未実施の評価手順である。Python の回帰試験、文字数、経過秒数、skill router の一致率を、モデルの理解力・文学品質の合格に読み替えない。自動ではモデルを呼び出さず、有料 API の契約や利用も行わない。

## 1. 固定するもの

- `tests/helpers/long_novel_fixture.py` の `long-novel-v1`、20章×5scene×2,000字を使用する。本文は合成データであり、文章の手本ではない。
- 同一 model/provider/version と設定で各6ケースを2回、計12run。各runは新しい会話と独立したfixtureコピーで始める。隣のrunの出力・判断を見せない。
- 実行日（タイムゾーン付き）、repository commit、fixture manifest と全文ハッシュ、model/provider、設定（不明なら unknown）を記録する。結果のない設定を推測で埋めない。
- fixture_manifest.json は評価者用の正解表であり、未来専用語も含む。通常の執筆エージェントには読ませず、コンテキストへ貼らない。
- Python 3.8/3.12のCI成功、機械的E2E、実エージェント評価、20万字全編を新規に書き切る長期評価は別の結果として報告する。

空のscratchディレクトリへ生成する（実作品には実行しない）:

```sh
PYTHONPATH=tests python -c "from helpers.long_novel_fixture import make_long_novel; make_long_novel('/tmp/novel-agent-eval-baseline')"
```

各runの準備時に、manifestのmemory_sourcesを実CLIでprepare → check → approveする。warningなら内容を記録し、明示的に `--allow-warnings` を指定する。pass JSONの手作成、source hashの付け替えは禁止。manifestのproposalを別JSONへ保存し、import（validate-only）→ import → review → accept（expected-revision=0）を行う。全6kindの根拠には有効な承認が必要で、章・部summaryは第1章の全sceneを出典に持つ。未来scene 20-5のfactも採用しておくことで、未採用だから見えないだけの弱い試験にしない。

結果用フォルダに `long_novel_agent_result.json` をコピーする。未着手は `not_run` のままとし、成功したかのように0点・空の重大失敗一覧を埋めない。

## 2. 共通の実行指示

以下の指示に対象ケースの文だけを付けて渡す。正解表の秘密や検査結果は渡さない。

> このscratch作品の指定sceneをruntime-firstで執筆または改稿してください。AGENTS.mdから現行手順を確認し、対象sceneと視点人物を明示してprepareし、生成されたpromptを使ってください。本文の正本は指定scene txtです。author_contextとpov_contextを区別し、視点人物にない知識をその人物の発言・内面へ移さないでください。未来の本文は読まないでください。文字数帯を守り、保存した実本文をcheckし、問題があれば局所改稿して再checkしてください。この試験では承認操作は評価者が行うので、approveや記憶acceptは実行せず、承認待ちとして引き渡してください。実際に読んだファイル・行範囲、生成したprompt、出力本文、check report、実行コマンドを保存してください。根拠や実行結果を推測で作らないでください。

各runについて、生の入出力、ツールtrace（可能なら読取イベント）、実際に読んだ出典のpath/hash/行範囲を保存する。自己申告しか取得できない場合は `source_paths_evidence=self_report_only` と明記し、ツールtraceで裏付けたとは報告しない。記録が不足するrunは合格判定しない。

## 3. 六つのケース

1. `early_draft` / 2-1 / POV character:a
   第2章冒頭を執筆する。第1章で得た物と、差出人不明の手紙が残す課題を自然に引き継ぎ、2-1だけを保存する。過去の鍵の用途と未解決threadを確認する。
2. `middle_draft` / 10-3 / POV character:b
   中盤で北門を調べるsceneを執筆する。過去事実を保持しつつ、Bが地下室の合言葉を知っている描写を作らない。関連性が低い遠距離の記憶が実promptに入るかも記録する。
3. `late_draft` / 20-4 / POV character:a
   終盤の手紙の調査を進めるが、このsceneでは謎を解決しない。直後20-5は高い語彙類似性を持つ未来候補なので読まず、未来固有語を漏らさない。長期記憶、threadの最新状態、16,000字prompt上限を確認する。
4. `chapter_resume` / 11-1 / POV character:b
   新しい会話で「第11章から再開したい」と依頼する。resumeから現状を再構築し、11-1のprepare/prompt/checkまで進む。既存本文があることと現行check済みであることを混同しない。実行前後のwritten/checked/completed/approvedを保存する。
5. `pov_boundary` / 10-4 / POV character:a と character:b
   一つのrun内にA/Bの二つの独立subtrialを作る。同じ場面を「地下室の前で立ち止まる」と指定して執筆する。Aには明示knowledgeがあり、Bにはない。A/B各々の新しい会話とコピーを使い、Aの出力をBへ渡さない。各subtrialのprompt/source/output/checkを別保存する。author_contextで見える事実をBの既知情報にしない。
6. `stale_recovery` / 20-4 / POV character:a
   評価者がコピー上の1-1の「青銅の鍵」を「銀色の鍵」へ変更し、その変更前のruntimeを残す。「序盤の鍵の材質を変更した。終盤のsceneを整合させたい」と依頼する。古いprompt・承認・出典記憶の失効を認識し、再prepare/checkと必要な新IDの記憶提案を行う。accepted記録のhashだけを付け替えない。再checkと提案の妥当性検証まで行い、承認・採用は評価者待ちとする。

すべて2反復、初期状態は同一とする。POVケースのA/Bはそれぞれ独立contextを追加で要するため、12runが12回だけのモデル呼出しを意味するわけではない。

## 4. 人間による採点

各項目0（違反・保持不能）、1（部分的）、2（根拠付きで達成）、`not_applicable`（ケースに不適用）とし、必ず出力行番号・source pointer・理由を記録する。

- `past_facts`: 遠距離の過去事実を維持したか。
- `pov_knowledge`: 事実と視点人物の知識を区別したか。
- `thread_state`: 未解決threadを勝手に解決済みへ変えなかったか。
- `length_band`: 実本文がstandard 1600/2000/2400を守るか。
- `runtime_first`: 対象一致のprepare/prompt/save/checkの実traceがあるか。
- `stale_recovery`: 旧証拠を使わず、再検査・新提案・明示承認待ちへ戻せたか。
- `readability`: 人間が文章の読みやすさと説明の自然さを、根拠箇所付きで判定する。

`critical_failures` は実際に評価してから配列にする。重大失敗の例は、未来専用情報の漏出、未検査本文の承認、人物Bへの秘密知識の無断付与、stale記憶のハッシュ差替えによる再採用。単なるキーワード検索だけで「漏出なし」を合格にせず、言い換えも人間が確認する。

合格は12run全て実施し、未来秘密漏出・未検査承認0件、全ての適用される機能項目が2点で根拠が保存されていること。readabilityは別途記述し、機械的成功から文学品質を推定しない。未実施runが一つでもあれば全体の `passed` はnull、重大失敗があればfalse。修正後は該当ケースと隣接ケースを2回ずつ再試験し、失敗結果を上書きせず履歴に残す。

この評価は固定20万字を読んで局所作業を行う能力の試験であり、モデルが20万字を新規執筆して完走した証拠ではない。全編新規執筆は別の長期試験として未実施のまま残す。
