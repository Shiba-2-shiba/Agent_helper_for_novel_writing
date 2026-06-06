# Scene Pipeline Refactor Tasks

Date: 2026-06-06

## Goal

既存の `runtime-first` / VCC 型 context / ledger 基盤を活かし、日常運用に必要な統合 CLI、承認・export、義務契約、health check、反AI文体検査を段階的に追加する。

## Cleanup Plan

Behavior lock:

- [x] Baseline verification: `python -m pytest tests/ -q` -> `79 passed in 6.90s`
- [x] Final verification: `python -m pytest tests/ -q` -> `87 passed in 8.51s`

Smell/Gap categories:

- [x] Boundary gap: 個別 script は強いが、標準 scene flow の入口が分散している
- [x] Terminal-state gap: check 済み scene を承認・export する終端が薄い
- [x] Contract gap: scene の目的・依存・回収義務が writer/checker/repair で共通化されていない
- [x] Sync gap: runtime/state/summary/approval/outline の不整合を一括診断できない
- [x] Quality gap: AI っぽい文体劣化の deterministic warning が不足している

## Phase 0: Behavior Lock

- [x] `python -m pytest tests/ -q` を実行する
- [x] baseline result を progress md に記録する
- [x] 既存 VCC/context/ledger 基盤が入っていることを確認する
- [x] 実装対象 1-5 を spec に固定する

## Phase 1: Thin Integrated CLI / Orchestrator

- [x] CLI 名を `run_scene_pipeline.py` に決める
- [x] CLI subcommands を定義する
- [x] `prepare` command を追加する
- [x] `prompt` command を追加する
- [x] `check` command を追加する
- [x] `repair` command を追加する
- [x] `approve` command を追加する
- [x] `export` command を追加する
- [x] `health` command を追加する
- [x] pipeline wrapper test を追加する
- [x] 既存 script 直接実行の互換 test を維持する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 2: Approval Gate and Export

- [x] `scripts/novel_agent/approvals.py` を作る
- [x] `approval_ledger_path()` を実装する
- [x] `read_approval_ledger()` を実装する
- [x] `write_approval_ledger()` を実装する
- [x] scene content hash helper は既存 ledger helper を再利用する
- [x] `approve_scene()` helper を実装する
- [x] `revoke_scene_approval()` helper を実装する
- [x] stale approval 判定を実装する
- [x] `scripts/approve_scene.py` を作る
- [x] `status=fail` は approve 不可にする
- [x] `status=warning` は `--allow-warnings` なしで approve 不可にする
- [x] `status=pass` は approve 可能にする
- [x] approval 時に `approved_at`, `approved_by`, `content_hash` を保存する
- [x] `scripts/novel_agent/exports.py` を作る
- [x] outline/scene metadata から export order を決める
- [x] approved scene だけを収集する
- [x] `scripts/export_manuscript.py` を作る
- [x] `exports/manuscript.md` を生成する
- [x] export 前に stale approval を検出する
- [x] `body.md` を本文 source にしない test を追加する
- [x] approve fail/warning/pass tests を追加する
- [x] export approved-only test を追加する
- [x] stale approval test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 3: Scene Obligation Contract

- [x] `scripts/novel_agent/obligations.py` を作る
- [x] scene ledger row から obligation payload を作る helper を実装する
- [x] `purpose` を `must_hit_now` 候補へ写す
- [x] `payoff_or_seed` を `required_payoff_touches` 候補へ写す
- [x] `depends_on` を `required_dependencies` へ写す
- [x] `build_runtime_context.py` が `obligation_contract.json` を出力する
- [x] `scene_brief_compact.md` に `## Obligation Contract` を追加する
- [x] dependency 欠落検出を `check_scene_output.py` へ接続する
- [x] `check_report.json` に `obligation_status` を追加する
- [x] `check_report.json` に `obligation_issues` を追加する
- [x] dependency 欠落を `blocking_issues` に反映する
- [x] obligation issue は expansion 対象にしないよう quality budget 判定に接続する
- [x] contract 生成 test を追加する
- [x] dependency blocking test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 4: Memory Sync / Project Health Check

- [x] `scripts/novel_agent/health.py` を作る
- [x] `health_report_path()` を実装する
- [x] health issue schema を定義する
- [x] outline existence check を実装する
- [x] scene txt readability check を実装する
- [x] approved scene hash check を実装する
- [x] stale scene summaries warning を実装する
- [x] story_state freshness warning を実装する
- [x] stale artifact warning を実装する
- [x] runtime_index mismatch warning を実装する
- [x] missing trace warning を実装する
- [x] token ledger summary info を実装する
- [x] quality budget exhausted scene count info を実装する
- [x] `--fix-safe` で scene_summaries を再生成する
- [x] `--fix-safe` で story_state を安全に初期化する
- [x] `--fix-safe` で trace views を再生成する
- [x] `scripts/sync_project_health.py` を作る
- [x] `--json` stdout を実装する
- [x] warning health test を追加する
- [x] fix-safe test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 5: Anti-AI Style Gate

- [x] `scripts/novel_agent/anti_ai_style.py` を作る
- [x] sentence split helper を実装する
- [x] paragraph length helper を実装する
- [x] `over_explain_pattern` detector を実装する
- [x] `triadic_listing_pattern` detector を実装する
- [x] `uniform_paragraph_length` detector を実装する
- [x] `repeated_sentence_ending` detector を実装する
- [x] `scene_summary_imbalance` detector を実装する
- [x] `dialogue_as_exposition` detector を実装する
- [x] `negative_assertion_repetition` detector を実装する
- [x] `check_scene_output.py` report に `anti_ai_style` を追加する
- [x] anti-AI warnings を top-level `warnings` に反映する
- [x] anti-AI warning だけでは `status=fail` にしない
- [x] warning evidence を短く切る
- [x] anti-AI warning does-not-fail test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 6: Documentation

- [x] README に統合 CLI の推奨フローを追記する
- [x] README に approve/export の完了条件を追記する
- [x] README に health check の使い方を追記する
- [x] `agent/HUB.md` に approve/export/health の参照方針を追記する
- [x] `agent/skills/novel-writer/SKILL.md` に obligation contract の扱いを追記する
- [x] `agent/skills/revision-editor/SKILL.md` に repair/obligation issue の扱いを追記する
- [x] `agent/skills/consistency-auditor/SKILL.md` に health/anti-AI warnings の扱いを追記する
- [x] `agent/skills/prose-polisher/SKILL.md` に anti-AI warning の扱いを追記する
- [x] progress md を final 状態に更新する
- [x] tasks md の完了項目を同期する
- [x] `python -m pytest tests/ -q` を実行する

## Overall Done Definition

- [x] 統合 CLI から prepare/prompt/check/repair/approve/export/health を辿れる
- [x] fail scene は approve/export されない
- [x] warning scene は明示 flag なしで approve されない
- [x] approved scene だけで `exports/manuscript.md` が作れる
- [x] approval stale が content hash で検出される
- [x] obligation contract が runtime に生成される
- [x] dependency 欠落が blocking issue になる
- [x] health check が project 不整合を検出する
- [x] `--fix-safe` が派生物だけを安全に再生成する
- [x] anti-AI style warning が check report に出る
- [x] anti-AI warning だけでは fail にならない
- [x] README / HUB / skill docs が新フローを説明している
- [x] `python -m pytest tests/ -q` が通る
