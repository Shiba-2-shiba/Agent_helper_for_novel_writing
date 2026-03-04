---
name: novel-writer
description: Draft new scene prose for an existing novel project. Use when the user wants a fresh scene or continuation written, not when they mainly want diagnosis, revision, or polish.
version: 0.5
---

# Purpose

既存プロジェクトの文脈に沿って、`runtime-first` で新しいシーンの初稿を作成する。

# Read First

- `agent/HUB.md`
- 対象プロジェクトの `runtime/draft_prompt.txt`（あれば最優先）
- `runtime/draft_prompt.txt` がない場合は `runtime/style_contract_compact.md`
- `runtime/scene_brief_compact.md`
- `runtime/continuity_pack.md`
- `runtime/request_compact.md`
- `runtime/` に不足がある場合のみ `agent/state_schema_novel.yaml`
- `runtime/` に不足がある場合のみ `agent/memory/global_notes.md`
- `runtime/` に不足がある場合のみ対象章の `05_chapter_outline_100k.md` 該当箇所
- `runtime/` に不足がある場合のみ直前シーンの `txt`
- `body.md` は章の方向転換があった場合のみ補助的に参照する

# Required Inputs

- `project_path`
- `chapter`
- `scene`
- 必要なら `length_contract`
- 必要なら既存の対象シーン `txt` の有無

# Procedure

## 1. `runtime/` を準備する

- 対象シーンの `runtime/draft_prompt.txt` があり、対象の `chapter` / `scene` と矛盾しないなら再利用する
- `runtime/draft_prompt.txt` がない、または `runtime/` の必須ファイルが欠けている場合は、先に以下を実行して更新する
- `python scripts/build_runtime_context.py --project <project_path> --chapter <chapter> --scene <scene> --mode draft`
- `python scripts/build_draft_prompt.py --project <project_path>`
- `runtime/` が使えない場合のみ、従来の広い文脈参照へフォールバックする

## 2. 文脈を集める

- まず `runtime/draft_prompt.txt` を読み、そこに含まれる制約を優先する
- `runtime/draft_prompt.txt` がなければ、`runtime/style_contract_compact.md`、`runtime/scene_brief_compact.md`、`runtime/continuity_pack.md`、`runtime/request_compact.md` を読む
- `runtime/` に不足がある場合のみ、対象シーンの章プロット、文体契約、進捗を補助参照する
- `runtime/continuity_pack.md` を優先し、直前シーンの感情、位置関係、会話温度を引き継ぐ
- 章の方針変更がある場合のみ `body.md` を確認する

## 3. 初稿を書く

- 指定シーンの本文を新規に執筆する
- 1シーン `1000-1500` を守る
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

- 文字数が `1000-1500`
- 視点がぶれていない
- 主要キャラの口調が契約から外れていない
- シーンの目的が達成されている
- 本文中に見出し、箇条書き、メタ発言がない

基準を満たさない場合は、最大 3 回まで自律的に修正する。

## 5. 保存する

- 完成した本文は、対象シーンの `txt` ファイルへ保存する
- 通常運用では `body.md` を更新しない
- 拡張を行う場合でも、フル文脈の再読込ではなく `runtime/expand_prompt.txt` を優先し、局所差分だけを反映する

# Handoff

- 設定やプロットの前提変更が必要: `SKILL_setting_creation.md`
- 既存シーンの修正が主目的になった: `SKILL_revision.md`
- 診断が必要: `SKILL_consistency_audit.md`

# Outputs

- 新規シーン初稿
- `runtime/check_report.json` による文字数チェック結果
- 必要なら短い自己評価メモ

# Do Not

- 既存の `body.md` を本文集約先として使わない
- 改稿や監査の責務を抱え込まない
- 文字数不足のまま完成扱いにしない
- 毎回フル文脈を読み直してクレジットを無駄に消費しない
- `needs_expand=true` なのに全面再生成へ戻らない
