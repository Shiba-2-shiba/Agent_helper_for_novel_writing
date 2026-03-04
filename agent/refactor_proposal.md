# Refactor Proposal

## Purpose

エージェント構成を、現在の実運用に合わせて再編する。
主目的は、ルーティング精度の向上、スキル責務の分離、運用ルールの一貫化、長編小説の継続品質の安定化。

---

## Fixed Decisions

### 1. 本文ファイルの正本

- 各シーンの正本は、シーン単位の `txt` ファイルとする。
- 通常運用では `body.md` に本文を追記しない。
- `body.md` は、章の方針メモ、章サマリ、または大幅改稿時の再設計メモとして扱う。
- `body.md` を更新するのは、章の方向性変更、構成再設計、要約の差し替えが必要な場合のみとする。

### 2. 文字数契約

- 当時の案では、1シーンの文字数契約を `2000-2500` に統一する。
- 現行標準は `1000-1500` へ更新済み。
- 当時の推奨内部運用値は以下。
- `min_chars = 2000`
- `target_chars = 2300`
- `max_chars = 2500`

### 3. セッション記憶方針

- Local LLM 前提の強圧縮をやめ、Agent アプリ前提の再開品質重視へ切り替える。
- ただし、無制限に履歴を積むのではなく、品質に効く文脈を優先保持する。
- 直近の詳細、過去の要約、永続ルールの分離を徹底する。

### 4. リファクタリング対象

- `HUB.md`
- `AGENT_GUIDE.md`
- `skills/SKILL_*.md`
- `compaction_policy.md`
- `request_template.md`
- `evals/README.md`
- `memory/global_notes.md`
- `state_schema_novel.yaml`

---

## Target Operating Model

### Skill Layers

- 企画: アイディア出しとログライン確定
- 設定: 設定構築とプロット整備
- 執筆: 新規シーンの初稿作成
- 改稿: 既存シーンのリライト
- 監査: 整合性、矛盾、弱点の診断
- 仕上げ: 文体調整、密度調整、読後感の改善
- 再開管理: 次回作業への復帰と進捗整理

### Shared Principles

- 正本は 1 つに寄せる
- スキル責務は混ぜない
- 曖昧依頼でも HUB から安全に分岐できるようにする
- 文体契約、文字数契約、進捗管理は共通ルールで統一する
- 長編運用では、再開時の品質を犠牲にしない

---

## New Skill Structure

### Existing Skills To Retain

- `SKILL_idea_generation.md`
- `SKILL_setting_creation.md`
- `SKILL_novel.md`

### New Skills To Add

- `SKILL_revision.md`
- `SKILL_consistency_audit.md`
- `SKILL_polish.md`
- `SKILL_resume_orchestrator.md`

### Responsibility Split

- `SKILL_novel.md` は新規執筆専用に絞る
- 改稿は `SKILL_revision.md` に分離する
- 整合性診断は `SKILL_consistency_audit.md` に分離する
- 文体や密度の仕上げは `SKILL_polish.md` に分離する
- セッション再開時の着手判断は `SKILL_resume_orchestrator.md` に分離する

---

## Refactor Goals

### Routing

- `HUB.md` の 3 分類を、実運用に近い 7 分類へ拡張する
- スキル間の遷移条件を明文化する

### Consistency

- `body.md` の扱いを、全ファイルで同じ定義に揃える
- 文字数契約を、全ファイルで同じ数値に揃える
- セッション記憶の保持方針を、Agent アプリ前提に更新する

### Quality Control

- 小説向けの評価観点を追加する
- 依頼テンプレートを、作業タイプ別に再編する

### Current Operations Priority

- 旧案件移行は補助的なメンテナンスとして扱う
- 主軸は、現行運用でのルーティング精度、スキル境界、記憶品質、評価品質の向上に置く
- 新しい案件や今後の運用が迷わず回ることを優先する

---

## Success Criteria

- `HUB.md` だけで主要な依頼を誤ルーティングしにくい
- スキルごとの責務が明確で、改稿や監査を執筆スキルに混在させない
- `body.md` と `txt` の使い分けが明確
- 文字数契約が `2000-2500` に統一されている（当時の成功条件。現行は `1000-1500`）
- セッション再開時に、必要な文脈を失わずに作業を継続できる
- テンプレートと評価系が、現在の長編運用に追随している
