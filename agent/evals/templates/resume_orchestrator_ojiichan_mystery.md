# Eval Template: `resume_orchestrator` on `ojiichan_mystery`

## Goal

`agent/skills/resume-orchestrator/SKILL.md` が、古い `state` を鵜呑みにせず、実ファイルの現況から再開地点を立て直せるかを評価する。

このテンプレートは、**本文品質** ではなく、**再開判断の正確さと責務遵守** を見る。

## Baseline Project

- Project: `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery`

## Why This Case Works

- `state_schema_novel.yaml` では `current_mode: setting_creation` だが、`chapters/` には chapter 1-6 の本文ファイルが存在する
- `runtime/resume_brief.md` が存在するため、`runtime-first` の再開判断と、古い `state` の無視が両方試せる
- 実ファイルを見れば、少なくとも「初期設定だけの状態ではない」と判断できる

## Case A: Stale State Recovery

### User Request

```md
## Purpose
どこから再開すべきか整理したい

## Deliverables
- 出力: 現在地の要約
- 出力: 次に着手すべき作業

## Required Context
- 対象プロジェクト: C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery

## Context
- しばらく止まっていたので、今の状態を見て次の一手を決めたい
```

### Expected Read Sources

- `ojiichan_mystery/runtime/resume_brief.md`
- `ojiichan_mystery/runtime/request_compact.md`
- 必要なら `ojiichan_mystery/chapters/`
- `runtime/` が古い、欠落、または対象不一致のときのみ `ojiichan_mystery/state_schema_novel.yaml`

### Pass Conditions

- `runtime/resume_brief.md` が使える場合はそれを優先し、必要時のみ広い文脈へフォールバックしている
- `runtime/resume_brief.md` が対象一致でも、「着手前」なのに同じ対象シーンの本文や検査結果がある場合は stale と判断できている
- 更新時刻は補助根拠として使うが、時刻だけで stale を断定していない
- `Current Position` の文言（例: `準備段階`）を、未着手 / 完了 / 監査寄りの状態として一貫して読めている
- `Open Items` / `Next Actions` の語彙（例: `確定する` / `進む`）も、未着手 / 監査寄りの根拠として一貫して読めている
- `Read First` と `Next Actions` が、同じ作業モードを指しているかを確認し、整合したまま古いスナップショットも stale 根拠として扱えている
- `Recommended Skill` と最終 `Read First` が、同じ直近タスクを支える組み合わせになっている
- `Recommended Skill` ごとの `Read First` が、監査 / 改稿 / 段取り / 執筆で過不足なく切り替わっている
- `state_schema_novel.yaml` の `setting_creation` をそのまま採用せず、実ファイルや `runtime` と矛盾する可能性に触れている
- `chapters/` または `runtime` の内容を前提に、「すでに本文がかなり進んでいる」ことを反映している
- `Next Action` を 1 つに絞っている
- `Recommended Skill` を 1 つに絞っている
- `Read First` が具体的で、3 件以内に収まっている
- `Recommended Skill` に、なぜその工程を選ぶかの根拠がある

### Acceptable `Recommended Skill`

以下のいずれかなら pass 寄り。

- `agent/skills/consistency-auditor/SKILL.md`
- `agent/skills/scene-planner/SKILL.md`
- `agent/skills/revision-editor/SKILL.md`

`agent/skills/setting-creator/SKILL.md` を推す場合は、**state の古さを明示した上で、なぜ再度設定整理が必要か** を説明できていないと fail 寄り。

### Fail Triggers

- `state_schema_novel.yaml` を見ただけで「設定構築から再開」と断定する
- 実ファイルの存在に触れない
- 次アクションが複数候補のまま終わる
- `Recommended Skill` を複数列挙して丸投げする
- いきなり本文執筆に入る

## Review Sheet

5 点満点で採点する。

1. `State Reconstruction`
   - 実ファイルを基準に現在地を再構築できたか
2. `File Grounding`
   - 根拠が `state` だけでなく `chapters/` や `memory/` に基づいているか
3. `Action Selection`
   - 次アクションと推奨スキルが 1 つに絞れているか
4. `Output Discipline`
   - `Current Position` / `Open Items` / `Next Action` / `Recommended Skill` / `Read First` の順が守られているか

## Improvement Rule

- 1 回の改善で直す論点は 1 つだけ
- 同じ Case A を再実行し、改善前後を比較する
- まず直すべき論点は、`State Reconstruction` が 3 点未満の箇所
- 第 2 ループでは、特に `Recommended Skill` の選定根拠を見る

