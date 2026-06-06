# Quality Budget Ledger Implementation Plan

Date: 2026-06-06

## Purpose

`quality_budget_ledger` は、長編小説の scene 修復ループで同じ問題に対して LLM 呼び出しを繰り返しすぎないための軽量台帳である。

今回の VCC refactor では、context compiler、artifact ledger、token ledger、story state、trace compiler まで入った。一方で、以下の判断はまだ明示的に管理していない。

- 文字数不足に対して何回まで `expand_prompt` を作るか。
- 修復後も同じ `check_report` 失敗が続く場合、いつ自動修復を止めるか。
- `needs_expand=true` ではない失敗に対して、誤って expansion を繰り返していないか。
- scene 単位で修復コストが膨らんでいるか。

この計画の目的は、**品質を落とさず、無駄な再生成と修復ループを止めるための deterministic budget gate** を追加することである。

## Current Repository Facts

現在の接続点:

- `scripts/check_scene_output.py`
  - `runtime/check_report.json` を生成する。
  - `needs_expand`, `status`, `blocking_issues`, `warnings`, `quality_score_hint` を持つ。
  - `story_state.json` と trace を更新する。
- `scripts/build_expand_prompt.py`
  - `check_report.json` を読み、文字数不足分の局所差分 prompt を作る。
  - 現状では `needs_expand=false` でも warning だけで prompt は作れる。
- `scripts/apply_expand_edits.py`
  - LLM の局所差分を本文へ反映する。
  - 現状では ledger / trace 連携がない。
- `scripts/novel_agent/ledgers.py`
  - `artifact_ledger.json` と `token_ledger.jsonl` の helper がある。
  - quality budget 用 helper を追加する自然な場所。

## Non-Goals

- 新しい依存ライブラリは入れない。
- LLM judge を追加しない。
- 自動改稿エンジン全体を作らない。
- `build_expand_prompt.py` を format violation や forbidden hit の万能修復 prompt にしない。
- 既存 `check_report.json` のフィールドを削除しない。
- 既存 scene txt の保存場所や `05_chapter_outline.md` の正本性を変えない。

## Design Principles

1. **Deterministic first**
   - LLM を呼ぶ前に、ローカル JSON 台帳で続行可否を判定する。

2. **Budget is per scene and per issue**
   - scene 全体の修復回数と、同じ問題種別の修復回数を分けて持つ。

3. **Expansion is only for shortage**
   - `build_expand_prompt.py` は文字数不足を局所増補する道具であり、format / forbidden / over max を直す道具ではない。

4. **Additive compatibility**
   - 既存 CLI の基本動作は維持し、budget exhausted のときだけ明示的に止める。

5. **Override is explicit**
   - 予算超過後に続ける場合は `--force` などの明示指定を必要にし、ledger に override として残す。

## Recommended Architecture

```text
check_scene_output.py
  -> check_report.json
  -> update_quality_budget_from_check()
  -> quality_budget_ledger.json

build_expand_prompt.py
  -> read check_report.json
  -> evaluate_quality_budget_for_expand()
  -> allow / warn / block
  -> expand_prompt.txt
  -> record_quality_budget_action("expand_prompt_generated")

apply_expand_edits.py
  -> apply local edits
  -> record_quality_budget_action("expand_edits_applied")

check_scene_output.py rerun
  -> resolve / continue / exhaust issue budget
```

## File Layout

追加・改修候補:

```text
scripts/
  build_expand_prompt.py
  apply_expand_edits.py
  check_scene_output.py
  novel_agent/
    ledgers.py

<project>/runtime/
  quality_budget_ledger.json
```

将来の optional CLI:

```text
scripts/report_quality_budget.py
```

これは v1 では必須にしない。まずは既存 runtime flow に budget gate を入れる。

## Ledger Schema

`<project>/runtime/quality_budget_ledger.json`

```json
{
  "version": 1,
  "updated_at": "2026-06-06T00:00:00+00:00",
  "policy": {
    "max_scene_repair_prompts": 3,
    "max_issue_attempts": 2,
    "max_expand_without_recheck": 1,
    "block_expansion_for_issue_types": [
      "format_violation",
      "forbidden_hit",
      "over_max_for_type"
    ]
  },
  "scenes": {
    "2-3": {
      "scene_id": "2-3",
      "status": "within_budget",
      "counters": {
        "check_runs": 1,
        "expand_prompts": 0,
        "expand_edits_applied": 0,
        "forced_overrides": 0
      },
      "issues": {
        "under_min_for_type": {
          "issue_type": "under_min_for_type",
          "severity": "blocking",
          "status": "open",
          "attempts": 0,
          "budget": 2,
          "first_seen_at": "2026-06-06T00:00:00+00:00",
          "last_seen_at": "2026-06-06T00:00:00+00:00",
          "last_evidence": {
            "actual_chars": 1300,
            "min_chars": 1600,
            "char_delta_to_min": -300
          },
          "artifacts": [
            "runtime/scenes/2-3/draft/check_report.json"
          ]
        }
      },
      "decisions": [
        {
          "created_at": "2026-06-06T00:00:00+00:00",
          "action": "allow_expand",
          "reason": "under_min_for_type attempts 0/2",
          "artifacts": [
            "runtime/scenes/2-3/draft/expand_prompt.txt"
          ]
        }
      ]
    }
  }
}
```

## Issue Key Policy

v1 では issue key を安定させすぎない。まずは機械的な種別でよい。

| Source | Issue Key |
|---|---|
| `needs_expand=true` / `under_min_for_type=true` | `under_min_for_type` |
| `over_max_for_type=true` | `over_max_for_type` |
| `format_violations_detail[].type` | `format_violation:<type>` |
| `forbidden_hits_detail[].type` or literal hit | `forbidden_hit:<type-or-rule>` |
| `blocking_issues[].type` | `blocking:<type>` |
| `warnings[].type` | `warning:<type>` |

細かい literal 本文や長い抜粋は ledger に入れない。trace と同じく、本文全文を蓄積しない。

## Default Budget Policy

v1 の推奨値:

| Budget | Value | Reason |
|---|---:|---|
| scene 全体の修復 prompt 上限 | 3 | 1 scene で何度も LLM を呼ばない |
| 同一 issue の試行上限 | 2 | 同じ失敗が 2 回残るなら方針が間違っている可能性が高い |
| recheck なしの連続 expand 上限 | 1 | 差分適用後は必ず `check_scene_output.py` に戻す |
| `format_violations` | expansion 禁止 | 増補では直らないことが多い |
| `forbidden_hits` | expansion 禁止 | 増補では悪化する可能性がある |
| `over_max_for_type` | expansion 禁止 | 増やすべきではない |

## Decision Matrix

| check result | budget state | build_expand_prompt behavior |
|---|---|---|
| `status=pass` | any | ledger の open issue を resolved にする。expand 不要。 |
| `needs_expand=true` only | within budget | expand prompt を許可する。attempt を増やす。 |
| `needs_expand=true` | issue exhausted | exit 1 で停止する。`--force` なら override 記録して続行。 |
| `format_violations` present | any | expand を block し、revision/manual repair を促す。 |
| `forbidden_hits` present | any | expand を block し、revision/manual repair を促す。 |
| `over_max_for_type=true` | any | expand を block する。短縮・改稿の対象。 |
| `check_report.json` invalid | any | 既存どおり error。ledger は更新しない。 |

## Implementation Phases

### Phase 0: Behavior Lock

- `python -m pytest tests/ -q` を実行する。
- 現在の `build_expand_prompt.py` 正常系・warning 系を確認する。
- quality budget 未導入時の既存 output を fixture 的に把握する。

### Phase 1: Ledger Helpers

Target:

- `scripts/novel_agent/ledgers.py`
- `tests/test_scripts.py`

Add:

- `quality_budget_ledger_path(project_dir)`
- `read_quality_budget_ledger(project_dir)`
- `write_quality_budget_ledger(project_dir, payload)`
- `default_quality_budget_policy()`
- `update_quality_budget_from_check(project_dir, scene_ref, report, report_path)`
- `evaluate_quality_budget_for_expand(project_dir, scene_ref, report)`
- `record_quality_budget_action(project_dir, scene_ref, action, reason, artifacts=None, force=False)`

### Phase 2: Check Report Integration

Target:

- `scripts/check_scene_output.py`

Behavior:

- `check_report.json` 作成後に `update_quality_budget_from_check()` を呼ぶ。
- `status=pass` なら該当 scene の open issue を resolved にする。
- `status=warning` は記録するが、expand budget を消費しない。
- `status=fail` は issue を open にする。

### Phase 3: Expand Prompt Budget Gate

Target:

- `scripts/build_expand_prompt.py`

Behavior:

- `--force` を追加する。
- prompt 作成前に `evaluate_quality_budget_for_expand()` を呼ぶ。
- allow なら prompt を生成し、`expand_prompt_generated` を記録する。
- block なら `ERROR: quality budget exhausted` または `ERROR: expansion is not appropriate for issue type` で exit 1。
- `--force` なら prompt を生成し、`forced_override` を記録する。

### Phase 4: Apply Edit Action Tracking

Target:

- `scripts/apply_expand_edits.py`

Behavior:

- scene ref を text path から推定する。
- edit 適用後に `expand_edits_applied` を記録する。
- `max_expand_without_recheck` を超えた場合、次の `build_expand_prompt.py` を止められるようにする。

### Phase 5: Documentation and Optional Reporting

Target:

- `README.md`
- `agent/HUB.md`
- `agent/skills/novel-writer/SKILL.md`
- optional: `scripts/report_quality_budget.py`

Behavior:

- `quality_budget_ledger.json` の意味を runtime-first 説明に追記する。
- exhausted 時は `check_scene_output.py` 再実行、手動改稿、または `--force` の判断に戻ることを明記する。

## Test Plan

### Unit / Script Tests

- ledger が存在しない場合、default payload を返す。
- ledger JSON が壊れている場合、安全な default payload を返す。
- `needs_expand=true` の check report から `under_min_for_type` issue が作られる。
- pass check により open issue が resolved になる。
- 同一 issue が budget 内なら `build_expand_prompt.py` が通る。
- 同一 issue が budget 超過なら `build_expand_prompt.py` が exit 1 する。
- `--force` なら budget 超過でも prompt を作り、override が記録される。
- `format_violations` がある場合、文字数不足でも expansion は block される。
- `apply_expand_edits.py` 後に `expand_edits_applied` が記録される。

### Integration Tests

- draft -> check fail under min -> expand prompt -> apply edits -> check pass の最短ループ。
- draft -> check fail under min -> expand prompt 連続 2 回 -> 3 回目 block。
- forbidden hit を含む draft -> expand prompt block。

### Regression

```bash
python -m pytest tests/ -q
```

## Acceptance Criteria

- 既存 `check_report.json` schema の互換が壊れていない。
- `runtime/quality_budget_ledger.json` が check / expand / apply の順で更新される。
- budget exhausted 時に追加 LLM prompt 生成が止まる。
- `--force` override が ledger に残る。
- format / forbidden / over max に対して expansion を誤用しない。
- 既存 tests が pass する。
- 新依存なし。

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| budget が厳しすぎて有用な修復を止める | `--force` を用意し、policy 値を JSON に保存する |
| issue key が細かすぎて budget が効かない | v1 は coarse issue key を使う |
| ledger が another summary sink になる | 本文全文や長い抜粋を保存しない |
| `build_expand_prompt.py` の責務が膨らむ | 判定ロジックは `novel_agent/ledgers.py` に寄せる |
| format violation に対して expand して悪化する | decision matrix で expansion を block する |

## Recommended First Implementation Slice

最初の実装は以下に絞る。

1. `ledgers.py` に quality budget helper を追加する。
2. `check_scene_output.py` で `needs_expand` / `status` を ledger に記録する。
3. `build_expand_prompt.py` で `under_min_for_type` の budget だけ判定する。
4. `--force` override を入れる。
5. tests を追加して `python -m pytest tests/ -q` を通す。

format / forbidden / over max の詳細な修復導線は、その後の phase で扱う。
