# Runtime Refactor Spec

## Purpose

本仕様は、日常の本文執筆フローを `script-first` 前提へ寄せるためのリファクタリング要件を定義する。
主目的は以下の 3 点。

- エージェント実行時に毎回読む文脈を圧縮し、クレジット消費を削減する
- 品質に効く文脈（文体、シーン目的、直前接続）は保持する
- 既存の `build_llm_prompt.py` と共存しつつ、段階的に軽量運用へ移行できるようにする

本仕様は「CLI 引数」「出力物」「終了条件」を明示し、次チャットでそのまま実装着手できる状態を目指す。

## Scope

対象:

- `小説作成/scripts/build_runtime_context.py`
- `小説作成/scripts/build_draft_prompt.py`
- `小説作成/scripts/check_scene_output.py`
- `小説作成/scripts/build_expand_prompt.py`
- 必要に応じて `小説作成/scripts/prompt_utils.py`

非対象:

- 既存 `agent/*.md` の文面変更
- 既存 `build_llm_prompt.py` の即時削除
- エージェントテンプレートの大規模再設計

## Runtime Directory Contract

各プロジェクト配下に `runtime/` ディレクトリを持つ。

想定パス:

- `<project>/runtime/style_contract_compact.md`
- `<project>/runtime/scene_brief_compact.md`
- `<project>/runtime/continuity_pack.md`
- `<project>/runtime/request_compact.md`
- `<project>/runtime/draft_prompt.txt`
- `<project>/runtime/check_report.json`
- `<project>/runtime/expand_instruction.md`
- `<project>/runtime/expand_prompt.txt`
- `<project>/runtime/resume_brief.md`

生成物は上書き更新を前提とし、履歴ファイルとして扱わない。

## Common CLI Rules

全スクリプト共通のルール:

- `--project` は相対パス・絶対パスの両方を許可する
- 相対パスは「カレントディレクトリ優先、なければ `scripts/` 親ディレクトリ基準」で解決する
- 文字コードは UTF-8
- 正常終了は exit code `0`
- 入力不備、必須ファイル不足、パース不能は exit code `1`
- 出力先ディレクトリがなければ作成する
- 既存出力ファイルがある場合は上書きする
- 例外トレースをそのまま出さず、1 行目に人間向けエラーを出す

標準出力の基本フォーマット:

- 成功時: `OK: <概要>`
- 警告時: `WARN: <概要>`
- 失敗時: `ERROR: <概要>`

## Script 1: `build_runtime_context.py`

### Purpose

実行時に必要な最小文脈を抽出し、`runtime/` 配下のコンパクトな入力ファイル群を生成する。

### CLI

```text
python scripts/build_runtime_context.py
  --project <path>
  --chapter <num>
  --scene <id>
  --mode <draft|resume>
  [--previous_text <path>]
  [--priority <speed|balanced|quality>]
  [--force]
```

### Arguments

- `--project`:
  - 必須
  - 対象プロジェクトディレクトリ
- `--chapter`:
  - 必須
  - 正の整数
- `--scene`:
  - 必須
  - 形式は `3-2` または `chapter_3_scene_2`
- `--mode`:
  - 必須
  - `draft` または `resume`
- `--previous_text`:
  - 任意
  - 指定時は自動探索より優先する
- `--priority`:
  - 任意
  - 既定値は `balanced`
- `--force`:
  - 任意
  - キャッシュ済みでも再生成する

### Input Dependencies

- `<project>/05_chapter_outline_100k.md`
- `<project>/agent/memory/global_notes.md` があれば参照
- `<project>/agent/state_schema_novel.yaml` があれば参照
- 直前シーンの `txt`（自動探索または `--previous_text`）
- `resume` 時のみ:
  - `<project>/agent/memory/session_notes.md` があれば参照

### Outputs

`draft` モード:

- `runtime/style_contract_compact.md`
- `runtime/scene_brief_compact.md`
- `runtime/continuity_pack.md`
- `runtime/request_compact.md`

`resume` モード:

- `runtime/style_contract_compact.md`
- `runtime/resume_brief.md`
- 必要なら `runtime/request_compact.md`

### Output Content Rules

`style_contract_compact.md`:

- 視点
- 地の文時制
- 口調ルール
- 禁止表現
- 文字数契約

`scene_brief_compact.md`:

- `Goal`
- `Conflict`
- `Emotion Shift`
- `Hook`
- `Hard Constraints`

`continuity_pack.md`:

- 直前シーン全文
- 1 つ前の要約
- それ以前は含めない

`request_compact.md`:

- 現在モード
- Purpose
- Deliverables
- Constraints
- Priority

`resume_brief.md`:

- Current Position
- Open Items
- Next Actions
- Read First

### Success Criteria

- 必須入力がある場合、最低 2 ファイル以上が `runtime/` に生成される
- `style_contract_compact.md` は常に生成される
- `draft` モードでは `scene_brief_compact.md` が必須
- `resume` モードでは `resume_brief.md` が必須

### Return / Stdout

成功時の例:

```text
OK: runtime context generated for chapter 3 scene 2
OK: wrote 4 files into <project>/runtime
```

警告例:

```text
WARN: agent/state_schema_novel.yaml not found, using defaults
WARN: previous scene not found, continuity pack contains fallback note
```

### Failure Conditions

- `--project` が存在しない
- `05_chapter_outline_100k.md` が存在しない
- `--chapter` が不正
- `--scene` が解釈不能

## Script 2: `build_draft_prompt.py`

### Purpose

`runtime` の圧縮済み文脈を使って、初稿生成専用の最小プロンプトを作成する。

### CLI

```text
python scripts/build_draft_prompt.py
  --project <path>
  [--runtime_dir <path>]
  [--min_chars <int>]
  [--target_chars <int>]
  [--max_chars <int>]
```

### Arguments

- `--project`:
  - 必須
- `--runtime_dir`:
  - 任意
  - 既定値は `<project>/runtime`
- `--min_chars`:
  - 任意
  - 既定値は `2000`
- `--target_chars`:
  - 任意
  - 既定値は `2300`
- `--max_chars`:
  - 任意
  - 既定値は `2500`

### Input Dependencies

- `runtime/style_contract_compact.md`
- `runtime/scene_brief_compact.md`
- `runtime/continuity_pack.md`
- `runtime/request_compact.md`

### Output

- `runtime/draft_prompt.txt`

### Prompt Rules

- 本文以外を出力させない
- 初稿は 1 回目の骨格生成として扱う
- 1 回目で最低文字数未達でも失敗扱いにしない
- ただし構造・文体・前後接続を優先させる

### Success Criteria

- `draft_prompt.txt` が生成される
- プロンプト末尾に「本文のみ出力」と明記される
- 必須 4 入力ファイルのうち 1 つでも欠けたら失敗する

### Return / Stdout

成功時の例:

```text
OK: draft prompt generated at <project>/runtime/draft_prompt.txt
```

### Failure Conditions

- 必須 `runtime` ファイル不足
- 文字数引数の大小関係が不正（`min <= target <= max` を満たさない）

## Script 3: `check_scene_output.py`

### Purpose

LLM を使わずに、初稿または拡張稿の機械判定可能な項目を検査する。

### CLI

```text
python scripts/check_scene_output.py
  --project <path>
  --text <path>
  [--runtime_dir <path>]
  [--min_chars <int>]
  [--target_chars <int>]
  [--max_chars <int>]
```

### Arguments

- `--project`:
  - 必須
- `--text`:
  - 必須
  - 検査対象の本文ファイル
- `--runtime_dir`:
  - 任意
  - 既定値は `<project>/runtime`
- `--min_chars`:
  - 任意
  - 既定値は `2000`
- `--target_chars`:
  - 任意
  - 既定値は `2300`
- `--max_chars`:
  - 任意
  - 既定値は `2500`

### Checks

- 実文字数
- 最小/目標/最大との比較
- 見出し混入
- 箇条書き混入
- メタ文言混入
- 明示的禁止表現の単純一致
- 段落数
- セリフ比率の粗いヒント

### Output

- `runtime/check_report.json`

### JSON Contract

最低限、以下のキーを含む:

- `target_file`
- `actual_chars`
- `min_chars`
- `target_chars`
- `max_chars`
- `needs_expand`
- `within_max`
- `format_violations`
- `forbidden_hits`
- `paragraph_count`
- `dialogue_ratio_hint`

### Success Criteria

- `check_report.json` が常に JSON として書き出される
- 文字数不足なら `needs_expand=true`
- 最大超過なら `within_max=false`
- 形式違反があれば `format_violations` に列挙される

### Return / Stdout

成功時の例:

```text
OK: scene output checked
OK: needs_expand=true actual_chars=1084
```

### Failure Conditions

- `--text` が存在しない
- 文字数引数が不正
- JSON 書き込み失敗

## Script 4: `build_expand_prompt.py`

### Purpose

初稿を全面再生成せず、不足字数を埋めるための拡張専用プロンプトを作成する。

### CLI

```text
python scripts/build_expand_prompt.py
  --project <path>
  --draft_text <path>
  [--runtime_dir <path>]
  [--check_report <path>]
```

### Arguments

- `--project`:
  - 必須
- `--draft_text`:
  - 必須
  - 初稿本文ファイル
- `--runtime_dir`:
  - 任意
  - 既定値は `<project>/runtime`
- `--check_report`:
  - 任意
  - 既定値は `runtime/check_report.json`

### Input Dependencies

- 初稿本文
- `runtime/check_report.json`
- `runtime/style_contract_compact.md`

### Outputs

- `runtime/expand_instruction.md`
- `runtime/expand_prompt.txt`

### Expand Rules

- 初稿の出来事を維持する
- 視点と口調を維持する
- 結末とフックを維持する
- 追加可能なのは「情景描写」「身体動作」「会話の間」「内面反応」「余韻」
- 展開順序、設定事実、固有名詞は変えない

### Success Criteria

- `check_report.json` が `needs_expand=true` のときにのみ有効
- `expand_instruction.md` に `Missing Chars` が明記される
- `expand_prompt.txt` は、初稿本文を含みつつフル文脈を再掲しない

### Return / Stdout

成功時の例:

```text
OK: expand prompt generated
OK: missing_chars=916
```

警告例:

```text
WARN: needs_expand=false but expand prompt requested
```

### Failure Conditions

- 初稿本文がない
- `check_report.json` がない
- `check_report.json` が壊れている

## Shared Helper Module: `prompt_utils.py`

### Purpose

既存 `build_llm_prompt.py` にある再利用可能な処理を、CLI を持たない関数群として切り出す。

### Candidate Functions

- パス解決
- 安全なファイル読込
- 章ブロック抽出
- 文体契約抽出
- 直前シーン探索
- 要約用 excerpt 生成
- 文字数契約計算
- 簡易トークン概算

### Constraints

- CLI を持たない
- 副作用は最小限にする
- ファイル書き込みは各コマンド側で行う

## Backward Compatibility

- 既存 `build_llm_prompt.py` は残す
- 既存スクリプトは「legacy manual mode」として継続利用可能にする
- 新スクリプトは既存ファイル構成を壊さず追加する

## Recommended Execution Flow

日常執筆の標準フロー:

1. `build_runtime_context.py --mode draft`
2. `build_draft_prompt.py`
3. LLM で初稿生成
4. `check_scene_output.py`
5. `needs_expand=true` なら `build_expand_prompt.py`
6. LLM で拡張生成
7. `check_scene_output.py` 再実行

再開時:

1. `build_runtime_context.py --mode resume`
2. `runtime/resume_brief.md` を見て次のモードを決定

## Acceptance Criteria

以下を満たしたら本リファクタリングの仕様面は完了とみなす。

- 各 CLI の必須/任意引数が明文化されている
- 各出力ファイルの責務が重複していない
- 2 回目の拡張時にフル文脈再投入を避ける設計になっている
- 既存 `build_llm_prompt.py` と共存可能
- 別チャットでこのファイルのみ読めば実装着手できる
