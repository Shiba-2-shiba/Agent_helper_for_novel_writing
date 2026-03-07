# Legacy Project Migration Policy

## Purpose

旧運用で進んでいる小説プロジェクトを、新しいエージェント運用へ安全に接続するための判断基準を定義する。

## Priority

- このドキュメントは補助用です
- 今後の主軸は現行運用のブラッシュアップであり、旧案件移行は必要時のみ参照します

---

## What Counts As Legacy

以下のいずれかに該当する場合、その案件は旧運用案件として扱う。

- 文字数契約が `1800-3200` など旧基準のまま
- `body.md` を本文集約前提で運用していた
- `00_restart_plan.md` の Backlog と実ファイルの扱いが新ルールと一致しない
- 改稿、監査、執筆の責務分離前のログが主な運用履歴になっている

---

## Source-Of-Truth Order For Legacy Projects

旧案件では、正本を以下の順で判断する。

1. 実在するシーン `txt` ファイル
2. 再開計画や Backlog (`00_restart_plan.md`, `99_progress_checkpoint.md` など)
3. `body.md`
4. 古いセッションメモ

理由:

- 旧案件では Backlog が古いまま残ることがある
- `body.md` は本文集約されていても、更新漏れや旧テンプレのままの可能性がある
- 実ファイルが最も信頼できる

---

## Length Contract Migration Rules

### Keep Legacy Contract Temporarily

以下に当てはまる場合は、旧文字数契約をいったん据え置いてよい。

- 章の終盤まで完成稿が進んでいる
- 旧基準で完結済みの章を大きく壊したくない
- まずは構造や整合性の確認が優先

### Migrate To New Contract

以下に当てはまる場合は、新標準 `1000-1500` へ寄せる。

- まだドラフト段階で確定していない
- これから大幅改稿する
- 章単位で再設計する
- 文字数超過がテンポを悪化させている

### Practical Rule

- 既存完成稿は「直ちに全件一括修正」しない
- まずは高影響シーンだけを選んで部分移行する

---

## Migration Workflow

1. `SKILL_resume_orchestrator` で現在地確認
2. `SKILL_consistency_audit` で高影響箇所を特定
3. `SKILL_revision` で優先シーンを修正
4. 必要なら `SKILL_polish` で文体と密度を整える
5. Backlog や計画書の状態を実態に合わせる

---

## Pilot: modern_isekai_40

### Project

- `C:\Users\inott\Downloads\MedicalResearchAgent\modern_isekai_40`

### Current Assessment

- Chapter 5 のシーンファイルは実在する
- したがって、即時の課題は「未生成」ではなく、「Backlog 状態の古さ」と「終盤シーンの過密」
- 旧文字数契約は残っているため、新標準への移行は段階的に行うのが妥当

### Migration Decision

- 方針: 部分移行
- 旧契約の全件即時修正はしない
- 高影響のシーンのみ、新標準に寄せながら改稿する

### First Revision Target

- `chapter_5_scene_4_restart.txt`

理由:

- 実質的に終幕だが、Backlog 上はドラフト扱い
- クライマックス、余波、エピローグが 1 シーンに過密
- 新標準 `1000-1500` からの乖離が大きい

### Deferred Target

- `chapter_2_scene_1_restart.txt`

理由:

- 旧ドラフトの取りこぼしだが、Chapter 5 の終盤整理より優先度は下

---

## Reusable Record For Other Legacy Projects

他の旧案件でも、まず以下だけを確認する。

- 実ファイルは揃っているか
- Backlog 状態は古くないか
- 文字数契約は旧基準か新基準か
- まず手を入れるべきシーンはどこか

この 4 点を短く記録できれば、横展開しやすい。
