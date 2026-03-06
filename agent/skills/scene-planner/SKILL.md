---
name: scene-planner
description: Plan the next chapter or the next one to three scenes before drafting. Use when the user wants execution-ready scene beats, chapter segmentation, or immediate writing prep without rewriting core setting or drafting full prose. 日本語トリガー例: 次の1〜3シーンの段取りを決めたいとき。
---

# Purpose

既存の設定と章方針を前提に、直近で書く章やシーンの段取りを固める。

# Read First

- `agent/HUB.md`
- 対象プロジェクトの `runtime/planning_gate_brief.md`（あれば最優先で gate 状態を確認）
- 対象プロジェクトの `runtime/scene_brief_compact.md`（対象シーンと一致する場合は最優先）
- `runtime/scene_brief_compact.md` がない場合は、対象プロジェクトの `state_schema_novel.yaml`
- `long_form_100k` や planning gate 確認が必要な場合は、対象プロジェクトの `state_schema_novel.yaml`
- 対象プロジェクトの `runtime/style_contract_compact.md`（あれば）
- 対象プロジェクトの `runtime/continuity_pack.md`（あれば）
- 対象プロジェクトの `memory/global_notes.md`
- 対象プロジェクトの `memory/05_chapter_outline_100k.md`
- 必要なら対象シーンの `txt` または直前シーンの `txt`

# Required Inputs

- `project_path`
- 対象章、または対象シーン
- 直近で達成したい執筆目標

# Procedure

## 1. 範囲を固定する

- 章全体か、次の 1〜3 シーンかを先に決める
- いま必要な範囲だけに絞り、長編全体の再設計に広げすぎない
- `runtime/scene_brief_compact.md` の `Scene ID` が対象章 / 対象シーンと一致しない場合は、既存 `scene_brief` を優先せず stale 候補として扱う
- `runtime/check_report.json` の `target_file` が存在する場合は、`scene_brief` の対象と一致するかを確認する
- `scene_brief` と `check_report` が不一致なら、先に `runtime` 再生成を優先する
- 対象シーンが明示されており、`runtime/` が未生成または古い場合は、必要に応じて以下を実行して圧縮文脈を更新する
- `python scripts/build_runtime_context.py --project <project_path> --chapter <chapter> --scene <scene> --mode draft`

## 2. 現在地を確認する

- `runtime/scene_brief_compact.md` があり、対象章や対象シーンと一致する場合のみ、そこに書かれた Goal / Conflict / Hook を優先する
- `runtime/planning_gate_brief.md` がある場合は、その `Planning Gate` と `Next Planning Action` を先に確認する
- 直近で確定している章方針と未解決要素を確認する
- 直前シーンとの接続条件を確認する
- `long_form_100k` で `planning_gate_status != ready` の場合は、シーン段取りへ進まず `setting-creator` へ戻す
- 章指定のみで、対象章のシーン `txt` がすでに存在する場合は、「未着手シーンを新規に作る」前提にせず、まず再整理対象の既存シーンを 1 つ決める
- 章指定のみで既存シーンが複数ある場合は、以下の順で再整理対象を 1 つ決める
- `scene_brief` と一致するシーン
- `runtime/check_report.json` で `needs_expand=true` のシーン
- 文字数が `1000` 未満のシーン
- 更新時刻が最も新しいシーン
- 「情報不足シーン」は、以下のいずれかを満たすシーンとして扱う
- `runtime/check_report.json` に `needs_expand=true` がある
- `runtime/check_report.json` がなく、シーン本文の文字数が `1000` 未満である
- `runtime/scene_brief_compact.md` があるのに、対象 `Scene ID` と再整理対象シーンが一致せず、要件反映漏れの疑いがある
- 情報不足シーンを選んだ場合は、返答で根拠を 1 行明示する

## 3. 段取りを作る

- 各シーンの目的
- 衝突または障害
- 見せる情報と伏線
- シーン末尾の次フック

上記を、執筆に移れる粒度で整理する。

## 4. 執筆へ渡す

- 次に書くシーンと、先に読むべきファイルを明確にする
- `Write Next` は、指定範囲の中で最も早く着手すべき 1 シーンを選ぶ
- 既定の優先順は「最初の未着手シーン」→「最初の情報不足シーン」→「最初の接続確認が必要なシーン」
- 対象章のシーンがすでに存在する場合は、新規空白シーン前提で扱わず、「どの既存シーンの段取りを再整理するか」を明示する
- `Read First` は、以下の優先順で最大 3 件までに絞る
- 対象と一致する `runtime/scene_brief_compact.md`
- stale 判定になった `runtime/scene_brief_compact.md` は `Read First` に含めない
- 対象章の `memory/05_chapter_outline_100k.md`
- 既存シーンを再整理する場合は、その対象シーンの `txt`
- 直前との接続確認が必要な場合は、対象シーンの 1 つ前の `txt`
- 世界観や制約の補足が不足する場合のみ `memory/global_notes.md`
- `Read First` に直前シーンを含める場合は、「接続確認のため」と分かる形で返す
- 次に書くシーンを 1 つに絞る
- 参照ファイルは最大 3 件までに絞る
- 骨格不足が見つかった場合のみ `agent/skills/setting-creator/SKILL.md` へ戻す
- `long_form_100k` で `planning_gate_status != ready` の場合は、`Write Next` を返さず `agent/skills/setting-creator/SKILL.md` への差し戻しを優先する

# Handoff

- 新規本文: `agent/skills/novel-writer/SKILL.md`
- 骨格再整理: `agent/skills/setting-creator/SKILL.md`

# Outputs

- 次章または次シーン群の段取り
- 直近で参照すべきファイル
- そのまま書き始めるべき対象

返答時は、以下の順で返す。

1. `Planning Scope`: 今回固めた範囲
2. `Scene Beats`: 目的 / 衝突 / 見せる情報 / 次フック
3. `Write Next`: 次に書くべきシーンを 1 つ
4. `Read First`: 執筆前に読むファイル

# Do Not

- 長編全体の骨格設計まで巻き取らない
- `long_form_100k` で `planning_gate_status != ready` のまま執筆直前段取りへ進めない
- 本文初稿を書き始めない
- 監査や改稿の責務を混ぜない
- 次に書く対象を複数候補のまま終えない


