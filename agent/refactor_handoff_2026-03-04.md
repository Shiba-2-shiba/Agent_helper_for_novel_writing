# Refactor Handoff (2026-03-04)

## Purpose

このファイルは、現行のリファクタリング状況を新しいチャットへ引き継ぐための短い再開用メモです。
次回は、まずこのファイルを読み、その後に必要な詳細だけ個別ファイルへ掘ってください。

## Current Status

- コアのスキル分割と `runtime-first` 運用は完了済み
- Phase 1 の追加ブラッシュアップとして、旧互換スキル整理と主要スキルの手順粒度統一を完了
- `resume_orchestrator` と `scene_planning` の初回改善ループを、実案件 `ojiichan_mystery` で 1 回ずつ実施済み
- `ojiichan_mystery` に対して、`resume` / `draft` の `runtime` 生成が両方通る状態までスクリプトを調整済み
- `scene_planning` の `Read First` 優先順と、`resume_orchestrator` の `Recommended Skill` 選定条件を追加した第 2 改善ループの文面調整を実施済み
- `ojiichan_mystery` で第 2 改善ループの再評価を実施し、結果を `agent/evals/results/` に追加済み
- 別案件が未作成のため、次案件用の汎用比較テンプレート `agent/evals/templates/runtime_ready_project_comparison.md` を追加済み
- `resume_orchestrator` に `resume_brief` の stale 判定条件を追加し、`ojiichan_mystery` で第 3 改善ループを記録済み
- `resume_orchestrator` に更新時刻ベースの補助 stale 判定を追加し、`ojiichan_mystery` で第 4 改善ループを記録済み
- `resume_orchestrator` に `Current Position` の文言パターン解釈を追加し、`ojiichan_mystery` で第 5 改善ループを記録済み
- `resume_orchestrator` に `Open Items` / `Next Actions` の語彙解釈を追加し、`ojiichan_mystery` で第 6 改善ループを記録済み
- `resume_orchestrator` に `Read First` / `Next Actions` の整合確認を追加し、`ojiichan_mystery` で第 7 改善ループを記録済み
- `resume_orchestrator` に `Recommended Skill` / `Read First` の整合確認を追加し、`ojiichan_mystery` で第 8 改善ループを記録済み
- `resume_orchestrator` にスキル別 `Read First` 対応表を追加し、`ojiichan_mystery` で第 9 改善ループを記録済み

## Restart Snapshot

- 直近の主対象は `resume_orchestrator` で、改善ループは **第 9 段階** まで到達
- 最新の追加点は、`Recommended Skill` に応じて `Read First` を切り替える **スキル別対応表**
- 次に詰める候補は、スキル別 `Read First` の**優先順位テンプレート共通化**
- `scene_planning` 側は第 2 改善ループ時点で一旦安定しており、直近は `resume_orchestrator` の磨き込みが中心

## Next Chat Quick Start

次のチャットでは、まず以下だけ見れば再開できる。

1. この `agent/refactor_handoff_2026-03-04.md`
2. `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md`
3. `agent/skills/resume-orchestrator/SKILL.md`
4. 必要になったら `agent/evals/README.md`

この順で見れば、「今どこまで改善したか」「直近の比較結果」「次に触るべき本文」が最短で揃う。

## What Changed In This Session

### 1. Legacy Skill Isolation

- `agent/skills/SKILL_planner.md` を `agent/skills/legacy/SKILL_planner.md` へ移動
- 旧互換専用であり、現行運用では使わないことを明示
- `AGENT_GUIDE.md` に `skills/legacy/` を「移行時のみ参照」として追加

### 2. Skill Format Hardening

- `agent/skills/project-bootstrap/SKILL.md`
  - 読むもの、実行するもの、返すものを明示
  - `python scripts/init_project.py <project_name>` を明記
- `agent/skills/scene-planner/SKILL.md`
  - `runtime/` の再生成条件を明記
  - `Write Next` を 1 つに絞る返答形式を固定
  - 章指定時の `Write Next` 選定順を明記
- `agent/skills/resume-orchestrator/SKILL.md`
  - `chapter` / `scene` 未指定時の再開候補推定順を明記
  - 返答順を固定

### 3. Evaluation Loop Setup

- `agent/evals/README.md` に、小説向けのスキル改善ループ運用を追加
- 以下の評価テンプレートを追加
  - `agent/evals/templates/resume_orchestrator_ojiichan_mystery.md`
  - `agent/evals/templates/scene_planning_ojiichan_mystery.md`
- 以下のパイロット結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_pilot.md`
  - `agent/evals/results/scene_planning_ojiichan_mystery_pilot.md`

### 4. Runtime Script Compatibility Fixes

- `scripts/build_runtime_context.py`
  - `resume` 時に章アウトラインを必須にしないよう変更
  - `draft` 時は `memory/05_chapter_outline_100k.md` も探索
- `scripts/prompt_utils.py`
  - root 直下の `state_schema_novel.yaml` を探索対象に追加
  - `# 第N章` 形式の章見出しを抽出できるよう変更
  - `## シーンN：...` 形式のシーン見出しを抽出できるよう変更

### 5. Second Improvement Loop Wording Tightening

- `agent/skills/scene-planner/SKILL.md`
  - `Read First` を `runtime` → 章アウトライン → 対象 / 直前シーン → `global_notes` の優先順に固定
  - 既存シーンがある章では、再整理対象の既存シーンを先に決めるよう明記
- `agent/skills/resume-orchestrator/SKILL.md`
  - `Recommended Skill` を、初期化 / シーン設計 / 改稿 / 監査 / 執筆 / 設定再整理の条件で選ぶよう明記
  - フォールバック時に読む `state` / `memory` を、対象プロジェクト基準に修正
- `agent/evals/README.md`
  - 第 2 改善ループで見る観点（`Read First` の順序と `Recommended Skill` の根拠）を追記

### 6. Second Pass Evaluation Records

- 以下の再評価結果を追加
  - `agent/evals/results/scene_planning_ojiichan_mystery_second_pass.md`
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_second_pass.md`
- `scene_planning`
  - `Read First` は 3 件に収束し、`runtime` → 章アウトライン → 対象シーン本文で安定
  - 残課題は「既存シーン複数時の情報不足判定」をどこまで明文化するか
- `resume_orchestrator`
  - `Recommended Skill` は `agent/skills/consistency-auditor/SKILL.md` へ収束
  - 残課題は「`resume_brief` が同じシーン番号でも stale な場合」の判定条件

### 7. Reusable Comparison Template

- `agent/evals/templates/runtime_ready_project_comparison.md` を追加
- `runtime/` が整っている次案件で、そのまま第 2 改善ループを横比較できる雛形にした

### 8. Third Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - 対象シーンが一致していても、`resume_brief.md` が「着手前」のままで、同じシーンの本文または `check_report` がある場合は stale とみなす条件を追加
  - stale 判定時は、最新のシーン本文と `runtime/check_report.json` で現在地を上書きしてから判断すると明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_third_pass.md`

### 9. Fourth Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - 更新時刻ベースの補助 stale 判定を追加
  - ただし、更新時刻だけでは断定せず、本文実体や `check_report` の内容確認も必須と明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_fourth_pass.md`

### 10. Fifth Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - `Current Position` の文言を、未着手 / 完了 / 監査寄りの状態として読むルールを追加
  - `準備段階` を未着手寄りに読むよう明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_fifth_pass.md`

### 11. Sixth Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - `Open Items` / `Next Actions` の語彙を、前工程残り / 監査寄り / 未移行の根拠として読むルールを追加
  - `確定する` / `決める` / `進む` などを、着手前メモの補強根拠として扱うよう明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_sixth_pass.md`

### 12. Seventh Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - `Read First` と `Next Actions` が、同じ作業モードを指しているか確認するルールを追加
  - 互いには整合していても、実ファイル状況より古い場合は「整合したまま古いスナップショット」として stale 根拠にするよう明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_seventh_pass.md`

### 13. Eighth Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - `Recommended Skill` と最終 `Read First` が、同じ直近タスクを支える組み合わせになっているか確認するルールを追加
  - スキル選定と参照ファイルがズレる場合は、現在地推定かスキル選定を見直してから返すよう明記
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_eighth_pass.md`

### 14. Ninth Improvement Loop For `resume_orchestrator`

- `agent/skills/resume-orchestrator/SKILL.md`
  - スキル別の `Read First` 対応表を追加
  - `agent/skills/consistency-auditor/SKILL.md` / `agent/skills/revision-editor/SKILL.md` / `agent/skills/scene-planner/SKILL.md` / `agent/skills/novel-writer/SKILL.md` / `agent/skills/setting-creator/SKILL.md` / `agent/skills/project-bootstrap/SKILL.md` ごとに優先ファイルを細分化
- 以下の再評価結果を追加
  - `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md`

## Live Validation Completed

以下のコマンドは実行し、`ojiichan_mystery` で通過確認済みです。

```powershell
python scripts/build_runtime_context.py --project C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery --chapter 6 --scene 6-3 --mode resume
python scripts/build_runtime_context.py --project C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery --chapter 2 --scene 2-2 --mode draft
```

期待結果:

- `OK: runtime context generated ...`
- `OK: wrote ... files into ...\runtime`

## Files To Read First In The Next Chat

1. `agent/refactor_handoff_2026-03-04.md`
2. `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md`
3. `agent/evals/results/resume_orchestrator_ojiichan_mystery_eighth_pass.md`
4. `agent/evals/results/resume_orchestrator_ojiichan_mystery_seventh_pass.md`
5. `agent/evals/results/resume_orchestrator_ojiichan_mystery_sixth_pass.md`
6. `agent/evals/results/resume_orchestrator_ojiichan_mystery_fifth_pass.md`
7. `agent/evals/results/resume_orchestrator_ojiichan_mystery_fourth_pass.md`
8. `agent/evals/results/resume_orchestrator_ojiichan_mystery_third_pass.md`
9. `agent/evals/results/resume_orchestrator_ojiichan_mystery_second_pass.md`
10. `agent/evals/results/scene_planning_ojiichan_mystery_second_pass.md`
11. `agent/evals/results/resume_orchestrator_ojiichan_mystery_pilot.md`
12. `agent/evals/results/scene_planning_ojiichan_mystery_pilot.md`
13. `agent/skills/resume-orchestrator/SKILL.md`
14. `agent/skills/scene-planner/SKILL.md`
15. `agent/evals/templates/runtime_ready_project_comparison.md`
16. `agent/evals/README.md`

## Recommended Next Step

次のチャットでは、以下の順で進めるのが自然です。

1. `resume_orchestrator` に、スキル別 `Read First` の優先順位テンプレートを共通化するか判断する
2. 新しい案件が入ったら `agent/evals/templates/runtime_ready_project_comparison.md` から比較テンプレートを起こす
3. 必要なら、既存シーンが多い章での `scene_planning` 選定ヒントも 1 行だけ追加する

## Known Remaining Work

- `session_notes.md` と `current_refactor_status.md` はこの時点まで同期済み
- 次の改善は「本文品質」より先に、「スキルが責務どおりに動くか」を中心に続ける方針でよい
- `resume_brief` のスキル別 `Read First` 対応表までは入れたが、優先順位テンプレートの共通化はまだない

## Notes

- このワークスペースは Git 管理下ではないため、`git status` では確認できない
- 今回はドキュメントとローカルスクリプト調整が中心で、包括的なテストスイートは未実行


