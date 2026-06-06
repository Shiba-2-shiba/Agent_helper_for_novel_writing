# 外部小説作成リポジトリ調査とリファクタリング取り込み案

Date: 2026-06-06

## Scope

対象リポジトリ: `Agent_helper_for_novel_writing`

目的:
- GitHub 上の類似した小説作成・AI執筆支援リポジトリから、現リポジトリに取り込む価値がある設計を抽出する。
- 既存の `runtime-first`、Markdown テンプレート、agent skills、eval/test 資産を壊さず、段階的にリファクタリングする。

Baseline:
- `python -m pytest tests/ -q`
- Result: `61 passed in 4.02s`

注意:
- `git status --short` は dubious ownership 警告で確認不可。
- 本メモは調査・計画のみ。コード変更は未実施。

## 参照した外部リポジトリ

1. ExplosiveCoderflome/AI-Novel-Writing-Assistant
   - https://github.com/ExplosiveCoderflome/AI-Novel-Writing-Assistant
   - 参考点: idea から世界観、人物、章実行、状態カード、承認ノード、Runtime へつなぐ「AI director」型の長編生成主導線。
   - 現リポへの示唆: UI や LangGraph/DB ではなく、既存 CLI/scripts に「現在フェーズ」「次アクション」「失敗理由」「再開点」を一貫表示する薄い orchestrator を追加する価値が高い。

2. NousResearch/autonovel
   - https://github.com/NousResearch/autonovel
   - 参考点: seed -> foundation -> draft -> revision -> production の pipeline、`state.json`、mechanical evaluator、anti-slop/anti-pattern gate、revision brief。
   - 現リポへの示唆: `check_scene_output.py` を deterministic quality gate に育て、`build_expand_prompt.py` / `apply_expand_edits.py` と接続する。LLM judge は後回し。

3. Anshler/graphify-novel
   - https://github.com/Anshler/graphify-novel
   - 参考点: `bible/` を正本、graph output を関係性レイヤーとして分離し、人物・スレッド・世界要素を追跡する。
   - 現リポへの示唆: いきなり graph 依存を入れず、まず `runtime/story_state.json` または project-local `agent/state/` に character/thread/world fact の正本を分ける。

4. xiaoxiaoxiaotao/novel-bot
   - https://github.com/xiaoxiaoxiaotao/novel-bot
   - 参考点: filesystem as memory、global memory と chapter memory の二層、workspace 内 Markdown ファイルを人間が直接編集できる設計。
   - 現リポへの示唆: 既存の `agent/memory/global_notes.md` と `session_notes.md` は良い方向。章単位 summary を正規化し、context overflow 対策を `find_previous_scene_pack` だけに寄せない。

5. MaoXiaoYuZ/Long-Novel-GPT
   - https://github.com/MaoXiaoYuZ/Long-Novel-GPT
   - 参考点: 既存小説の import、関連本文・剧情纲要の retrieval、本文変更と outline 更新の同期、モデル選択や費用表示。
   - 現リポへの示唆: RAG/vector DB は見送り。ただし scene summary index と関連シーン検索は標準ライブラリだけで先に実装できる。

6. forsonny/book-os
   - https://github.com/forsonny/book-os
   - 参考点: Standards / Novel / Manuscripts の三層文脈。
   - 現リポへの示唆: 現在の template、agent memory、runtime をこの三層に命名・責務整理すると学習コストが下がる。

7. mrigankad/Novel-OS
   - https://github.com/mrigankad/Novel-OS
   - 参考点: agent 出力を structured parser で central JSON state に merge し、各章の continuity/status/score を残す。
   - 現リポへの示唆: YAML を正本にし続けるより、ランタイム生成物は JSON state へ寄せるほうがテストしやすい。既存互換のため YAML は同期先として残す。

8. raestrada/storycraftr
   - https://github.com/raestrada/storycraftr
   - 参考点: simple CLI による story/worldbuilding/outline/chapter 生成。
   - 現リポへの示唆: 本リポも標準ライブラリ CLI の利点がある。重い UI 化より CLI 体験の整理が優先。

## 現リポジトリの強み

- `runtime-first` の思想が既にあり、フル文脈再投入を避ける方向性は外部リポジトリと一致している。
- `05_chapter_outline.md` の Chapter Card / Scene Ledger が、長編の正本として機能している。
- `check_scene_output.py`、`build_expand_prompt.py`、`apply_expand_edits.py` により、生成後の検査と局所差分拡張の流れがある。
- 既存テストが 61 件あり、CLI の主要挙動をかなり保護している。
- Markdown と標準ライブラリ中心なので、利用者が直接編集しやすい。

## 主な弱点

1. `scripts/prompt_utils.py` が 40KB 超で、outline parsing、state sync、runtime path、scene discovery、style contract、dependency check が混在している。
2. `scripts/build_llm_prompt.py` が legacy だが、独自の chapter/context/style 関数を持ち、`prompt_utils.py` と責務が重複している。
3. state が YAML、runtime index JSON、Markdown memory、outline table に散っており、「何が正本か」が機能ごとに違う。
4. quality gate は存在するが、`pass/fail/blocking warning` のレベル付けと pipeline 上の停止条件がまだ弱い。
5. context retrieval は直前シーン中心で、伏線・人物・世界設定の関連取得には伸びしろがある。

## 取り込むべき設計

### A. 三層コンテキスト命名

Book-OS / Novel Bot 型の整理を採用する。

- Standards: 文体、禁止表現、ジャンル作法、出力フォーマット。
- Novel: 作品固有の premise、world、characters、decisions、target profile。
- Manuscript: outline、scene ledger、drafts、runtime、check reports。

現リポでは新規ファイル構造を急に変えず、まず docs/README とコード内の関数名・出力名でこの分類に揃える。

### B. JSON Story State

Novel-OS / autonovel 型の central state を軽量導入する。

候補:
- `runtime/story_state.json`
- `runtime/state_events.jsonl`

初期フィールド:
- `active_scene`
- `characters`
- `threads`
- `world_facts`
- `foreshadowing`
- `continuity_issues`
- `quality_status`
- `propagation_debts`

既存の `agent/state_schema_novel.yaml` は互換のため残し、CLI が必要最小限を同期する。

### C. Mechanical Quality Gate

autonovel の mechanical evaluator 発想を、既存 `check_scene_output.py` に追加する。

既存検査:
- meta commentary
- heading / bullet list
- forbidden terms
- unclosed dialogue
- duplicate paragraphs
- length band

追加候補:
- 似た文末の連続
- 形容詞・副詞過多の簡易検出
- 同一名詞句の近接反復
- dialogue ratio warning
- scene objective missing warning
- unresolved dependency blocking

重要: LLM judge や新依存は入れない。まず deterministic gate のみ。

### D. Related Context Pack

Long-Novel-GPT / graphify-novel から、RAG ではなく軽量 retrieval を取り込む。

実装案:
- scene 作成・検査後に `runtime/scene_summaries.json` を更新。
- `build_runtime_context.py` が target scene の `purpose`、`depends_on`、character names、thread terms から関連 scene を 2-3 件選ぶ。
- 出力は `runtime/scenes/<scene-id>/<mode>/related_context_pack.md`。

標準ライブラリだけで始める。vector DB は不要。

### E. Propagation Debt

autonovel の lore/outline/chapter 伝播負債の考え方を取り込む。

例:
- world fact を変えたら、影響する character sheet / outline / drafted scene を debt として記録。
- debt が残る場合、`resume_brief.md` と `planning_gate_brief.md` に表示。
- blocking debt と warning debt を分ける。

## 見送るべき設計

- LangGraph / LangChain / vector DB / desktop UI / web frontend: 現リポの軽量 CLI/Markdown 設計と衝突しやすい。
- 一括自動生成の多スレッド化: まず state と quality gate が安定してから。
- 5-agent editorial pipeline の完全移植: agent skills は既にあるため、役割追加より状態・検査の共通基盤を先に整える。
- Prompt ギャラリーやスタイル模倣集: 著作権・品質・保守面のリスクが高く、現時点では不要。

## Cleanup Plan

Behavior lock:
- 既存テスト `61 passed` を維持。
- 各 pass の前に対象関数の narrow regression test を追加する。

Pass 1: Package boundary extraction
- `scripts/prompt_utils.py` から純粋関数を分離。
- 予定モジュール:
  - `novel_agent/io.py`
  - `novel_agent/outline.py`
  - `novel_agent/state.py`
  - `novel_agent/runtime.py`
  - `novel_agent/text_quality.py`
- CLI スクリプトは薄い entrypoint にする。

Pass 2: Duplicate removal
- `build_llm_prompt.py` の local parsing/context 関数を `novel_agent/*` に寄せる。
- legacy 動作は維持し、出力文言と exit code はテストで固定する。

Pass 3: Quality gate normalization
- `check_scene_output.py` の report schema に `status`, `blocking_issues`, `warnings`, `details` を追加。
- 既存 `format_violations` は互換維持。
- `build_expand_prompt.py` は `status=fail` と不足字数を明確に読めるようにする。

Pass 4: Story state introduction
- `runtime/story_state.json` を導入。
- `migrate_project_state.py` で既存 project に空 state を作れるようにする。
- YAML 同期は wrapper に閉じ込める。

Pass 5: Related context pack
- `scene_summaries.json` の生成・更新を追加。
- `build_runtime_context.py` に `related_context_pack.md` を追加。
- 直前シーン full text + さらに関連要約、という二段構えにする。

Pass 6: Documentation
- README の workflow を三層コンテキスト + quality gate + story state に整理。
- `history/` の古い refactor docs は消さず、現行計画への索引だけ作る。

## 最初に実装するなら

最小で効果が高い順:

1. `check_scene_output.py` の report schema に `status` と severity を追加する。
2. `prompt_utils.py` から outline parsing だけを `novel_agent/outline.py` に切り出す。
3. `build_llm_prompt.py` の重複 parser を共通関数へ寄せる。
4. `runtime/story_state.json` はまだ空に近い形で導入し、後続 pass の受け皿にする。

この順なら、既存機能の挙動をほぼ変えずに、外部リポジトリの有用な要素を段階的に取り込める。
