---
name: resume-orchestrator
description: Recover project state, identify the correct next step, and route back into the right writing skill. Use when the user wants to resume after a pause, understand current progress, or decide what to do next. 日本語トリガー例: どこから再開すべきか整理したいとき。
---

# Purpose

中断後の現在地を整理し、`runtime-first` で次に着手すべき作業と呼び出すべきスキルを決める。

# Read First

- `agent/HUB.md`
- 対象プロジェクトの `runtime/planning_gate_brief.md`（あれば gate 状態の確認を優先）
- 対象プロジェクトの `runtime/resume_brief.md`（あれば最優先）
- `runtime/resume_brief.md` がない場合は、対象プロジェクトの `runtime/style_contract_compact.md`
- 対象プロジェクトの `runtime/request_compact.md`
- 対象プロジェクトの `runtime/scene_brief_compact.md`（あれば対象一致を確認するために参照）
- `runtime/scene_brief_compact.md` がない場合は、対象プロジェクトの `runtime/check_report.json` を優先する
- `runtime/scene_brief_compact.md` も `runtime/check_report.json` もない場合は、対象プロジェクトの最新シーン `txt` を優先する
- `runtime/` に不足がある場合のみ、対象プロジェクトの `state_schema_novel.yaml`
- target profile や planning gate 確認が必要な場合は、対象プロジェクトの `state_schema_novel.yaml`
- `runtime/` に不足がある場合のみ、対象プロジェクトの `memory/global_notes.md`
- `runtime/` に不足がある場合のみ、対象プロジェクトの `memory/session_notes.md`
- 必要なら `agent/memory/session_archive.md`
- 必要なら `agent/trace/trace_min.txt` または `agent/trace/trace_view.txt`
- 必要なら最新のシーン `txt` や進捗ファイル

# Required Inputs

- 対象プロジェクト
- 前回の作業範囲が分かる手がかり
- 可能なら `chapter` と `scene`

# Procedure

## 1. 再開候補を先に推定する

- `chapter` / `scene` が明示されていない場合は、先に再開候補を 1 つに絞る
- 推定順は以下を優先する
- 最新のシーン `txt`（更新時刻が最も新しいもの）
- `runtime/check_report.json`（存在する場合は直近の検査対象を補助根拠にする）
- `runtime/scene_brief_compact.md` の `Scene ID`（存在する場合は補助根拠にする）
- `state_schema_novel.yaml`
- `session_notes.md`
- `state_schema_novel.yaml` の `current_mode` と実ファイル状況が矛盾する場合は、実ファイルを優先する
- 推定した `chapter` / `scene` を、以後の `runtime` 更新と再開判断の基準にする

## 2. `runtime/` を準備する

- 対象の `runtime/resume_brief.md` があり、現在の再開対象と矛盾しないなら再利用する
- ただし `runtime/resume_brief.md` が「対象シーンの着手前」を示しているのに、同じ対象シーンの `txt` または `runtime/check_report.json` がすでに存在する場合は、`resume_brief.md` を stale とみなす
- 補助判定として、`runtime/resume_brief.md` の更新時刻が、同じ対象シーンの `txt` または `runtime/check_report.json` より古い場合も、stale 寄りの根拠として扱う
- `runtime/scene_brief_compact.md` の `Scene ID`、`runtime/check_report.json` の `target_file`、推定した `chapter` / `scene` が互いに一致しない場合は、`runtime` パック全体を stale とみなす
- `runtime/resume_brief.md` と `runtime/scene_brief_compact.md` が互いには整合していても、実際の最新シーン `txt` より古い対象を指す場合は stale とみなす
- `runtime/scene_brief_compact.md` が欠落している場合は、`runtime/check_report.json` と最新シーン `txt` の一致を `runtime` 対象判定の基準にする
- `runtime/check_report.json` も欠落している場合は、最新シーン `txt` と `state_schema_novel.yaml` の `current_mode` を突き合わせ、実ファイル優先で再開対象を推定する
- `runtime/resume_brief.md` がない、古い、または対象シーンと不一致なら、先に以下を実行して更新する
- `python scripts/build_runtime_context.py --project <project_path> --chapter <chapter> --scene <scene> --mode resume`
- `resume_brief` の文言より、実在する scene `txt` と scene 対応 `check_report` を優先する
- `runtime/` が使えない場合のみ、従来の広い文脈参照へフォールバックする

## 3. 現在地を確認する

- まず `runtime/resume_brief.md` を読み、そこに書かれた `Current Position`、`Open Items`、`Next Actions` を優先する
- `Write Next` がある場合は、`Next Action` と `Recommended Skill` をその `Scene ID` / `Output Path` に揃える
- `runtime/planning_gate_brief.md` がある場合は、`Planning Gate` と `Next Planning Action` を `resume_brief` の補助判断に使う
- `Current Position` の文言は、少なくとも以下の粒度で読む
- `準備段階` / `着手前` / `書き始める前` は、未着手寄りの状態として扱う
- `完了` / `通過済み` / `書き終えた` は、本文完了寄りの状態として扱う
- `監査` / `整合確認` / `見直し` は、監査または改稿寄りの状態として扱う
- `Open Items` と `Next Actions` の語彙は、少なくとも以下の粒度で読む
- `確定する` / `決める` / `詰める` は、未確定の前工程が残っている状態として扱う
- `確認する` / `見直す` / `監査する` は、監査または整合確認が主目的の状態として扱う
- `進む` / `着手する` / `書き始める` は、その工程へまだ未移行である根拠として扱う
- `Read First` と `Next Actions` は、同じ作業モードを指しているかも確認する
- `style_contract_compact.md` / `request_compact.md` / 直前シーンの参照と、`進む` / `着手する` / `着手条件を決める` は、着手前モードとして整合しやすい
- 最新シーン `txt` / `runtime/check_report.json` の参照と、`確認する` / `見直す` / `監査する` は、監査または完了確認モードとして整合しやすい
- `Read First` と `Next Actions` が互いには整合していても、実ファイル状況とズレる場合は、「整合したまま古いスナップショット」として stale の補強根拠にする
- `resume_brief.md` を stale と判断した場合は、最新のシーン `txt` と `runtime/check_report.json` で現在地を上書きしてから次判断へ進む
- `scene_brief_compact.md` や `check_report.json` の対象が stale の場合は、どのファイルが古いかを明示し、`runtime` 再生成が必要であることを返答に含める
- 後続 scene が存在するのに対象 scene が `準備段階` とされている場合は、対象 scene を stale 候補として扱う
- 更新時刻の補助判定だけでは断定せず、本文実体や検査結果の内容確認も合わせて最終判断する
- `runtime/resume_brief.md` がない場合のみ、状態ファイルやメモから現在地を再構築する
- 判断履歴が必要な場合は、先に `agent/trace/trace_min.txt` を確認し、必要な event だけ `trace_full.txt` または `trace_view.txt` で復元する
- `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合は、再開対象が本文寄りでも `setting-creator` を優先する

- 完了済みの章、シーン
- 直近の未解決事項
- 次回着手点
- 直近の重要な方向転換

## 4. 次の最適行動を決める

- まだ案件の箱がない、または `state` / `memory` の基本ファイルが未作成なら、初期化を先にする
- 対象シーンが未作成、または「次に何を書くか」が未確定なら、執筆前にシーン設計を先にする
- ただし `resume_brief` に欠落依存起点の `Write Next` がある場合は、`scene-planner` へ戻さずそのシーン作成を先にする
- 対象シーンはあるが、文字数不足、形式違反、直近修正の取り込み不足が主問題なら、改稿を先にする
- 対象シーンや章の整合、締め、伏線回収の確認が主問題なら、監査を先にする
- `runtime/resume_brief.md` が「書き始める条件は揃っている」と示し、次の対象シーンも明確なら、新規執筆に進める
- ただし `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合は、新規執筆や `scene-planner` ではなく `setting-creator` に戻す
- 問題の本体がシーン単位ではなく、設定穴や世界観の未確定にある場合のみ、設定再整理を優先する
- 複数候補があり得る場合は、「最も次の 1 アクションに近いスキル」を優先し、広い工程へ戻しすぎない
- 新規執筆に進む場合は、`agent/skills/novel-writer/SKILL.md` の `runtime-first` ループへ渡す

## 5. 必要なスキルへ渡す

- 次に呼ぶべきスキルを 1 つに絞る
- 参照すべきファイルを短く案内する
- `Recommended Skill` と `Read First` は、同じ直近タスクを支える組み合わせにする
- `agent/skills/consistency-auditor/SKILL.md` を選ぶなら、`runtime/check_report.json`、最新シーン `txt`、必要なら隣接シーン `txt` を優先する
- `agent/skills/revision-editor/SKILL.md` を選ぶなら、対象シーン `txt`、`runtime/check_report.json`、必要なら直前シーン `txt` を優先する
- `agent/skills/scene-planner/SKILL.md` を選ぶなら、章アウトライン、対象シーン `txt`、必要なら直前シーン `txt` を優先する
- `agent/skills/novel-writer/SKILL.md` を選ぶなら、`runtime/resume_brief.md`、`runtime/style_contract_compact.md`、`runtime/request_compact.md` を優先する
- `agent/skills/setting-creator/SKILL.md` を選ぶなら、`state_schema_novel.yaml`、`memory/global_notes.md`、必要なら `memory/session_notes.md` を優先する
- `agent/skills/project-bootstrap/SKILL.md` を選ぶなら、既存の `state_schema_novel.yaml`、`memory/global_notes.md`、必要なら案件ルートの進捗手がかりを優先する
- `Recommended Skill` と `Read First` が互いにズレる場合は、現在地の推定かスキル選定のどちらかを見直してから返す
- 参照ファイルは最大 3 件までに絞る
- `runtime/scene_brief_compact.md` が欠落している場合は、`Read First` を `runtime/check_report.json` → 対象シーン `txt` → 直前シーン `txt` の順で補う
- `runtime/check_report.json` も欠落している場合は、`Read First` を 対象シーン `txt` → 直前シーン `txt` → `state_schema_novel.yaml` の順で補う
- 新規執筆へ渡す場合は、`runtime/resume_brief.md` と、必要なら再生成した `runtime/` の参照を明示する

# Handoff

- 新規執筆: `agent/skills/novel-writer/SKILL.md`
- 初期化: `agent/skills/project-bootstrap/SKILL.md`
- シーン設計: `agent/skills/scene-planner/SKILL.md`
- 改稿: `agent/skills/revision-editor/SKILL.md`
- 監査: `agent/skills/consistency-auditor/SKILL.md`
- 設定整理: `agent/skills/setting-creator/SKILL.md`

# Outputs

- 現在地の要約
- 次に着手すべきタスク
- 推奨スキル
- 必要なら `runtime/resume_brief.md` の更新案内

返答時は、以下の順で返す。

1. `Current Position`: いまどこまで進んでいるか
2. `Open Items`: 未解決事項
3. `Next Action`: 次にやることを 1 つ
4. `Recommended Skill`: 呼ぶべきスキルを 1 つ
5. `Read First`: 着手前に見るファイル

`Write Next` がある場合は、`Next Action` にその `Output Path` を含める。

# Do Not

- いきなり本文執筆に入らない
- 古い履歴を無制限に読み込み続けない
- 次の優先タスクを曖昧なまま終えない
- `runtime/resume_brief.md` が使えるのに、先にフル文脈を読み直さない
- 推奨スキルを複数列挙して判断をユーザーに丸投げしない

