# Skill Refactor Specification for Codex / antigravity

- Status: Completed (Phase 0-6 passed)
- Last Updated: 2026-03-05 (Phase 6 completion)
- Target Repository: `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main`
- Scope: `agent/skills` と関連ルーティング文書

## 1. 目的

本仕様は、現在の小説支援スキル群を壊さずに段階移行し、以下を同時に満たすための実行計画を定義する。

1. Agent Skills 標準に近い構成へ寄せる
2. Codex / antigravity での運用互換性を高める
3. 既存の運用導線（`HUB.md` 中心のルーティング）を維持しながら移行する
4. Phase ごとに検証ゲートを通過しない限り先へ進まない

## 2. 非目的

1. 小説本文生成ロジックそのものの刷新
2. `scripts/` の大規模改修
3. 1 回の作業で全スキルを完全再設計すること

## 3. 現状課題（要約）

1. スキル配置が `agent/skills/SKILL_*.md` のフラット構成で、標準的な `skill-name/SKILL.md` と差異がある
2. Frontmatter に `version` が含まれ、最小互換運用時に差異が出る可能性がある
3. `description` が英語中心で、日本語入力時のトリガー最適化余地がある
4. eval の実績が一部スキルに偏っている

## 4. 設計原則

1. Compatibility First: 既存導線を残したまま段階移行する
2. Small Batch: 1 Phase 1 論点で変更を閉じる
3. Gate Driven: 構造検証と動作検証を通過しない限り次へ進まない
4. Reversible: 各 Phase で明確なロールバック手段を持つ
5. Router-Centric: `agent/HUB.md` を最終的な起点として整合させる

## 5. 対象ファイル群

### 5.1 直接対象

1. `agent/skills/SKILL_*.md`
2. `agent/HUB.md`
3. `agent/AGENT_GUIDE.md`
4. `agent/evals/README.md`

### 5.2 参照対象

1. `agent/decisions_log.md`
2. `agent/change_log.md`
3. `agent/refactor_handoff_2026-03-04.md`

## 6. ゴール構成（最終状態）

`agent/skills` 配下を以下へ段階移行する。

```text
agent/skills/
  consistency-auditor/
    SKILL.md
  idea-generator/
    SKILL.md
  novel-writer/
    SKILL.md
  prose-polisher/
    SKILL.md
  project-bootstrap/
    SKILL.md
  resume-orchestrator/
    SKILL.md
  revision-editor/
    SKILL.md
  scene-planner/
    SKILL.md
  setting-creator/
    SKILL.md
  legacy/
    SKILL_consistency_audit.md
    SKILL_idea_generation.md
    SKILL_novel.md
    SKILL_polish.md
    SKILL_project_bootstrap.md
    SKILL_resume_orchestrator.md
    SKILL_revision.md
    SKILL_scene_planning.md
    SKILL_setting_creation.md
    SKILL_planner.md
```

注記:
1. `legacy/` 側は移行期間中の互換レイヤとして維持する
2. 最終的に `HUB.md` は新パスを正本として参照する

## 7. Phase 実行計画

## Phase 0: Baseline 固定

### 目的

現状を固定し、以降の比較基準を作る。

### 実施内容

1. 現在の `agent/skills` 一覧をスナップショット化
2. 現行のスモークプロンプトセットを固定
3. `decisions_log.md` に「移行開始」エントリを追加

### 検証ゲート

1. 現行9スキルのファイル存在確認
2. `HUB.md` のマッピングと実ファイルの一致確認
3. スモークテスト結果を保存（比較用）

### ロールバック

1. この Phase は読み取り中心のため、失敗時は記録を破棄して再採取

### Exit 条件

1. Baseline 記録が1セット揃っていること

## Phase 1: 標準構造の追加（非破壊）

### 目的

既存構成を残したまま、`skill-name/SKILL.md` を新規併設する。

### 実施内容

1. 9スキル分の新ディレクトリを作成
2. 既存 `SKILL_*.md` の内容を `skill-name/SKILL.md` に移植
3. まだ `HUB.md` は旧パス参照のまま据え置く

### 検証ゲート

1. 新旧で `name` と `description` が一致
2. 新規 `SKILL.md` の YAML パースが通る
3. 旧パス参照での既存運用が壊れていない

### ロールバック

1. 追加した新ディレクトリのみ削除して復元可能

### Exit 条件

1. 新旧2系統が併存し、旧導線動作が維持されること

## Phase 2: Frontmatter 正規化

### 目的

新系統 `SKILL.md` を最小互換形（`name`, `description`）へ統一する。

### 実施内容

1. 新系統 `SKILL.md` から `version` を frontmatter から外す
2. バージョン管理が必要な場合は本文末尾へ `Skill Version Note` として移す
3. `description` に日本語トリガーフレーズを追加し、日英両対応化する

### 検証ゲート

1. 全新規 `SKILL.md` が `name`, `description` のみを frontmatter に持つ
2. `description` 1024文字以下
3. 手動トリガー評価で誤発火/未発火が許容範囲内

### ロールバック

1. 各 `SKILL.md` を Phase 1 版へ戻せること

### Exit 条件

1. 新規9スキルすべてが frontmatter 正規化済み

## Phase 3: ルータ切替

### 目的

`HUB.md` と `AGENT_GUIDE.md` の正本参照先を新構造へ切替える。

### 実施内容

1. `HUB.md` の対象パスを `agent/skills/<skill-name>/SKILL.md` へ更新
2. `AGENT_GUIDE.md` の説明を新構造へ更新
3. 旧 `SKILL_*.md` は `legacy/` へ移動し、移行案内テキストに変更

### 検証ゲート

1. `HUB.md` の全リンク先が存在する
2. 旧ファイルを直接読んでも新パスへ辿れる
3. 既存の主要ユースケースで推奨スキル選定が変わらない

### ロールバック

1. `HUB.md` と `AGENT_GUIDE.md` を旧参照へ戻す
2. `legacy/` 移動分を元位置へ戻す

### Exit 条件

1. 新構造が正本であることが文書とファイル構成で一致

## Phase 4: Trigger QA 拡張

### 目的

各スキルの `description` で日本語依頼文を安定トリガーできる状態にする。

### 実施内容

1. 9スキル分の trigger eval セットを作成
2. 各スキルで should-trigger / should-not-trigger を最低8件ずつ用意
3. 近接語彙の誤爆ケースを追加

### 検証ゲート

1. should-trigger 再現率の下限を満たす
2. should-not-trigger 誤発火率が上限以下
3. 競合スキル間の境界ケースで優先ルールが説明可能

### ロールバック

1. 直前の `description` セットへ一括復帰

### Exit 条件

1. trigger レポートが9スキル分揃う

## Phase 5: Evals カバレッジ標準化

### 目的

`resume_orchestrator` / `scene_planning` 偏重を解消し、全スキルで最低限の回帰確認を可能にする。

### 実施内容

1. `agent/evals/prompts/` にスキル別最小ケースを追加
2. `agent/evals/README.md` に実行手順と合格基準を追記
3. `agent/evals/results/` に初回基準結果を残す

### 検証ゲート

1. 9スキルすべてに最低1件の回帰ケースがある
2. 結果記録フォーマットが統一されている
3. Fail Trigger が再現可能な形で記録されている

### ロールバック

1. 追加 eval のみ戻し、既存 eval を維持

### Exit 条件

1. 全スキルの最低回帰ラインが可視化される

## Phase 6: 移行完了判定

### 目的

最終運用に必要な文書整合、導線整合、評価整合を確定する。

### 実施内容

1. `decisions_log.md` に完了判断を追記
2. `change_log.md` に変更履歴を集約
3. 別チャット運用向けの「再開プロンプト雛形」を固定

### 検証ゲート

1. 主要ドキュメントの参照切れゼロ
2. 主要9スキルのルーティング説明が矛盾なし
3. rollback 手順が文書化済み

### ロールバック

1. Phase 3 完了時点のタグまたはコミットへ戻す

### Exit 条件

1. 「新構造が正本」かつ「旧構造が補助」で運用可能

## 8. フェーズ間共通ゲート

各 Phase の終了時に必ず以下を満たす。

1. Structural Gate: ファイル存在、frontmatter、参照整合
2. Routing Gate: `HUB.md` の選定ロジック整合
3. Behavior Gate: 主要ユースケースの期待挙動維持
4. Documentation Gate: 変更理由と戻し方が記録済み

## 9. 検証マトリクス（最小）

最低1ケースずつ、以下を毎 Phase で抽出実行する。

1. Idea: 「新しい小説案を出したい」→ `idea-generator`
2. Bootstrap: 「このログラインで案件作成」→ `project-bootstrap`
3. Setting: 「設定矛盾を解消したい」→ `setting-creator`
4. Scene Plan: 「次の2シーン段取り」→ `scene-planner`
5. Draft: 「第X章Yシーンを書いて」→ `novel-writer`
6. Revision: 「このシーンを改稿」→ `revision-editor`
7. Audit: 「矛盾チェックして」→ `consistency-auditor`
8. Polish: 「文体を整えて」→ `prose-polisher`
9. Resume: 「どこから再開すべき？」→ `resume-orchestrator`

## 10. 別チャットでの実行プロトコル

### 10.1 開始時の入力テンプレート

以下を最初に貼る。

```text
このチャットでは skill_refactor_spec_codex_antigravity.md に従って、
Phase N のみ実行してください。
変更は Phase N の範囲に限定し、終了時に以下を報告してください。
1) 変更ファイル一覧
2) 実施した検証
3) 未解決リスク
4) 次 Phase に進めるかの判定
```

### 10.2 1 Phase の完了報告フォーマット

```text
[Phase]
[Changed Files]
[Validation Result]
[Known Risks]
[Rollback Plan]
[Go/No-Go]
```

### 10.3 停止条件（No-Go）

以下のいずれかを満たしたら次 Phase へ進まない。

1. `HUB.md` の参照切れが1件でもある
2. 主要9ケースのうち1件でも期待スキルに到達しない
3. rollback 手順がその Phase で成立しない

## 11. 受け入れ基準（Definition of Done）

1. 新構造 `skill-name/SKILL.md` が正本として稼働
2. `legacy/` は互換レイヤとして明示管理
3. frontmatter は `name`, `description` 中心で統一
4. 9スキル分の trigger/eval 基本セットが存在
5. 別チャットで Phase 指定実行が可能な運用文書が揃っている

## 12. リスク一覧

1. ルーティング破壊リスク
2. 日本語トリガー過剰化による誤発火
3. ドキュメント更新漏れによる参照不整合
4. legacy 撤去タイミングの早すぎ問題

## 13. 推奨実行順

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6

各 Phase は「Gate pass の確認後」にのみ次へ進むこと。

## 14. Completion Record (2026-03-05)

1. Phase 0-6 のゲート確認はすべて pass
2. 完了報告: `agent/skill_refactor_phase6_completion_2026-03-05.md`
3. ロールバック手順: `agent/skill_refactor_rollback_runbook.md`
4. 評価スイート結果: `agent/evals/results/skill_eval_suite_report_2026-03-05.md`
5. 最終ハンドオフ: `agent/skill_refactor_handoff_final_2026-03-05.md`
