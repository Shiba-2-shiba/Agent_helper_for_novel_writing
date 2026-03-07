# 実装仕様書: 長編生成安定化（10万字到達・文体維持・複数話劣化防止）

## 1. 目的
本仕様は、`小説作成` と `Agenthelper` の連携運用において発生している以下3課題を解消するための実装要件を定義する。

1. 全体想定10万字に対し、実績が2万〜3万字規模で止まりやすい
2. Agent再起動後に口調・文体がずれる
3. 1回のプランで複数話を作ると、後半話ほど文字数が減る

本仕様は「実装に必要な要件・設計・検証基準」を定義する。実装コードは本仕様の対象外。

## 2. スコープ
### 2.1 対象（実装する）
1. `小説作成/scripts/build_llm_prompt.py` の出力設計強化
2. `小説作成/agent/*` の運用仕様強化（長編用）
3. `Agenthelper/agent_templates_catalog/novel/*` のテンプレート強化
4. `Agenthelper/agent_templates_common/*` の共通テンプレート強化
5. 文字数・文体・連続生成品質を担保するテスト追加

### 2.2 非対象（今回やらない）
1. 物語内容そのものの自動改善ロジック（プロット自動生成AIの高度化）
2. 外部API依存の追加
3. 既存作品本文の自動リライト

## 3. 現状課題の原因整理（実装前提）
### 3.1 スクリプト側
1. プロンプト最終指示が「次のシーン（約2000〜3000文字）」固定で、累積10万字の予算管理がない
2. 「本文提案」か「アイデア出し」かを同一指示に含み、本文以外の短い出力に流れやすい
3. `previous_text` が任意で、連続話生成時の文体引継ぎが弱い
4. 章目標や全体目標との差分（残文字数）を出力指示に反映していない

### 3.2 Agent機能側
1. `global_notes.md` に文体固定情報が未定着でも運用可能なため、再起動時に口調が揺れる
2. `state_schema_novel.yaml` の `tone` / `pov` はあるが、必須運用になっていない
3. `request_template.md` の短文例（800字、1000〜1500字）が短文化バイアスになる
4. `session_notes.md` 圧縮時に文体錨情報を失いやすい
5. 複数話一括生成時の「各話最小文字数」契約がない

## 4. 目標値（KPI）
### 4.1 文字数
1. 1話あたりの下限: 1800文字以上（例外は明示）
2. 章目標達成率: 章完了時に目標比80%以上
3. 全体目標達成率: 章5完了時に8万〜11万字レンジ

### 4.2 文体一貫性
1. セッション再開後の一人称/語尾ルール逸脱率: 5%未満
2. 主要キャラ口調ルール違反: 1話あたり0〜1件以内

### 4.3 複数話生成安定性
1. N話連続生成時（N=3想定）、最後の話の文字数が最初の話比で85%未満に落ちない

## 5. 要件: スクリプト側（小説作成）
対象ファイル: `小説作成/scripts/build_llm_prompt.py`

### 5.1 機能要件（Script-FR）
1. `Script-FR-01` 残予算ベース文字数計画
`--chapter` と進捗情報から「章残文字数」「推奨今回文字数」を算出し、指示文に埋め込む。
2. `Script-FR-02` 出力モード明示
`本文生成モード` と `アイデアモード` を分離する。本文生成モード時は「本文のみ出力」を必須化する。
3. `Script-FR-03` 連続性コンテキスト強化
`previous_text` を未指定時に自動探索し、直近1〜2話を自動注入する。
4. `Script-FR-04` 文体契約の注入
`agent/memory/global_notes.md` または専用文体ファイルを読み、口調・視点・語彙ルールをプロンプトへ強制挿入する。
5. `Script-FR-05` 複数話連続生成の逐次化指示
複数話を一度に要求された場合、1話ずつ順次生成して毎回文脈を更新する指示テンプレートを出す。
6. `Script-FR-06` 長さ制約の明文化
指示に「最小文字数」「目標文字数」「上限文字数」「不足時の自動追記ルール」を明示する。

### 5.2 CLI要件（Script-CLI）
既存互換を維持しつつ以下を追加する。

1. `--mode prose|idea`（既定: prose）
2. `--scene <id>`（例: `2-4`）
3. `--min_chars <int>`（既定: 1800）
4. `--target_chars <int>`（既定: 2500）
5. `--max_chars <int>`（既定: 3200）
6. `--batch_scenes <csv>`（例: `2-1,2-2,2-3`）
7. `--strict_length`（不足時に追記要求を指示文へ追加）

### 5.3 出力仕様（Script-OUT）
`llm_prompt_output.txt` に以下セクションを追加する。

1. `### 文字数契約`
2. `### 文体契約`
3. `### 連続性要約（直近話）`
4. `### 出力フォーマット契約（本文のみ / 見出し禁止 等）`

## 6. 要件: Agent機能側（Agenthelperテンプレート）
対象:
1. `Agenthelper/agent_templates_catalog/novel/skills/SKILL_novel.md`
2. `Agenthelper/agent_templates_catalog/novel/state_schema_novel.yaml`
3. `Agenthelper/agent_templates_catalog/novel/evals/prompts/*`
4. `Agenthelper/agent_templates_common/request_template.md`
5. `Agenthelper/agent_templates_common/compaction_policy.md`
6. `Agenthelper/agent_templates_common/memory/global_notes.md`

### 6.1 機能要件（Agent-FR）
1. `Agent-FR-01` 文体固定の必須化
セッション開始時に `global_notes.md` の文体規約未設定なら、本文生成前に必ず確定する。
2. `Agent-FR-02` 状態スキーマ拡張
`state_schema_novel.yaml` に文字数予算と進捗を追加する。
3. `Agent-FR-03` 圧縮時の文体保護
`compaction_policy.md` に「文体規約は要約で削除しない」「必ず global へ昇格」を追記する。
4. `Agent-FR-04` 複数話運用規約
`SKILL_novel.md` に「複数話は逐次生成」「各話ごと自己チェック」「最小文字数未達なら再生成」を追記する。
5. `Agent-FR-05` リクエストテンプレート修正
`request_template.md` の短文例を長編向け（2000〜3000字）に変更する。
6. `Agent-FR-06` 評価軸追加
eval prompt に `length_compliance` と `style_adherence` を追加する。

### 6.2 スキーマ要件（Agent-Schema）
`state_schema_novel.yaml` に以下キーを追加する。

1. `targets.total_chars`
2. `targets.chapter_chars`（章別マップ）
3. `targets.scene_default_chars`
4. `progress.total_chars_written`
5. `progress.chapter_chars_written`（章別マップ）
6. `style_contract.pov`
7. `style_contract.narration_tense`
8. `style_contract.dialogue_rules`
9. `style_contract.lexical_rules`

## 7. プロンプト契約仕様
### 7.1 本文生成モード契約
1. 本文のみを出力する
2. 指定最小文字数を下回らない
3. 見出し、箇条書き、メタ解説を出さない
4. 文体契約違反時は自己修正してから最終出力する

### 7.2 自己検査契約（内部）
最終出力前に内部チェック:

1. 文字数下限チェック
2. POVチェック
3. キャラ口調チェック
4. 前話接続チェック

## 8. テスト仕様
### 8.1 小説作成側テスト追加
対象: `小説作成/tests/test_scripts.py`

1. `test_prompt_contains_length_contract`
2. `test_prompt_contains_style_contract`
3. `test_auto_load_previous_text_when_missing`
4. `test_mode_prose_forbids_idea_output_instruction`
5. `test_batch_scene_prompt_includes_sequential_rule`

### 8.2 Agenthelper側テスト追加
対象: `Agenthelper/tests/*`

1. `test_novel_skill_contains_multi_scene_sequential_policy`
2. `test_state_schema_has_target_and_style_contract_fields`
3. `test_request_template_examples_are_long_form`
4. `test_compaction_policy_preserves_style_contract`
5. `test_eval_prompts_include_length_and_style_checks`

### 8.3 受け入れ試験（E2E）
1. 第2章シーン1〜3を連続生成し、各話1800字以上を確認
2. セッション再起動後に同条件で1話生成し、POV/語尾ルール維持を確認
3. 章進行後も平均文字数が初期比85%以上を維持することを確認

## 9. 実装タスク分解
### 9.1 フェーズA（スクリプト）
1. CLI拡張
2. 文字数計画ロジック追加
3. 文体契約読み込み実装
4. 直近本文自動解決実装
5. プロンプトテンプレ更新
6. テスト追加

### 9.2 フェーズB（Agentテンプレート）
1. `SKILL_novel.md` 改訂
2. `state_schema_novel.yaml` 改訂
3. `request_template.md` 改訂
4. `compaction_policy.md` 改訂
5. eval prompt 改訂
6. テスト追加

### 9.3 フェーズC（統合検証）
1. サンプルプロジェクトで3話連続生成を実施
2. 再起動後1話生成を実施
3. KPI適合判定

## 10. 互換性・移行
1. 既存CLI引数は保持する
2. 新引数未指定時は従来互換の既定値で動作する
3. 既存プロジェクトに `agent/` がある場合は `compose_agent_package.py` の上書きポリシーに従う
4. 既存 `global_notes.md` が空の場合は初回実行時に最小テンプレを補完する

## 11. リスクと対策
1. 文字数制約を強めすぎると冗長化する
`strict_length` を任意化し、章進行に応じて可変目標を採用する。
2. 文体ルール過多で創造性が落ちる
必須ルールと推奨ルールを分離する。
3. 複数話逐次化で処理時間が増える
品質優先モードとして明示し、高速モードを別途残す。

## 12. 完了条件（Definition of Done）
1. 本仕様の Script-FR/Agent-FR がすべて実装済み
2. 追加テストが全件パス
3. E2E受け入れ試験3件がすべて合格
4. READMEまたは運用ドキュメントに新フローが反映済み

