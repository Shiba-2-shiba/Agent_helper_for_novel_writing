# Runtime Refactor Tasks

## Goal

`script-first` 軽量執筆フローを追加し、既存 `build_llm_prompt.py` と共存できる状態にする。

## Task List

- [x] `runtime_refactor_spec.md` に基づき、スクリプト追加方針を最終確認する
- [x] `小説作成/scripts/build_runtime_context.py` を追加する
- [x] `小説作成/scripts/build_draft_prompt.py` を追加する
- [x] `小説作成/scripts/check_scene_output.py` を追加する
- [x] `小説作成/scripts/build_expand_prompt.py` を追加する
- [x] 共通処理を `小説作成/scripts/prompt_utils.py` へ切り出すか判断する
- [x] 既存 `小説作成/scripts/build_llm_prompt.py` から再利用可能な関数を整理する
- [x] `runtime/` 出力ファイルのパス生成と上書き挙動を実装する
- [x] `style_contract_compact.md` の抽出ロジックを実装する
- [x] `scene_brief_compact.md` の抽出ロジックを実装する
- [x] `continuity_pack.md` の抽出ロジックを実装する
- [x] `request_compact.md` の生成ロジックを実装する
- [x] `resume_brief.md` の生成ロジックを実装する
- [x] `draft_prompt.txt` の生成ロジックを実装する
- [x] `check_report.json` の JSON スキーマに沿った出力を実装する
- [x] `expand_instruction.md` の生成ロジックを実装する
- [x] `expand_prompt.txt` の生成ロジックを実装する
- [x] 各 CLI の引数バリデーションを実装する
- [x] 各 CLI の終了コードと標準出力メッセージを仕様に合わせる
- [x] 最低限の正常系テストを追加する
- [x] 異常系（入力不足、パス不正、JSON 壊れ）テストを追加する
- [x] README または補助ドキュメントに新フローの使い方を追記するか判断する
- [x] `check_scene_output.py` のメタ文言検出の誤検知を減らす
- [x] `check_report.json` に詳細フィールドを追加する
- [x] `check_scene_output.py` に未閉じカギ括弧検出を追加する
- [x] `check_scene_output.py` に重複段落検出を追加する
- [x] 強化分のテストを追加し、19 件通過を確認する

## Suggested Order

1. `check_scene_output.py` に句読点連続や空行過多の検出を追加する
2. `check_scene_output.py` に視点ぶれ・口調逸脱のヒューリスティックを追加する
3. 必要に応じて `build_llm_prompt.py` 側にも共通処理を反映する
4. 新フローの利用例を増やす

## Done Definition

以下を満たしたら完了:

- [x] 4 本の新スクリプトが仕様通りに動く
- [x] `runtime/` 配下の出力が再現性を持って生成される
- [x] 初稿 1 回目と拡張 2 回目の分離が確認できる
- [x] 既存 `build_llm_prompt.py` が壊れていない
