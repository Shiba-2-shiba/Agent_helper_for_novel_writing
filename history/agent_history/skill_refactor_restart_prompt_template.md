# Skill Refactor Restart Prompt Template

## 実行用（Phase 0-5）

このチャットでは `skill_refactor_spec_codex_antigravity.md` に従って、Phase N のみ実行してください。  
変更は Phase N の範囲に限定し、終了時に以下を報告してください。

1. 変更ファイル一覧
2. 実施した検証
3. 未解決リスク
4. 次 Phase に進めるかの判定

報告フォーマット:

```text
[Phase]
[Changed Files]
[Validation Result]
[Known Risks]
[Rollback Plan]
[Go/No-Go]
```

## 完了判定用（Phase 6）

このチャットでは `skill_refactor_spec_codex_antigravity.md` の Phase 6 完了判定だけ実行してください。  
以下を必ず確認して報告してください。

1. 主要文書の参照切れがゼロか
2. `agent/HUB.md` の9スキル導線に矛盾がないか
3. `agent/evals/results/skill_eval_suite_report_2026-03-05.json` が pass か
4. rollback 手順が `agent/skill_refactor_rollback_runbook.md` に明記されているか

完了済み案件を再開する場合は、最初に
`agent/skill_refactor_handoff_final_2026-03-05.md` を参照してください。
