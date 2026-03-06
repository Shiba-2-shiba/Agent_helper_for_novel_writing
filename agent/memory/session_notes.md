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

## [2026-03-04] 引き継ぎ要約

### 新事実
- `agent/skills/legacy/SKILL_planner.md` は `agent/skills/legacy/` へ移動し、旧互換専用に整理した。
- `agent/skills/project-bootstrap/SKILL.md`、`agent/skills/scene-planner/SKILL.md`、`agent/skills/resume-orchestrator/SKILL.md` の「読む / 実行する / 返す」を明示化した。
- `agent/evals/README.md` に小説向けスキル改善ループを追加し、`ojiichan_mystery` を基準案件にした評価テンプレートを追加した。
- `resume_orchestrator` と `scene_planning` の初回パイロットを実施し、結果を `agent/evals/results/` に記録した。
- `build_runtime_context.py` と `prompt_utils.py` を調整し、`ojiichan_mystery` で `resume` / `draft` の `runtime` 生成が両方通る状態にした。
- 次チャット向けの引き継ぎ書として `agent/refactor_handoff_2026-03-04.md` を追加した。
- `agent/skills/scene-planner/SKILL.md` に、`Read First` の優先順と、既存シーン再整理時の参照ルールを追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、`Recommended Skill` を選ぶ条件分岐を追加した。
- `agent/current_refactor_status.md` と `agent/evals/README.md` を、この第 2 改善ループに合わせて同期した。
- `ojiichan_mystery` で、`scene_planning` / `resume_orchestrator` の第 2 改善ループ再評価結果を `agent/evals/results/` に追加した。
- 別案件がまだないため、次案件へ流用するための汎用比較テンプレート `agent/evals/templates/runtime_ready_project_comparison.md` を追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、「対象一致でも `resume_brief.md` を stale とみなす条件」を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 3 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_third_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、更新時刻ベースの補助 stale 判定を追加した（ただし時刻だけでは断定しない）。
- `ojiichan_mystery` で、`resume_orchestrator` の第 4 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_fourth_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、`resume_brief.md` の文言パターン解釈（未着手 / 完了 / 監査寄り）を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 5 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_fifth_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、`Open Items` / `Next Actions` の語彙解釈（前工程残り / 監査寄り / 未移行）を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 6 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_sixth_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、`Read First` と `Next Actions` の整合確認（整合したまま古いスナップショット判定）を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 7 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_seventh_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、`Recommended Skill` と最終 `Read First` の整合確認を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 8 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_eighth_pass.md` に追加した。
- `agent/skills/resume-orchestrator/SKILL.md` に、スキル別の `Read First` 対応表（監査 / 改稿 / 段取り / 執筆 / 設定 / 初期化）を追加した。
- `ojiichan_mystery` で、`resume_orchestrator` の第 9 改善ループ結果を `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md` に追加した。

### 決定事項
- 次のチャットでは、まず `agent/refactor_handoff_2026-03-04.md` を起点に再開する。
- 直近の主タスクは、本文品質そのものではなく、`scene_planning` / `resume_orchestrator` の責務精度をもう一段磨くこと。
- 次の改善ループも、1 回につき 1 論点だけ直して同じケースで再比較する。

### 未解決
- 別案件でも、`scene_planning` の `Read First` 選定順が過不足なく機能するかは未確認。
- 別案件でも、`resume_orchestrator` の条件分岐が過度に広い工程へ戻さないかは未確認。
- `resume_brief.md` のスキル別 `Read First` 対応表は入れたが、優先順位テンプレートを共通化するかは未整理。

### 次アクション
- 次は `agent/refactor_handoff_2026-03-04.md` を参照して再開する。
- 次は、別案件が入った時に `agent/evals/templates/runtime_ready_project_comparison.md` を起点に比較する。
- `resume_orchestrator` の次の改善候補として、スキル別 `Read First` の優先順位テンプレートを共通化するか検討する。
- 実案件が増えたら、今回の汎用比較テンプレートから個別テンプレートを派生させる。

### 最短再開手順
- まず `agent/refactor_handoff_2026-03-04.md` を開く。
- 次に `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md` を確認する。
- その後に `agent/skills/resume-orchestrator/SKILL.md` を見て、次の 1 論点だけを選ぶ。

## [2026-03-01] 現在の作業要約

### 新事実
- `agent` 側のコア設計刷新は完了し、残タスクは現行運用の磨き込みに移った。
- `state_schema_novel.yaml` は、特定作品の固定データではなく、現行運用用の可変状態テンプレートへ再設計済み。
- 旧案件 `modern_isekai_40` のパイロット対応は一区切りつき、今は主タスクではない。
- `request_template.md` は、必須入力と最小依頼例を含む、実依頼寄りの粒度へ再調整した。
- `evals/README.md` は、Severity / Scope / Impact を含むレビュー出力粒度と、実運用向けの優先チェック順を追加した。
- 現時点の到達点を `current_refactor_status.md` として別ファイルに記録した。
- `HUB.md` に `Mode` / `current_mode` の正式語彙を定義し、ルーティング語彙の正本を一本化した。
- 執筆前工程を `agent/skills/project-bootstrap/SKILL.md`（案件初期化）と `agent/skills/scene-planner/SKILL.md`（執筆直前の段取り）に分割した。
- `agent/skills/setting-creator/SKILL.md` は長編骨格設計に責務を絞り、`agent/skills/idea-generator/SKILL.md` の次段は初期化へ変更した。
- `global_notes.md`、`state_schema_novel.yaml`、`request_template.md` から、作品固有の文体サンプルを外して中立化した。
- `current_refactor_status.md` と `refactor_task_checklist.md` も、新しい 9 スキル構成へ同期済み。
- `HUB.md`、`agent/skills/novel-writer/SKILL.md`、`agent/skills/resume-orchestrator/SKILL.md` を `runtime-first` に更新し、執筆開始・再開時に `runtime/` を優先参照する運用へ揃えた。
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
- `agent/skills/project-bootstrap/SKILL.md` と `agent/skills/scene-planner/SKILL.md` の発火条件とハンドオフが、実依頼で過不足ないかはまだ要観察。
- `runtime-first` の追加機械チェック（句読点連続、空行過多、視点ぶれヒント）をどこまで増やすかは未決定。

### 次アクション
- 次は、実運用の中で `agent/skills/project-bootstrap/SKILL.md` と `agent/skills/scene-planner/SKILL.md` の使い分けを検証する。
- `HUB.md` / `request_template.md` / `evals/README.md` の追加微調整ポイントを拾う。
- 新しい依頼パターンが出たら、`HUB.md` の曖昧依頼例へ反映する。
- 必要になった時だけ、個別の運用課題を追加でブラッシュアップする。
- 現在の基準確認が必要なときは、まず `current_refactor_status.md` を参照する。
- `runtime-first` 運用で不足が出たら、機械チェックかスキル手順のどちらを増やすべきか切り分けて調整する。

## アクティブ案件メモ

- 主タスク: 現行運用ブラッシュアップ
- 直近の焦点: `resume_orchestrator` のスキル別 `Read First` 対応表まで入れたので、次は優先順位テンプレートの共通化と別案件再現性を詰める
- 参照優先: `agent/refactor_handoff_2026-03-04.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_eighth_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_seventh_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_sixth_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_fifth_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_fourth_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_third_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_second_pass.md` -> `agent/evals/results/scene_planning_ojiichan_mystery_second_pass.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_pilot.md` -> `agent/evals/results/scene_planning_ojiichan_mystery_pilot.md` -> `agent/skills/resume-orchestrator/SKILL.md` -> `agent/skills/scene-planner/SKILL.md` -> `agent/evals/templates/runtime_ready_project_comparison.md` -> `agent/evals/README.md`
- 再開ショートカット: `agent/refactor_handoff_2026-03-04.md` -> `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md` -> `agent/skills/resume-orchestrator/SKILL.md`

## 共通メモ

- 通常運用では、本文の正本はシーン単位 `txt`
- `body.md` は本文追記先ではなく、章方針メモまたは大幅改稿時のみ使用
- 新標準の文字数契約は `1000-1500`
- 新規本文と再開整理は、`runtime/` を優先参照する
- 文字数不足時は、局所差分ブロックで増補し、必要なら `scripts/apply_expand_edits.py` で本文へ反映する


