---
name: novel-writer
description: Draft new scene prose for an existing novel project. Use when the user wants a fresh scene or continuation written, not when they mainly want diagnosis, revision, or polish. 日本語トリガー例: 第X章Yシーンを書いて、続きを執筆したいとき。
---

# Purpose

既存プロジェクトの文脈に沿って、`runtime-first` で新しいシーンの初稿を作成する。

# Read First

- `agent/HUB.md`
- 対象シーンの scene-scoped runtime 内 `draft_prompt.txt`（あれば最優先）
- scene-scoped `draft_prompt.txt` がない場合は、対象シーンの scene-scoped `style_contract_compact.md`
- 対象プロジェクトの `runtime/planning_gate_brief.md`（あれば gate 状態の確認を優先）
- 対象シーンの scene-scoped `scene_brief_compact.md`
- 対象シーンの scene-scoped `continuity_pack.md`
- 対象シーンの scene-scoped `request_compact.md`
- `runtime/` に不足がある場合のみ `agent/state_schema_novel.yaml`
- `runtime/` に不足がある場合のみ `agent/memory/global_notes.md`
- `runtime/` に不足がある場合のみ対象章の `05_chapter_outline.md` 該当箇所
- legacy project では `05_chapter_outline_100k.md` を fallback としてよい
- `runtime/` に不足がある場合のみ直前シーンの `txt`
- `body.md` は章の方向転換があった場合のみ補助的に参照する

# Required Inputs

- `project_path`
- `chapter`
- `scene`
- 必要なら `length_contract`
- 必要なら `scene_type`
- 必要なら `length_band`
- 必要なら既存の対象シーン `txt` の有無

# Procedure

## 1. scene-scoped `runtime/` を準備する

- 対象シーンの scene-scoped `runtime/draft_prompt.txt` があり、対象の `chapter` / `scene` と矛盾しないなら再利用する
- `runtime/draft_prompt.txt` がない、または `runtime/` の必須ファイルが欠けている場合は、先に以下を実行して更新する
- `python scripts/build_runtime_context.py --project <project_path> --chapter <chapter> --scene <scene> --mode draft`
- `python scripts/build_draft_prompt.py --project <project_path>`
- `Depends On` があるシーンは、依存先 `txt` が無い場合に本文執筆へ進めない
- `request_compact.md` または `scene_brief_compact.md` に `Planning Gate: blocked` がある場合は、本文執筆へ進まず `setting-creator` へ戻す
- `runtime/` が使えない場合のみ、従来の広い文脈参照へフォールバックする

## 2. 文脈を集める

- まず `runtime/draft_prompt.txt` を読み、そこに含まれる制約を優先する
- `runtime/draft_prompt.txt` がなければ、`runtime/style_contract_compact.md`、`runtime/scene_brief_compact.md`、`runtime/continuity_pack.md`、`runtime/request_compact.md` を読む
- `runtime/planning_gate_brief.md` がある場合は、`Planning Gate` が `ready` かを本文執筆前に確認する
- `runtime/scene_brief_compact.md` に `Scene Type` と `Length Band` がある場合は、それを文字数契約の正本として扱う
- `Target Length Profile` は補助情報として扱い、本文長の制御自体は `Length Band` を正本とする
- `runtime/` に不足がある場合のみ、対象シーンの章プロット、文体契約、進捗を補助参照する
- `runtime/continuity_pack.md` を優先し、直前シーンの感情、位置関係、会話温度を引き継ぐ
- 章の方針変更がある場合のみ `body.md` を確認する

## 3. 初稿を書く

- 指定シーンの本文を新規に執筆する
- `Length Band` がある場合は、その `min / target / max` を守る
- `bridge` は接続と整理を優先し、無理に膨らませない
- `standard` は通常の前進シーンとして、目的と抵抗を明確に保つ
- `anchor` / `climax` は感情変化、対立、決断、回収を厚くする
- 地の文、会話、内面描写の比率が偏りすぎないようにする
- 次シーンへつながる未解決要素を残す

## 4. 機械チェックと自己評価を行う

- 初稿を対象シーンの `txt` へ一度保存する
- 保存後、以下を実行して機械チェックする
- `python scripts/check_scene_output.py --project <project_path> --text <scene_txt_path>`
- `runtime/check_report.json` を確認し、`needs_expand=true` なら以下を実行する
- `python scripts/build_expand_prompt.py --project <project_path> --draft_text <scene_txt_path>`
- `runtime/expand_prompt.txt` の制約に従い、全文再生成ではなく途中差し込みまたは末尾追記の局所差分だけを増補する
- 差分を採用する場合は `python scripts/apply_expand_edits.py --project <project_path> --text <scene_txt_path> --edits <expand_response_path>` で反映する
- 増補後は再度 `python scripts/check_scene_output.py --project <project_path> --text <scene_txt_path>` を実行する

保存前または再保存前に以下を確認する。

- 文字数が対象シーンの `Length Band` に収まっている、または少なくとも `min` 未満ではない
- 視点がぶれていない
- 主要キャラの口調が契約から外れていない
- シーンの目的が達成されている
- 本文中に見出し、箇条書き、メタ発言がない

`runtime/scene_brief_compact.md` に `Length Band` がない場合のみ、旧基準の `length_contract` または `1000-1500` をフォールバックとして使う。

基準を満たさない場合は、最大 3 回まで自律的に修正する。

## 5. 保存する

- 完成した本文は、対象シーンの `txt` ファイルへ保存する
- 通常運用では `body.md` を更新しない
- 拡張を行う場合でも、フル文脈の再読込ではなく `runtime/expand_prompt.txt` を優先し、局所差分だけを反映する

# Handoff

- 設定やプロットの前提変更が必要: `agent/skills/setting-creator/SKILL.md`
- 既存シーンの修正が主目的になった: `agent/skills/revision-editor/SKILL.md`
- 診断が必要: `agent/skills/consistency-auditor/SKILL.md`

# Outputs

- 新規シーン初稿
- `runtime/check_report.json` による文字数チェック結果
- 必要なら `scene_type` と `length_band` に対する短い自己評価メモ
- 必要なら短い自己評価メモ

# Do Not

- 既存の `body.md` を本文集約先として使わない
- 改稿や監査の責務を抱え込まない
- `planning_gate_enabled=true` かつ `planning_gate_status != ready` のまま初稿を書き始めない
- 文字数不足のまま完成扱いにしない
- `runtime/scene_brief_compact.md` の `Length Band` があるのに、旧固定値だけで自己判定しない
- 毎回フル文脈を読み直してクレジットを無駄に消費しない
- `needs_expand=true` なのに全面再生成へ戻らない

