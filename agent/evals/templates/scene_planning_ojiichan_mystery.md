# Eval Template: `scene_planning` on `ojiichan_mystery`

## Goal

`agent/skills/scene-planner/SKILL.md` が、本文を書かずに「次に書ける粒度の段取り」を返せるかを評価する。

このテンプレートは、**段取りの実務性** と **責務逸脱の有無** を見る。

## Baseline Project

- Project: `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery`

## Why This Case Works

- `memory/05_chapter_outline_100k.md` に第2章のシーン設計があり、段取り素材として使える
- `runtime/scene_brief_compact.md` が存在し、第2章シーン2の圧縮文脈が使える
- 既に本文が存在する案件なので、「本文へ流れすぎる」「改稿へ流れすぎる」逸脱を見やすい
- `scene_planning` の責務である「次に書く対象を 1 つに絞る」と、「Read First を 3 件以内で絞る」を評価しやすい

## Case A: Planning Discipline Check

### User Request

```md
## Purpose
第2章の段取りを、いま書き始められる粒度まで固めたい

## Deliverables
- 出力: 次に書くべきシーンの段取り
- 出力: 直近で読むべきファイル

## Required Context
- 対象プロジェクト: C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery
- 対象章: 第2章

## Focus
- 目的
- 衝突
- 見せる情報
- 次へのフック
```

### Expected Read Sources

- `ojiichan_mystery/runtime/scene_brief_compact.md`（`Write Next` を 2-2 に寄せる場合）
- `ojiichan_mystery/memory/05_chapter_outline_100k.md`
- 再整理対象の既存シーン `txt`、または接続確認用の直前シーン `txt`
- `ojiichan_mystery/memory/global_notes.md` は、上記で不足する場合のみ

### Pass Conditions

- 章全体ではなく、直近で書く 1 シーンへ収束している
- 各項目が「目的 / 衝突 / 見せる情報 / 次フック」の粒度で整理されている
- 本文初稿を書き始めていない
- `Write Next` を 1 シーンに絞っている
- `Read First` が具体的で、3 件以内に収まっている
- `Read First` が、おおむね `runtime` → 章アウトライン → 対象 / 直前シーン → `global_notes` の優先順に沿っている

### Acceptable `Write Next`

以下のいずれかなら pass 寄り。

- 第2章シーン1
- 第2章シーン2

重要なのは「妥当な 1 シーンに絞れていること」であり、必ずしも同じシーン番号でなくてよい。

### Fail Triggers

- 章全体の再設計や設定再構築に広がる
- 本文の地の文や会話を書き始める
- `Write Next` が複数候補のまま終わる
- `Read First` が抽象的すぎる、または 4 件以上になる
- `agent/skills/revision-editor/SKILL.md` や `agent/skills/consistency-auditor/SKILL.md` の責務を混ぜる

## Review Sheet

5 点満点で採点する。

1. `Scope Control`
   - 必要範囲だけに絞れているか
2. `Execution Readiness`
   - そのまま執筆に入れる粒度か
3. `Handoff Quality`
   - `Write Next` と `Read First` が明確か
4. `Role Discipline`
   - 本文生成、監査、改稿へ逸脱していないか

## Improvement Rule

- 1 回の改善で直す論点は 1 つだけ
- 同じ Case A を再実行し、改善前後を比較する
- まず直すべき論点は、`Role Discipline` と `Handoff Quality` の低得点箇所
- 第 2 ループでは、特に `Read First` の選定順と件数制御を見る

