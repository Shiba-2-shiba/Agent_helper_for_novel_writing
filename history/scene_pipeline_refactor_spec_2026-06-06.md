# Scene Pipeline Refactor Spec

Date: 2026-06-06

## Purpose

本仕様は、`Agent_helper_for_novel_writing` の次段階リファクタリングとして、既存の `runtime-first` / VCC 型 context compiler / quality ledger 基盤の上に、実運用で使いやすい scene production pipeline を追加する要件を定義する。

対象は、参考リポジトリから取り込む価値が高く、かつ現リポの軽量 Markdown/CLI/標準ライブラリ方針と衝突しない以下 5 点。

1. 薄い統合 CLI / orchestrator
2. 承認ゲートと export
3. 章・シーン義務契約
4. memory sync / project health check
5. 反AI文体検査の強化

目的は以下。

- 利用者が個別 script の順序を覚えなくても、標準フローを安全に実行できるようにする。
- `check_report.json` の結果を「完成承認」と「書き出し」に接続する。
- シーンが果たすべき義務を、writer / checker / repair が同じ意味で扱えるようにする。
- stale runtime、古い summary、矛盾した outline status をまとめて検出する。
- LLM を呼ぶ前に、AI っぽい文体劣化を deterministic に検出する。

## Non-Goals

- Web UI / desktop UI は作らない。
- DB、LangChain、Chroma、Qdrant、LangGraph は導入しない。
- 毎 scene の LLM judge は追加しない。
- PDF / ePub / LaTeX export はこの段階では扱わない。
- 既存 script を削除しない。
- `body.md` を本文集約先に戻さない。
- 自動で本文を全文再生成する orchestration は作らない。

## Behavior Lock

実装前 baseline:

```bash
python -m pytest tests/ -q
```

直近確認:

- Result: `79 passed in 6.90s`

各 phase の原則:

- 実装前に対象挙動の regression test を追加する。
- 既存 CLI は互換維持し、新しい入口は additive にする。
- 新依存は入れない。
- 新しい JSON field は additive にする。
- prompt/runtime 文脈を増やす場合は、長文抜粋ではなく pointer / summary を優先する。
- 人間が編集した本文・設定を上書きする可能性がある操作には、明示的な CLI flag を要求する。

## Current Foundation

すでに実装済みの基盤:

- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/check_scene_output.py`
- `scripts/build_expand_prompt.py`
- `scripts/apply_expand_edits.py`
- `scripts/compile_project_context.py`
- `scripts/compile_agent_trace.py`
- `scripts/build_scene_index.py`
- `runtime/artifact_ledger.json`
- `runtime/token_ledger.jsonl`
- `runtime/quality_budget_ledger.json`
- `runtime/story_state.json`
- `runtime/scene_summaries.jsonl`
- `agent/trace/trace.jsonl`

今回の refactor は、これらを置き換えるのではなく、実運用の入口と終端を足す。

## Architecture Overview

現行:

```text
build_runtime_context.py
  -> build_draft_prompt.py
  -> user/model writes scene txt
  -> check_scene_output.py
  -> build_expand_prompt.py / apply_expand_edits.py
```

改訂後:

```text
novel_cli.py / run_scene_pipeline.py
  -> prepare runtime
  -> build prompt
  -> accept draft/revised file
  -> deterministic check
  -> repair prompt when appropriate
  -> approve scene when gate passes
  -> export approved manuscript
  -> sync health checks
```

新規概念:

- **Scene Pipeline Command**: 複数 script を順序付きで呼ぶ薄い CLI。
- **Approval Gate**: `check_report.json` と人間承認を使い、scene を export 対象へ昇格する境界。
- **Obligation Contract**: scene が今満たすべき義務を構造化した小さな契約。
- **Project Health Check**: runtime / state / outline / summaries / trace の同期診断。
- **Anti-AI Style Gate**: 文体劣化を deterministic warning として報告する検査群。

## File Layout

追加候補:

```text
scripts/
  novel_cli.py
  run_scene_pipeline.py
  approve_scene.py
  export_manuscript.py
  sync_project_health.py
  novel_agent/
    approvals.py
    exports.py
    health.py
    obligations.py
    anti_ai_style.py

<project>/runtime/
  approval_ledger.json
  health_report.json

<project>/exports/
  manuscript.md
```

既存に追加する可能性がある出力:

```text
runtime/scenes/<scene>/<mode>/check_report.json
runtime/scenes/<scene>/<mode>/obligation_contract.json
```

## Phase 1: Thin Integrated CLI / Orchestrator

### Purpose

既存 script を置き換えず、日常運用の入口を 1 つにまとめる。

### Target Files

- `scripts/novel_cli.py` または `scripts/run_scene_pipeline.py`
- `scripts/novel_agent/pipeline.py`
- `tests/test_scripts.py`
- `README.md`

### CLI Shape

MVP は以下のどちらかでよい。

```bash
python scripts/run_scene_pipeline.py prepare --project <project> --chapter 2 --scene 2-3
python scripts/run_scene_pipeline.py prompt --project <project> --chapter 2 --scene 2-3
python scripts/run_scene_pipeline.py check --project <project> --text <scene_txt>
python scripts/run_scene_pipeline.py repair --project <project> --text <scene_txt>
python scripts/run_scene_pipeline.py approve --project <project> --scene 2-3
python scripts/run_scene_pipeline.py export --project <project>
python scripts/run_scene_pipeline.py health --project <project>
```

または:

```bash
python scripts/novel_cli.py scene prepare ...
python scripts/novel_cli.py scene check ...
python scripts/novel_cli.py project health ...
python scripts/novel_cli.py project export ...
```

### Required Behavior

- `prepare` は `build_runtime_context.py --mode draft` を呼ぶ相当の処理を行う。
- `prompt` は `build_draft_prompt.py` 相当の処理を行う。
- `check` は `check_scene_output.py` 相当の処理を行う。
- `repair` は quality budget を見て、適切な場合だけ `build_expand_prompt.py` 相当へ進む。
- `approve`, `export`, `health` は後続 phase の CLI へ委譲する。
- 既存 script は残す。
- subprocess 乱用ではなく、可能な範囲で既存関数を import して使う。ただし大規模抽出は避ける。

### Acceptance Criteria

- 既存 script の CLI が壊れない。
- 統合 CLI は各 stage の stdout に、次の推奨操作を 1 行で出す。
- `planning_gate_status != ready` の場合、`prompt` または `prepare --strict` が本文生成へ進めない。
- `repair` は format / forbidden / over max では expansion を生成しない。
- `python -m pytest tests/ -q` が通る。

## Phase 2: Approval Gate and Export

### Purpose

機械チェック済みの scene を、人間承認を経て export 対象にする。Novel-OS の `approve` / `export` 発想を、軽量 Markdown/JSON で実装する。

### Target Files

- `scripts/approve_scene.py`
- `scripts/export_manuscript.py`
- `scripts/novel_agent/approvals.py`
- `scripts/novel_agent/exports.py`
- `tests/test_scripts.py`
- `README.md`

### Approval Ledger

Path:

```text
<project>/runtime/approval_ledger.json
```

Schema:

```json
{
  "version": 1,
  "updated_at": "...",
  "scenes": {
    "2-3": {
      "status": "approved|blocked|revoked",
      "approved_at": "...",
      "approved_by": "user|system",
      "scene_path": "chapter_02_scene_03.txt",
      "check_report_path": "runtime/scenes/2-3/draft/check_report.json",
      "check_status": "pass",
      "content_hash": "...",
      "notes": ""
    }
  }
}
```

### CLI

```bash
python scripts/approve_scene.py --project <project> --scene 2-3
python scripts/approve_scene.py --project <project> --scene 2-3 --allow-warnings
python scripts/approve_scene.py --project <project> --scene 2-3 --revoke

python scripts/export_manuscript.py --project <project> --format markdown
python scripts/export_manuscript.py --project <project> --format markdown --include-warnings
```

### Gate Rules

- `check_report.json` が存在しない scene は承認不可。
- `status=fail` は承認不可。
- `status=warning` は `--allow-warnings` がない限り承認不可。
- 承認時に scene txt の content hash を保存する。
- 承認後に scene txt が変わった場合、approval は stale または blocked として扱う。
- export は approved scene のみ対象にする。
- outline の scene order を正本にして結合する。

### Export Output

MVP:

```text
<project>/exports/manuscript.md
```

Format:

```markdown
# <project name>

## 第1章

<scene 1-1>

<scene 1-2>
```

### Acceptance Criteria

- `status=fail` の scene は approve できない。
- `status=warning` は flag なしで approve できない。
- approved scene だけ export される。
- scene hash 変更後の stale approval が検出される。
- export は `body.md` ではなく scene txt を読む。
- `python -m pytest tests/ -q` が通る。

## Phase 3: Scene Obligation Contract

### Purpose

シーンの「今果たすべきこと」を writer / checker / repair が同じ契約として扱えるようにする。

### Target Files

- `scripts/build_runtime_context.py`
- `scripts/check_scene_output.py`
- `scripts/novel_agent/obligations.py`
- `templates/05_chapter_outline.md`
- `tests/test_scripts.py`
- `agent/skills/novel-writer/SKILL.md`
- `agent/skills/consistency-auditor/SKILL.md`
- `agent/skills/revision-editor/SKILL.md`

### Contract Source

MVP では `05_chapter_outline.md` の Scene Ledger 既存列を活用する。

既存列:

- `purpose`
- `turn`
- `payoff_or_seed`
- `depends_on`
- `status`

必要なら将来列:

- `must_hit_now`
- `must_preserve`
- `can_defer`
- `forbidden_crossings`

ただし初回実装では template の大変更を避け、`scene_brief_compact.md` に以下を生成する。

```markdown
## Obligation Contract
- must_hit_now: <purpose / payoff_or_seed から抽出>
- must_preserve: <depends_on / continuity から抽出>
- can_defer: <任意、空可>
- forbidden_crossings: <style / state から抽出、空可>
```

同時に machine-readable copy を生成する。

Path:

```text
runtime/scenes/<scene>/draft/obligation_contract.json
```

Schema:

```json
{
  "version": 1,
  "scene_id": "2-3",
  "must_hit_now": [],
  "must_preserve": [],
  "required_payoff_touches": [],
  "required_dependencies": [],
  "can_defer": [],
  "forbidden_crossings": []
}
```

### Check Rules

Deterministic MVP は意味理解をやりすぎない。

- `required_dependencies` の scene txt が存在しなければ blocking。
- `must_hit_now` が空で、scene type が `anchor` / `climax` なら warning。
- `payoff_or_seed` があるのに contract に入っていなければ warning。
- `forbidden_crossings` は literal/style rules の範囲だけ検査する。
- 創作意味の達成判定は LLM judge ではなく、人間/後段監査へ残す。

### Acceptance Criteria

- `build_runtime_context.py` が obligation contract を生成する。
- `check_scene_output.py` が dependency 欠落を blocking issue にできる。
- `check_report.json` に `obligation_status` と `obligation_issues` を additive に出す。
- `quality_budget_ledger.json` は obligation issue を通常の expansion 対象にしない。
- `python -m pytest tests/ -q` が通る。

## Phase 4: Memory Sync / Project Health Check

### Purpose

novel-bot の sync 発想を取り込み、再開前・export 前に project の同期不整合をまとめて検出する。

### Target Files

- `scripts/sync_project_health.py`
- `scripts/novel_agent/health.py`
- `tests/test_scripts.py`
- `agent/skills/resume-orchestrator/SKILL.md`
- `README.md`

### CLI

```bash
python scripts/sync_project_health.py --project <project>
python scripts/sync_project_health.py --project <project> --fix-safe
python scripts/sync_project_health.py --project <project> --json
```

### Health Report

Path:

```text
<project>/runtime/health_report.json
```

Schema:

```json
{
  "version": 1,
  "created_at": "...",
  "status": "pass|warning|fail",
  "blocking_issues": [],
  "warnings": [],
  "info": []
}
```

### Checks

Blocking:

- outline が存在しない。
- scene txt があるのに読めない。
- approved scene の content hash が変化している。
- `status=completed` なのに scene txt がない。

Warning:

- `scene_summaries.jsonl` が scene txt より古い。
- `story_state.json` に最新 checked scene が反映されていない。
- `artifact_ledger.json` に stale artifact が残っている。
- `runtime_index.json` と scene-scoped runtime が不一致。
- `trace.jsonl` が存在しない、または最後の重要イベントが古い。
- outline status と `check_report.json` が矛盾する。

Info:

- scene count
- approved scene count
- latest checked scene
- token ledger total estimate
- quality budget exhausted scene count

### Safe Fixes

`--fix-safe` で許可する修復:

- `scene_summaries.jsonl` の再生成。
- `story_state.json` の空初期化または check report からの再同期。
- `trace_min.txt` / `trace_view.txt` の再生成。
- health report の保存。

許可しない修復:

- scene txt の上書き。
- outline の自動変更。
- approval の自動削除。
- user content の削除。

### Acceptance Criteria

- health check は project を破壊しない read-mostly operation。
- `--fix-safe` は安全な派生物だけ再生成する。
- export 前に `status=fail` なら export script が警告または停止できる。
- `python -m pytest tests/ -q` が通る。

## Phase 5: Anti-AI Style Gate

### Purpose

autonovel の anti-slop / anti-pattern 発想を、毎 scene で無料・deterministic に回せる範囲で取り込む。

### Target Files

- `scripts/novel_agent/text_quality.py`
- `scripts/novel_agent/anti_ai_style.py`
- `scripts/check_scene_output.py`
- `tests/test_scripts.py`
- `agent/skills/prose-polisher/SKILL.md`
- `agent/skills/consistency-auditor/SKILL.md`

### New Warning Types

MVP warning:

- `over_explain_pattern`
- `triadic_listing_pattern`
- `uniform_paragraph_length`
- `repeated_sentence_ending`
- `scene_summary_imbalance`
- `dialogue_as_exposition`
- `negative_assertion_repetition`

### Detection Rules

All rules must be deterministic and conservative.

- 誤検出しやすいものは `warning` にする。
- `fail` に昇格するのは、既存の format / forbidden / length / dependency 欠落だけ。
- 本文中の引用・会話で出た語句を即禁止しない。
- 日本語本文を前提に、句点 `。` と改行で粗く分割する。
- 英語向け anti-slop list をそのまま literal 禁止語にしない。

### Report Additions

`check_report.json` に additive に追加する。

```json
{
  "anti_ai_style": {
    "status": "pass|warning",
    "warnings": [
      {
        "type": "over_explain_pattern",
        "message": "...",
        "evidence": "..."
      }
    ]
  }
}
```

既存 top-level `warnings` にも、同じ warning を `type=anti_ai_style:<name>` として反映する。

### Acceptance Criteria

- anti-AI warning だけでは `status=fail` にならない。
- `check_report.json` 旧 field は維持される。
- warning evidence は短く、本文全文を重複保存しない。
- false positive が出ても repair loop が無限化しない。
- `python -m pytest tests/ -q` が通る。

## Documentation Updates

更新対象:

- `README.md`
- `agent/HUB.md`
- `agent/skills/novel-writer/SKILL.md`
- `agent/skills/revision-editor/SKILL.md`
- `agent/skills/consistency-auditor/SKILL.md`
- `agent/skills/prose-polisher/SKILL.md`

追加する説明:

- 統合 CLI の推奨コマンド。
- approve/export の完了条件。
- obligation contract の位置づけ。
- project health check の使い方。
- anti-AI style warning は fail ではなく推敲・監査への入力であること。

## Cross-Phase Quality Gates

毎 phase:

```bash
python -m pytest tests/ -q
```

代表 smoke:

```bash
python scripts/run_scene_pipeline.py prepare --project <project> --chapter 2 --scene 2-3
python scripts/run_scene_pipeline.py prompt --project <project> --chapter 2 --scene 2-3
python scripts/run_scene_pipeline.py check --project <project> --text <scene_txt>
python scripts/sync_project_health.py --project <project>
python scripts/approve_scene.py --project <project> --scene 2-3
python scripts/export_manuscript.py --project <project> --format markdown
```

## Done Definition

- 統合 CLI から日常 scene flow を実行できる。
- `status=fail` の scene は承認・export されない。
- approved scene だけで `exports/manuscript.md` を生成できる。
- obligation contract が runtime と check report に出る。
- dependency 欠落が blocking issue として扱われる。
- health check が project の同期不整合を検出する。
- anti-AI style warning が check report に出る。
- 既存 script の直接実行フローが壊れていない。
- `python -m pytest tests/ -q` が通る。
