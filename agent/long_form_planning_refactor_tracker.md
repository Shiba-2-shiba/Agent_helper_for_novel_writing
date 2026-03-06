# Long-Form Planning Refactor Tracker

Last Updated: 2026-03-06
Owner: inott + Codex
Overall Status: done

## Goal

10万字前提の案件で、初期計画が薄いまま執筆へ進んで短文化する問題を抑える。

今回の方針:
- 1シーンを一律に長くするのではなく、計画段階で必要なシーン在庫を確定する
- `runtime` には全体設計をそのまま流さず、対象シーンの判断に必要な最小情報だけを渡す
- `Codex` / `Antigravity` のクレジット消費を抑えるため、重要シーンだけ厚くし、つなぎシーンは短く保つ

## Non-Goals

- 一律の最低文字数を大きく引き上げること
- 既存の旧案件すべてを即時移行すること
- 本文生成ロジック全体を別方式へ作り直すこと

## Success Criteria

- `long_form_100k` 案件では、計画ゲート未通過のまま `scene-planner` / `novel-writer` に進まない
- `05_chapter_outline_100k.md` から `planned_total_min_chars` を算出できる
- `runtime/scene_brief_compact.md` に `Scene Type` と `Length Band` と章予算差分が載る
- `novel-writer` / `check_scene_output.py` が固定 `1000-1500` ではなく `scene_type` 帯域で動く
- 旧テンプレ案件ではフォールバックが効く

## Constraints

- 低クレジット運用を維持する
- 再生成回数を増やしすぎない
- `runtime` 出力は肥大化させない
- 旧テンプレ / 旧案件との互換性を段階的に保つ

## Status Summary

| Phase | Scope | Status | Notes |
|---|---|---|---|
| A | 計画ゲート導入 | done | state / bootstrap / setting / outline template |
| B | runtime 圧縮品質 | done | prompt utils / runtime context / draft prompt |
| C | 執筆と検査の同期 | done | novel writer / checker / request / eval |
| D | gate enforcement hardening | done | routing docs + draft prompt guard + regression test |
| E | planning-gate feedback loop | done | planning_gate_brief artifact + routing/eval sync |

## Phase A

### Files

| File | Purpose | Status | Notes |
|---|---|---|---|
| `agent/state_schema_novel.yaml` | 計画値と実績差分を持たせる | done | `length_mode`, `planning_gate_status`, `scene_type_bands` を追加 |
| `agent/skills/project-bootstrap/SKILL.md` | 長編案件を `setting-creator` へ確実に渡す | done | `Planning Gate: blocked` を初期値で残す |
| `agent/skills/setting-creator/SKILL.md` | 長編計画の owner にする | done | `planned_total_min_chars` 算出と gate 判定を追加 |
| `templates/05_chapter_outline_100k.md` | 章カード + シーン台帳の正本に変える | done | 大量空欄シーン方式を廃止 |

### Checklist

- [x] `agent/state_schema_novel.yaml` に `targets.length_mode` を追加
- [x] `agent/state_schema_novel.yaml` に `targets.planning_gate_min_chars` を追加
- [x] `agent/state_schema_novel.yaml` に `targets.planning_target_total_chars` を追加
- [x] `agent/state_schema_novel.yaml` に `targets.scene_type_bands` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.planned_total_min_chars` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.planned_total_target_chars` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.planned_scene_count` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.completed_scene_count` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.chapter_scene_counts` を追加
- [x] `agent/state_schema_novel.yaml` に `progress.chapter_planned_chars` を追加
- [x] `agent/state_schema_novel.yaml` に `active_work.planning_gate_status` を追加
- [x] `agent/state_schema_novel.yaml` に `active_work.current_scene_type` を追加
- [x] `agent/state_schema_novel.yaml` に `continuity_watch.planned_payoffs` を追加
- [x] `agent/state_schema_novel.yaml` に `continuity_watch.missing_payoffs` を追加
- [x] `agent/skills/project-bootstrap/SKILL.md` に `length_mode` 決定手順を追加
- [x] `agent/skills/project-bootstrap/SKILL.md` に `long_form_100k -> planning_gate_status=blocked` を追加
- [x] `agent/skills/project-bootstrap/SKILL.md` の `Outputs` に `Length Mode` を追加
- [x] `agent/skills/project-bootstrap/SKILL.md` の `Outputs` に `Planning Gate` を追加
- [x] `agent/skills/project-bootstrap/SKILL.md` の `Do Not` に長編直行禁止を追加
- [x] `agent/skills/setting-creator/SKILL.md` の `Read First` に `05_chapter_outline_100k.md` を追加
- [x] `agent/skills/setting-creator/SKILL.md` に `long_form_100k` 用の `長編計画ゲート` 節を追加
- [x] `agent/skills/setting-creator/SKILL.md` に `planned_total_min_chars` 算出手順を追加
- [x] `agent/skills/setting-creator/SKILL.md` に `planning_gate_status` 判定手順を追加
- [x] `agent/skills/setting-creator/SKILL.md` の `Outputs` に `Planning Verdict` を追加
- [x] `templates/05_chapter_outline_100k.md` を `Chapter Card + Scene Ledger` 構成へ変更
- [x] `templates/05_chapter_outline_100k.md` に `Scene Type Bands` を追加
- [x] `templates/05_chapter_outline_100k.md` に `Planning Totals` を追加

### Exit Criteria

- `05_chapter_outline_100k.md` から `planned_total_min_chars` を算出できる
- `long_form_100k` 案件で `planning_gate_status` を `blocked` / `ready` に分けられる
- `project-bootstrap` から長編案件が `setting-creator` に流れる

## Phase B

### Files

| File | Purpose | Status | Notes |
|---|---|---|---|
| `scripts/prompt_utils.py` | `Scene Ledger` 抽出を追加する | done | 旧テンプレへのフォールバックを維持 |
| `scripts/build_runtime_context.py` | `scene_brief_compact.md` に計画情報を載せる | done | `Scene Type`, `Length Band`, 章予算差分を追加 |
| `scripts/build_draft_prompt.py` | 一律 `1000-1500` 依存を弱める | done | `bridge` / `anchor` / `climax` の扱いを追加 |

### Checklist

- [x] `scripts/prompt_utils.py` に `parse_scene_ledger()` を追加
- [x] `scripts/prompt_utils.py` に `find_scene_ledger_entry()` を追加
- [x] `scripts/prompt_utils.py` に `compute_planned_totals()` を追加
- [x] `scripts/prompt_utils.py` の `extract_scene_description()` を `Scene Ledger` 優先に変更
- [x] `scripts/build_runtime_context.py` が `Scene Ledger` から対象シーン情報を読める
- [x] `scripts/build_runtime_context.py` の `scene_brief_compact.md` に `Scene Type` を追加
- [x] `scripts/build_runtime_context.py` の `scene_brief_compact.md` に `Length Band` を追加
- [x] `scripts/build_runtime_context.py` の `scene_brief_compact.md` に `Chapter Budget Remaining` を追加
- [x] `scripts/build_runtime_context.py` の `scene_brief_compact.md` に `This Scene Pays Off` を追加
- [x] `scripts/build_runtime_context.py` の `request_compact.md` に `Planning Gate` を追加
- [x] `scripts/build_draft_prompt.py` から `最低文字数未達でも失敗扱いにしない` を削除または置換
- [x] `scripts/build_draft_prompt.py` に `Scene Type` 依存の帯域指示を追加
- [x] `scripts/build_draft_prompt.py` に `bridge は無理に膨らませない` を追加

### Exit Criteria

- `runtime/scene_brief_compact.md` が `Scene Type` と `Length Band` を持つ
- `runtime` 生成で長文プロット全文を毎回読まない

## Phase C

### Files

| File | Purpose | Status | Notes |
|---|---|---|---|
| `agent/skills/novel-writer/SKILL.md` | 帯域ベースの執筆ルールへ移行 | done | `runtime` の `Length Band` を優先するよう変更 |
| `scripts/check_scene_output.py` | `scene_type` 帯域で検査 | done | 旧案件フォールバックを維持 |
| `agent/request_template.md` | 低クレジット長編の指定をしやすくする | done | `Length Mode`, `Scene Type`, `Prefer Low Credit Mode` を追加 |
| `agent/evals/README.md` | 計画不足を eval で落とす | done | `planning coverage` と `runtime compression` 観点を追加 |

### Checklist

- [x] `agent/skills/novel-writer/SKILL.md` の固定 `1000-1500` を `Length Band` 準拠に置換
- [x] `agent/skills/novel-writer/SKILL.md` に `scene_type` を追加
- [x] `scripts/check_scene_output.py` に `expected_band` を追加
- [x] `scripts/check_scene_output.py` の `needs_expand` を帯域ベースに変更
- [x] `agent/request_template.md` から共通ルールの固定 `1000-1500` を削除
- [x] `agent/request_template.md` に `Length Mode` を追加
- [x] `agent/request_template.md` に `Prefer Low Credit Mode` を追加
- [x] `agent/request_template.md` に `Scene Type` を追加
- [x] `agent/evals/README.md` に `Planning` 観点を追加
- [x] `agent/evals/README.md` に gate 未達の fail trigger を追加
- [x] `agent/evals/README.md` に `runtime compression fidelity` を追加

### Exit Criteria

- 執筆ルールと検査ルールが `scene_type` 帯域で揃う
- `planning_gate_status` 未通過案件を eval で落とせる

## Phase D

### Files

| File | Purpose | Status | Notes |
|---|---|---|---|
| `scripts/build_draft_prompt.py` | gate 未通過案件の draft prompt 生成を止める | done | `blocked` / 未準備ステータスを拒否 |
| `agent/skills/scene-planner/SKILL.md` | 長編 gate 未通過の差し戻し先を明記 | done | `setting-creator` 優先へ統一 |
| `agent/skills/resume-orchestrator/SKILL.md` | 再開時も gate 優先で routing する | done | 本文再開前に gate を確認 |
| `agent/skills/novel-writer/SKILL.md` | 執筆前 gate 確認を明示 | done | `Planning Gate: blocked` を拒否 |
| `agent/HUB.md` | ハブの routing 規則を長編 gate と同期 | done | `scene-planner` / `novel-writer` 直行を抑止 |
| `tests/test_scripts.py` | gate hardening の回帰テストを追加 | done | `draft_prompt` 非生成を検証 |

### Checklist

- [x] `scripts/build_draft_prompt.py` が `Planning Gate: blocked` なら失敗する
- [x] `agent/skills/scene-planner/SKILL.md` に gate 未通過時の差し戻しを追加
- [x] `agent/skills/resume-orchestrator/SKILL.md` に gate 優先 routing を追加
- [x] `agent/skills/novel-writer/SKILL.md` に gate 未通過時の執筆禁止を追加
- [x] `agent/HUB.md` に長編 gate の共通 routing ルールを追加
- [x] `tests/test_scripts.py` に `planning_gate_status=blocked` の回帰テストを追加

### Exit Criteria

- `planning_gate_status != ready` の長編案件で `draft_prompt.txt` を生成しない
- `scene-planner` / `resume-orchestrator` / `novel-writer` / `HUB` の routing が `setting-creator` 優先で揃う

## Phase E

### Files

| File | Purpose | Status | Notes |
|---|---|---|---|
| `scripts/build_runtime_context.py` | `planning_gate_brief.md` を生成する | done | draft / resume の共通 planning artifact |
| `scripts/prompt_utils.py` | planning totals の state fallback を持つ | done | old project compatibility を維持 |
| `scripts/build_draft_prompt.py` | planning gate brief を prompt に載せる | done | gate 判定の共通 artifact を参照 |
| `agent/skills/scene-planner/SKILL.md` | planning gate brief を読む | done | gate status と next action を先頭確認 |
| `agent/skills/resume-orchestrator/SKILL.md` | planning gate brief を読む | done | resume と planning gate を同じ artifact に寄せる |
| `agent/skills/novel-writer/SKILL.md` | planning gate brief を読む | done | 本文前 gate 確認を一元化 |
| `agent/HUB.md` | planning gate brief を共通正本にする | done | routing rule を artifact 基準に同期 |
| `agent/evals/README.md` | planning gate loop を eval 観点へ追加 | done | resume 型回帰手順を明記 |
| `agent/evals/prompts/skill_trigger_qa_2026-03-05.md` | planning gate blocked の trigger QA を追加 | done | setting-creator への routing を補強 |
| `agent/evals/prompts/skill_regression_boundary_2026-03-05.md` | planning gate blocked の boundary case を追加 | done | scene-planner / novel-writer 直行を抑止 |
| `scripts/eval_skill_trigger_qa.py` | planning gate prompt の router heuristic を追加 | done | setting-creator を優先 |
| `tests/test_scripts.py` | planning gate brief と router の回帰テストを追加 | done | runtime artifact と routing を検証 |

### Checklist

- [x] `runtime/planning_gate_brief.md` を生成する
- [x] `planning_gate_brief.md` に `Planning Gate` / `Planned Total Min Chars` / `Next Planning Action` を載せる
- [x] `resume-orchestrator` / `scene-planner` / `novel-writer` が `planning_gate_brief.md` を参照する
- [x] `draft_prompt.txt` に `planning_gate_brief.md` を反映する
- [x] planning gate blocked の routing prompt を eval に追加する
- [x] router heuristic に planning gate blocked -> `setting-creator` を追加する
- [x] runtime artifact と router の回帰テストを追加する

### Exit Criteria

- `planning_gate_brief.md` を見れば gate 状態と次 planning action を同じ形式で再確認できる
- `resume` と同様に、planning gate の回帰改善を同じ artifact と prompt set で再実行できる

## Concrete Text Drafts

### `agent/state_schema_novel.yaml`

- `targets` に以下を追加する
- `length_mode`
- `planning_gate_min_chars`
- `planning_target_total_chars`
- `scene_type_bands`

- `progress` に以下を追加する
- `planned_total_min_chars`
- `planned_total_target_chars`
- `planned_scene_count`
- `completed_scene_count`
- `chapter_scene_counts`
- `chapter_planned_chars`

- `active_work` に以下を追加する
- `planning_gate_status`
- `current_scene_type`

### `agent/skills/project-bootstrap/SKILL.md`

- `Current State` の次に `Length Mode` と `Planning Gate` を返す
- `long_form_100k` 案件では `setting-creator` 直行を原則にする

### `agent/skills/setting-creator/SKILL.md`

- `long_form_100k` では `05_chapter_outline_100k.md` を必須化する
- `planned_total_min_chars` を算出し、`planning_gate_status` を返す

### `templates/05_chapter_outline_100k.md`

- 大量の空欄シーンではなく、章カードとシーン台帳へ置き換える
- 章ごとに `役割 / 感情線 / 章末フック / 回収 / 種まき / 想定字数` を持つ
- シーンごとに `scene_type / purpose / payoff_or_seed / min-target-max` を持つ

## Progress Log

| Date | Phase | Status | Summary | Files |
|---|---|---|---|---|
| 2026-03-06 | Planning | done | Tracker document created from the long-form planning refactor design and checklists. | `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Setup | done | Initialized tracker ownership and set the refactor status to `in_progress` before Phase A implementation. | `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase A | done | Implemented planning-gate documentation changes for schema, bootstrap, setting creation, and the 100k outline template. | `agent/state_schema_novel.yaml`, `agent/skills/project-bootstrap/SKILL.md`, `agent/skills/setting-creator/SKILL.md`, `templates/05_chapter_outline_100k.md`, `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase B | done | Implemented `Scene Ledger` parsing, enriched runtime compact files with scene type and length-band data, and updated draft-prompt generation to use the runtime band. | `scripts/prompt_utils.py`, `scripts/build_runtime_context.py`, `scripts/build_draft_prompt.py`, `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase C (partial) | done | Updated `novel-writer` and `check_scene_output.py` so drafting guidance and `needs_expand` can follow `runtime` length bands before the request/eval docs are synchronized. | `agent/skills/novel-writer/SKILL.md`, `scripts/check_scene_output.py`, `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase C (complete) | done | Synchronized `request_template.md` and `evals/README.md` with the planning-gate and scene-type workflow, completing the drafting/checking/request/eval alignment. | `agent/request_template.md`, `agent/evals/README.md`, `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase D | done | Hardened long-form planning-gate enforcement by blocking `draft_prompt` generation when planning is not ready and synchronizing routing docs/tests around `setting-creator` fallback. | `scripts/build_draft_prompt.py`, `agent/skills/scene-planner/SKILL.md`, `agent/skills/resume-orchestrator/SKILL.md`, `agent/skills/novel-writer/SKILL.md`, `agent/HUB.md`, `tests/test_scripts.py`, `agent/long_form_planning_refactor_tracker.md` |
| 2026-03-06 | Phase E | done | Added `runtime/planning_gate_brief.md` as a shared planning artifact, synchronized skill routing around it, and extended eval/tests so planning-gate recovery can be iterated like `resume`. | `scripts/build_runtime_context.py`, `scripts/prompt_utils.py`, `scripts/build_draft_prompt.py`, `agent/skills/scene-planner/SKILL.md`, `agent/skills/resume-orchestrator/SKILL.md`, `agent/skills/novel-writer/SKILL.md`, `agent/HUB.md`, `agent/evals/README.md`, `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`, `agent/evals/prompts/skill_regression_boundary_2026-03-05.md`, `scripts/eval_skill_trigger_qa.py`, `tests/test_scripts.py`, `agent/long_form_planning_refactor_tracker.md` |

## Decision Log

- `long_form_100k` では、文字数を一律に増やすより `scene inventory` を先に確保する
- `runtime` は全体設計を全文保持せず、対象シーンの判断に必要な最小情報だけを保持する
- 重要シーンだけ厚くし、つなぎシーンは短く保つ

## Open Questions

- `planning_gate_min_chars` を `80000` で固定するか、案件ごとに可変にするか
- `scene_type` を 4 種で固定するか、`payoff` などを追加するか
- 旧テンプレ案件への移行支援をどこまで自動化するか

## Update Rules

- 作業着手時に対象ファイルの `Status` を `in_progress` に変える
- 完了したチェックボックスは都度更新する
- 方針変更が出たら `Decision Log` に 1 行で追記する
- ブロッカーは `Open Questions` に追加する
- フェーズ完了時は `Status Summary` の該当行を更新する
