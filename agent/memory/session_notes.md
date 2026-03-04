# Session Notes (Common)

このファイルには **直近の再開に必要な最小限の作業メモ** を記録します。
詳細な経緯や低優先度案件の履歴は `session_archive.md` を参照してください。

---

## 運用メモ

- 原則として「最新の要約 1 件 + アクティブ案件メモ + 共通メモ」に収める
- 直近の主タスクに不要な詳細は、要約して `session_archive.md` に移す
- 文体契約、未解決の論点、次アクションは必ず残す

---

## Notes

## [2026-03-01] 現在の作業要約

### 新事実
- `agent` 側のコア設計刷新は完了し、残タスクは現行運用の磨き込みに移った。
- `state_schema_novel.yaml` は、特定作品の固定データではなく、現行運用用の可変状態テンプレートへ再設計済み。
- 旧案件 `modern_isekai_40` のパイロット対応は一区切りつき、今は主タスクではない。
- `request_template.md` は、必須入力と最小依頼例を含む、実依頼寄りの粒度へ再調整した。
- `evals/README.md` は、Severity / Scope / Impact を含むレビュー出力粒度と、実運用向けの優先チェック順を追加した。
- 現時点の到達点を `current_refactor_status.md` として別ファイルに記録した。
- `HUB.md` に `Mode` / `current_mode` の正式語彙を定義し、ルーティング語彙の正本を一本化した。
- 執筆前工程を `SKILL_project_bootstrap.md`（案件初期化）と `SKILL_scene_planning.md`（執筆直前の段取り）に分割した。
- `SKILL_setting_creation.md` は長編骨格設計に責務を絞り、`SKILL_idea_generation.md` の次段は初期化へ変更した。
- `global_notes.md`、`state_schema_novel.yaml`、`request_template.md` から、作品固有の文体サンプルを外して中立化した。
- `current_refactor_status.md` と `refactor_task_checklist.md` も、新しい 9 スキル構成へ同期済み。
- `HUB.md`、`SKILL_novel.md`、`SKILL_resume_orchestrator.md` を `runtime-first` に更新し、執筆開始・再開時に `runtime/` を優先参照する運用へ揃えた。
- `小説作成/scripts/` に runtime 系スクリプト一式を同期し、`python -m pytest 小説作成/tests/test_scripts.py -v` で 19 件通過を確認した。

### 決定事項
- 今後の主軸は、現行運用のルーティング、記憶、テンプレート、評価の精度向上に置く。
- 旧案件の詳細経緯は、必要時のみ `session_archive.md` を参照する。
- `state_schema_novel.yaml` は、案件ごとの「現在地」と「次アクション」を持つ正本として使う。
- `request_template.md` は、`HUB.md` の正式モード名をそのまま使う前提で運用する。
- `evals/README.md` は、レビュー時に severity と修正優先度を切り分ける前提で使う。
- ここまでのリファクタリング到達点は、要約スナップショットを見ればすぐ把握できるようにする。
- 前工程は「企画」→「初期化」→「骨格設計」→「シーン設計」→「本文」の順で、責務を分けて扱う。
- 共通テンプレートには、作品固有の口調やキャラ例を残さない。
- 新規本文と再開整理は、`runtime/` が利用可能ならフル文脈より先に使う。

### 未解決
- `HUB.md` の曖昧依頼優先順位が、現行の実依頼パターンに十分対応しているか継続確認が必要。
- `session_notes.md` / `session_archive.md` の粒度が、今後の作業密度に対してちょうどよいかは継続確認が必要。
- 現行ブラッシュアップのコア項目は一通り反映済みで、残りは運用中の微調整フェーズ。
- `SKILL_project_bootstrap.md` と `SKILL_scene_planning.md` の発火条件とハンドオフが、実依頼で過不足ないかはまだ要観察。
- `runtime-first` の追加機械チェック（句読点連続、空行過多、視点ぶれヒント）をどこまで増やすかは未決定。

### 次アクション
- 次は、実運用の中で `SKILL_project_bootstrap.md` と `SKILL_scene_planning.md` の使い分けを検証する。
- `HUB.md` / `request_template.md` / `evals/README.md` の追加微調整ポイントを拾う。
- 新しい依頼パターンが出たら、`HUB.md` の曖昧依頼例へ反映する。
- 必要になった時だけ、個別の運用課題を追加でブラッシュアップする。
- 現在の基準確認が必要なときは、まず `current_refactor_status.md` を参照する。
- `runtime-first` 運用で不足が出たら、機械チェックかスキル手順のどちらを増やすべきか切り分けて調整する。

## アクティブ案件メモ

- 主タスク: 現行運用ブラッシュアップ
- 直近の焦点: `runtime-first` 統合は反映済み。次は運用中の追加微調整
- 参照優先: `current_refactor_status.md` -> `HUB.md` -> `agent/skills/SKILL_novel.md` -> `agent/skills/SKILL_resume_orchestrator.md` -> `request_template.md` -> `evals/README.md`

## 共通メモ

- 通常運用では、本文の正本はシーン単位 `txt`
- `body.md` は本文追記先ではなく、章方針メモまたは大幅改稿時のみ使用
- 新標準の文字数契約は `1000-1500`
- 新規本文と再開整理は、`runtime/` を優先参照する
- 文字数不足時は、局所差分ブロックで増補し、必要なら `scripts/apply_expand_edits.py` で本文へ反映する
