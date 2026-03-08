# Skill / Runtime Workflow Refactor Specification

Status: draft
Date: 2026-03-08
Owner: Codex review memo

## 1. Purpose

小説プロジェクトの初期化、企画立ち上げ、再開、シーン設計、本文執筆の連携を見直し、以下の不具合を再発しない運用仕様を定める。

- 作品テーマやログラインの検討前に、目標文字数が確定しないまま進行する
- `scene-planner` の handoff で `Length Band` が落ちる
- 中断再開後に `runtime/` が stale なまま使われる
- 依存シーン未生成でも後続シーンへ進めてしまう
- `state_schema_novel.yaml` が実ファイル状況を十分に反映しない

この文書はリファクタリング実装の仕様書であり、コード差分そのものではない。

## 2. Background

今回の観測事象は以下。

- 対象案件: `源一じいさんの日常系タイムリープ`
- 企画立ち上げ時点では `Target Total Chars` が先に固定されず、後から `30000` 指定が追加された
- `runtime/resume_brief.md` は `chapter 1 scene 1 の準備段階` を示していた
- 同時に `runtime/scene_brief_compact.md` と `runtime/check_report.json` は `scene 1-3` を示していた
- `chapter_1_introduction/scene_1-2.txt` は存在しないのに `scene_1-3.txt` が存在した
- プランニング時に、執筆へ渡すべき文字数帯が返答に明示されなかった

この事象は単発ではなく、現行スキル責務と runtime artifact 設計の境界不備で再発しうる。

## 3. Scope

本仕様の対象は以下。

- `idea-generator`
- `project-bootstrap`
- `setting-creator`
- `scene-planner`
- `novel-writer`
- `resume-orchestrator`
- `scripts/init_project.py`
- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/check_scene_output.py`
- `state_schema_novel.yaml`
- `runtime/` artifact 命名と配置
- 関連テスト、eval、受け入れ条件

## 4. Non-Goals

今回の対象外は以下。

- 文章品質そのものの改善
- プロット内容の良し悪しの評価
- UI 実装
- LLM プロンプト文面の微調整だけで解決する対症療法

## 5. Current Problems

### P1. 目標文字数の確定タイミングが遅い

- `idea-generator` が長さ目標を必須入力として扱っていない
- `project-bootstrap` では必須と書かれているが、実運用では前段未確定のまま流入できる
- `init_project.py` が `--target-total-chars` 未指定でも `100000` に fallback して続行する
- その結果、企画の粒度や構成判断が長さ未確定のまま進む

### P2. `scene-planner` から `novel-writer` への handoff 契約が弱い

- `scene-planner` の期待責務には `Scene Type` / `Length Band` が必要
- しかし出力 contract に `Length Band` を返す必須項目がない
- その結果、執筆開始時に文字数帯が会話履歴依存になりやすい

### P3. `runtime/` artifact が単一ファイル名で上書きされる

- `resume_brief.md`
- `scene_brief_compact.md`
- `check_report.json`
- `draft_prompt.txt`

これらがプロジェクト全体で単一名のため、別シーン・別モードの artifact が混在する。

### P4. stale 判定はスキルに書かれているが、スクリプト側で担保されていない

- `resume-orchestrator` は stale を検知すべき設計になっている
- しかし `build_runtime_context.py` は渡された `chapter/scene` をそのまま `resume_brief` 化する
- 実ファイルと矛盾する `Current Position` が生成されうる

### P5. 依存シーン欠落時の停止条件がない

- `Depends On` は `scene_brief_compact.md` に出る
- しかし `novel-writer` 実行前や runtime 生成前に必須依存の存在確認を行っていない
- その結果、`1-2` 未作成でも `1-3` が進行できる

### P6. 進捗正本が更新されない

- `active_work.active_scene`
- `progress.current_scene`
- `completed_scene_count`
- Scene Ledger の `status`

これらが本文生成後や再開判断後に同期更新されないため、再開時に毎回推定に頼る。

### P7. テストが境界ケースを十分に覆っていない

- `Target Total Chars` 未確定での起票停止
- stale runtime の差し戻し
- 依存シーン欠落時の停止
- `scene-planner` 出力への `Length Band` 含有
- late target confirmation を持つ既存案件の移行

これらが自動回帰に入っていない。

## 6. Design Principles

### 6.1 Length-first

企画初期段階では、テーマやログラインの固定より先に `Target Total Chars` を確定する。

### 6.2 Runtime is scene-scoped

runtime artifact は「案件全体で1個」ではなく、「対象 scene / mode 単位」の識別を持つ。

### 6.3 File reality beats stale summaries

再開判断では、自然言語要約よりも実在する `txt`、最新チェック結果、依存関係、進捗 state を優先する。

### 6.4 Handoff must be explicit

次スキルへ渡す情報は、会話文脈に期待せず artifact と output contract に明示する。

### 6.5 Stop before inconsistency

不整合を検出したら「それでも先へ進む」のではなく、停止または差し戻しを標準挙動とする。

## 7. Functional Requirements

### FR-1. 企画立ち上げ時に `Target Total Chars` を先に確定する

#### Requirements

- `idea-generator` は、テーマ・ログライン・世界観フックの固定前に `Target Total Chars` を確認する
- 許容値は `30000 / 50000 / 100000`
- `Target Length Profile` を使う場合も、内部では必ず canonical な `Target Total Chars` に正規化する
- 長さ未確定なら、ログラインの確定と project handoff を行わない

#### Notes

- 現案件のように「後から 30000 を追加指定」したケースは legacy / migration 対象として扱う
- 既存案件では、後追い確定を禁止するのではなく、「late confirmed」であることを state に残す

### FR-2. `project-bootstrap` は長さ未確定の案件を初期化しない

#### Requirements

- `project-bootstrap` は `Target Total Chars` または canonical 化済み `Target Length Profile` が無い場合、停止する
- `init_project.py` は `--target-total-chars` 必須とし、黙って fallback しない
- 既存案件への agent 運用追加では、対象案件に canonical target fields が無い場合は補完タスクへ誘導する

### FR-3. target 確定の履歴を state に残す

#### Requirements

- `state_schema_novel.yaml` に target 確定状態を保持する
- 最低限、以下の情報を持つ
- `target_confirmed: true/false`
- `target_confirmation_source: initial|late_update|migration`
- `target_confirmed_at`
- `target_confirmed_by: user|migration|system`

#### Goal

- 「今の `30000` は最初から決まっていたのか、途中追加なのか」を後から識別できるようにする

### FR-4. `scene-planner` の output contract を拡張する

#### Requirements

- `Write Next` は単なる scene ID ではなく、以下を含む
- `Scene ID`
- `Scene Type`
- `Length Band`
- `Depends On`
- `Output Path`
- `Read First` は最大3件を維持する
- `scene-planner` の返答だけで `novel-writer` が必要文字数帯を失わないこと

### FR-5. runtime artifact を scene / mode 単位に識別可能にする

#### Requirements

- `runtime/` artifact は、少なくとも `chapter`, `scene`, `mode`, `generated_at` を識別可能にする
- 命名で識別する方法でも、index ファイルを置く方法でもよい
- ただし「単一の `scene_brief_compact.md` を常に上書きする」構成は不可
- `check_report.json` も対象 scene と1対1に対応させる

#### Minimum acceptance

- `resume` 用 artifact と `draft` 用 artifact が混在しても、対象 scene の取り違えが起きない

### FR-6. 再開判断は実ファイル優先で行う

#### Requirements

- `resume-orchestrator` は、以下の優先順で現在地を推定する
- 実在する scene `txt`
- scene 依存関係
- 最新の scene 対応 `check_report`
- `runtime/resume_brief`
- `state_schema_novel.yaml`
- `session_notes`
- `resume_brief` が `未着手` を示していても、対象 scene `txt` またはその後続 scene の `txt` が存在するなら stale 扱いにする
- `scene_brief` / `check_report` / 実シーン群が互いに別 scene を指す場合は、runtime 再生成または差し戻しを返す

### FR-7. 依存シーン欠落時は後続シーンへ進めない

#### Requirements

- `scene-planner` と `novel-writer` は `Depends On` を必須確認する
- 依存先 scene `txt` が無い場合、後続シーンの draft 生成を止める
- 代替として許されるのは以下のみ
- 依存先シーンを新規に書く
- 依存先を飛ばしてよいとユーザーが明示確認する
- Scene Ledger 側の依存関係を見直す

#### Example

- `1-3` が `Depends On: 1-2` を持つなら、`scene_1-2.txt` 不在時に `scene_1-3.txt` の執筆へ進まない

### FR-8. 執筆完了後に progress を同期更新する

#### Requirements

- scene `txt` 保存後に、最低限以下が同期される
- `active_work.active_scene`
- `progress.current_scene`
- `progress.completed_scene_count`
- 可能なら `05_chapter_outline.md` の該当 Scene Ledger `status`
- `check_report` の対象 scene と progress の対象 scene が一致すること

### FR-9. 既存案件の migration を定義する

#### Requirements

- 既存案件で canonical target が後追い追加された場合、案件を壊さずに取り込めること
- 既存の単一 runtime artifact が残っていても、新仕様で stale と判定できること
- migration 時は以下をレポートする
- target 確定状態
- runtime stale 有無
- 欠落 scene
- state と実ファイルの不一致

## 8. Required Output Contracts

### 8.1 `idea-generator`

- 現段階の長さ目標
- その長さに適した企画粒度の前提
- 未確定なら次の確認質問

### 8.2 `project-bootstrap`

- `Current State`
- `Target`
- `Planning Gate`
- `Next Skill`
- `Read First`

ここで `Target` が空欄になることは不可。

### 8.3 `scene-planner`

- `Planning Scope`
- `Scene Beats`
- `Write Next`
- `Read First`

`Write Next` には `Scene Type` と `Length Band` を必須含有とする。

### 8.4 `resume-orchestrator`

- `Current Position`
- `Open Items`
- `Next Action`
- `Recommended Skill`
- `Read First`

`Current Position` は実ファイルと矛盾しないこと。

## 9. State Schema Changes

以下の新設または拡張を想定する。

- `targets.target_confirmed`
- `targets.target_confirmation_source`
- `targets.target_confirmed_at`
- `targets.target_confirmed_by`
- `active_work.runtime_mode`
- `active_work.runtime_scene`
- `active_work.runtime_generated_at`
- `progress.last_checked_scene`
- `progress.last_completed_scene`

名称は実装時に多少調整してよいが、意味は維持すること。

## 10. Runtime Layout Requirements

許容案は複数あるが、満たすべき条件は以下。

- scene ごとに artifact が識別できる
- mode ごとに artifact が識別できる
- 最新採用版が判別できる
- 旧 artifact が stale として検出できる

実装候補:

- `runtime/scenes/1-2/draft/...`
- `runtime/scenes/1-2/check/...`
- `runtime/resume/1-2/...`
- `runtime/index.json`

実装候補は例であり、固定仕様ではない。

## 11. Acceptance Criteria

### AC-1. Length-first 起票

- 新規企画で `Target Total Chars` 未指定のままログライン確定や初期化へ進まない

### AC-2. Bootstrap strictness

- `init_project.py` は長さ未指定で成功終了しない

### AC-3. Planner handoff completeness

- `scene-planner` の `Write Next` に `Length Band` が含まれる

### AC-4. Runtime consistency

- `resume` と `draft` の artifact が別 scene を指す場合、取り違えず stale 判定できる

### AC-5. Dependency stop

- `scene_1-2.txt` が無い状態で `scene_1-3` の draft 作成に進まない

### AC-6. Resume correctness

- `resume_brief` が `未着手` を示していても、実在 scene に応じて上書き判断できる

### AC-7. Existing project migration

- 後追いで `30000` が設定された既存案件を壊さず、新 state へ移行できる

## 12. Test Requirements

最低限、以下を自動テストに追加する。

1. `idea-generator` / `project-bootstrap` 境界で、target 未確定なら handoff しない
2. `init_project.py` が長さ未指定で失敗する
3. `scene-planner` 出力に `Scene Type` と `Length Band` が含まれる
4. `resume_brief` が実ファイルと矛盾する場合に stale と判定する
5. `scene 1-2` 欠落時に `scene 1-3` 執筆へ進まない
6. `check_report` と `scene_brief` が別対象なら runtime stale と判定する
7. late target confirmation を持つ既存案件が migration できる

## 13. Migration Policy

### Existing projects

- 既存案件は即時破棄しない
- 初回アクセス時に migration チェックを実行する
- late confirmed target を持つ案件は有効案件として扱う
- ただし「いつ確定したか不明」の場合は `migration` ソースとして記録する

### Legacy runtime artifacts

- 旧単一ファイル runtime は読み取り専用の legacy artifact として扱う
- 新規生成時は新レイアウトへ再出力する
- legacy artifact と新 artifact が矛盾したら、新 artifact を優先する

## 14. Risks

- 厳格化により初期対話のテンポが少し落ちる
- 既存案件 migration の実装を雑にすると、逆に stale 判定が増えすぎる
- Scene Ledger の `depends_on` 記述が雑な案件では、停止判定が過剰に出る可能性がある

ただし、現在の「誤って先へ進んでしまう」リスクよりは小さい。

## 15. Implementation Priority

1. `Target Total Chars` の先行確定と fallback 廃止
2. 依存シーン欠落時の停止
3. runtime artifact の scene / mode 分離
4. `resume` の実ファイル優先判定
5. `scene-planner` の handoff 拡張
6. progress / state 同期
7. migration と回帰テスト整備

## 16. Open Questions

- `theme` の定義をどこまで広く取るか
- `Target Total Chars` を `idea-generator` で必ず質問するか、最初のユーザー入力に含まれていなければ即確認するか
- Scene Ledger `status` を state とどちらが正本にするか

以上を未確定事項として残すが、リファクタリング着手の前提条件にはしない。
