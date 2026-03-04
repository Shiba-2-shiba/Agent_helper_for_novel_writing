# Refactor Plan

## Phase 1: Fix Operating Rules

### Goal

後続の変更がぶれないよう、先に共通ルールを固定する。

### Tasks

1. 本文の正本をシーン単位 `txt` に統一する。
2. `body.md` を通常本文の集約先から外す。
3. 文字数契約を `2000-2500` に統一する（当時の計画。現行は `1000-1500`）。
4. セッション記憶を Agent アプリ前提の保持方針に切り替える。
5. 各情報の正本を定義する。

### Files

- `agent/refactor_proposal.md`
- `agent/memory/global_notes.md`
- `agent/state_schema_novel.yaml`
- `agent/compaction_policy.md`

---

## Phase 2: Rebuild Routing

### Goal

`HUB.md` を、実運用の作業タイプに合うルータへ拡張する。

### Tasks

1. スキル分類を 3 つから 7 つへ拡張する。
2. 各スキルの発動条件を具体化する。
3. 曖昧依頼時の優先順位を明記する。
4. スキル間のハンドオフ条件を定義する。

### Files

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`

---

## Phase 3: Refactor Skill Docs

### Goal

スキル責務を分離し、全スキルを同じ運用形式に揃える。

### Tasks

1. 既存スキルの責務を整理する。
2. `SKILL_novel.md` を新規執筆専用へ絞る。
3. 改稿、監査、仕上げ、再開の新スキルを追加する。
4. 共通の記述項目を揃える。

### Files

- `agent/skills/SKILL_idea_generation.md`
- `agent/skills/SKILL_setting_creation.md`
- `agent/skills/SKILL_novel.md`
- `agent/skills/SKILL_revision.md`
- `agent/skills/SKILL_consistency_audit.md`
- `agent/skills/SKILL_polish.md`
- `agent/skills/SKILL_resume_orchestrator.md`

---

## Phase 4: Update User Input and Quality Controls

### Goal

依頼の解像度と、成果物の自己評価品質を上げる。

### Tasks

1. 依頼テンプレートを用途別に再構成する。
2. 執筆、改稿、監査向けの入力項目を整理する。
3. 評価観点を小説向けに拡張する。
4. リトライ条件を明文化する。

### Files

- `agent/request_template.md`
- `agent/evals/README.md`

---

## Phase 5: Sync Guide and Logs

### Goal

ガイドとログを、新しい運用モデルに合わせて同期する。

### Tasks

1. `AGENT_GUIDE.md` の読み順と責務説明を更新する。
2. 重要な設計判断を `decisions_log.md` に記録する。
3. 今回のドキュメント変更を `change_log.md` に記録する。

### Files

- `agent/AGENT_GUIDE.md`
- `agent/decisions_log.md`
- `agent/change_log.md`

---

## Validation Pass

### Checkpoints

- `HUB.md` から新しいスキルが選べる
- `SKILL_novel.md` が `body.md` 前提で動かない
- 文字数契約が全体で `2000-2500`（当時。現行は `1000-1500`）
- `session_notes.md` の方針が Agent アプリ向けに更新されている
- 依頼テンプレートが、改稿や監査を扱える
- 評価系が、視点・文体・連続性を検査できる

---

## Phase 6: Current Operations Hardening

### Goal

現行のエージェント運用を、今後の通常利用で崩れにくい状態まで磨き込む。

### Tasks

1. 現行のルーティングで曖昧依頼が誤分岐しないかを詰める。
2. `SKILL_novel` / `SKILL_revision` / `SKILL_consistency_audit` の境界が実運用で迷わないか確認する。
3. `state_schema_novel.yaml` を現行運用の正本として使いやすい形に再設計する。
4. `session_notes.md` と `session_archive.md` の運用が実務上ちょうどよい粒度か見直す。
5. テンプレートと eval の観点が、実際の依頼とレビューで不足なく機能するかを追加検証する。

### Current Focus

- 新規または現行運用中の案件全般
- 旧案件対応は、必要時のみ補助的に実施する

### Recommended First Pass

1. `HUB.md` の曖昧依頼判定見直し
2. `state_schema_novel.yaml` の項目整理
3. `evals/README.md` の実運用観点の追加調整
4. `request_template.md` の入力粒度調整

### Deliverables

- 現行運用の最終判断基準
- 運用上よくある依頼のルーティング補強
- state / memory / eval の追加調整案

---

## Legacy Projects (Low Priority)

- 旧案件移行は、必要時のみ `legacy_project_migration.md` を参照して対処する
- ただし、今後の主要ブラッシュアップ対象ではない
