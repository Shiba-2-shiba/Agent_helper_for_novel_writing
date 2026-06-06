# VCC Context Refactor Spec

Date: 2026-06-06

## Purpose

本仕様は、長編小説を AI エージェントで作成する際の利用枠・トークン・再読込コストを下げるため、現行の `runtime-first` フローを **VCC 型の view-oriented context compiler** へ段階的に拡張する要件を定義する。

目的は以下の 4 点。

- 長編化しても、毎回フル文脈を読ませない。
- 要約劣化を避け、必要時に正本へ戻れる pointer を保持する。
- LLM を呼ぶ前に、ローカル検査・検索・stale 判定で無駄な再生成を減らす。
- 既存 Markdown/CLI/標準ライブラリ中心の軽量設計を維持する。

## Non-Goals

- Web アプリ化しない。
- LangChain / Chroma / Qdrant / LangGraph を導入しない。
- 毎 scene で LLM judge を呼ばない。
- `body.md` を本文集約先に戻さない。
- 既存 `build_llm_prompt.py` を即時削除しない。
- 既存 `runtime-first` の CLI 互換を壊さない。

## Behavior Lock

実装前に以下を回帰ベースラインとする。

```bash
python -m pytest tests/ -q
```

現時点の直近確認:

- Result: `61 passed in 4.02s`

各 phase は原則として次を守る。

- 実装前に対象挙動の regression test を追加する。
- 既存 JSON フィールドは互換維持する。
- 新しい出力は additive にする。
- Phase ごとに targeted tests を実行する。
- 標準ライブラリで実装する。新依存は入れない。

## Architecture Overview

現行:

```text
outline / state / memory / previous scene
  -> build_runtime_context.py
  -> style_contract_compact.md
  -> scene_brief_compact.md
  -> continuity_pack.md
  -> request_compact.md
  -> build_draft_prompt.py
  -> draft_prompt.txt
```

改訂後:

```text
source artifacts
  -> context compiler
  -> full/min/search views with pointers
  -> runtime projections
  -> draft/resume/review/repair prompts
  -> deterministic quality gates
  -> artifact + token + quality ledgers
```

新規概念:

- **Source Artifact**: `05_chapter_outline.md`, scene txt, runtime md/json, memory md, trace jsonl などの正本。
- **Block**: 役割・source path・line range を持つ文脈単位。
- **Pointer**: `<path>:<start>-<end>` と block id を持つ参照。
- **Projection**: `draft`, `resume`, `review`, `repair`, `search` 用に切り出した view。
- **Ledger**: artifact freshness、token 使用量、quality loop の状態台帳。

## File Layout

新規または改修候補:

```text
scripts/
  compile_project_context.py
  compile_agent_trace.py
  build_scene_index.py
  search_project_context.py
  novel_agent/
    __init__.py
    text_quality.py
    context_blocks.py
    context_compiler.py
    ledgers.py
    story_state.py
    trace.py

<project>/runtime/
  context/
    context_full.txt
    context_min.txt
    context_view.txt
    context_index.json
  artifact_ledger.json
  token_ledger.jsonl
  quality_budget_ledger.json
  story_state.json
  scene_summaries.jsonl

<project>/agent/trace/
  trace.jsonl
  trace_full.txt
  trace_min.txt
  trace_view.txt
```

`scripts/novel_agent/` は import 用の軽量 package とする。CLI は既存 `scripts/*.py` 形式を維持する。

## Phase 1: Deterministic Quality Gate

### Purpose

`check_scene_output.py` の機械検査を severity 付きにし、LLM を呼ぶ前に修復方針を決められるようにする。

### Target Files

- `scripts/check_scene_output.py`
- `scripts/novel_agent/text_quality.py`
- `tests/test_scripts.py`

### Required Behavior

既存 report の以下は維持する。

- `needs_expand`
- `under_min_for_type`
- `within_max`
- `over_max_for_type`
- `format_violations`
- `format_violations_detail`
- `forbidden_hits`
- `forbidden_hits_detail`

追加 report fields:

```json
{
  "status": "pass|warning|fail",
  "blocking_issues": [],
  "warnings": [],
  "info": [],
  "quality_score_hint": {
    "mechanical_penalty": 0,
    "max_penalty": 10
  }
}
```

Severity rules:

- `fail`: min 未満、max 大幅超過、見出し/箇条書き/メタ出力、未閉じ会話、禁止表現 hit。
- `warning`: 重複段落、台詞比率偏り、文末単調、同一語句近接反復、説明過多疑い。
- `pass`: fail なし、warning が許容範囲。

### Acceptance Criteria

- 既存 61 tests が通る。
- 新規 tests が `status=pass|warning|fail` を検証する。
- 旧フィールドを読む既存フローが壊れない。
- `check_scene_output.py` の CLI 出力は既存 `OK:` 行を維持する。

## Phase 2: Context Compiler MVP

### Purpose

VCC 型の full/min/search view と pointer index を小説 project 用に導入する。

### Target Files

- `scripts/compile_project_context.py`
- `scripts/novel_agent/context_blocks.py`
- `scripts/novel_agent/context_compiler.py`
- `tests/test_scripts.py`

### CLI

```bash
python scripts/compile_project_context.py \
  --project <project_path> \
  --chapter <num> \
  --scene <scene_id> \
  --mode <draft|resume|review|repair> \
  [--grep <regex>] \
  [--runtime_dir <path>]
```

### Inputs

MVP では以下だけ対象にする。

- `05_chapter_outline.md`
- `05_chapter_outline_100k.md` fallback
- scene txt files
- scene-scoped `runtime/scenes/<scene>/<mode>/*.md`
- `runtime/check_report.json`

### Outputs

```text
runtime/context/context_full.txt
runtime/context/context_min.txt
runtime/context/context_view.txt
runtime/context/context_index.json
```

`context_index.json` schema:

```json
{
  "version": 1,
  "project": "...",
  "chapter": 2,
  "scene": "2-3",
  "mode": "draft",
  "created_at": "...",
  "blocks": [
    {
      "id": "outline:2:scene-ledger:2-3",
      "role": "outline",
      "source_path": "05_chapter_outline.md",
      "start_line": 10,
      "end_line": 14,
      "summary": "Scene Ledger row for 2-3",
      "tokens_estimate": 120
    }
  ]
}
```

### View Rules

`context_full.txt`:
- 全 block を順序付きで出力する。
- block header に `id`, `role`, `source`, `lines` を含める。

`context_min.txt`:
- 各 block を 1-5 行に圧縮する。
- 長文本文は excerpt ではなく pointer 中心にする。

`context_view.txt`:
- `--grep` 指定時のみ検索 hit block を出力する。
- hit 行だけでなく block range pointer を必ず出す。

### Acceptance Criteria

- `--grep` が Python regex として動く。
- grep 結果が source path と line range を持つ。
- long scene txt を full prompt にそのまま混ぜない。
- 出力は deterministic。

## Phase 3: Runtime Stale Detection

### Purpose

古い runtime を読んだまま執筆・再生成する無駄を防ぐ。

### Target Files

- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/novel_agent/ledgers.py`
- `tests/test_scripts.py`

### Artifact Ledger

Path:

```text
<project>/runtime/artifact_ledger.json
```

Schema:

```json
{
  "version": 1,
  "updated_at": "...",
  "artifacts": [
    {
      "id": "scene_brief:2-3:draft",
      "type": "scene_brief",
      "path": "runtime/scenes/2-3/draft/scene_brief_compact.md",
      "content_hash": "...",
      "status": "active|stale|superseded|protected",
      "source": "generated|user_edited|migrated",
      "depends_on": [
        {
          "id": "outline:05_chapter_outline.md",
          "content_hash": "..."
        }
      ],
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### Required Behavior

- `build_runtime_context.py` は生成物を ledger 登録する。
- `build_draft_prompt.py` は必須 artifact が stale なら警告または失敗する。
- `--force` で stale を再生成できる。
- user edited artifact は protected 扱いにできる余地を残す。

### Acceptance Criteria

- outline 変更後、既存 scene_brief が stale 判定される。
- stale runtime を使う時に `WARN:` が出る。
- 既存 runtime index と競合しない。

## Phase 4: Token Ledger

### Purpose

利用枠削減の効果を測れるようにする。

### Target Files

- `scripts/build_draft_prompt.py`
- `scripts/build_runtime_context.py`
- `scripts/compile_project_context.py`
- `scripts/novel_agent/ledgers.py`
- `tests/test_scripts.py`

### Token Ledger

Path:

```text
<project>/runtime/token_ledger.jsonl
```

Record schema:

```json
{
  "created_at": "...",
  "command": "build_draft_prompt",
  "projection": "draft",
  "chapter": 2,
  "scene": "2-3",
  "runtime_dir": "...",
  "total_estimated_tokens": 4321,
  "sections": {
    "style_contract": 300,
    "scene_brief": 500,
    "continuity_pack": 1200,
    "request_compact": 400,
    "planning_gate_brief": 300
  },
  "budget": 8000,
  "status": "within_budget|over_budget"
}
```

### Acceptance Criteria

- `build_draft_prompt.py` 実行ごとに token ledger が append される。
- 既存 stdout の token warning は維持する。
- token estimate の関数は既存 `estimate_tokens` を再利用する。

## Phase 5: Story State MVP

### Purpose

自由文要約ではなく、検査可能な小さい事実台帳を作る。

### Target Files

- `scripts/migrate_project_state.py`
- `scripts/check_scene_output.py`
- `scripts/build_runtime_context.py`
- `scripts/novel_agent/story_state.py`
- `tests/test_scripts.py`

### Story State

Path:

```text
<project>/runtime/story_state.json
```

MVP schema:

```json
{
  "version": 1,
  "updated_at": "...",
  "active_scene": "2-3",
  "progress": {
    "completed_scene_count": 0,
    "total_chars_written": 0
  },
  "scenes": {
    "2-3": {
      "status": "planned|drafted|completed|needs_repair",
      "path": "...",
      "actual_chars": 1300,
      "check_status": "pass|warning|fail"
    }
  },
  "characters": {},
  "threads": {},
  "payoffs": {},
  "timeline": [],
  "open_questions": [],
  "continuity_findings": []
}
```

### Required Behavior

- `check_scene_output.py` 後に scene status を更新する。
- `migrate_project_state.py` で既存 project に空 state を作れる。
- 既存 `agent/state_schema_novel.yaml` 同期は維持する。

### Acceptance Criteria

- 既存 project で state 未存在でも各 CLI が壊れない。
- scene check 後に `story_state.json` が更新される。
- YAML と JSON の責務が混同されない。

## Phase 6: Related Context View

### Purpose

直前シーン以外の関連文脈を、全文投入せず pointer と短い要約で渡す。

### Target Files

- `scripts/build_scene_index.py`
- `scripts/build_runtime_context.py`
- `scripts/compile_project_context.py`
- `scripts/novel_agent/context_compiler.py`
- `tests/test_scripts.py`

### Scene Summaries

Path:

```text
<project>/runtime/scene_summaries.jsonl
```

Record schema:

```json
{
  "scene_id": "2-3",
  "chapter": 2,
  "scene": 3,
  "path": "chapter_2_scene_3.txt",
  "summary": "主人公が障害を越える決断をする。",
  "characters": [],
  "threads": [],
  "keywords": [],
  "content_hash": "...",
  "updated_at": "..."
}
```

### Related Context Pack

Path:

```text
runtime/scenes/<scene>/<mode>/related_context_pack.md
```

Format:

```markdown
# Related Context Pack

## Selected Context
- [scene 1-2] <summary> (source: chapter_1_scene_2.txt:1-20)

## Pointers
- outline:05_chapter_outline.md:33-37
- scene:chapter_1_scene_2.txt:1-20
```

### Acceptance Criteria

- `related_context_pack.md` は本文の長い抜粋を含めない。
- 関連候補は lexical scoring または `--grep` 結果から選ぶ。
- 直前 scene full text の既存 `continuity_pack.md` は維持する。

## Phase 7: Agent Trace Compiler

### Purpose

compaction/resume 後に「なぜそう判断したか」を復元できる project-local trace を作る。

### Target Files

- `scripts/compile_agent_trace.py`
- `scripts/novel_agent/trace.py`
- runtime scripts with trace event writes
- `tests/test_scripts.py`

### Trace Log

Path:

```text
<project>/agent/trace/trace.jsonl
```

Record schema:

```json
{
  "created_at": "...",
  "event_type": "runtime_generated",
  "chapter": 2,
  "scene": "2-3",
  "summary": "draft runtime generated",
  "artifacts": ["runtime/scenes/2-3/draft/draft_prompt.txt"],
  "decision": null,
  "evidence": [],
  "tokens_estimate": 4321
}
```

### CLI

```bash
python scripts/compile_agent_trace.py \
  --project <project_path> \
  [--grep <regex>]
```

Outputs:

```text
agent/trace/trace_full.txt
agent/trace/trace_min.txt
agent/trace/trace_view.txt
```

### Acceptance Criteria

- trace compiler は VCC 型の full/min/search view を出す。
- trace が存在しない project でも no-op で成功または明確な `WARN:` を出す。
- resume-orchestrator が将来 trace_min を参照できる形にする。

## Cross-Phase Quality Gates

各 phase の最低確認:

```bash
python -m pytest tests/ -q
```

必要に応じた追加確認:

```bash
python scripts/build_runtime_context.py --project <tmp_project> --chapter 2 --scene 2-3 --mode draft
python scripts/build_draft_prompt.py --project <tmp_project>
python scripts/check_scene_output.py --project <tmp_project> --text <scene_txt>
python scripts/compile_project_context.py --project <tmp_project> --chapter 2 --scene 2-3 --mode draft
```

## Done Definition

全 phase 完了条件:

- 既存 runtime-first フローが維持されている。
- `draft_prompt.txt` の常時投入文脈が増えていない。
- context compiler の pointer から正本へ戻れる。
- stale runtime が検出できる。
- token ledger により、利用枠削減の測定ができる。
- quality budget により、同一問題の無限修復ループを止められる。
- `story_state.json` が要約ではなく事実台帳として使える。
- agent trace の min/view から過去判断を復元できる。
