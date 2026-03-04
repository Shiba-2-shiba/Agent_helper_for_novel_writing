# クレジット消費に関する調査：Codex と Google Antigravity のエージェント機能における課金・クォータ消費の比較分析

## エグゼクティブサマリー
Codex は「ChatGPT サブスクリプション内の利用枠（ローカル／クラウド）＋追加クレジット」または「APIキーでの従量課金（トークン＋ツール課金）」という二重の課金経路を持ち、コスト主要因が“メッセージ数”と“ツール（検索・実行環境）使用”に強く依存します。citeturn2view1turn11view0turn6view0turn6view3turn14search24  
一方 Google Antigravity は、公式に「“work done（仕事量）”に相関するクォータ／レート制限」という説明が中心で、消費ロジック（トークン換算や計算式）は公開情報だけでは特定困難です。citeturn7view0turn12search4turn9view0  
ただし Antigravity が利用する基盤モデル（Gemini 系）を API として使う場合は、Gemini API / Vertex AI の “トークン単価＋検索グラウンディング課金＋キャッシュ” で定量評価できます。citeturn10view1turn10view2turn19view0  
両者に共通して、最大のコストドライバは「大規模コンテキスト（長文・大規模コードベース）」「探索（Web検索／ブラウズ）」「実行（テスト実行等のコンテナ／計算資源）」「並列化・リトライ」です。citeturn2view1turn6view3turn7view0turn10view1turn10view2turn16view0  

## 比較
### 対象スコープと未指定事項
本レポートの比較対象は、Codex（entity["company","OpenAI","ai company"]が提供する代码支援／エージェント機能）と Google Antigravity（entity["company","Google","technology company"]のエージェント型開発プラットフォーム）です。citeturn14search24turn7view0turn12search4  
「Google Antigravity の課金単位（credits の数式、トークン換算、明確な“1リクエスト当たり消費”）」は、公開ソースからは未指定（特定不能）として扱います。根拠として、公式フォーラムで“正確な計算ロジックやプログラム的取得APIの有無”が質問されている状況が確認できます。citeturn9view0  

### Codex の課金モデル概要
Codex は、クラウドに“隔離サンドボックス環境”を用意してタスクを実行し、並列で複数タスクを走らせられる「ソフトウェア工学エージェント」として紹介されています（この性質が“実行”と“並列”をコストドライバにします）。citeturn14search24turn15view1  
課金（消費）の見え方は大きく二系統です。  

- **ChatGPT プラン内（利用枠＋クレジット）**：利用枠を超えると追加クレジットを購入して継続でき、消費は「ローカル作業（Local）」と「クラウド作業（Cloud）」「コードレビュー」に分かれて提示されています（平均でローカル ~5 credits/メッセージ、クラウド ~25 credits/メッセージ、コードレビュー ~25 credits/PR）。citeturn11view0turn2view1  
- **APIキーで従量課金**：追加のローカル実行は API レート（トークン単価）で課金され、加えて Web 検索、コンテナ実行（Hosted Shell / Code Interpreter）、ファイル検索などのビルトインツールに個別の課金行が存在します。citeturn2view1turn6view3turn6view0  

利用枠はプラン別に「5時間ごとの更新（ローカル＆クラウド）」と「週次更新（コードレビュー）」が明示され、同じ“1メッセージ”でもタスク規模・複雑性・推論量で消費が変動する旨が明記されています。citeturn2view1turn11view0  

### Google Antigravity の課金・クォータモデル概要
Google Antigravity は「エージェント・ファーストの開発プラットフォーム」で、エージェントが計画・実装・（必要に応じて）Webブラウズまで行える、という立て付けで説明されています。citeturn12search4turn7view0  
公開プレビューとして「個人 Gmail アカウント向けに提供され、プレミアモデルを使うための free quota が付く」と明示されています。citeturn12search4  
制限・消費の説明は「無料プランは週次ベースのレート制限」「Google AI Pro/Ultra は 5時間ごとに更新されるクォータ（優先アクセス）」が核で、さらに「使用量はエージェントの“work done”に相関し、単純タスクは消費が少なく複雑推論は消費が大きい」とされています。citeturn7view0turn2view2turn7view1  

加えて、Google AI Pro/Ultra サブスクリプションは Antigravity の“AI Agent クォータ増加”を特典として掲げ、月額（日本）として Pro 2,900円、Ultra 36,400円が提示されています。citeturn7view1turn2view2  
ただし、Antigravity 内部のクォータ残量の定量指標・計算式は公式ドキュメントの静的確認が難しく（本調査環境では docs/plans 等の本文抽出ができず）、公開情報だけでは「トークン課金（API）처럼の精密な見積り」はできません。したがって、**“Gemini API / Vertex AI の単価による換算（proxy）”**を補助的に示します。citeturn10view1turn10view2turn9view0  

## 要因分析
以下では「Codex（ChatGPT credits）」「Codex（API従量）」「Google Antigravity（内部クォータ）」「Gemini API/Vertex AI（換算）」の4つの視点で、消費要因を定量・準定量で整理します。

```mermaid
flowchart TD
  U[ユーザー要求] --> A[エージェント編成/計画]
  A --> M[モデル推論: 入力/出力(思考含む)]
  A --> T[ツール呼び出し]
  T --> WS[Web検索/ブラウズ]
  T --> EX[コード実行/テスト/コンテナ]
  T --> RET[リトリーバル/ファイル検索]
  M --> BILL1[課金: トークン単価]
  WS --> BILL2[課金: 1k calls単価 + 検索コンテンツトークン]
  EX --> BILL3[課金: コンテナ(時間/メモリ) + 追加トークン]
  RET --> BILL4[課金: ストレージ + 1k calls単価 + 追加トークン]
```

### トークン数（入力・出力・思考）
**Codex（API従量）**では、モデル別に「入力／（cached）入力／出力」の 1M tokens 単価が明示されます。例えば gpt-5.3-codex は Standard で input $1.75、cached input $0.175、output $14 / 1M tokens です。citeturn6view0  
このとき総コストは概ね  
**Cost ≈ (input_tokens×Rate_in + cached_input_tokens×Rate_cached + output_tokens×Rate_out) + ツール課金**  
で近似できます（厳密にはツールが追加で投入するトークンや、検索コンテンツ等が上乗せされます）。citeturn6view0turn6view3  

**Google 側（換算）**では、Gemini API が input $2 / 1M tokens、output（thinking含む）$12 / 1M tokens（<=200k tokens の場合）と示しています。citeturn10view1turn10view1  
また「thinking tokens が出力課金に含まれる」ことが明記されており、深い推論（長い思考）ほど出力側コストが増える設計です。citeturn10view1  

**Codex（ChatGPT credits）**はトークン単価ではなく“メッセージ単位の平均 credits”が提示されますが、同じく「タスク規模・複雑性・推論量で credits が変動する」ため、実態としては“トークン＋推論強度”に相関する設計と解釈するのが妥当です。citeturn11view0turn2view1  

**Google Antigravity（内部クォータ）**は「work done ベース」「単純タスクは小、複雑推論は大」と説明されますが、トークン換算係数は未指定です。citeturn7view0turn9view0  

### モデル種類（大モデル／軽量モデル、長文対応）
Codex では gpt-5.3-codex（高性能）と gpt-5.1-codex-mini（軽量）で、credits と API単価の両方が大きく異なります。ChatGPT Rate Card ではローカル作業が平均 ~5 credits/メッセージに対し mini は ~1 credits/メッセージで、単純比較で約80%削減が見込めます。citeturn11view0  
API 単価も、gpt-5.3-codex（input $1.75 / output $14）に対し gpt-5.1-codex-mini（input $0.25 / output $2）で約7倍の差があります（同トークン量なら約85%削減に相当）。citeturn6view0  

Google 側（換算）でも Pro と Flash の単価差が大きく、Gemini 3 Flash は input $0.5 / output $3、Gemini 3 Pro は input $2 / output $12 と提示されています。citeturn10view1turn10view2  

長文（ロングコンテキスト）の扱いも重要です。Gemini API は prompts >200k tokens で input $4、output $18 に上がると明示されており、長文に踏み込むだけで“同量トークンでも単価が2倍”になります。citeturn10view1turn10view2  

### API呼び出し回数・メッセージ回数
Codex（ChatGPT credits）は「1メッセージ＝1プロンプト＋1レスポンス」を単位として credits が計上されます。citeturn11view0turn2view1  
したがって、同じ仕事でも **“往復回数（プロンプトの細切れ、確認ターンの多さ）”**が増えるほど credits が増えます。加えて Codex はクラウドタスク（Cloud Tasks）だと平均 ~25 credits/メッセージと重く、クラウドに投げる回数が増えるだけでコスト構造が変わります。citeturn11view0turn2view1  

Codex（API従量）も同様に、呼び出し回数が増えればトークン（特に“毎回同じコンテキストを再送する入力トークン”）が積み上がります。これを抑える方法が “cached input / prompt caching” です（後述）。citeturn6view0turn17view0  

Google Antigravity（内部クォータ）は回数ではなく “work done” 強調ですが、実務的には「やり直し／往復／冗長な計画」は work done を増やしやすいので、結果としてクォータ消費を押し上げるリスクが高いです。citeturn7view0  

### 外部ツール呼び出し（検索、ブラウザ、コード実行、リトリーバル）
**OpenAI API**はツール課金が明確で、典型例は以下です。  
- **Web search**：$10 / 1k calls ＋「検索コンテンツトークン」をモデル入力単価で課金（※モデル種別により例外あり）citeturn6view3  
- **Container usage（Hosted Shell / Code Interpreter）**：現在は 1GB $0.03 / container、しかし **2026-03-31 以降は 1GB $0.03 / 20分 / container** のように“時間課金”へ移行（メモリ tier 別も明示）citeturn6view0turn6view3  
- **File search**：ストレージ $0.10 / GB-day（1GB free）＋ tool call $2.50 / 1k calls（Responses API only）citeturn6view3  

Codex の CLI では Web search を「既定は cached」「`--search` で live web search」に切り替え可能で、live を使うと外部情報取得が増えやすく（かつツール課金や入力トークンが増えやすい）設計です。citeturn15view0  

Codex（ChatGPT credits）側はツール課金の“個別単価”は出ませんが、ローカル／クラウド実行や MCP など“ツールが増えるほどコンテキストが増え利用枠を消費する”旨が明記されています（たとえば MCP サーバ追加が limit 消費を増やす）。citeturn2view1turn3view4  

**Google 側（換算）**では、Gemini API の “Grounding with Google Search” が $14 / 1,000 search queries と明示され、検索連動タスクではトークン課金とは別のメータが立つことになります。citeturn10view1  
一方 Antigravity 自体は「ブラウザ統合」等を含むとされるものの、Antigravity 内での検索・ブラウズが “いくら相当のクォータ消費か” は未指定です。citeturn7view0turn9view0  

### コンテキスト長（リポジトリ規模、長文入力、ルール、AGENTS.md、MCP）
Codex は `AGENTS.md` をプロジェクト文脈として読み込み、既定で合計 32KiB まで（`project_doc_max_bytes`）読み込むなど、恒常的に“指示文脈が入力に乗る”設計です。citeturn4view2  
また設定面でも `model_auto_compact_token_limit` のような“コンテキスト圧縮（compaction）トリガ”が存在し、長期セッションでは“コンテキスト管理”が消費に直結します。citeturn16view0  

Google 側（換算）では、200k tokens を境に単価が上がるため、コンテキストを 200k 未満に保つだけで“単価2倍化”を防げます。citeturn10view1turn10view2  

### 並列実行（マルチエージェント・多スレッド）
Codex は「並列タスク」前提のクラウドエージェントとして説明され、設定にも `agents.max_threads`（同時オープンスレッド数制限）が存在します。citeturn14search24turn16view0  
一般に並列度を上げると「各スレッドが独自にコンテキストを保持し、重複トークンやツール呼び出しが増える」ため、**“速度とコストの交換”**になります（特にクラウドタスクは credits が重い）。citeturn11view0turn16view0turn2view1  

Antigravity も “agentic development platform” として複数エージェント的な運用が想定されますが、クォータ計算式が未指定のため「並列が何倍で効くか」は定量化できません。citeturn7view0turn12search4turn9view0  

### リトライ・失敗応答・エラーハンドリング
従量課金（API）の場合、単純には“成功したリクエスト・ツール呼び出しが増えるほど課金が増える”ため、リトライはコストを押し上げます。OpenAI API はトークンとツール課金が明確に分離されているため、同じ処理を繰り返せばその分のトークン＋ツール課金が再発生します。citeturn6view0turn6view3  
Google Vertex AI は「200応答のみ課金（4xx/5xxは input/output を課金しない）」と明記しており、失敗の種類によって“課金されない失敗”があり得ます（ただし成功するまでの累積コストは別問題）。citeturn10view2  

Antigravity はクォータ更新に関するユーザー報告がフォーラムに見られるものの、これは運用上の不確実性として扱い、課金ロジックの決定打とはしません（後述の限界）。citeturn9view2turn9view1  

### ログ保存・デバッグモード
Codex 側には `history.persistence`（session transcript の保存制御）、`log_dir`、`hide_agent_reasoning` など“ログ／表示”に関わる設定が存在します。citeturn16view0  
これら自体が直接課金単位になるとは明記されていませんが、実務上は「デバッグ用に出力を冗長化する」「詳細なトレースをモデルに説明させる」などで **出力トークンが増えれば課金が増えます**（OpenAI はモデル出力トークン単価を明示）。citeturn6view0  
Google 側でも出力課金に thinking tokens が含まれるため、デバッグ目的で推論を長くさせるほど換算コストは増えます。citeturn10view1  

## ユースケース別見積り
### 前提（見積りの置き方）
以下は「典型的なトークン量／ツール回数」を仮定し、(A) Codex の ChatGPT credits、(B) OpenAI API（gpt-5.3-codex Standard 単価）、(C) Antigravity の内部クォータ（未指定なので定性）、(D) Gemini API（Gemini 3 Pro Standard 単価）でレンジを示します。単価は公式価格表に基づきます。citeturn11view0turn6view0turn10view1turn10view2  
なお Codex credits は「平均」であり、同じ“1メッセージ”でもタスク規模・複雑性・推論量でブレることが明記されています。citeturn11view0turn2view1  

| ユースケース | 典型操作の仮定（例） | Codex（ChatGPT credits）推定レンジ | OpenAI API（USD）推定レンジ | Google Antigravity（内部クォータ） | Gemini API（USD）換算レンジ |
|---|---|---:|---:|---|---:|
| チャット型エージェント（軽いQA/設計相談） | ローカル 1〜3メッセージ、入力 合計 6k tokens / 出力 合計 1.5k tokens | 5〜20 credits（主にローカル） | 約 $0.01〜$0.10 | 低（単純タスク想定） | 約 $0.01〜$0.12 |
| コード生成・小規模修正（単一ファイル中心） | ローカル 2〜6メッセージ、入力 20k〜80k / 出力 2k〜8k | 10〜40 credits | 約 $0.06〜$0.30 | 低〜中 | 約 $0.06〜$0.35 |
| コード修正＋テスト（複数ファイル・実行あり） | クラウド 1〜4メッセージ、入力 60k〜200k / 出力 10k〜40k ＋コンテナ実行 20〜60分 ＋Web検索 0〜3回 | 25〜150 credits（クラウド比重） | 約 $0.25〜$1.50（ツール次第） | 中〜高（“work done”増） | 約 $0.25〜$1.80（検索課金含む） |
| 長文要約（仕様書/議事録/設計docs） | ローカル 1〜2メッセージ、入力 100k〜200k / 出力 5k〜15k | 5〜40 credits（長文・推論で増え得る） | 約 $0.25〜$0.70 | 中（長文＝仕事量増） | 約 $0.25〜$0.80 |
| Web検索を伴う調査タスク（実装方針＋根拠集め） | ローカル 2〜6メッセージ＋Web検索 2〜8回（検索コンテンツが入力に追加） | 10〜60 credits | 約 $0.15〜$2.00（検索回数と取得トークンで変動） | 中〜高（検索・推論で増） | 約 $0.10〜$2.50（$14/1k queries＋トークン） |
| 自動化ワークフロー（大量の定型修正、夜間バッチ等） | ローカル 20〜200メッセージ（スケール）／場合によりクラウド併用 | 100〜数千 credits（要設計） | 数ドル〜数十ドル（Batch/キャッシュ有無で大差） | 未指定（週次上限がボトルネックになり得る） | 数ドル〜数十ドル（Batch/キャッシュ有無で大差） |

上表の OpenAI API 見積りでは、Codex 系モデル単価と、Web search / container / file search 等のツール課金が別立てで発生する点がボトルネックになります。citeturn6view0turn6view3  
Google 側の換算でも、トークン単価に加えて Google Search グラウンディングが $14/1,000 queries と別課金になるため、検索多用タスクは費用が跳ねます。citeturn10view1  
Antigravity 内部クォータは「仕事量相関・5時間更新（Pro/Ultra）・週次（Free）」という高レベル情報はある一方、1タスク当たりの消費量は未指定であり、公開情報だけでは “credits 的な精密レンジ” を置けません。citeturn7view0turn2view2turn9view0  

## 節約手法
以下は「どの要因を削るか」を中心に、期待削減率の目安と注意点をまとめます。削減率は、公式に提示された単価差・割引（Batch/キャッシュ）を基準にしています。citeturn6view0turn6view3turn11view0turn10view1turn19view0turn10view2  

| 手法 | 主要効果（期待削減率の目安） | 適用先 | 実装上の注意点 |
|---|---|---|---|
| 軽量モデルへ切替（例：Codex mini / Gemini Flash） | 同一トークンなら **約80〜85%削減**（Codex credits: ~5→~1、API: 単価7倍差） | Codex（credits/API）、Gemini（換算） | 品質低下の可能性。まず“編集・リネーム・局所修正”を軽量に寄せ、設計・難所だけ上位モデルに戻す。citeturn11view0turn6view0turn10view1 |
| Prompt/Context caching（OpenAI: cached input、Gemini: implicit/explicit cache） | **入力側を最大~90%削減**（cached input 単価が 1/10 など） | Codex（API）、Gemini API/Vertex | キャッシュヒットには“共通プレフィックス”設計が重要。Gemini は implicit caching が既定有効で、usage_metadata に cache hit が出る。citeturn6view0turn19view0 |
| Batch 処理（夜間バッチ、非同期でまとめる） | 多くのモデルで **約50%割引**（Standard→Batch 単価差） | OpenAI API、Gemini API/Vertex（換算） | レイテンシ要件がある処理には不向き。24h window 等の制約があるため“非即時”タスクに限定する。citeturn6view0turn10view1 |
| コンテキストの圧縮（要約・差分・必要箇所のみ） | 入力 tokens を直接圧縮（ケースにより **30〜80%削減**） | 全般 | Codex は AGENTS.md 等の常駐コンテキストがあるので、巨大な恒常指示を避け、階層化・分割を検討。自動 compaction の閾値設定も有効。citeturn4view2turn16view0 |
| ツール呼び出しの抑制（検索・ブラウザ・retrieval） | “呼び出し回数×単価”を直撃で削減（検索は $/1k calls が別途） | OpenAI API / Gemini API、Antigravity（クォータ） | OpenAI web search は「calls + 検索コンテンツtokens」の二重課金。Gemini も Search grounding が $14/1k queries。先にローカル情報（リポジトリ・docs）で解けるか判定する。citeturn6view3turn10view1 |
| 実行環境（コンテナ）時間・メモリの最適化 | 実行時間が長いほど効く。**2026-03-31 以降は20分課金**で“放置コスト”が顕在化 | OpenAI API（Hosted Shell/Code Interpreter 相当） | 20分課金に備えて「テストをまとめて実行」「不要なリトライを減らす」「必要最小メモリ tier」を徹底。citeturn6view0turn6view3 |
| 並列度を制御（必要時のみマルチエージェント） | 仕事量が線形増になりがち（**無制限並列はコスト爆発**） | Codex / Antigravity | Codex は `agents.max_threads` 等で上限管理できる。並列は“探索”だけに限定し、最終統合は単一スレッドに戻す。citeturn16view0turn14search24 |
| 事前にトークン見積り→ルーティング（小なら安いモデルへ） | ルーティング最適化（**20〜60%削減**の余地） | OpenAI API | OpenAI は input token count API で、ツール・ファイル込みの正確な input tokens を事前算出できる。citeturn17view0 |

Antigravity については「単純タスクほど消費が少ない」という公式説明があるため、プロンプト設計は“複雑推論を不要にしない（＝タスクを分割し、成功条件を明確化し、探索を限定する）”方向が費用対効果に直結します。citeturn7view0  

## 設定・運用上のベストプラクティス
### 課金モニタリングと可視化
Codex は「使用状況ダッシュボード」および CLI セッション中の `/status` で残量確認できると説明されています。citeturn14search2turn2view1  
加えて、利用枠はプラン別に 5時間・週次で更新されるため、チーム運用では「5時間のウィンドウをスプリント枠」「週次を安全弁」として運用設計するのが合理的です。citeturn2view1turn11view0  

Google Antigravity は “work done ベースのクォータ” という説明はあるものの、クォータ計算式・メトリクスのプログラム的取得は公開情報では未指定です（公式フォーラムに問い合わせが存在）。citeturn7view0turn9view0  
従って、コスト管理を厳密にしたい場合は、(a) Antigravity のクォータ枠を“人間の運用ルール”で管理するか、(b) 可能なら Gemini API / Vertex AI 側の課金メトリクス（トークン・検索クエリ）で観測可能な形に寄せる、のどちらかになります。citeturn10view1turn10view2turn12search4  

### アラート設定（上限・通知・自動制御）
Google Cloud 側（Gemini API / Vertex AI を使う場合）は、Cloud Billing budgets により「予算に対する実績・予測」「しきい値でのメール通知」「Pub/Sub 通知による自動制御」が公式に提供されています。citeturn19view1  
ただし budgets は“ハードキャップではない”ことが明記されているため、厳密な上限が必要なら「API利用量の上限（cap）」「予算通知での課金停止自動化」など別制御が必要です。citeturn19view1  

OpenAI 側も（少なくとも Business/Enterprise/Edu 向けの柔軟課金文脈では）“どの機能が何 credits か”のレートカードが示され、計測基盤（分析ダッシュボード）に反映される前提で運用できます。citeturn11view0turn2view1  
API 利用では、ツール課金（検索 calls/コンテナ/ストレージ）が別行になるため、請求明細上も「どの機能が燃えたか」を切り分けやすい構造です。citeturn6view3turn6view0  

### コスト試算の自動化（事前見積り・ルーティング）
OpenAI は token counting API により「送信前に正確な input tokens を算出し、コスト見積りやサイズ別ルーティングに使える」と明記しています（ツールやファイル等も含めて計測できる点が重要）。citeturn17view0  
Gemini API は caching に関して usage_metadata に cache hit tokens を表示できるとしており、キャッシュ戦略の費用対効果を計測しやすい構造です。citeturn19view0  

### A/B テストでの比較方法（品質×コスト）
エージェントの A/B は「品質指標（例：テスト合格率、PR レビュー指摘数、バグ再発率）」「速度（リードタイム）」「コスト（credits / $ / ツールcalls）」を同じ入力分布で比較するのが基本です。Codex はローカル／クラウドで消費が大きく変わるため、“同一タスクを Local と Cloud で比較”するだけでも費用対効果が変わります。citeturn11view0turn2view1turn14search24  
Google 側は Antigravity の内部式が未指定なので、A/B のコスト面は「Gemini API/Vertex AI を使った場合のトークン・検索課金」または「クォータ枠の消費割合（UIで見える範囲）」で近似するのが現実的です。citeturn10view1turn10view2turn7view0  

## 不確実性と調査限界
Antigravity の課金・クォータの“正確な計算式（トークン換算、モデル別係数、ツール別係数）”は、公開情報では未指定です。公式フォーラムに「credits 計算ロジックや programmatic API を求める」質問がある点からも、少なくとも公開ドキュメントとして確立していない可能性が高いと推定されます。citeturn9view0turn7view0  
Codex の ChatGPT credits についても「credits の $ 換算（1 credit の価格）」はレートカード上では提示されず、“何 credits/メッセージか”が中心です（従って、金額換算はアカウント内情報に依存し得ます）。citeturn11view0turn2view1  
OpenAI API のツール課金は明確ですが、特に **2026-03-31 にコンテナ課金が“20分単位”へ変更**されるなど、時点依存の変更が存在します（本レポート日付：2026-03-02）。運用設計はこの変更を織り込む必要があります。citeturn6view0turn6view3  
料金・制限は両社とも更新頻度が高く、特に「無料枠」「プレビュー」「レート制限」は変動しやすい領域です。従って、最終判断にあたっては最新の公式料金ページ・ヘルプ・API仕様を都度確認することが不可欠です。citeturn2view1turn6view0turn10view1turn7view1  

## 結論
最も実務的な結論は、Codex は「credits（メッセージ単位）」と「API従量（トークン＋ツール）」の両方で定量管理でき、特に検索・実行環境（コンテナ）・大規模コンテキストが費用を決めるため、**モデル選択（mini化）＋キャッシュ＋ツール抑制＋並列制御**が最優先レバーになります。citeturn11view0turn6view0turn6view3turn16view0turn17view0  
Google Antigravity は「仕事量相関のクォータ」という設計思想が明確で、単純タスクに寄せればクォータ効率は上がる一方、現時点の公開情報では“1タスクの消費レンジを厳密に数値化”できません。そのため、コスト厳密性が必要なら **Gemini API / Vertex AI のトークン課金（＋検索課金）で観測できる経路に寄せる**か、Cloud Billing budgets 等の既存 FinOps 機構で統制するのが現実解です。citeturn7view0turn10view1turn10view2turn19view1turn12search4  
両者を比較した“費用予見性”は、現状では Codex（API）が最も高く、Antigravity はクォータ計算式が未指定であるぶん運用設計（ワーク分割・探索制限・再実行抑制）がより重要になります。citeturn6view3turn7view0turn9view0  

参考URL（公式・主要資料）
```text
OpenAI Codex pricing: https://developers.openai.com/codex/pricing/
ChatGPT Rate Card (Business, Enterprise/Edu): https://help.openai.com/en/articles/11481834-chatgpt-rate-card-business-enterpriseedu
Using Codex with your ChatGPT plan: https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
Introducing Codex: https://openai.com/index/introducing-codex/
OpenAI API Pricing (docs): https://developers.openai.com/api/docs/pricing
OpenAI token counting: https://developers.openai.com/api/docs/guides/token-counting
Codex config reference: https://developers.openai.com/codex/config-reference
Codex CLI command line options: https://developers.openai.com/codex/cli/reference/

Google Keyword (Antigravity rate limits update): https://blog.google/feed/new-antigravity-rate-limits-pro-ultra-subsribers/
Getting Started with Google Antigravity (codelab): https://codelabs.developers.google.com/getting-started-google-antigravity
Google One / AI plans benefits: https://support.google.com/googleone/answer/16572372?hl=en
Gemini subscriptions (Japan): https://gemini.google/subscriptions/
Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
Gemini API context caching: https://ai.google.dev/gemini-api/docs/caching
Vertex AI Generative AI pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing
Cloud Billing budgets & alerts: https://docs.cloud.google.com/billing/docs/how-to/budgets
Google Cloud quotas (view/manage): https://docs.cloud.google.com/docs/quotas/view-manage

(参考: 公式フォーラムでの「Antigravity credits 計算ロジック」質問)
https://discuss.ai.google.dev/t/calculating-credits-in-antigravity/122965
```