# Agent Guide (Common)

このフォルダは全プロジェクト共通のベースです。
`compose_agent_package.py` によって `<project>/agent/` としてセットアップされます。

---

## Agent が最初に読む順番

1. **HUB.md** — ユーザーの依頼から、どのスキルを呼び出すべきかのルーティングを確認する（※最重要）
2. **このファイル（AGENT_GUIDE.md）** — 全体像を把握する
3. **personality.md** — アクティブなパーソナリティを確認する
4. **decision_rules.md** — 行動制約と安全ルールを確認する
5. **state_schema_*.yaml** — プロジェクト固有の状態・制約・進捗を確認する
6. **memory/global_notes.md** — このプロジェクト固有の不変情報を確認する
7. **memory/session_notes.md** — 直近セッションの引き継ぎ事項を確認する
8. **skills/<skill-name>/SKILL.md** — 今のタスクに対応するスキル手順を確認する
9. **memory/session_archive.md**（存在する場合） — 古い経緯が必要なときだけ参照する
10. **skills/legacy/**（存在する場合） — 旧案件の移行や互換確認が必要なときだけ参照する

---

## 各ファイルの役割

| ファイル | 役割 | 更新タイミング |
|----------|------|----------------|
| `personality.md` | Agentの応答スタイル定義 | プロジェクト開始時に1回 |
| `decision_rules.md` | 行動の判断基準・安全ルール | 変更時のみ |
| `state_schema_*.yaml` | プロジェクト固有の可変状態の正本（進捗・現在地・直近推奨アクション） | 状態変化時に更新 |
| `compaction_policy.md` | セッション記憶の圧縮ルール | 変更時のみ |
| `naming_conventions.md` | ファイル・フォルダ名のルール | 変更時のみ |
| `request_template.md` | 依頼を構造化するテンプレート | 依頼のたびに参照 |
| `memory/global_notes.md` | プロジェクト全体の不変情報 | 重要決定時に更新 |
| `memory/session_notes.md` | 直近再開のための作業メモ | セッションごとに更新・整理 |
| `memory/session_archive.md` | 古いセッションの詳細履歴 | 必要時に追記 |
| `decisions_log.md` | 重要な判断の履歴 | 重要決定のたびに追記 |
| `change_log.md` | ファイル変更の履歴 | 変更のたびに追記 |
| `evals/` | スキル出力品質の検証プロンプト | evalを実行するとき参照 |
| `skills/<skill-name>/SKILL.md` | カタログ固有のスキル手順（企画・初期化・設定・段取り・執筆・改稿・監査・推敲・再開） | タスク開始時に参照 |

---

## セッション開始・終了のチェックリスト

### セッション開始時
- [ ] `state_schema_*.yaml` の進捗と文字数契約を確認
- [ ] `global_notes.md` の文体契約と不変制約を確認
- [ ] `session_notes.md` の次回着手点と未解決事項を確認
- [ ] 今のタスクに対応する `skills/<skill-name>/SKILL.md` を確認

### セッション終了時
- [ ] `session_notes.md` を `compaction_policy.md` のルールに従って整理
- [ ] 重要な決定があれば `decisions_log.md` に追記
- [ ] ファイルを変更した場合は `change_log.md` に追記

---

## Current Operating Rules

- 通常運用では、本文の正本はシーン単位 `txt` ファイルとする
- `body.md` は本文の追記先ではなく、章方針メモまたは大幅改稿時の補助ファイルとして扱う
- 1 シーンの文字数契約は原則 `1000-1500`
- 文字数不足の補完は、全文再生成ではなく局所差分ブロックを優先し、必要なら `scripts/apply_expand_edits.py` で反映する
- `session_notes.md` は再開品質重視で運用し、古い詳細は必要に応じて `session_archive.md` へ退避する
- `state_schema_*.yaml` は、特定作品の固定サンプルではなく、案件ごとの「現在地」と「次に何をするか」を持つ

## Canonical Mode Names

`request_template.md` の `Mode` と `state_schema_*.yaml` の `active_work.current_mode` は、`HUB.md` の「正式モード名（正本）」に揃える。

---

## Selected Catalogs
- novel

