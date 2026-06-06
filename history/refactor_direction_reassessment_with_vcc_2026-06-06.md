# VCC とローカル参考リポジトリを踏まえたリファクタリング方針再検討

Date: 2026-06-06

## Scope

対象:
- `Agent_helper_for_novel_writing`
- ローカル参考リポジトリ: `../参考/*`
- 特に `../参考/VCC`

現リポの目的:
- AIエージェントを使って長編小説を作成する。
- 長編化に伴う利用枠・トークン・再読込コストを、品質を落とさずに下げる。
- 進化している agent 技術を、現行の軽量 Markdown/CLI/runtime-first 設計に合う形で取り込む。

## 前回方針からの変更点

前回は「central JSON state」「quality gate」「related context pack」を主軸にした。

今回、VCC を読んだ結果、優先順位を変える。

新しい主軸:

1. 要約を増やす前に、正本を索引化する。
2. 常時投入する文脈を増やすのではなく、必要な時だけ正本へ戻れる projection/view を作る。
3. LLM に読ませる前に、ローカルで検索・検査・候補抽出する。
4. chapter/scene/story state だけでなく、agent との会話や判断履歴も「復元可能な正本」として扱う。

つまり、単なる RAG 化ではなく **VCC 型の view-oriented context compiler** を小説執筆ドメインへ移植する方向が強い。

## VCC から取り込むべき本質

VCC の価値は「会話ログを要約して保存すること」ではない。

取り込むべき点:

- 元 JSONL を正本として保持する。
- full view / min view / grep view を同じ行番号座標で生成する。
- grep 結果が単なる行ではなく、role と block range pointer を持つ。
- 要約では失われる「なぜそう判断したか」を後から元ログへ戻って確認できる。
- dynamic projection なので、事前に巨大な memory / embedding / graph を作らなくても使える。
- stats footer で token 使用量を集計し、利用枠消費の可視化にも使える。

小説リポへの翻訳:

- `scene txt`、`05_chapter_outline.md`、`runtime/*.md`、`check_report.json`、`agent/memory/*.md` をただ読むのではなく、役割付き block と line range を持つ view に変換する。
- `draft_prompt.txt` は最終出力ではなく、compiler が作った一時 view として扱う。
- `resume_brief.md` は要約正本ではなく、正本へ戻るための pointer を持つ resume view にする。
- 重要判断や user 指示は `agent_trace.jsonl` 的な project-local log に落とし、VCC 型に復元できるようにする。

## 参考リポジトリ別の再評価

### VCC

最重要。

採用:
- full/min/search view
- block range pointer
- role-aware grep
- compile-on-demand
- token/stat accounting

見送り:
- Claude Code JSONL への密結合
- conversation log 専用の tool call parser

現リポ向けに作るなら:
- `scripts/compile_project_context.py`
- 入力: project root, chapter, scene, mode, optional grep
- 出力:
  - `runtime/context_full.txt`
  - `runtime/context_min.txt`
  - `runtime/context_view.txt`
  - `runtime/context_index.json`

### novel-bot

採用:
- filesystem as memory
- global memory と chapter memory の分離
- progress check

注意:
- `STORY_SUMMARY.md`、recent chapter summaries、outline、characters を常時 prompt に入れる設計は長編で太りやすい。

現リポでは:
- `chapter memory` は常時全文投入しない。
- `scene_summaries.jsonl` / `chapter_summaries.md` に pointer を持たせる。
- prompt へは「現在 scene に必要な 2-5 件だけ」投影する。

### autonovel

採用:
- deterministic slop detector
- evaluator before expensive revision
- state.json with phase/debts
- revision loop budget and plateau stop
- adversarial cuts / over-explain detection

注意:
- フル自動 pipeline と LLM judge は利用枠消費が大きい。

現リポでは:
- `check_scene_output.py` をまず強化する。
- LLM judge は daily/章末/巻末だけに限定し、毎 scene では使わない。
- 「評価で低かったから全再生成」ではなく、現行の `build_expand_prompt.py` / `apply_expand_edits.py` 型の局所修正を維持する。

### Novel-OS

採用:
- structured `story_state.json`
- deterministic continuity engine
- Character / PlotThread / ChapterState / TimelineEvent のデータ分解

注意:
- 章単位 state は便利だが、現リポは scene ledger が正本なので、scene 粒度を失ってはいけない。

現リポでは:
- `runtime/story_state.json` を導入する場合、chapter ではなく scene-first にする。
- `characters`, `threads`, `timeline`, `payoffs`, `style_profile` は採用候補。

### AI-Novel-Writing-Assistant

採用:
- Director artifact ledger
- content hash / version / dependency / stale detection
- quality loop budget ledger
- canonical state snapshot
- model route / prompt version / repair ticket の追跡

注意:
- Express/Prisma/LangGraph/Qdrant/React を現リポへ入れるのは過剰。

現リポでは:
- DB ではなく JSON ledger で十分。
- `artifact_ledger.json` で `outline`, `style_contract`, `scene_brief`, `draft`, `check_report`, `expand_patch` の依存を追跡する。
- 同じ問題への修復試行回数を `quality_budget_ledger.json` で制限する。

### graphify-novel

採用:
- bible を正本、graph を関係性レイヤーとして分ける考え方。
- character/thread/world/timeline の Markdown schema。
- review と update を分離する運用。

注意:
- graphify 導入は依存が増える。
- 最初から graph 抽出を必須にすると軽量性を失う。

現リポでは:
- まず `bible/` 相当を `agent/state/` または `runtime/story_state.json` で軽く実装。
- graph は optional future work。

### Long-Novel-GPT

採用:
- 既存本文の import / summarization / outline sync。
- cost 表示。
- context generation prompt の分離。

注意:
- マルチスレッド大量生成は、現目的では後回し。

現リポでは:
- cost/token accounting を `runtime/token_ledger.jsonl` に入れる。
- 関連本文検索は embedding なしの lexical retrieval から始める。

### storycraftr

採用:
- assistant graph / retriever の発想は参考程度。

見送り:
- LangChain/Chroma は現時点では過剰。

## 改訂後のアーキテクチャ方針

### 1. Context Compiler Layer を追加する

新規概念:
- `Context Compiler`: 正本ファイルから小さい実行 view を作る。
- `Projection`: draft/resume/review/repair 用の view。
- `Pointer`: 正本ファイルと line/block range への参照。

想定ファイル:

```text
scripts/compile_project_context.py
scripts/compile_agent_trace.py
scripts/search_project_context.py
scripts/build_scene_index.py
```

想定出力:

```text
runtime/context/
  context_full.txt
  context_min.txt
  context_view.txt
  context_index.json
  token_ledger.jsonl
```

`build_runtime_context.py` は肥大化した generator から、compiler の projection consumer へ寄せる。

### 2. 常時投入文脈をさらに減らす

現行:
- `style_contract_compact.md`
- `scene_brief_compact.md`
- `continuity_pack.md`
- `request_compact.md`
- `planning_gate_brief.md`

改訂:
- `draft_prompt.txt` は以下だけを基本にする。
  - Style Contract: 300-800 tokens
  - Scene Mission: 300-800 tokens
  - Immediate Previous: 600-1500 tokens
  - Related Pointers: 3-8 件、各 1-2 行
  - Hard Constraints: 10-20 行

本文・設定の長い抜粋は入れない。必要なら pointer から復元する。

### 3. Story State は「圧縮要約」ではなく「可検査な台帳」にする

`runtime/story_state.json` は prose summary ではなく、検査と検索に使う小さい事実台帳にする。

初期 schema:

```json
{
  "version": 1,
  "active_scene": "2-3",
  "characters": {},
  "threads": {},
  "payoffs": {},
  "timeline": [],
  "style_profile": {},
  "open_questions": [],
  "continuity_findings": []
}
```

自由文 summary は別ファイルに逃がす。

### 4. Artifact Ledger を導入する

AI-Novel-Writing-Assistant の artifact ledger を軽量化して採用する。

```json
{
  "artifacts": [
    {
      "id": "scene_brief:2-3",
      "type": "scene_brief",
      "path": "runtime/scenes/2-3/draft/scene_brief_compact.md",
      "content_hash": "...",
      "status": "active",
      "depends_on": ["outline:05_chapter_outline.md", "state:story_state"],
      "updated_at": "..."
    }
  ]
}
```

目的:
- stale runtime を機械判定する。
- outline 変更後に、どの scene brief / draft prompt が古いか分かる。
- user edited content を保護する。

### 5. Quality Budget Ledger を導入する

同じ問題で agent が何度も修復を繰り返して利用枠を消費するのを止める。

現行の novel-writer は最大3回修正という指示を持つが、問題 signature の永続化はない。

追加:

```json
{
  "entries": [
    {
      "signature": "2-3|under_min|standard|1000",
      "patch_repair_count": 1,
      "rewrite_count": 0,
      "replan_count": 0,
      "next_action": "patch_repair"
    }
  ]
}
```

遷移:
- 1回目: patch repair
- 2回目: scene rewrite
- 3回目: replan scene/window
- 以降: defer and ask/review

### 6. Deterministic Quality Gate を強化する

`check_scene_output.py` に severity を入れる。

追加カテゴリ:
- `critical`: 形式違反、依存欠落、min 未満、max 大幅超過、未閉じ会話。
- `warning`: 重複段落、同一文末連続、台詞比率偏り、説明過多疑い、伏線未接触。
- `info`: paragraph count、dialogue ratio、token estimate。

毎 scene の LLM judge は使わない。
LLM judge は以下だけ:
- planning gate 通過前
- chapter 完了時
- 巻/章群の節目
- deterministic gate が repeated warning を出した時

### 7. Agent Trace を project-local に残す

長編では「前回なぜこの判断をしたか」が失われると再読込コストが跳ねる。

追加候補:

```text
agent/trace/
  trace.jsonl
  trace_full.txt
  trace_min.txt
  trace_view.txt
```

VCC をそのまま使うのではなく、現リポ用 JSONL schema を作る。

event 例:
- `user_instruction`
- `planning_decision`
- `runtime_generated`
- `scene_drafted`
- `check_failed`
- `patch_applied`
- `state_updated`
- `handoff`

この trace を `compile_agent_trace.py` で min/view 化する。

## 変更すべきリファクタリング順

### Phase 0: Behavior lock

- 既存 `python -m pytest tests/ -q` を baseline にする。
- 新規変更はまず tests に入れる。

### Phase 1: text_quality 抽出

目的:
- `check_scene_output.py` のローカル検査を強くする。
- LLM を呼ぶ前に落とせる問題を増やす。

作業:
- `scripts/novel_agent/text_quality.py` を作る。
- 既存の検出関数を移す。
- `severity`, `status`, `blocking_issues`, `warnings` を report に追加。
- 既存 `format_violations` は互換維持。

### Phase 2: context compiler 最小版

目的:
- VCC 型の view-oriented context を導入する。

作業:
- `scripts/compile_project_context.py` を作る。
- まず対象は `05_chapter_outline.md`, scene txt, runtime md のみ。
- full/min/view と pointer index を出す。
- `--grep` は Python regex で block range を返す。

### Phase 3: runtime stale 判定

目的:
- 古い runtime を読んで無駄な執筆・再生成をしない。

作業:
- `runtime/artifact_ledger.json` を導入。
- `build_runtime_context.py` が生成物を ledger 登録する。
- outline/state/scene txt の hash 変化で stale を検出する。

### Phase 4: token/cost ledger

目的:
- 利用枠削減の効果を測れるようにする。

作業:
- `estimate_tokens` を各 runtime section ごとに記録。
- `runtime/token_ledger.jsonl` に projection 名、section tokens、total tokens を保存。
- `build_draft_prompt.py` の警告を ledger ベースにする。

### Phase 5: story_state 最小版

目的:
- 要約ではなく可検査な事実台帳を作る。

作業:
- `runtime/story_state.json` を導入。
- scene ledger と check report から埋められる範囲だけ入れる。
- character/thread 自動抽出は後回し。

### Phase 6: related context view

目的:
- 直前シーン以外の必要文脈を少量だけ入れる。

作業:
- `scene_summaries.jsonl` を作る。
- `compile_project_context.py --grep` または lexical scoring で関連 scene pointer を選ぶ。
- `related_context_pack.md` は抜粋ではなく pointer + one-line summary 中心にする。

### Phase 7: agent trace compiler

目的:
- compaction/resume 時の再探索コストを下げる。

作業:
- `agent/trace/trace.jsonl` を導入。
- runtime scripts が重要イベントを書き込む。
- `scripts/compile_agent_trace.py` で min/view を作る。

## 逆にやらないこと

- いきなり LangChain / Chroma / Qdrant を入れない。
- 現リポを Web アプリ化しない。
- 毎 scene で LLM judge を呼ばない。
- summary を無制限に肥大化させない。
- `body.md` 集約に戻さない。
- prompt を長くして品質を担保する方向へ戻さない。

## 最終方針

現リポはすでに「長編執筆のためにコンテキストを圧縮する」方向へ進んでいる。
ただし次の一手は、単純な要約やRAGではない。

最も価値が高いアップデートは:

> 小説プロジェクト用 VCC、つまり **正本から必要な view を作る context compiler** を追加すること。

これにより:
- 利用枠消費を下げる。
- 要約劣化を避ける。
- 必要時に正本へ戻れる。
- stale runtime を検出できる。
- 同じ修復ループの浪費を止められる。
- 長編でも品質の根拠を失いにくくなる。

最初の実装単位は `check_scene_output.py` の severity 化と `compile_project_context.py` の最小版。
この2つが入ると、以後の story state / artifact ledger / related context / trace compiler が無理なく接続できる。
