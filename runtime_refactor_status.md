# Runtime Refactor Status

## Current State

- Overall Status: implemented
- Spec Status: completed
- Implementation Status: completed
- Validation Status: completed
- Handoff Status: ready_for_use

## Completed

- `script-first` 軽量化の方向性を整理した
- 新フローのランタイムファイル構成を定義した
- 各スクリプトの CLI 引数、出力物、成功条件、失敗条件を仕様化した
- 実装タスク一覧を別ファイル化した
- `小説作成/scripts/prompt_utils.py` を追加し、共通処理を切り出した
- `小説作成/scripts/build_runtime_context.py` を追加した
- `小説作成/scripts/build_draft_prompt.py` を追加した
- `小説作成/scripts/check_scene_output.py` を追加した
- `小説作成/scripts/build_expand_prompt.py` を追加した
- `tests/test_scripts.py` に runtime 系の正常系・異常系テストを追加した
- `README.md` に runtime フローの使い方を追記した
- `check_scene_output.py` のメタ文言検出を誤検知しにくい形へ調整した
- `check_report.json` に詳細フィールド（差分文字数、違反詳細、禁止表現詳細）を追加した
- `check_scene_output.py` に未閉じカギ括弧と重複段落の検出を追加した
- テストは `python -m pytest tests/test_scripts.py -v` で 19 件通過を確認した

## Not Started

- なし

## Risks

- `scene` 引数の表記揺れ（`3-2` と `chapter_3_scene_2`）の正規化が必要
- プロジェクトごとに `agent/` 配下のファイル有無が異なる可能性がある
- `check_scene_output.py` は機械判定を強化したが、視点ぶれや口調逸脱はまだ別扱いが必要
- `build_llm_prompt.py` との責務重複を放置すると、将来メンテナンスが割れる

## Next Recommended Action

次に着手するなら、以下が候補。

1. `check_scene_output.py` に句読点連続や空行過多などの追加ルールを入れる
2. `check_scene_output.py` に視点ぶれ・口調逸脱のヒューリスティックを検討する
3. runtime フローを使うサンプルプロジェクトを追加する
4. 必要なら `build_llm_prompt.py` 側でも `prompt_utils.py` を段階的に利用する

## Reference Files

- `runtime_refactor_spec.md`
- `runtime_refactor_tasks.md`
- `runtime_refactor_status.md`
