# VCC Context Refactor Tasks

Date: 2026-06-06

## Goal

段階的に VCC 型 context compiler、品質ゲート、runtime stale 判定、token ledger、story state、related context、agent trace を導入し、長編小説作成時の利用枠消費を品質を落とさずに下げる。

## Implementation Update

2026-06-06 実装結果:

- [x] Phase 0 completed
- [x] Phase 1 completed: deterministic quality gate
- [x] Phase 2 completed: context compiler MVP
- [x] Phase 3 completed: artifact ledger / stale detection
- [x] Phase 4 completed: token ledger
- [x] Phase 5 completed: story state MVP
- [x] Phase 6 completed: related context view
- [x] Phase 7 completed: agent trace compiler
- [x] Documentation references updated in README, HUB, novel-writer, resume-orchestrator
- [x] Validation completed: `python -m pytest tests/ -q` -> `74 passed in 5.73s`

Deferred:

- [ ] Full quality budget ledger for repair-loop limiting remains a follow-up. The numbered 1-7 phase set was completed without it.
- [ ] Related context currently uses lexical scoring directly; using `compile_project_context.py --grep` as an alternate selector remains a follow-up.

## Phase 0: Behavior Lock

- [x] `python -m pytest tests/ -q` を実行し、実装前 baseline を記録する
- [x] 失敗がある場合は新規実装へ進まず原因を分離する
- [x] 変更対象の既存挙動を確認する
- [x] Phase 1 の regression test 方針を決める

## Phase 1: Deterministic Quality Gate

- [x] `scripts/novel_agent/` package を作る
- [x] `scripts/novel_agent/__init__.py` を作る
- [x] `scripts/novel_agent/text_quality.py` を作る
- [x] `check_scene_output.py` から `detect_unclosed_dialogue` を移す
- [x] `check_scene_output.py` から `detect_duplicate_paragraphs` を移す
- [x] `check_scene_output.py` から `collect_format_violations` を移す
- [x] `check_scene_output.py` から `dialogue_ratio_hint` を移す
- [x] `status` field を `check_report.json` に追加する
- [x] `blocking_issues` field を追加する
- [x] `warnings` field を追加する
- [x] `info` field を追加する
- [x] `quality_score_hint` field を追加する
- [x] min 未満を `fail` に分類する
- [x] format violation を `fail` に分類する
- [x] forbidden hit を `fail` に分類する
- [x] duplicate paragraph を `warning` に分類する
- [x] dialogue ratio 偏りを `warning` に分類する
- [x] 既存 `format_violations` と `forbidden_hits` の互換を維持する
- [x] pass report の test を追加する
- [x] warning report の test を追加する
- [x] fail report の test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 2: Context Compiler MVP

- [x] `scripts/novel_agent/context_blocks.py` を作る
- [x] `scripts/novel_agent/context_compiler.py` を作る
- [x] `scripts/compile_project_context.py` を作る
- [x] block model を定義する
- [x] source path + line range pointer を定義する
- [x] outline block 抽出を実装する
- [x] scene txt block 抽出を実装する
- [x] runtime md block 抽出を実装する
- [x] `runtime/check_report.json` block 抽出を実装する
- [x] `context_full.txt` 出力を実装する
- [x] `context_min.txt` 出力を実装する
- [x] `context_index.json` 出力を実装する
- [x] `--grep` regex 検索を実装する
- [x] `context_view.txt` 出力を実装する
- [x] grep stdout に block role と line range を出す
- [x] long scene txt を min view に全文投入しない
- [x] compiler 正常系 test を追加する
- [x] grep view test を追加する
- [x] `python -m pytest tests/ -q` を実行する

## Phase 3: Runtime Stale Detection

- [ ] `scripts/novel_agent/ledgers.py` を作る
- [ ] content hash helper を実装する
- [ ] `runtime/artifact_ledger.json` read/write を実装する
- [ ] artifact id 規則を定義する
- [ ] `build_runtime_context.py` 生成物を ledger 登録する
- [ ] source dependency hash を保存する
- [ ] outline hash 変化による stale 判定を実装する
- [ ] runtime md hash 変化による stale 判定を実装する
- [ ] `build_draft_prompt.py` で stale warning を出す
- [ ] `--force` 再生成時の ledger 更新を確認する
- [ ] protected/user-edited 予約 field を入れる
- [ ] stale 判定 test を追加する
- [ ] existing runtime index 互換 test を追加する
- [ ] `python -m pytest tests/ -q` を実行する

## Phase 4: Token Ledger

- [ ] `runtime/token_ledger.jsonl` append helper を実装する
- [ ] `build_runtime_context.py` の section token を記録する
- [ ] `build_draft_prompt.py` の section token を記録する
- [ ] `compile_project_context.py` の projection token を記録する
- [ ] `status=within_budget|over_budget` を記録する
- [ ] 既存 stdout の estimated_tokens 表示を維持する
- [ ] over budget warning test を追加する
- [ ] token ledger append test を追加する
- [ ] `python -m pytest tests/ -q` を実行する

## Phase 5: Story State MVP

- [ ] `scripts/novel_agent/story_state.py` を作る
- [ ] `runtime/story_state.json` read/write を実装する
- [ ] 空 state 初期化を実装する
- [ ] `migrate_project_state.py` から state 初期化できるようにする
- [ ] `check_scene_output.py` 後に scene status を更新する
- [ ] `completed_scene_count` を更新する
- [ ] `total_chars_written` を更新する
- [ ] YAML sync との責務境界をコメントまたは doc に残す
- [ ] state 未存在時の backward compatibility test を追加する
- [ ] check 後 state 更新 test を追加する
- [ ] `python -m pytest tests/ -q` を実行する

## Phase 6: Related Context View

- [ ] `scripts/build_scene_index.py` を作る
- [ ] `runtime/scene_summaries.jsonl` schema を実装する
- [ ] scene txt から scene summary record を作る
- [ ] content hash による summary freshness を持つ
- [ ] lexical keyword 抽出を実装する
- [ ] target scene と関連 scene の簡易 scoring を実装する
- [ ] `compile_project_context.py --grep` 結果を related context 候補に使えるようにする
- [ ] `build_runtime_context.py` で `related_context_pack.md` を生成する
- [ ] related context は pointer + one-line summary 中心にする
- [ ] 長文本文抜粋が入らない test を追加する
- [ ] 関連 scene 選択 test を追加する
- [ ] `python -m pytest tests/ -q` を実行する

## Phase 7: Agent Trace Compiler

- [ ] `scripts/novel_agent/trace.py` を作る
- [ ] `agent/trace/trace.jsonl` append helper を実装する
- [ ] `runtime_generated` event を記録する
- [ ] `draft_prompt_generated` event を記録する
- [ ] `scene_checked` event を記録する
- [ ] `patch_prompt_generated` event を記録する
- [ ] `state_updated` event を記録する
- [ ] trace event に全文本文を入れない制約を実装する
- [ ] `scripts/compile_agent_trace.py` を作る
- [ ] `trace_full.txt` 出力を実装する
- [ ] `trace_min.txt` 出力を実装する
- [ ] `--grep` と `trace_view.txt` 出力を実装する
- [ ] trace 未存在時の no-op/warn test を追加する
- [ ] trace compiler grep test を追加する
- [ ] `python -m pytest tests/ -q` を実行する

## Documentation Tasks

- [ ] README に context compiler の位置づけを追記する
- [ ] README の runtime-first 説明を pointer-first に更新する
- [ ] `agent/HUB.md` に stale runtime / context compiler の参照方針を追記する
- [ ] `agent/skills/novel-writer/SKILL.md` に `related_context_pack.md` の扱いを追記する
- [ ] `agent/skills/resume-orchestrator/SKILL.md` に trace view の扱いを追記する
- [ ] `history/vcc_context_refactor_progress_2026-06-06.md` を各 phase 後に更新する

## Phase Done Checklist

各 phase 完了時に確認する。

- [ ] 変更範囲が phase scope 内に収まっている
- [ ] 新規テストがある
- [ ] 既存テストが通る
- [ ] 旧フィールド/旧CLI互換が壊れていない
- [ ] prompt/runtime 文脈が不要に肥大化していない
- [ ] progress md を更新した

## Overall Done Definition

- [ ] Phase 1 から Phase 7 まで完了
- [ ] `python -m pytest tests/ -q` が通る
- [ ] context compiler が full/min/search view を生成する
- [ ] pointer から正本 source に戻れる
- [ ] stale runtime が検出できる
- [ ] token ledger で実行ごとの推定 token を追える
- [ ] quality budget ledger で同一問題の修復ループを制限できる（deferred）
- [ ] story_state が scene/check 状態を保持する
- [ ] related_context_pack が pointer-first で生成される
- [ ] agent trace の min/view が生成できる
