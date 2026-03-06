# Eval Template: Runtime-Ready Project Comparison

## Goal

`runtime/` がすでに整っている別案件で、`scene_planning` と `resume_orchestrator` の第2改善ループを横並びで比較する。

このテンプレートは、`ojiichan_mystery` 以外の案件が増えたときに、同じ観点で再現性を確認するための雛形。

## Project Requirements

以下を満たす案件を選ぶ。

- `runtime/resume_brief.md` がある
- `runtime/scene_brief_compact.md` がある
- `state_schema_novel.yaml` がある
- `chapters/` に少なくとも 2 シーン以上ある
- `memory/05_chapter_outline_100k.md` がある

## Case A: `scene_planning` Comparison

### User Request

```md
## Purpose
第<chapter>章の段取りを、いま書き始められる粒度まで固めたい

## Deliverables
- 出力: 次に書くべきシーンの段取り
- 出力: 直近で読むべきファイル

## Required Context
- 対象プロジェクト: <project_path>
- 対象章: 第<chapter>章

## Focus
- 目的
- 衝突
- 見せる情報
- 次へのフック
```

### Expected Read Sources

- `<project_path>/runtime/scene_brief_compact.md`
- `<project_path>/memory/05_chapter_outline_100k.md`
- 再整理対象の既存シーン `txt`、または接続確認用の直前シーン `txt`
- `global_notes.md` は、上記で足りない場合のみ
- `scene_brief_compact.md` の `Scene ID` が対象と不一致なら、`scene_brief` を stale として除外し、対象シーン `txt` と章アウトラインを優先する

### Pass Conditions

- `Write Next` が 1 シーンに絞れている
- 既存シーンがある章では、「再整理対象」を明示している
- 既存シーン複数時は、「情報不足シーン」選定の根拠を 1 行で示している
- `Read First` が 3 件以内
- `Read First` が、おおむね `runtime` → 章アウトライン → 対象 / 直前シーン → `global_notes` の優先順に沿う
- `scene_brief_compact.md` が stale の場合、`Read First` から外せている
- 本文初稿、改稿、監査へ責務逸脱していない

## Case B: `resume_orchestrator` Comparison

### User Request

```md
## Purpose
どこから再開すべきか整理したい

## Deliverables
- 出力: 現在地の要約
- 出力: 次に着手すべき作業

## Required Context
- 対象プロジェクト: <project_path>

## Context
- 少し止まっていたので、今の状態を見て次の一手を決めたい
```

### Expected Read Sources

- `<project_path>/runtime/resume_brief.md`
- `<project_path>/runtime/request_compact.md`
- 必要なら最新のシーン `txt`
- `runtime/` が古い、欠落、または対象不一致のときのみ `state_schema_novel.yaml`
- 必要なら `<project_path>/runtime/scene_brief_compact.md` と `<project_path>/runtime/check_report.json` を突き合わせて対象一致を確認する

### Pass Conditions

- `runtime/resume_brief.md` を先に確認している
- `runtime` より新しい本文や検査結果がある場合は、それを根拠に上書き判断できる
- `resume_brief` / `scene_brief` / `check_report` の対象が不一致な場合、stale 扱いで再生成判断できる
- `Next Action` を 1 つに絞っている
- `Recommended Skill` を 1 つに絞っている
- `Recommended Skill` に、未着手 / 改稿 / 監査 / 設定不足のどれが主問題かの根拠がある
- いきなり本文執筆に入らない

## Review Sheet

各ケースとも 5 点満点で採点する。

- `State / Scope Control`
- `File Grounding`
- `Action / Handoff Selection`
- `Output Discipline`

## Comparison Notes

- `ojiichan_mystery` と違い、`state` が新しい案件か、`runtime` が新しい案件かを明記する
- 差分は 1 回につき 1 論点だけ抽出する
- 結果ファイルは、`agent/evals/results/<skill>_<project_name>_<date>.md` の形で保存する
