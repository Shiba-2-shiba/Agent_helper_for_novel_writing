# 司令塔ハブ (AGENT HUB)

このファイルは、ユーザーの依頼内容から適切なエージェント機能（スキル）を選択し、必要に応じて次のスキルへ安全にハンドオフするためのルーティングハブです。

## エージェント（あなた）への指示

ユーザーからこのファイル（`agent/HUB.md`）を参照するよう指示された場合、あるいは依頼の意図が下記のいずれかに該当する場合、直ちに該当する `agent/skills/<skill-name>/SKILL.md` を読み込み、その手順に従ってタスクを実行してください。

ルーティング時は、以下を優先してください。

- 依頼の主目的を 1 つに絞ってスキルを選ぶ
- 1 回の応答で複数スキルを混在させない
- 途中で依頼の性質が変わった場合のみ、明示して別スキルへ移る
- 通常運用では、本文の正本をシーン単位 `txt` とし、`body.md` を本文追記先として扱わない
- 新規本文の執筆と再開整理は `runtime/` を優先参照する `runtime-first` で扱う
- `runtime/` が未生成、対象シーンと不一致、または欠損している場合のみ、従来の広い文脈へフォールバックする
- `planning_gate_enabled=true` で、`planning_gate_status=ready` になるまで `scene-planner` / `novel-writer` へ進めず、先に `setting-creator` で計画を詰める

### 正式モード名（正本）

以下を、このカタログの正式な `Mode` / `current_mode` 名として扱います。
`request_template.md` の `Mode`、`state_schema_novel.yaml` の `active_work.current_mode`、再開判断はこの表記に揃えてください。

- `idea_generation` → `agent/skills/idea-generator/SKILL.md`
- `project_bootstrap` → `agent/skills/project-bootstrap/SKILL.md`
- `setting_creation` → `agent/skills/setting-creator/SKILL.md`
- `scene_planning` → `agent/skills/scene-planner/SKILL.md`
- `novel` → `agent/skills/novel-writer/SKILL.md`
- `revision` → `agent/skills/revision-editor/SKILL.md`
- `consistency_audit` → `agent/skills/consistency-auditor/SKILL.md`
- `polish` → `agent/skills/prose-polisher/SKILL.md`
- `resume_orchestrator` → `agent/skills/resume-orchestrator/SKILL.md`

---

## 機能マッピング（対応スキル一覧）

### 1. アイディア出し・ブレスト (`idea-generator`)

- 対象ファイル: `agent/skills/idea-generator/SKILL.md`
- 発動条件: 「新しい小説を書きたい」「アイディアを壁打ちしたい」「どんな話にするか一緒に考えて」など、企画の立ち上げ段階
- 主な役割: 発想の発散、ログラインの仮決定、プロジェクト初期化への誘導

### 2. プロジェクト初期化 (`project-bootstrap`)

- 対象ファイル: `agent/skills/project-bootstrap/SKILL.md`
- 発動条件: 「この企画でプロジェクトを作りたい」「箱を作って始めたい」「ログラインから案件を立ち上げたい」など、合意済み企画を実作業用の案件へ変える段階
- 主な役割: プロジェクト名とパスの確定、初期ファイルの用意、次に呼ぶ設計スキルの確定

### 3. 設定構築・プロット整備 (`setting-creator`)

- 対象ファイル: `agent/skills/setting-creator/SKILL.md`
- 発動条件: 「設定を詰めたい」「プロットの土台を作りたい」「設定の矛盾を直したい」など、世界観・人物・大枠構成の整備
- 主な役割: 設定テンプレートの記入、動機や因果の強化、長編骨格の破綻防止

### 4. シーン設計・着手前段取り (`scene-planner`)

- 対象ファイル: `agent/skills/scene-planner/SKILL.md`
- 発動条件: 「次の章の段取りを固めたい」「この章をシーン分解したい」「書く前に次の 1〜3 シーンだけ詰めたい」など、執筆直前の中粒度設計
- 主な役割: 次章または次シーン群の目的整理、シーン順序の確定、執筆前の参照ファイル整理

### 5. 新規本文の執筆 (`novel-writer`)

- 対象ファイル: `agent/skills/novel-writer/SKILL.md`
- 発動条件: 「第◯章を書いて」「続きを書いて」「このシーンの初稿を作って」など、新しい本文の作成
- 主な役割: `runtime/` の圧縮文脈を更新して参照し、新規シーンの執筆、文字数・文体の自己評価、シーン単位 `txt` への出力

### 6. 改稿・リライト (`revision-editor`)

- 対象ファイル: `agent/skills/revision-editor/SKILL.md`
- 発動条件: 「このシーンを書き直して」「テンポを改善して」「方向性は維持したまま修正して」など、既存本文の修正
- 主な役割: 既存稿の問題整理、保持点と変更点の分離、指定方針に沿った再構成

### 7. 整合性監査・診断 (`consistency-auditor`)

- 対象ファイル: `agent/skills/consistency-auditor/SKILL.md`
- 発動条件: 「矛盾がないか見て」「この章の弱点を洗って」「違和感を指摘して」など、診断やレビュー
- 主な役割: 設定・プロット・文体・感情線の監査、問題点と修正方針の提示

### 8. 仕上げ・推敲 (`prose-polisher`)

- 対象ファイル: `agent/skills/prose-polisher/SKILL.md`
- 発動条件: 「読みやすく整えて」「語尾を揃えて」「密度を上げたい」など、完成度向上の調整
- 主な役割: 文体の均し、冗長部の圧縮、読後感と引きの強化

### 9. 再開・進捗整理 (`resume-orchestrator`)

- 対象ファイル: `agent/skills/resume-orchestrator/SKILL.md`
- 発動条件: 「どこから再開すべき？」「前回の続きから進めたい」「今の状態を整理して」など、再開判断や状況整理
- 主な役割: 必要に応じて `runtime/resume_brief.md` を用いた現在地の確認、次の着手点の特定、必要スキルへの橋渡し

---

## 曖昧依頼時の優先順位

依頼が複数スキルにまたがる場合、主目的が明示されていなければ以下の順で判断します。

1. 診断が主目的なら `consistency-auditor`
2. 修正が主目的なら `revision-editor`
3. 新規作成が主目的なら `novel-writer`
4. 執筆直前の段取りなら `scene-planner`
5. 設計変更が主目的なら `setting-creator`
6. 案件の立ち上げなら `project-bootstrap`
7. 再開判断が主目的なら `resume-orchestrator`
8. 方向性の模索が主目的なら `idea-generator`
9. 仕上げ調整が主目的なら `prose-polisher`

### 実運用での判定メモ

- 「見て」「チェックして」「違和感ある？」は、基本的に `consistency-auditor`
- 「直して」「書き直して」「弱いから改善して」は、基本的に `revision-editor`
- 「続きを書いて」「次のシーンを書いて」「本文を作って」は、基本的に `novel-writer`
- 「軽量文脈で書いて」「クレジットを抑えて書いて」「runtime を使って書いて」は、`novel-writer` を選び、`runtime-first` で処理する
- 「この企画で始めたい」「箱を作って」「案件を立ち上げて」は、基本的に `project-bootstrap`
- 「次の章の段取りを詰めたい」「先にシーン構成だけ決めたい」は、基本的に `scene-planner`
- 「整えて」「読みやすくして」「語尾を揃えて」は、基本的に `prose-polisher`
- 「どこから再開？」「今どこまで進んでる？」は、基本的に `resume-orchestrator`
- 「設定を変えたい」「話の土台を変えたい」は、基本的に `setting-creator`

### 迷いやすいケースの優先ルール

- 「続きを見て」は、本文生成ではなく、まず `consistency-auditor`
- 「この章を良くして」は、問題点の指定がなければ、まず `consistency-auditor`
- 「このシーンを完成させて」は、未執筆なら `novel-writer`、既存稿があるなら `revision-editor`
- 「第◯章を書いて。`agent/HUB.md` を参照して」は、`novel-writer` を選び、まず `runtime/` を準備してから執筆する
- 「次を書ける状態にして」は、本文執筆ではなく、まず `scene-planner`
- 「ログラインは決まったから始めたい」は、まず `project-bootstrap`
- 「このままでいい？」は、まず `consistency-auditor`
- 「軽く直して」は、構造変更の示唆がなければ `prose-polisher`
- 「テンポを直して」「引きを強くして」は、構造を触るなら `revision-editor`、表現調整で足りるなら `prose-polisher`

---

## ハンドオフ条件

- ログライン合意後に案件の箱が未作成な場合: `idea-generator` から `project-bootstrap` へ移る
- 初期化後に世界観や骨格が未確定な場合: `project-bootstrap` から `setting-creator` へ移る
- 初期化後に大枠は固まっており、直近の章やシーンだけ詰めればよい場合: `project-bootstrap` から `scene-planner` へ移る
- ただし `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合: `project-bootstrap` / `resume-orchestrator` / `scene-planner` から `setting-creator` を優先する
- 執筆中に設定やプロットの前提変更が必要になった場合: `novel-writer` から `setting-creator` へ移る
- 執筆前に次の章やシーンの段取り不足が見つかった場合: `novel-writer` から `scene-planner` へ移る
- 監査で重大な矛盾が見つかり、設定の修正が必要な場合: `consistency-auditor` から `setting-creator` へ移る
- 監査で本文改善が必要だが方向性維持で足りる場合: `consistency-auditor` から `revision-editor` へ移る
- 設定の大枠は維持したまま、直近の章やシーンだけ具体化したい場合: `setting-creator` から `scene-planner` へ移る
- シーン設計が固まり、本文執筆に入れる場合: `scene-planner` から `novel-writer` へ移る
- 改稿後に仕上げ段階へ入る場合: `revision-editor` から `prose-polisher` へ移る
- 再開整理で次の作業が確定した場合: `resume-orchestrator` から該当スキルへ移る

### ハンドオフ時の判断基準

- 問題点の特定前なら、先に `consistency-auditor`
- 案件自体が未初期化なら、先に `project-bootstrap`
- 大枠はあるが直近の書き出しに必要な段取りが足りないなら、先に `scene-planner`
- `planning_gate_enabled=true` で planning gate 未通過なら、直近段取り不足として扱わず、先に `setting-creator`
- 問題点が特定済みなら、直接 `revision-editor` または `prose-polisher`
- 「次に何をすべきか」自体が曖昧なら、先に `resume-orchestrator`

---

## ルーティング時の共通注意

- `body.md` は通常の本文追記先ではない
- 1 シーンの文字数契約は原則 `1000-1500`
- `Mode` / `current_mode` は、このファイルの「正式モード名（正本）」に揃える
- `Target Total Chars` を最初に決める
- `Target Length Profile` は補助ラベルであり、本文長の正本は `Length Band`
- 全体計画の正本は `05_chapter_outline.md`
- legacy project では `05_chapter_outline_100k.md` を fallback として読んでよい
- 新規本文では `runtime/draft_prompt.txt` または `runtime/style_contract_compact.md` / `scene_brief_compact.md` / `continuity_pack.md` / `request_compact.md` を優先参照する
- `runtime/planning_gate_brief.md` があれば、長編の gate 判定と次 planning action の正本として優先参照する
- `planning_gate_enabled=true` かつ `request_compact.md` または `state_schema_novel.yaml` の `planning_gate_status != ready` なら、本文執筆へ進めない
- 再開整理では `runtime/resume_brief.md` があれば優先参照する
- 文体契約、進捗、キャラ制約は `runtime/` に不足がある場合のみ `state_schema_*.yaml` と `memory/global_notes.md` を補助参照する
- 診断結果と修正方針は混同せず、必要なら監査と改稿を分ける

