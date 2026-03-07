# Target Length Profile Refactor Plan

Last Updated: 2026-03-07
Owner: inott + Codex
Status: planning

## Goal

初期化時に作品全体の目標文字数を `30000 / 50000 / 100000` から選べるようにし、その選択を project / runtime / agent routing の共通正本として扱える状態にする。

今回の主眼は「機能追加」よりも「既存の 100k 前提を壊さず、安全に一般化すること」に置く。

## Why This Needs a Structured Refactor

現状の 100k 前提は、単一の UI 入力だけでなく以下に分散している。

- `scripts/init_project.py` の初期化手順と章フォルダ生成
- `agent/state_schema_novel.yaml` の既定値
- `templates/05_chapter_outline_100k.md` のファイル名と本文
- `scripts/build_runtime_context.py` / `scripts/build_llm_prompt.py` の探索パス
- `agent/HUB.md` と各 skill の `long_form_100k` 分岐
- `tests/test_scripts.py` の fixture と期待値
- `README.md` / `walkthrough.md` の説明

そのため、単純に選択 UI だけ足すと、下流が 100k 固定のまま残り、挙動不整合を起こす。

## Non-Goals

- 今回の refactor で章数設計を大きく変えること
- `scene_type_bands` の思想を別方式へ置き換えること
- 既存の旧案件を一括自動移行すること
- 本文生成ロジック自体を作り直すこと

## Refactor Principles

1. `target_total_chars` を正本にする
2. 互換期間は `05_chapter_outline_100k.md` と旧 `length_mode` を読み取り可能に保つ
3. 先に read-path を互換化し、その後 write-path を切り替える
4. 既存 100k プロジェクトが、移行直後も無変更で動くことを最優先する
5. 各 Phase に「着手前の保護テスト」と「完了判定」を置く

## Proposed Data Model

### New Canonical Fields

- `targets.target_total_chars`
- `targets.target_length_profile`
- `targets.planning_gate_enabled`
- `targets.planning_gate_min_chars`
- `targets.planning_target_total_chars`

### Target Length Profile Mapping

| profile | target_total_chars | planning_gate_min_chars | planning_target_total_chars | notes |
|---|---:|---:|---:|---|
| `novel_30k` | 30000 | 24000 | 30000 | 80% gate |
| `novel_50k` | 50000 | 40000 | 50000 | 80% gate |
| `novel_100k` | 100000 | 80000 | 100000 | 現行互換 |

### Compatibility Policy

- 旧 `length_mode=long_form_100k` は当面 `target_length_profile=novel_100k` に解決する
- 旧 `05_chapter_outline_100k.md` は当面探索対象に残す
- 新規作成時は汎用ファイル名へ寄せる
- 読み取りは dual-read、書き込みは段階的に single-write へ寄せる

## Baseline Invariants

以下は refactor 完了まで壊してはいけない。

- 既存 100k 案件で `build_runtime_context.py` が動く
- 既存 100k 案件で `build_draft_prompt.py` が gate 判定込みで動く
- 既存 100k 案件で `check_scene_output.py` が帯域判定を維持する
- `agent/HUB.md` で blocked planning case が `setting-creator` に落ちる
- 既存テストの 100k 系 fixture が、互換モードでは通る

## Phase Overview

| Phase | Name | Focus |
|---|---|---|
| 0 | Baseline Lock | 現状保護、比較基準、命名方針固定 |
| 1 | Canonical Model Design | 文字数プロファイルと互換仕様を定義 |
| 2 | Compatibility Layer | 共通解決ロジックを追加し read-path を先に安全化 |
| 3 | Bootstrap and Template Refactor | 初期化入力とテンプレート正本を切り替える |
| 4 | Runtime and Prompt Refactor | runtime / checker / legacy prompt を新正本へ寄せる |
| 5 | Agent Routing Refactor | HUB / skills / request template を新正本へ寄せる |
| 6 | Test Expansion and Migration Safety | 回帰・互換・新規ケースを増やす |
| 7 | Docs and Rollout | README / walkthrough / 移行手順を更新する |

---

## Phase 0: Baseline Lock

### Goal

後続 Phase で「何が壊れたか」を即判定できる比較基準を作る。

### Tasks

1. 現行の 100k 前提依存を一覧化し、変更対象と凍結対象を分ける
2. `tests/test_scripts.py` のうち、現行 100k 挙動を保証するケースを baseline として明示する
3. 新旧ファイル名、旧 `length_mode`、旧 state field の互換方針を文章で固定する
4. 新規 canonical 名称を先に確定する

### Files

- `agent/target_length_profile_refactor_plan.md`
- `tests/test_scripts.py`
- 必要なら `agent/decisions_log.md`

### Validation

- 100k 既存 fixture の期待値を一覧化できている
- 新旧正本の優先順位が文章で固定されている
- 「何を Phase 2 まで触らないか」が明記されている

### Exit Criteria

- baseline 回帰対象が定義済み
- canonical field 名が合意済み
- compatibility policy が文書化済み

### Rollback Rule

- なし
- この Phase は設計固定のみ

### Phase 0 Execution Pack

この Phase は「設計メモ」ではなく、後続 Phase の安全装置を作る作業として扱う。

#### Step 0-1. Baseline Test Inventory を固定する

既存テストから、今回の refactor で壊してはいけない動作を `baseline characterization` として固定する。

#### Baseline Characterization Buckets

| Bucket | Existing Test Intent | Why It Must Stay Green |
|---|---|---|
| Bootstrap | `init_project.py` がテンプレートと章フォルダを生成する | 新規 project 作成フローの最低保証 |
| Legacy Prompt | `build_llm_prompt.py` が full-context prompt を出せる | 旧運用 fallback を壊さないため |
| Runtime Draft | runtime artifacts と draft prompt が生成される | 現行推奨フローの中核 |
| Gate Guard | blocked planning で draft を止める | 安全制御を維持するため |
| Router | blocked planning が `setting-creator` に落ちる | agent routing の安全性を維持するため |
| Checker | scene output checker が band と違反を返す | 執筆品質の guard rail |

#### Step 0-2. Characterization として凍結する既存テスト

以下を、Phase 0 以後は「仕様の近似値」ではなく「壊してはいけない基準線」として扱う。

1. `TestInitProject.test_creates_correct_folder_structure`
2. `TestInitProject.test_exits_with_error_on_existing_directory`
3. `TestInitProject.test_from_ideas_transfers_logline`
4. `TestBuildLLMPrompt.test_generates_output_file`
5. `TestBuildLLMPrompt.test_output_contains_required_sections`
6. `TestBuildLLMPrompt.test_prompt_contains_length_contract`
7. `TestRuntimeRefactorScripts.test_runtime_flow_generates_compact_files_and_expand_prompt`
8. `TestRuntimeRefactorScripts.test_build_draft_prompt_fails_when_planning_gate_is_blocked`
9. `TestRuntimeRefactorScripts.test_build_runtime_context_resume_mode_generates_resume_brief`
10. `TestRuntimeRefactorScripts.test_route_prompt_prefers_setting_creator_for_blocked_planning_gate`
11. `TestRuntimeRefactorScripts.test_check_scene_output_writes_detailed_report_fields`

#### Step 0-3. 実装前に追加する先行 characterization test

本体の書き換えより先に、互換レイヤが守るべき観測点を追加する。

1. `legacy_state_without_new_fields_resolves_to_100k_profile`
2. `legacy_outline_filename_is_discoverable`
3. `legacy_runtime_context_works_with_old_outline_only`
4. `legacy_build_llm_prompt_works_with_old_outline_only`
5. `legacy_length_mode_long_form_100k_maps_to_novel_100k`

#### Step 0-4. Test Naming Policy を固定する

今回追加するテストの prefix/suffix は以下で統一する。

- `legacy_*`: 旧互換を守るテスト
- `canonical_*`: 新正本を使うテスト
- `mixed_*`: 新旧混在ケース
- `invalid_*`: 異常系

#### Step 0-5. Merge 前の最小実行コマンドを固定する

```bash
python -m pytest tests/test_scripts.py -v
```

必要に応じて、影響範囲確認では以下も使う。

```bash
python -m pytest tests/test_scripts.py -k "InitProject or RuntimeRefactorScripts or BuildLLMPrompt" -v
```

#### Windows Local Execution Note

一部の Windows 環境では、`pytest` の temp / cache cleanup で `WinError 5` が出ることがある。
その場合は、`TEMP` / `TMP` と `--basetemp` を明示し、cache provider を無効化して実行する。

```powershell
$env:TEMP = "C:\pytest_tmp"
$env:TMP = "C:\pytest_tmp"
python -m pytest tests/test_scripts.py -v --basetemp C:\pytest_tmp\run1 -p no:cacheprovider
```

### Phase 0 Deliverables

- baseline characterization test list
- pre-refactor compatibility tests の追加方針
- test naming policy
- merge 前の最小実行コマンド

### Phase 0 Hard Stop Conditions

以下に当てはまる場合、この refactor の実装 Phase に入らない。

1. `legacy` と `canonical` の命名が未確定
2. outline path の優先順位が未確定
3. 既存 100k runtime tests のどれを基準線にするか曖昧
4. `target_total_chars` と `target_length_profile` の役割分担が曖昧

---

## Phase 1: Canonical Model Design

### Goal

`30000 / 50000 / 100000` の選択を、下流で一貫して扱える canonical model に変換する。

### Tasks

1. `target_total_chars` を最上位の判断根拠にする
2. `target_length_profile` の値を `novel_30k / novel_50k / novel_100k` に固定する
3. gate 閾値を `80%` 基準で定義する
4. `planning_gate_enabled` を導入し、将来の分岐を `long_form_100k` 依存から外せるようにする
5. 旧 `length_mode` の読み替え表を定義する
6. outline ファイル名の新 canonical 候補を決める

### Proposed Canonical Names

- state field: `target_total_chars`
- state field: `target_length_profile`
- state field: `planning_gate_enabled`
- outline file: `05_chapter_outline.md`

### Compatibility Resolution Order

1. 新 field があればそれを使う
2. 新 field がなければ旧 field から補完する
3. 新 outline があればそれを使う
4. 新 outline がなければ `05_chapter_outline_100k.md` を使う

### Validation

- 30k / 50k / 100k の各 profile に、数値と gate 閾値が一意に割り当てられている
- `long_form_100k` 依存を置換する判断根拠が定義されている
- file/path/state の優先順位が矛盾なく定義されている

### Exit Criteria

- canonical model と compatibility mapping が確定
- 実装者が追加質問なしで field 追加に着手できる

### Rollback Rule

- `target_length_profile` 名称が定まらない場合は実装着手しない

### Phase 1 Execution Pack

#### Step 1-1. Canonical State Contract を固定する

`agent/state_schema_novel.yaml` に最終的に存在すべき canonical fields を、この Phase で先に文章として固定する。

##### Canonical State Contract

```yaml
targets:
  target_total_chars: 50000
  target_length_profile: "novel_50k"
  planning_gate_enabled: true
  planning_gate_min_chars: 40000
  planning_target_total_chars: 50000
```

#### Step 1-2. Derived Value Contract を固定する

`planning_gate_min_chars` と `planning_target_total_chars` は、原則として profile から導出される値として扱う。

##### Derivation Rules

- `target_total_chars=30000` -> `planning_gate_min_chars=24000`
- `target_total_chars=50000` -> `planning_gate_min_chars=40000`
- `target_total_chars=100000` -> `planning_gate_min_chars=80000`
- `planning_target_total_chars` は `target_total_chars` と同値
- `planning_gate_enabled` は今回の 3 profile ではすべて `true`

#### Step 1-3. Legacy Mapping Contract を固定する

旧 field が残っている project は、以下の順で読み替える。

##### Legacy Mapping Table

| Legacy Signal | Canonical Resolution |
|---|---|
| `length_mode=long_form_100k` | `target_length_profile=novel_100k` |
| `targets.total_chars=100000` only | `target_length_profile=novel_100k` |
| `planning_target_total_chars=100000` only | `target_length_profile=novel_100k` |
| no legacy/new fields | conservative fallback to `novel_100k` only for compatibility code path |

#### Step 1-4. Outline Canonical Name を固定する

新規 write-path の canonical file name は `05_chapter_outline.md` とする。

##### Rationale

- 100k 固有名を排除できる
- 既存のテンプレ番号体系を維持できる
- scripts 側で path 置換が最小で済む

#### Step 1-5. Review Checklist を固定する

この Phase のレビューでは、コードを書く前に以下を確認する。

1. `target_total_chars` が最上位の数値正本になっているか
2. `target_length_profile` が表示・分岐のラベル用途に限定されているか
3. `planning_gate_*` が profile 由来の派生値として説明できるか
4. 旧 field と新 field が同時にあるときの優先順位が決まっているか
5. 新 outline 名が 1 つに固定されているか

### Phase 1 Hard Stop Conditions

1. `target_total_chars` と `planning_target_total_chars` の使い分けが曖昧
2. `target_length_profile` を UI 表示用にするのか分岐用にするのか未整理
3. `planning_gate_enabled` の必要性に合意がない
4. canonical outline 名が未決定

### Phase 1 Deliverables

- canonical state contract
- derived value contract
- legacy mapping table
- canonical outline naming decision
- code review checklist for subsequent phases

---

## Phase 2: Compatibility Layer

### Goal

既存構造を壊さずに、新旧 state / file / profile を解決できる共通層を先に入れる。

### Tasks

1. `scripts/prompt_utils.py` に profile 解決ロジックを集中させる
2. `target_total_chars` / `target_length_profile` / 旧 `length_mode` の読み取りを一元化する
3. outline path 解決を `05_chapter_outline.md` 優先、旧名フォールバックに変更する
4. gate 判定が `target_total_chars` 系から導出されるようにする
5. 旧 100k データしかないプロジェクトでも現状挙動を維持する

### Candidate Functions

- `load_target_length_profile(project_dir)`
- `resolve_target_profile_from_state(state_schema_text)`
- `resolve_outline_path(project_dir)`
- `compute_gate_threshold(target_total_chars)`

### Files

- `scripts/prompt_utils.py`
- `scripts/build_runtime_context.py`
- `scripts/build_llm_prompt.py`

### Validation

- 新 field がない旧 project でも runtime が壊れない
- 新 field がある project で旧 `length_mode` がなくても動く
- outline 新旧どちらのファイル名でも探索できる

### Required Tests

- old state only -> resolves to 100k
- new 30k state -> resolves to 30k
- new 50k state -> resolves to 50k
- new outline name only -> runtime can load
- old outline name only -> runtime can still load

### Exit Criteria

- read-path が互換対応済み
- 以後の Phase で新 field / 新ファイル名を書いても旧案件が壊れない

### Rollback Rule

- 既存 100k runtime test が 1 件でも壊れたら、この Phase から先に進まない

### Phase 2 Execution Pack

#### Step 2-1. Common Resolver の責務を固定する

新旧の state / file / profile 解決は `scripts/prompt_utils.py` に集約し、他スクリプトは raw field を直接読まない。

##### Resolver Responsibilities

| Function | Responsibility |
|---|---|
| `resolve_target_profile_from_state()` | state text から canonical profile payload を解決する |
| `resolve_outline_path()` | 新旧 outline path を優先順位付きで解決する |
| `compute_gate_threshold()` | target_total_chars から gate 閾値を返す |
| `load_target_length_profile()` | project 単位で state + defaults を束ねて返す |

#### Step 2-1a. Resolver API Signature を固定する

Phase 2 で追加する resolver API は、以下の関数シグネチャで固定する。

##### Function Signatures

```python
def resolve_target_profile_from_state(
    state_schema_text: str,
    *,
    fallback_total_chars: int = 100000,
) -> dict:
    ...

def compute_gate_threshold(target_total_chars: int) -> int:
    ...

def compute_target_length_profile(target_total_chars: int) -> str:
    ...

def build_target_profile_payload(
    target_total_chars: int,
    *,
    source: str,
    planning_gate_enabled: bool = True,
) -> dict:
    ...

def resolve_outline_path(
    project_dir: str,
    *,
    require_exists: bool = False,
) -> str:
    ...

def load_target_length_profile(project_dir: str) -> dict:
    ...

def load_planning_metadata(project_dir: str) -> dict:
    ...
```

#### Step 2-1b. Payload Contract を固定する

resolver が返す payload shape は、今後の runtime / bootstrap / routing で共通利用する。

##### `build_target_profile_payload()` Return Shape

```python
{
    "target_total_chars": 50000,
    "target_length_profile": "novel_50k",
    "planning_gate_enabled": True,
    "planning_gate_min_chars": 40000,
    "planning_target_total_chars": 50000,
    "source": "canonical_state",
}
```

##### Allowed `source` Values

- `canonical_state`
- `legacy_length_mode`
- `legacy_total_chars`
- `legacy_planning_target`
- `fallback`

#### Step 2-1c. Function-by-Function Contract を固定する

##### `compute_target_length_profile(target_total_chars: int) -> str`

- 役割: `30000 / 50000 / 100000` を `novel_30k / novel_50k / novel_100k` に変換する
- 許可入力: `30000`, `50000`, `100000`
- 異常系: 許可外の値は `UserFacingError` を投げる

##### `compute_gate_threshold(target_total_chars: int) -> int`

- 役割: target total chars から gate 下限を返す
- 変換規則:
  - `30000 -> 24000`
  - `50000 -> 40000`
  - `100000 -> 80000`
- 異常系: 未対応値は `UserFacingError`

##### `build_target_profile_payload(...) -> dict`

- 役割: canonical payload を一箇所で構築する
- 入力:
  - `target_total_chars`
  - `source`
  - `planning_gate_enabled`
- 出力:
  - `target_total_chars`
  - `target_length_profile`
  - `planning_gate_enabled`
  - `planning_gate_min_chars`
  - `planning_target_total_chars`
  - `source`

##### `resolve_target_profile_from_state(state_schema_text: str, *, fallback_total_chars: int = 100000) -> dict`

- 役割: state text から canonical payload を解決する
- 優先順位:
  1. `target_total_chars`
  2. `target_length_profile`
  3. `planning_target_total_chars`
  4. `total_chars`
  5. `length_mode`
  6. fallback
- 特記事項:
  - `target_total_chars` があればそれを最優先する
  - `target_length_profile` のみある場合は対応する total chars に展開する
  - `length_mode=long_form_100k` は `novel_100k` に解決する
  - state が空でも payload を返す

##### `resolve_outline_path(project_dir: str, *, require_exists: bool = False) -> str`

- 役割: 新旧 outline path を優先順位付きで返す
- 探索順:
  1. `<project>/05_chapter_outline.md`
  2. `<project>/05_chapter_outline_100k.md`
  3. `<project>/plot/05_chapter_outline.md`
  4. `<project>/plot/05_chapter_outline_100k.md`
  5. `<project>/memory/05_chapter_outline.md`
  6. `<project>/memory/05_chapter_outline_100k.md`
- `require_exists=False`:
  - 既存 file があればその path を返す
  - 見つからなければ canonical path `<project>/05_chapter_outline.md` を返す
- `require_exists=True`:
  - 見つからない場合は `UserFacingError`

##### `load_target_length_profile(project_dir: str) -> dict`

- 役割: project から state file を読み、canonical payload を返す
- 入力:
  - `project_dir`
- 内部処理:
  - state schema text を取得
  - `resolve_target_profile_from_state()` を呼ぶ
- 出力:
  - canonical payload

##### `load_planning_metadata(project_dir: str) -> dict`

- 役割: 既存 API 互換を保ちながら planning metadata 一式を返す
- 追加項目:
  - `target_total_chars`
  - `target_length_profile`
  - `planning_gate_enabled`
  - `planning_gate_min_chars`
  - `planning_target_total_chars`
  - `target_profile_source`
- 互換維持項目:
  - `state_schema_text`
  - `planning_gate_status`
  - `planned_total_min_chars`
  - `planned_total_target_chars`
  - `planned_scene_count`
  - `scene_type_bands`

#### Step 2-1d. Error Contract を固定する

resolver API の異常系は以下で統一する。

##### Error Rules

- user が修正可能な入力不正:
  - `UserFacingError`
- file 未検出で `require_exists=True`:
  - `UserFacingError`
- internal coding bug:
  - 既存の unexpected failure ハンドリングに委譲

#### Step 2-1e. Call Site Replacement Map を固定する

Phase 2 では、呼び出し側を以下の順で差し替える。

| Caller | Replace Direct Access With |
|---|---|
| `build_runtime_context.py` | `resolve_outline_path()` + `load_planning_metadata()` |
| `build_llm_prompt.py` | `resolve_outline_path()` + `load_target_length_profile()` |
| 将来の bootstrap write-path | `compute_target_length_profile()` + `build_target_profile_payload()` |

#### Step 2-1f. Non-Goals for Resolver API

resolver API は以下を担当しない。

- state file の書き込み
- template の複製
- chapter allocation の自動生成
- scene band の解決ロジック置換
- routing 文言の生成

#### Step 2-1g. Pre-Implementation Tests for Phase 2

resolver 実装に入る前に、以下の先行テストを追加する。目的は「旧 100k 互換を壊さないこと」と「新 canonical resolver の期待 shape を先に固定すること」。

##### Test Placement

- 既存 `tests/test_scripts.py` に追加してよい
- 可能なら `class TestTargetProfileResolvers:` を新設する
- runtime 連携を含むものは `class TestRuntimeRefactorScripts:` に追加してもよい

##### Shared Fixture Strategy

- resolver 単体テスト:
  - `tmp_path` 上に最小 project を作る
  - `agent/state_schema_novel.yaml` を必要最小限だけ書く
- runtime 連携テスト:
  - 既存 `runtime_project` fixture を流用するか、profile 専用 fixture を追加する
- outline path テスト:
  - `05_chapter_outline.md` と `05_chapter_outline_100k.md` を排他的に配置する

##### Common Minimal Outline Fixture

```md
# Outline

## 第1章 Chapter Card
- 章の役割: 導入
- 想定シーン数: 1
- 想定最小字数: 1000
- 想定目標字数: 1250

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 1-1 | standard | 導入 | 平穏 -> 不穏 | 種まき | 1000 | 1250 | 1500 | - | planned |
```

##### Common Legacy State Fixture

```yaml
targets:
  length_mode: long_form_100k
  planning_gate_min_chars: 80000
  planning_target_total_chars: 100000
active_work:
  planning_gate_status: blocked
progress:
  planned_total_min_chars: 0
  planned_total_target_chars: 0
  planned_scene_count: 0
```

##### Common Canonical 30k State Fixture

```yaml
targets:
  target_total_chars: 30000
  target_length_profile: "novel_30k"
  planning_gate_enabled: true
  planning_gate_min_chars: 24000
  planning_target_total_chars: 30000
active_work:
  planning_gate_status: blocked
progress:
  planned_total_min_chars: 0
  planned_total_target_chars: 0
  planned_scene_count: 0
```

##### Common Canonical 50k State Fixture

```yaml
targets:
  target_total_chars: 50000
  target_length_profile: "novel_50k"
  planning_gate_enabled: true
  planning_gate_min_chars: 40000
  planning_target_total_chars: 50000
active_work:
  planning_gate_status: blocked
progress:
  planned_total_min_chars: 0
  planned_total_target_chars: 0
  planned_scene_count: 0
```

### Phase 2 Detailed Pre-Tests

#### 1. `test_legacy_state_without_new_fields_resolves_to_100k_profile`

##### Purpose

旧 state のみがある案件で、resolver が `novel_100k` payload を返すことを固定する。

##### Fixture

- `agent/state_schema_novel.yaml` に `Common Legacy State Fixture`

##### Suggested Assertions

- `payload["target_total_chars"] == 100000`
- `payload["target_length_profile"] == "novel_100k"`
- `payload["planning_gate_enabled"] is True`
- `payload["planning_gate_min_chars"] == 80000`
- `payload["planning_target_total_chars"] == 100000`
- `payload["source"] == "legacy_length_mode"`

#### 2. `test_canonical_30k_state_resolves_target_profile_payload`

##### Purpose

新 canonical 30k state が、resolver でそのまま 30k payload に解決されることを固定する。

##### Fixture

- `agent/state_schema_novel.yaml` に `Common Canonical 30k State Fixture`

##### Suggested Assertions

- `payload["target_total_chars"] == 30000`
- `payload["target_length_profile"] == "novel_30k"`
- `payload["planning_gate_min_chars"] == 24000`
- `payload["planning_target_total_chars"] == 30000`
- `payload["source"] == "canonical_state"`

#### 3. `test_canonical_50k_state_resolves_target_profile_payload`

##### Purpose

新 canonical 50k state が、resolver でそのまま 50k payload に解決されることを固定する。

##### Fixture

- `agent/state_schema_novel.yaml` に `Common Canonical 50k State Fixture`

##### Suggested Assertions

- `payload["target_total_chars"] == 50000`
- `payload["target_length_profile"] == "novel_50k"`
- `payload["planning_gate_min_chars"] == 40000`
- `payload["planning_target_total_chars"] == 50000`
- `payload["source"] == "canonical_state"`

#### 4. `test_resolve_outline_path_prefers_canonical_outline_name`

##### Purpose

新旧両方の outline がある場合、canonical 名を優先することを固定する。

##### Fixture

- `<project>/05_chapter_outline.md`
- `<project>/05_chapter_outline_100k.md`

##### Suggested Assertions

- returned path endswith `05_chapter_outline.md`

#### 5. `test_resolve_outline_path_falls_back_to_legacy_outline_name`

##### Purpose

旧 outline 名しかない project でも resolver が path を返せることを固定する。

##### Fixture

- `<project>/05_chapter_outline_100k.md` のみ配置

##### Suggested Assertions

- returned path endswith `05_chapter_outline_100k.md`

#### 6. `test_resolve_outline_path_returns_canonical_default_when_missing_and_not_required`

##### Purpose

outline 未作成 project で、`require_exists=False` のとき canonical path を返す方針を固定する。

##### Fixture

- outline file を配置しない

##### Suggested Assertions

- returned path endswith `05_chapter_outline.md`
- exception is not raised

#### 7. `test_resolve_outline_path_raises_when_missing_and_required`

##### Purpose

outline 必須ケースで file 未検出なら `UserFacingError` を返すことを固定する。

##### Fixture

- outline file を配置しない

##### Suggested Assertions

- `UserFacingError` is raised

#### 8. `test_runtime_context_works_with_legacy_outline_only`

##### Purpose

Phase 2 完了後も、旧 outline 名だけの project で `build_runtime_context.py` が動くことを固定する。

##### Fixture

- `Common Legacy State Fixture`
- `<project>/05_chapter_outline_100k.md` に `Common Minimal Outline Fixture`
- 最小 `global_notes.md`
- 直前シーン用 `chapter_1_scene_1.txt`

##### Suggested Assertions

- command returns `0`
- `runtime/planning_gate_brief.md` exists
- `runtime/request_compact.md` exists

#### 9. `test_build_llm_prompt_works_with_legacy_outline_only`

##### Purpose

legacy full-context path でも旧 outline 名のみの project を扱えることを固定する。

##### Fixture

- `<project>/05_chapter_outline_100k.md` に `Common Minimal Outline Fixture`

##### Suggested Assertions

- command returns `0`
- `llm_prompt_output.txt` exists
- output contains `### 5. 現在の章のシーン構成`

#### 10. `test_load_planning_metadata_exposes_canonical_target_fields`

##### Purpose

既存 API 互換を保つ `load_planning_metadata()` が、新 target fields も露出することを固定する。

##### Fixture

- `agent/state_schema_novel.yaml` に `Common Canonical 30k State Fixture`

##### Suggested Assertions

- `meta["target_total_chars"] == 30000`
- `meta["target_length_profile"] == "novel_30k"`
- `meta["planning_gate_enabled"] is True`
- `meta["planning_gate_min_chars"] == 24000`
- `meta["planning_target_total_chars"] == 30000`

### Suggested Test Skeleton

```python
class TestTargetProfileResolvers:
    def test_legacy_state_without_new_fields_resolves_to_100k_profile(self, tmp_path):
        project_dir = tmp_path / "legacy_profile"
        state_dir = project_dir / "agent"
        state_dir.mkdir(parents=True)
        (state_dir / "state_schema_novel.yaml").write_text(LEGACY_STATE_TEXT, encoding="utf-8")

        payload = load_target_length_profile(str(project_dir))

        assert payload["target_total_chars"] == 100000
        assert payload["target_length_profile"] == "novel_100k"
```

### Phase 2 Test Review Checklist

1. resolver 単体テストと command 経由テストが両方あるか
2. old/new 両 state の成功ケースがあるか
3. canonical/legacy outline 名の両方を通しているか
4. `load_planning_metadata()` の後方互換が確認できるか
5. 例外系が `UserFacingError` 前提で固定されているか

#### Step 2-2. Canonical Payload Shape を固定する

各スクリプトへ返す profile payload は、同じ shape を使う。

##### Profile Payload Draft

```python
{
    "target_total_chars": 50000,
    "target_length_profile": "novel_50k",
    "planning_gate_enabled": True,
    "planning_gate_min_chars": 40000,
    "planning_target_total_chars": 50000,
    "source": "canonical_state"  # canonical_state / legacy_length_mode / legacy_total_chars / fallback
}
```

#### Step 2-3. Read Path Migration Rule を固定する

各スクリプトは以下の順で path / state を解決する。

##### Read Order

1. 新 state fields
2. 旧 state fields
3. hardcoded compatibility fallback

##### Outline Path Order

1. `<project>/05_chapter_outline.md`
2. `<project>/05_chapter_outline_100k.md`
3. `<project>/plot/05_chapter_outline.md`
4. `<project>/plot/05_chapter_outline_100k.md`
5. `<project>/memory/05_chapter_outline.md`
6. `<project>/memory/05_chapter_outline_100k.md`

#### Step 2-4. Touch Policy を固定する

この Phase では write-path を増やさない。新 field を保存するのはまだ Phase 3 以降。

##### Do In Phase 2

- 読み取り関数の追加
- path 探索順の集約
- runtime / llm prompt の read-path 置換

##### Do Not In Phase 2

- `init_project.py` の出力変更
- template 新規生成
- state schema の default 書き換え

#### Step 2-5. File-by-File Work Plan

##### `scripts/prompt_utils.py`

- resolver 群を追加
- 既存 `load_planning_metadata()` を canonical payload を使う形へ整理
- 旧 field 直接参照箇所を段階的に resolver 経由へ寄せる

##### `scripts/build_runtime_context.py`

- `_find_outline_path()` を共通 resolver へ置換
- `planning_meta` の target/gate 値を canonical payload から取得
- `long_form_100k` の直接分岐を最小化する準備をする

##### `scripts/build_llm_prompt.py`

- `outline_path` を直書きせず resolver を使う
- chapter target / project target の表示用数値解決に resolver を使う

#### Step 2-6. Code Review Checklist

1. raw string `long_form_100k` の新規追加がないか
2. outline path 解決が関数経由になっているか
3. compatibility fallback の source が trace できるか
4. Phase 2 で write-path を触っていないか

### Phase 2 Hard Stop Conditions

1. `prompt_utils.py` に resolver が分散追加されている
2. `build_runtime_context.py` と `build_llm_prompt.py` が別々の path order を持つ
3. compatibility fallback の根拠が不明
4. Phase 2 中に write-path 変更が混ざっている

### Phase 2 Deliverables

- shared resolver API
- canonical profile payload shape
- unified outline path resolution order
- file-by-file read-path migration plan

---

## Phase 3: Bootstrap and Template Refactor

### Goal

新規案件の入り口で `30000 / 50000 / 100000` を選択でき、その値が project の初期正本へ反映される状態にする。

### Tasks

1. `scripts/init_project.py` に目標文字数選択入力を追加する
2. CLI は明示引数で指定可能にする
3. 未指定時の挙動を決める
4. 新規 project 作成時に state に canonical fields を書く
5. 新 canonical outline ファイルを生成する
6. 必要ならテンプレート本文を 100k 固有表現から一般化する
7. 章フォルダ構成は当面 5 章固定で維持する

### Design Constraints

- 初回実装では章数可変化まで入れない
- 100k 固有表現は、ユーザー向け文言から先に除去する
- 旧 `templates/05_chapter_outline_100k.md` は互換資産として一定期間残してよい

### Files

- `scripts/init_project.py`
- `templates/05_chapter_outline.md` または同等の新 canonical template
- `templates/01_concept_sheet.md`
- `templates/04_plot_outline.md`
- `agent/state_schema_novel.yaml`

### Validation

- 新規 30k project を初期化できる
- 新規 50k project を初期化できる
- 新規 100k project を初期化できる
- 既存の `--from_ideas` が壊れない
- 新規 project で state / outline / chapter folder が整合する

### Required Tests

- `init_project.py --target-total-chars 30000`
- `init_project.py --target-total-chars 50000`
- `init_project.py --target-total-chars 100000`
- invalid target value fails
- default target behavior is explicit and tested

### Exit Criteria

- 新規 project の正本が 100k 固定でなくなる
- 新 project は canonical fields と canonical outline を持つ

### Rollback Rule

- 新規初期化が不安定なら、write-path は旧 state/旧 template に戻し、Phase 2 の dual-read だけ残す

### Phase 3 Execution Pack

#### Step 3-1. `init_project.py` の入力仕様を固定する

初期化の target length 指定は CLI 引数を正本にし、必要なら agent 側がこの引数を使って呼び出す。

##### CLI Draft

```bash
python scripts/init_project.py my_novel --target-total-chars 30000
python scripts/init_project.py my_novel --target-total-chars 50000
python scripts/init_project.py my_novel --target-total-chars 100000
```

##### Validation Rule

- 許可値は `30000`, `50000`, `100000` のみ
- それ以外は fail fast
- 未指定時は legacy compatibility fallback として `100000` を使い、warning を出す
- agent / bootstrap の新標準導線では、target selection を明示必須にする

#### Step 3-2. Project Bootstrap Write Contract を固定する

新規 project では、state / outline / chapter folders の 3 点が同じ target profile を指す必要がある。

##### New Project Write Contract

- state に canonical fields を書く
- outline は新 canonical filename で生成する
- chapter folders は現行 5 章構成を維持する
- `--from_ideas` は target selection の有無と独立に動く

#### Step 3-2a. Write-Path Output Inventory を固定する

Phase 3 では、`init_project.py` が新規 project に何を書き出すかを明示的に固定する。

##### Generated Files Inventory

| Path | Generate? | Source | Notes |
|---|---|---|---|
| `<project>/01_concept_sheet.md` | yes | `templates/01_concept_sheet.md` | `--from_ideas` 時は後段でログライン転記あり |
| `<project>/02_character_sheet.md` | yes | `templates/02_character_sheet.md` | 静的コピー |
| `<project>/03_world_building.md` | yes | `templates/03_world_building.md` | 静的コピー |
| `<project>/04_plot_outline.md` | yes | `templates/04_plot_outline.md` | 静的コピー |
| `<project>/05_chapter_outline.md` | yes | canonical template | target chars / gate threshold を埋めて生成 |
| `<project>/05_chapter_outline_100k.md` | no | - | 新規 write-path では生成しない |
| `<project>/generated_ideas.md` | conditional | repo root `generated_ideas.md` | `--from_ideas` 時のみコピー |
| `<project>/agent/state_schema_novel.yaml` | yes | schema template + injected values | canonical fields を埋めて生成 |
| `<project>/agent/memory/global_notes.md` | yes | new bootstrap stub or template | 最低限の運用メモを置く |
| `<project>/agent/memory/session_notes.md` | yes | new bootstrap stub or template | 初回の next action を残す |
| `<project>/runtime/` | no | - | 初期化では作らない |
| `<project>/chapter_1_introduction/body.md` | yes | generated | 現行通り生成 |
| `<project>/chapter_2_rising_action/body.md` | yes | generated | 現行通り生成 |
| `<project>/chapter_3_complication/body.md` | yes | generated | 現行通り生成 |
| `<project>/chapter_4_climax/body.md` | yes | generated | 現行通り生成 |
| `<project>/chapter_5_resolution/body.md` | yes | generated | 現行通り生成 |

##### Directories Inventory

| Path | Generate? | Notes |
|---|---|---|
| `<project>/` | yes | project root |
| `<project>/agent/` | yes | project-local agent root |
| `<project>/agent/memory/` | yes | project-local memory root |
| `<project>/chapter_1_introduction/` | yes | 現行互換 |
| `<project>/chapter_2_rising_action/` | yes | 現行互換 |
| `<project>/chapter_3_complication/` | yes | 現行互換 |
| `<project>/chapter_4_climax/` | yes | 現行互換 |
| `<project>/chapter_5_resolution/` | yes | 現行互換 |
| `<project>/runtime/` | no | runtime 生成時まで作らない |

#### Step 3-2b. File Ownership Rules を固定する

新規 project 生成後、各ファイルの正本責務を以下で固定する。

##### Ownership Rules

- `05_chapter_outline.md`
  - 全体計画と chapter / scene inventory の正本
- `agent/state_schema_novel.yaml`
  - target profile と planning 状態の正本
- `agent/memory/global_notes.md`
  - 運用上の共通契約の project-local 補助メモ
- `agent/memory/session_notes.md`
  - 初回着手点と次アクションの短期メモ
- `body.md`
  - 章メモ用であり、本文の正本ではない

#### Step 3-2c. Generated File Content Contract を固定する

##### `<project>/05_chapter_outline.md`

- 必須で埋める項目:
  - `Target Total Chars`
  - `Gate Threshold`
  - profile に応じた explanatory note
- 初期内容:
  - 5 章カードの空テンプレ
  - `Scene Type Bands`
  - `Planning Totals`

##### `<project>/agent/state_schema_novel.yaml`

- 必須で埋める項目:
  - `project.name`
  - `project.path`
  - `targets.target_total_chars`
  - `targets.target_length_profile`
  - `targets.planning_gate_enabled`
  - `targets.planning_gate_min_chars`
  - `targets.planning_target_total_chars`
  - `active_work.current_mode`
  - `active_work.recommended_skill`
  - `active_work.next_action`
  - `active_work.files_to_check_first`
  - `active_work.planning_gate_status`
- 初期値方針:
  - `planning_gate_status=blocked`
  - `recommended_skill=setting-creator`
  - `current_mode=project_bootstrap` または次工程に応じた正式モード

##### `<project>/agent/memory/global_notes.md`

- 初期化時は最小スタブでよい
- 最低限含める:
  - target profile summary
  - current length contract summary
  - note that scene text files become source of truth later

##### `<project>/agent/memory/session_notes.md`

- 初期化直後の短期メモとして生成する
- 最低限含める:
  - current state
  - next action
  - read first

#### Step 3-2d. Files Not Generated by Design

以下は「あえて生成しない」ことを仕様として固定する。

- `runtime/*`
- scene-level `chapter_x_scene_y.txt`
- legacy canonical duplicate `05_chapter_outline_100k.md`
- project-local copy of every top-level agent doc

#### Step 3-2e. `--from_ideas` Interaction Rules

`--from_ideas` を使う場合でも write-path の主契約は変わらない。

##### Rules

- `generated_ideas.md` のコピーは追加生成物として扱う
- `01_concept_sheet.md` へのログライン転記のみ追加で行う
- target profile / state / outline の生成内容は `--from_ideas` の有無で変えない

#### Step 3-2f. Phase 3 Write Sequence

`init_project.py` の内部処理順も固定しておく。

1. target total chars を確定する
2. target profile payload を解決する
3. project root を作る
4. project-local `agent/` と `agent/memory/` を作る
5. static templates をコピーする
6. `05_chapter_outline.md` を profile 値入りで生成する
7. `agent/state_schema_novel.yaml` を profile 値入りで生成する
8. `agent/memory/global_notes.md` / `session_notes.md` を生成する
9. chapter directories と `body.md` を生成する
10. `--from_ideas` があれば `generated_ideas.md` コピーと concept 転記を行う

#### Step 3-2g. Review Checklist for Write-Path

1. 新規 project に旧 outline 名が生成されていないか
2. project-local state file が生成されているか
3. state / outline / session note の target 値が一致しているか
4. `runtime/` を誤って先に生成していないか
5. `--from_ideas` が write-path 本体を変えていないか

#### Step 3-3a. Initial Generated Content Drafts を固定する

Phase 3 の実装では、単に file を作るだけでなく「初回起動時に中身が何を指しているか」まで一致している必要がある。

##### `<project>/05_chapter_outline.md` Draft

以下をベースに、`{target_total_chars}`、`{planning_gate_min_chars}`、`{target_length_profile}` を埋めて生成する。

```md
# 章カード＆シーン台帳 (Chapter Cards + Scene Ledger)

> このテンプレートは、作品全体を chapter / scene inventory ベースで管理するための正本です。
> Target Length Profile: `{target_length_profile}`
> Target Total Chars: `{target_total_chars}`
> Planning Gate Threshold: `{planning_gate_min_chars}`

---

## 全体方針

- Target Total Chars: {target_total_chars}
- Planning Gate Threshold: {planning_gate_min_chars}
- Target Length Profile: {target_length_profile}
- 章数は当面 5 章固定
- 1シーン固定ではなく、`scene_type` ごとの長さ帯で設計する

### Scene Type Bands

| scene_type | 用途 | min | target | max |
|---|---|---:|---:|---:|
| bridge | 接続、移動、軽い整理 | 1200 | 1500 | 1800 |
| standard | 通常の前進シーン | 1600 | 2000 | 2400 |
| anchor | 章の主軸になる重要シーン | 2200 | 2700 | 3200 |
| climax | 決断、対立、回収の山場 | 2600 | 3200 | 3800 |

---

## 第1章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 1-1 | anchor |  |  |  | 2200 | 2700 | 3200 | - | planned |

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第2章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第3章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第4章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第5章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## Planning Totals
- planned_scene_count:
- planned_total_min_chars:
- planned_total_target_chars:
- gate_threshold: {planning_gate_min_chars}
- gate_result:

## Notes
- `planned_total_min_chars` が `gate_threshold` 未満なら、執筆前にシーン在庫か章配分を増やす
- Target Length Profile は `{target_length_profile}`
- 新規本文の前に planning gate を確認する
```

##### Notes on the Draft

- scene type bands は当面固定
- profile 差は `Target Total Chars` と `Planning Gate Threshold` に集約する
- 30k / 50k でも 5 章テンプレを維持する

##### `<project>/agent/state_schema_novel.yaml` Draft

以下をベースに、project 固有値を埋めて生成する。

```yaml
version: 4

project:
  name: "{project_name}"
  path: "{project_path}"
  status: "active"
  notes: "新規初期化直後"

source_of_truth:
  prose_files: "scene txt files"
  chapter_notes_file: "body.md"
  backlog_files: []

profile:
  genre: ""
  target_audience: ""
  tone: ""
  pov_default: ""

targets:
  target_total_chars: {target_total_chars}
  target_length_profile: "{target_length_profile}"
  planning_gate_enabled: true
  planning_gate_min_chars: {planning_gate_min_chars}
  planning_target_total_chars: {target_total_chars}
  total_chars: {target_total_chars} # legacy compatibility
  chapter_chars: {}
  scene_default_chars: 1250
  scene_min_chars: 1000
  scene_max_chars: 1500
  # deprecated: length_mode は旧案件読み取り互換のため resolver 側のみで扱う
  scene_type_bands:
    bridge:
      min: 1200
      target: 1500
      max: 1800
    standard:
      min: 1600
      target: 2000
      max: 2400
    anchor:
      min: 2200
      target: 2700
      max: 3200
    climax:
      min: 2600
      target: 3200
      max: 3800

style_contract:
  pov: ""
  narration_tense: ""
  dialogue_rules: []
  lexical_rules: []
  tone_watch: []

characters: []

story_constraints:
  must_include: []
  must_avoid: []

continuity_watch:
  unresolved_threads: []
  upcoming_payoffs: []
  risk_flags: []
  planned_payoffs: []
  missing_payoffs: []

active_work:
  current_mode: "project_bootstrap"
  recommended_skill: "setting-creator"
  primary_scope: ""
  active_chapter: 0
  active_scene: ""
  next_action: "05_chapter_outline.md と基本設定を埋めて planning gate を通す"
  files_to_check_first:
    - "05_chapter_outline.md"
    - "01_concept_sheet.md"
    - "04_plot_outline.md"
  planning_gate_status: "blocked"
  current_scene_type: ""

progress:
  total_chapters: 5
  completed_chapters: []
  current_chapter: 0
  current_scene: ""
  total_chars_written: 0
  chapter_chars_written: {}
  planned_total_min_chars: 0
  planned_total_target_chars: 0
  planned_scene_count: 0
  completed_scene_count: 0
  chapter_scene_counts: {}
  chapter_planned_chars: {}

recent_decisions: []
open_questions: []
```

##### Notes on the State Draft

- 新規 write-path では `length_mode` は書かない
- `total_chars` は compatibility 用に残してよい
- `recommended_skill` と `planning_gate_status` は Phase 3 の初期値として固定する

##### `<project>/agent/memory/global_notes.md` Draft

```md
# Global Notes

## Project Bootstrapping Summary

- Target Total Chars: {target_total_chars}
- Target Length Profile: {target_length_profile}
- Planning Gate Threshold: {planning_gate_min_chars}
- Current Operating Assumption: planning gate を通すまで本文執筆に進まない

## Source of Truth

- 本文の正本は最終的に scene txt files
- `body.md` は章メモや再設計メモ向け
- 全体計画の正本は `05_chapter_outline.md`
```

##### `<project>/agent/memory/session_notes.md` Draft

```md
# Session Notes

- Current State: 新規 project を初期化した直後
- Planning Gate: blocked
- Next Action: `05_chapter_outline.md` と基本設定を埋めて planning gate を通す
- Read First: `05_chapter_outline.md`, `01_concept_sheet.md`, `04_plot_outline.md`
```

#### Step 3-3b. Generation Method Rules

各ファイルの生成方法も固定する。

##### Generation Rules

- `01` から `04` の md:
  - 基本は template の静的コピー
- `05_chapter_outline.md`:
  - template ベース + placeholder 置換
- `agent/state_schema_novel.yaml`:
  - schema 雛形ベース + placeholder 置換
- `agent/memory/global_notes.md`:
  - bootstrap stub を直接生成
- `agent/memory/session_notes.md`:
  - bootstrap stub を直接生成

#### Step 3-3c. Placeholder Set

初期生成時に埋める placeholder は以下に限定する。

| Placeholder | Source |
|---|---|
| `{project_name}` | CLI 引数 |
| `{project_path}` | 実解決した絶対パス |
| `{target_total_chars}` | resolver payload |
| `{target_length_profile}` | resolver payload |
| `{planning_gate_min_chars}` | resolver payload |

#### Step 3-3d. Review Checklist for Initial Content

1. `05_chapter_outline.md` に target total と gate threshold が入っているか
2. `agent/state_schema_novel.yaml` に canonical fields が入っているか
3. `session_notes.md` の `Read First` が state と矛盾していないか
4. `global_notes.md` が project 固有 summary だけに留まり、共通ルールの重複で肥大化していないか
5. legacy 互換項目が新正本を汚染していないか

#### Step 3-3. Template Migration Rule を固定する

template 変更は「文言の一般化」と「canonical filename 化」を分けて扱う。

##### Template Work Split

| Template | Change Type |
|---|---|
| `05_chapter_outline.md` | 新 canonical template を追加 |
| `05_chapter_outline_100k.md` | 互換資産として残すか、wrapper 的扱いにする |
| `01_concept_sheet.md` | 参照先 filename の一般化 |
| `04_plot_outline.md` | 参照先 filename の一般化 |

#### Step 3-4. State Schema Migration Rule を固定する

`agent/state_schema_novel.yaml` のサンプル既定値も canonical fields に寄せるが、legacy 説明はコメントで残してよい。

##### State Schema Update Items

- `targets.target_total_chars`
- `targets.target_length_profile`
- `targets.planning_gate_enabled`
- 旧 `length_mode` の扱いコメント
- `files_to_check_first` の例 path 更新

#### Step 3-5. File-by-File Work Plan

##### `scripts/init_project.py`

- argparse に `--target-total-chars` を追加
- allowed choices を制限
- target profile を算出
- 新 outline をコピー
- 必要なら project 配下に state 初期ファイルを書ける形へ拡張

##### `templates/05_chapter_outline.md`

- 100k 固有文言を除去
- `Target Total Chars` と `Gate Threshold` が profile に応じて埋められる余地を残す

##### `agent/state_schema_novel.yaml`

- canonical fields を例示
- comments を新 terminology へ更新

#### Step 3-6. Review Checklist

1. `init_project.py` が 3 値以外を受けないか
2. state と outline の target 値がズレないか
3. `--from_ideas` の既存挙動を壊していないか
4. canonical filename のみを書き出しているか

### Phase 3 Hard Stop Conditions

1. default target 挙動が未確定
2. state を書くのか template のみなのかが未整理
3. canonical outline と legacy outline を同時生成するかが未確定
4. 5 章固定を崩す変更が紛れ込んでいる

### Phase 3 Deliverables

- CLI contract for target selection
- new project write contract
- template migration split
- file-by-file implementation plan for bootstrap layer

---

## Phase 4: Runtime and Prompt Refactor

### Goal

runtime / prompt / checker が、新 canonical fields と profile を前提に動きつつ、旧 project も処理できる状態にする。

### Tasks

1. `build_runtime_context.py` の `long_form_100k` 分岐を profile/gate ベースに置換する
2. `planning_gate_brief.md` に `Target Total Chars` と profile 情報を明示する
3. `build_draft_prompt.py` の gate 判定を新 canonical source に寄せる
4. `build_llm_prompt.py` の outline path と target chars 表示を新正本化する
5. `check_scene_output.py` は scene band ロジックを維持しつつ、新 profile project で壊れないことを確認する

### Files

- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/build_llm_prompt.py`
- `scripts/check_scene_output.py`
- `scripts/prompt_utils.py`

### Validation

- 30k / 50k / 100k の新規 project で runtime artifacts が生成される
- 旧 100k project でも runtime artifacts が従来通り生成される
- blocked gate は全 profile で同じ規則で止まる
- profile 情報が `planning_gate_brief.md` と `request_compact.md` に載る

### Required Tests

- runtime project fixture for 30k
- runtime project fixture for 50k
- runtime project fixture for 100k
- old legacy 100k outline fixture still passes
- draft prompt guard works for blocked 30k / 50k / 100k

### Exit Criteria

- runtime layer が新旧 project を共通処理できる
- `long_form_100k` 依存の主要分岐が profile/gate 基準へ置換される

### Rollback Rule

- legacy 100k runtime に不整合が出た場合は、新 write-path を止め、profile 解決ロジックだけ残す

### Phase 4 Execution Pack

#### Step 4-1. Runtime Output Contract を固定する

runtime artifacts は、新 profile project でも旧 project でも、最低限同じ読み口を保つ。

##### Runtime Output Additions

- `planning_gate_brief.md` に `Target Total Chars`
- `planning_gate_brief.md` に `Target Length Profile`
- `request_compact.md` に `Target Total Chars` または profile
- 必要なら `Length Mode` は compatibility note に格下げ

#### Step 4-2. Branch Replacement Rule を固定する

`long_form_100k` を直接見る分岐は、原則として以下へ置換する。

##### Replacement Rule

- old: `length_mode == "long_form_100k"`
- new: `planning_gate_enabled is True`

補助的に profile 表示が必要な場合だけ `target_length_profile` を使う。

#### Step 4-3. File-by-File Work Plan

##### `scripts/build_runtime_context.py`

- `planning_meta` に canonical profile payload を混ぜる
- `build_planning_gate_brief()` へ target total/profile を追加
- `next_action` 文言を profile 非依存へ調整
- outline not found error を新旧 filename 対応にする

##### `scripts/build_draft_prompt.py`

- gate 判定は `planning_gate_brief.md` または canonical meta から読む
- prompt に profile 情報を入れるかを決める
- blocked 判定メッセージを profile 共通文へ揃える

##### `scripts/build_llm_prompt.py`

- canonical outline path resolver を利用
- length contract 表示に project total target を追加するか判断
- legacy prompt でも新規 project を扱えるようにする

##### `scripts/check_scene_output.py`

- scene band 判定ロジックは維持
- new profile project に対して state/profile の有無で壊れないことを確認

#### Step 4-4. Output Snapshot Review Points

レビュー時は以下を snapshot 的に確認する。

1. `planning_gate_brief.md` に target total が出ているか
2. `request_compact.md` に profile または target total が載るか
3. blocked gate のエラーメッセージが profile 非依存になっているか
4. legacy 100k project で出力フォーマットが破壊されていないか

#### Step 4-5. Migration Safety Rule

この Phase では artifact の key headings を大きく変えない。

##### Keep Stable

- `Planning Gate:`
- `Planned Total Min Chars:`
- `Next Planning Action:`
- `Length Band:`

#### Step 4-6. Review Checklist

1. `long_form_100k` 文字列依存が runtime 層で減っているか
2. artifact heading が下流 skill の期待を壊していないか
3. legacy fixture の出力比較が大きく崩れていないか
4. blocked guard が 30k/50k/100k 全てで説明可能か

#### Step 4-7. Runtime Artifact Drafts を固定する

Phase 4 では、canonical target 情報を runtime artifact にどう表出するかを出力断片レベルまで固定する。

##### `runtime/planning_gate_brief.md` Draft

```md
# Planning Gate Brief
Target Length Profile: novel_50k
Target Total Chars: 50000
Planning Gate Enabled: true
Planning Gate: blocked
Planning Totals:
- Planned Scene Count: 18
- Planned Total Min Chars: 34200
- Planned Total Target Chars: 46800
- Gate Threshold: 40000
- Target Total Chars: 50000
Coverage Snapshot:
- Outline Chapters Found: 5
- Chapters With Scene Inventory: 1, 2, 3
- Chapters Missing Scene Inventory: 4, 5
- Gate Gap To Threshold: 5800
Next Planning Action:
- 不足している章の Scene Ledger を先に埋める: 第4章, 第5章
```

##### Rules for `planning_gate_brief.md`

- heading `# Planning Gate Brief` は維持する
- `Planning Gate:` 行は既存互換のため必須
- canonical target 情報は `Planning Gate:` より前に置く
- `Target Total Chars` は重複しても、summary section と header section の両方に出してよい
- `Length Mode` は canonical field へ移行後は削除候補

##### `runtime/request_compact.md` Draft

```md
# Request Compact
Current Mode: draft
Purpose: 圧縮済み文脈のみで初稿の骨格を作る
Deliverables:
- 自然な本文初稿
- 直前シーンと接続した導入
- 次シーンへ渡すフック
Constraints:
- フル文脈を再投入しない
- 文体契約を優先する
- 対象シーン: 2-3
- Target Length Profile: novel_50k
- Target Total Chars: 50000
- Planning Gate Enabled: true
- Planning Gate: blocked
- Target Band: 1600 / 2000 / 2400
Priority: balanced
```

##### Rules for `request_compact.md`

- `Planning Gate:` 行は既存互換のため維持する
- `Target Length Profile` と `Target Total Chars` は `Constraints:` ブロック内に入れる
- `Length Mode` は新規 write-path では原則出さない
- 旧案件互換が必要な間だけ `Length Mode` を補助行として残してもよい

##### `runtime/scene_brief_compact.md` Draft

```md
# Scene Brief Compact
Goal: 主人公が依頼を受け、次の障害へ進む理由を確定する
Conflict: 依頼を受けることで失うものを最低1つ置く
Emotion Shift: 日常 -> 予感
Hook: 仲間と合流した直後に最初の障害へぶつかる
Scene Type: standard
Length Band: 1600 / 2000 / 2400
Target Length Profile: novel_50k
Target Total Chars: 50000
Chapter Budget Remaining: 8200
Chapter Planned Scenes Remaining: 4
This Scene Pays Off: -
This Scene Seeds: 障害への予感
Depends On: 2-1
Hard Constraints:
- Scene ID: 2-3
- Source Outline: Scene Ledger を起点に構成する
- Planning Gate: blocked
- 直前シーンとの接続を優先する
- 新しい設定事実は必要最小限に留める
```

##### Rules for `scene_brief_compact.md`

- `Length Band:` と `Planning Gate:` は既存互換のため維持する
- target profile / total chars は `Length Band` の後ろに追加する
- 下流 skill が `Scene Type` と `Length Band` を正本として読む前提は変えない

##### `runtime/style_contract_compact.md` Draft

```md
# Style Contract Compact
- 視点: 一人称（主人公）
- 地の文時制: 過去形
- 口調ルール:
  - 主要キャラの語尾と話し方を固定する
- 禁止表現:
  - 見出しや箇条書きの混入
  - 作者視点のメタ説明
- 文字数契約:
  - 初稿: 1600 / 2000 / 2400 字（min/target/max）
- Planning Context:
  - Target Length Profile: novel_50k
  - Target Total Chars: 50000
```

##### Rules for `style_contract_compact.md`

- style contract の本体は scene band 優先で維持する
- target profile 情報は補助情報として末尾に置く
- ここを routing の正本にしない

##### `runtime/draft_prompt.txt` Draft Fragment

```txt
## Request Compact
# Request Compact
Current Mode: draft
...
- Target Length Profile: novel_50k
- Target Total Chars: 50000
- Planning Gate Enabled: true
- Planning Gate: ready
- Target Band: 1600 / 2000 / 2400

## Planning Gate Brief
# Planning Gate Brief
Target Length Profile: novel_50k
Target Total Chars: 50000
Planning Gate Enabled: true
Planning Gate: ready
...
```

##### Rules for `draft_prompt.txt`

- `build_draft_prompt.py` は canonical target 情報を runtime artifact から受け取り、そのまま含めてよい
- prompt 側で新たに target profile を再計算しない
- blocked guard は `Planning Gate:` または canonical planning metadata から判定する

#### Step 4-8. Artifact Field Stability Rules

追加 field は入れるが、既存 field の削除はこの Phase では慎重に扱う。

##### Must Stay Stable

- `Planning Gate:`
- `Length Band:`
- `Scene Type:`
- `Target Band:`
- `Next Planning Action:`

##### May Be Deprecated Later

- `Length Mode:`

#### Step 4-9. Parsing Compatibility Notes

Phase 4 実装時、既存 parser や regex は以下の前提で守る。

##### Existing Parsers That Must Keep Working

- `build_draft_prompt.py` の `parse_scene_brief_metadata()`
  - `Scene Type:` と `Length Band:` を読み続けられること
- `build_draft_prompt.py` の `parse_request_compact_metadata()`
  - `- Planning Gate:` を読み続けられること
- `build_draft_prompt.py` の `parse_planning_gate_brief_metadata()`
  - `Planning Gate:` を読み続けられること
- `check_scene_output.py`
  - `Length Band:` 依存を壊さないこと

#### Step 4-10. Snapshot Assertions to Add Later

Phase 6 で追加する snapshot/assertion 候補も、ここで固定する。

##### Suggested Assertions

- `planning_gate_brief.md` contains `Target Length Profile: novel_30k|novel_50k|novel_100k`
- `planning_gate_brief.md` contains `Target Total Chars: ...`
- `request_compact.md` contains `Planning Gate Enabled: true`
- `scene_brief_compact.md` contains `Target Length Profile: ...`
- `draft_prompt.txt` still includes `## Planning Gate Brief`

### Phase 4 Hard Stop Conditions

1. runtime artifact の heading を無計画に変更している
2. `build_draft_prompt.py` の blocked guard が state/profile と二重実装されている
3. legacy outline project が runtime 生成できない
4. `check_scene_output.py` が profile 導入で band 判定を失っている

### Phase 4 Deliverables

- runtime output contract
- branch replacement rule
- artifact snapshot review checklist
- file-by-file runtime refactor plan

---

## Phase 5: Agent Routing Refactor

### Goal

agent の判断が `long_form_100k` 固定ではなく、選択された target profile を基準に動く状態へ移行する。

### Tasks

1. `agent/HUB.md` の `long_form_100k` 依存記述を profile/gate ベースに置換する
2. `project-bootstrap` に `3万 / 5万 / 10万` の初期選択ルールを追加する
3. `setting-creator` の必須 planning 条件を profile 共通に整理する
4. `scene-planner` / `resume-orchestrator` / `novel-writer` の blocked 判定を profile 共通にする
5. `request_template.md` の `Length Mode` 欄を `Target Length Profile` または `Target Total Chars` 中心に再設計する

### Files

- `agent/HUB.md`
- `agent/skills/project-bootstrap/SKILL.md`
- `agent/skills/setting-creator/SKILL.md`
- `agent/skills/scene-planner/SKILL.md`
- `agent/skills/resume-orchestrator/SKILL.md`
- `agent/skills/novel-writer/SKILL.md`
- `agent/request_template.md`

### Validation

- blocked planning case が profile に関係なく `setting-creator` へ落ちる
- new project bootstrap で 3 択を前提に説明できる
- agent docs に 100k 固有前提が残っていない

### Required Tests / Checks

- router regression: blocked planning wording still maps to `setting-creator`
- router regression: project bootstrap wording mentions target total chars
- manual review: docs 同士で field 名がぶれていない

### Exit Criteria

- agent docs が canonical model と整合
- routing rule が新旧 project を同じ基準で扱える

### Rollback Rule

- docs 間で field 名が揃わない場合は merge しない

### Phase 5 Execution Pack

#### Step 5-1. Routing Language Contract を固定する

agent docs では、`long_form_100k` という用語を routing 条件の主語にしない。

##### New Routing Vocabulary

- `target_length_profile`
- `target_total_chars`
- `planning_gate_enabled`
- `planning_gate_status`

#### Step 5-2. Skill-by-Skill Rewrite Policy を固定する

##### `agent/HUB.md`

- global routing rules を canonical vocabulary へ置換
- blocked planning の共通条件を `planning_gate_enabled + planning_gate_status != ready` にする

##### `project-bootstrap`

- 必須入力に `Target Total Chars` を追加
- 3 択を最初に決める手順を追加
- `init_project.py` 呼び出し例を新 CLI に更新

##### `setting-creator`

- planning gate は 100k 専用ではなく profile 共通の設計工程として記述
- outline 名を canonical 名中心に更新

##### `scene-planner`

- blocked 判定の条件を canonical vocabulary に変更
- `memory/05_chapter_outline_100k.md` 参照を canonical + legacy fallback に書き換える

##### `resume-orchestrator`

- profile 共通で blocked planning を `setting-creator` へ返す
- stale 判定ロジックの文面は維持しつつ、target profile terminology へ寄せる

##### `novel-writer`

- drafting 前提条件を canonical vocabulary に変更
- `Planning Gate` 参照ルールを runtime artifact 基準で維持

##### `request_template`

- `Length Mode` を主項目から下げ、`Target Total Chars` と `Target Length Profile` を前面に出す
- 記入例も 3 択前提へ更新する

#### Step 5-3. Documentation Consistency Rules

各 doc で以下を統一する。

| Concept | Canonical Label |
|---|---|
| 作品全体の目標文字数 | `Target Total Chars` |
| プロファイル名 | `Target Length Profile` |
| gate 有効判定 | `Planning Gate Enabled` |
| gate 状態 | `Planning Gate` または `planning_gate_status` |

#### Step 5-4. Manual Review Pass

コード変更後の doc review では、以下を grep で確認する。

1. `long_form_100k` が routing condition として残っていないか
2. `05_chapter_outline_100k.md` が canonical path のように書かれていないか
3. `Length Mode` が主入力のように残っていないか
4. field 名が `target_total_chars` / `target_length_profile` に揃っているか

#### Step 5-5. Router Safety Checks

この Phase は docs 更新中心だが、routing の安全性を落とさないため以下を確認する。

- blocked planning prompt は引き続き `setting-creator` に落ちる
- bootstrap prompt は target total chars を含んでも誤ルーティングしない
- scene planning prompt が profile 名を含んでも主目的を見失わない

#### Step 5-6. Doc Rewrite Before/After を固定する

Phase 5 では、置換対象の文言を before/after で固定してから編集する。

##### `agent/HUB.md`

###### Before

- `long_form_100k` では、`planning_gate_status=ready` になるまで `scene-planner` / `novel-writer` へ進めず、先に `setting-creator` で計画を詰める
- ただし `long_form_100k` で `planning_gate_status != ready` の場合: `project-bootstrap` / `resume-orchestrator` / `scene-planner` から `setting-creator` を優先する

###### After

- `planning_gate_enabled=true` で、`planning_gate_status=ready` になるまで `scene-planner` / `novel-writer` へ進めず、先に `setting-creator` で計画を詰める
- `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合: `project-bootstrap` / `resume-orchestrator` / `scene-planner` から `setting-creator` を優先する

##### `agent/skills/project-bootstrap/SKILL.md`

###### Before

- 必要なら `length_mode`
- `length_mode` を 1 つ決める
- `long_form_100k` の場合は、この段階では執筆前提を作らず、長編計画ゲートを通す前提で初期化する

###### After

- 必須: `Target Total Chars` または `Target Length Profile`
- `30000 / 50000 / 100000` のいずれかを最初に決める
- `planning_gate_enabled=true` の profile では、この段階では執筆前提を作らず、planning gate を通す前提で初期化する

##### `agent/skills/setting-creator/SKILL.md`

###### Before

- `length_mode` が `long_form_100k` かどうかを確認する
- `long_form_100k` の場合は `05_chapter_outline_100k.md` を必須とする

###### After

- `target_total_chars` / `target_length_profile` / `planning_gate_enabled` を確認する
- `planning_gate_enabled=true` の場合は `05_chapter_outline.md` を正本として必須とする
- legacy project では `05_chapter_outline_100k.md` を fallback として読んでよい

##### `agent/skills/scene-planner/SKILL.md`

###### Before

- `long_form_100k` で `planning_gate_status != ready` の場合は、シーン段取りへ進まず `setting-creator` へ戻す
- 対象プロジェクトの `memory/05_chapter_outline_100k.md`

###### After

- `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合は、シーン段取りへ進まず `setting-creator` へ戻す
- 対象プロジェクトの `05_chapter_outline.md` を優先し、legacy project では `05_chapter_outline_100k.md` を fallback とする

##### `agent/skills/resume-orchestrator/SKILL.md`

###### Before

- `long_form_100k` や planning gate 確認が必要な場合は、対象プロジェクトの `state_schema_novel.yaml`
- `long_form_100k` で `planning_gate_status != ready` の場合は、再開対象が本文寄りでも `setting-creator` を優先する

###### After

- target profile や planning gate 確認が必要な場合は、対象プロジェクトの `state_schema_novel.yaml`
- `planning_gate_enabled=true` かつ `planning_gate_status != ready` の場合は、再開対象が本文寄りでも `setting-creator` を優先する

##### `agent/skills/novel-writer/SKILL.md`

###### Before

- `long_form_100k` で `planning_gate_status != ready` のまま初稿を書き始めない

###### After

- `planning_gate_enabled=true` かつ `planning_gate_status != ready` のまま初稿を書き始めない
- `Target Length Profile` は補助情報として扱い、本文の長さ制御自体は `Length Band` を正本とする

##### `agent/request_template.md`

###### Before

- `Length Mode`（例: `standard` / `long_form_100k`）
- `long_form_100k` では固定 `1000-1500` ではなく、`scene_type` ごとの `Length Band` を使う

###### After

- `Target Total Chars`（例: `30000` / `50000` / `100000`）
- `Target Length Profile`（例: `novel_30k` / `novel_50k` / `novel_100k`）
- `planning_gate_enabled=true` の profile では固定 `1000-1500` ではなく、`scene_type` ごとの `Length Band` を使う

#### Step 5-7. Section-Level Rewrite Targets

各 doc でどの section を優先的に更新するかも固定する。

##### `agent/HUB.md`

- top-level routing rules
- handoff conditions
- common notes

##### `project-bootstrap`

- required inputs
- procedure step 1
- procedure step 3
- outputs
- do not

##### `setting-creator`

- read first
- procedure step 1
- procedure step 3
- do not

##### `scene-planner`

- read first
- procedure step 2
- procedure step 4
- do not

##### `resume-orchestrator`

- read first
- procedure step 3
- procedure step 4
- handoff

##### `novel-writer`

- read first
- drafting gate checks
- do not

##### `request_template`

- common rules
- project bootstrap template
- common helper items
- minimal request examples

#### Step 5-8. New Canonical Phrases to Reuse

文書間のブレを防ぐため、以下の定型句を使い回す。

##### Reusable Phrases

- `planning_gate_enabled=true の案件では、planning gate 通過前に本文執筆へ進めない`
- `Target Total Chars を最初に決める`
- `全体計画の正本は 05_chapter_outline.md`
- `legacy project では 05_chapter_outline_100k.md を fallback として読んでよい`
- `Target Length Profile は補助ラベルであり、本文長の正本は Length Band`

#### Step 5-9. Grep Checklist Before Merge

Phase 5 の merge 前に、最低限以下を確認する。

```bash
rg -n "long_form_100k|05_chapter_outline_100k.md|Length Mode" agent
```

##### Expected Outcome

- `long_form_100k`
  - routing 条件としては極小化されている
  - 残る場合は legacy fallback 説明のみ
- `05_chapter_outline_100k.md`
  - canonical file のようには書かれていない
  - fallback 説明としてのみ残る
- `Length Mode`
  - 新主入力ではなく補助/legacy 用語としてのみ残る

### Phase 5 Hard Stop Conditions

1. docs 間で canonical label が揃っていない
2. `long_form_100k` が条件文として大量に残る
3. outline path の説明が canonical/legacy で逆転している
4. request template が旧 terminology のまま

### Phase 5 Deliverables

- routing language contract
- skill-by-skill rewrite policy
- documentation consistency rules
- manual review and router safety checklist

---

## Phase 6: Test Expansion and Migration Safety

### Goal

新旧両系統を守るテスト網を作り、移行中の破壊を防ぐ。

### Tasks

1. 既存 100k tests を legacy compatibility bucket として整理する
2. 30k / 50k / 100k の新 canonical fixture を追加する
3. old-state/new-outline、new-state/old-outline など混在ケースを追加する
4. invalid state / invalid target chars / unknown profile の異常系を追加する
5. snapshot 的に runtime artifact の主要行を検証する

### Test Matrix

| Case | State | Outline | Expected |
|---|---|---|---|
| A | old | old | pass |
| B | new 30k | new | pass |
| C | new 50k | new | pass |
| D | new 100k | new | pass |
| E | new 30k | old | pass |
| F | old | new | pass if resolvable |
| G | invalid target | any | fail fast |
| H | blocked gate 30k | new | draft blocked |
| I | blocked gate 50k | new | draft blocked |
| J | blocked gate 100k | new | draft blocked |

### Files

- `tests/test_scripts.py`
- 必要なら `tests/fixtures/*`

### Validation

- 新旧混在ケースが定義済み
- `init_project`、runtime、draft prompt、router の 4 系統に最低 1 つずつ新 profile test がある
- 100k 既存運用の characterization test が残っている

### Exit Criteria

- この refactor の主要リスクがテストで再現できる
- 互換 regression が CI 相当で検出可能になる

### Rollback Rule

- mixed compatibility case が通らない限り、旧 outline 名削除や旧 field 廃止には進まない

### Phase 6 Detailed Test Backlog

Phase 6 のテスト追加は、以下の wave に分けて順に積む。

#### Wave 1: Compatibility Guard

1. `legacy_runtime_project_with_old_state_and_old_outline_passes`
2. `legacy_build_llm_prompt_with_old_outline_passes`
3. `legacy_router_prompt_for_blocked_planning_still_maps_to_setting_creator`

#### Wave 2: Canonical Happy Path

1. `canonical_30k_init_project_writes_target_profile`
2. `canonical_50k_init_project_writes_target_profile`
3. `canonical_100k_init_project_writes_target_profile`
4. `canonical_30k_runtime_generates_planning_gate_brief`
5. `canonical_50k_runtime_generates_planning_gate_brief`
6. `canonical_100k_runtime_generates_planning_gate_brief`

#### Wave 3: Mixed Compatibility

1. `mixed_new_state_with_legacy_outline_passes`
2. `mixed_legacy_state_with_new_outline_passes`
3. `mixed_new_profile_with_legacy_fields_present_prefers_new_fields`

#### Wave 4: Guard Rails

1. `invalid_target_total_chars_fails_fast`
2. `invalid_target_length_profile_fails_fast`
3. `blocked_30k_draft_prompt_is_rejected`
4. `blocked_50k_draft_prompt_is_rejected`
5. `blocked_100k_draft_prompt_is_rejected`

#### Wave 5: Output Consistency

1. `planning_gate_brief_includes_target_total_chars`
2. `request_compact_includes_target_profile`
3. `state_profile_resolution_prefers_new_fields_over_legacy_fields`

---

## Phase 7: Docs and Rollout

### Goal

ユーザー向け説明、開発者向け説明、移行時の注意事項を揃える。

### Tasks

1. `README.md` の「10万字固定」表現を 3 択へ更新する
2. `walkthrough.md` の初期化手順と milestone 説明を一般化する
3. 新規 project と既存 project の差分を短い migration note にまとめる
4. 旧名の outline をいつまで残すか明記する
5. decisions / change log に設計判断を記録する

### Files

- `README.md`
- `walkthrough.md`
- 必要なら `agent/decisions_log.md`
- 必要なら `agent/change_log.md`

### Validation

- README の導入、手順、構成図が canonical model と一致する
- walkthrough が 100k 固有前提を含まない
- migration note が既存ユーザーに必要な最小手順を示している

### Exit Criteria

- 新規利用者が 3 択の存在を README だけで理解できる
- 既存利用者が互換方針を誤解しない

### Rollback Rule

- docs 更新だけ先行公開しない
- 実装とテストが揃ってから反映する

---

## Cross-Phase Validation Strategy

### 1. Characterization First

最初に既存 100k 運用の期待動作を固定し、以後はその差分として新 profile を追加する。

### 2. Dual-Read Before Single-Write

先に新旧両方を読めるようにしてから、新規 project の書き出し形式を切り替える。

### 3. Legacy Fixtures Must Stay Green

既存 100k fixture が落ちた場合は、新 profile 実装を進めない。

### 4. File Rename Must Be Non-Destructive

`05_chapter_outline_100k.md` を読む処理を消すのは最後にする。最初の段階では rename を必須にしない。

## Merge Gates

各 Phase の merge 前に最低限満たすべき条件:

- Phase 2: legacy 100k runtime tests green
- Phase 3: new init flow for 30k/50k/100k green
- Phase 4: runtime and draft prompt tests green for old/new projects
- Phase 5: router and skill docs internally consistent
- Phase 6: mixed compatibility matrix green
- Phase 7: user docs reflect actual shipped behavior

## Known Risks

### Risk 1: `length_mode` と `target_length_profile` の二重正本化

対策:
- read-path は両方読む
- write-path は新 field のみを正本にする
- 旧 field は deprecate 扱いで注記する

### Risk 2: outline ファイル名変更による探索漏れ

対策:
- 共通関数へ path 解決を集約する
- 直書き探索を段階的に排除する

### Risk 3: agent docs だけ古いまま残る

対策:
- Phase 5 を独立 Phase にする
- skill 群と `HUB.md` を同じタイミングで更新する

### Risk 4: 30k / 50k に 100k と同じ planning gate 文言を当てて違和感が出る

対策:
- gate の考え方は共通にしつつ、説明文は profile 依存で調整可能にする
- `Planning Gate Brief` に target total を明示する

## Resolved Decisions

1. `init_project.py` の未指定時挙動
   - 決定: CLI の移行期間では `100000` を legacy compatibility fallback とし、warning を出す
   - 決定: agent / bootstrap の新標準導線では `30000 / 50000 / 100000` の明示選択を必須にする
   - 理由: 既存 CLI 利用と既存テストを即時に壊さず、同時に「最初に選択する」新要件も満たせる

2. 新 outline ファイル名
   - 決定: canonical filename は `05_chapter_outline.md` とする
   - 理由: 100k 固有名を排除しつつ、既存の番号体系と役割を維持できる

3. 旧 `length_mode` の扱い
   - 決定: 新規 project では canonical field のみを書き、旧 `length_mode` は書かない
   - 決定: 読み取り互換のため、resolver では当面 `length_mode` を読む
   - 決定: `state_schema_novel.yaml` には deprecate コメントを残してよい
   - 理由: 二重正本化を避けつつ、旧案件の無修正動作を維持するため

4. `planning_gate_enabled` の扱い
   - 決定: field として持つ
   - 理由: 今回の 3 profile はすべて `true` だが、将来 profile 追加時に routing 条件と target chars を切り離せる
   - 実装ルール: routing と gate enforcement は `planning_gate_enabled + planning_gate_status` を主条件にする

### Decision Impact Summary

- Phase 1: canonical state contract をこの決定に合わせて固定する
- Phase 2: read-path は `length_mode` 互換を維持する
- Phase 3: `init_project.py` は新規 write-path で canonical fields のみを出力する
- Phase 4: runtime 層は `planning_gate_enabled` を主条件として使う
- Phase 5: docs / skills / HUB は `Length Mode` 中心表現から段階的に離脱する

## Recommended Order of Execution

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 6 の一部を先行実装して compatibility tests を増やす
5. Phase 3
6. Phase 4
7. Phase 5
8. Phase 6 の残り
9. Phase 7

## PR Breakdown Plan

この refactor は、1 回でまとめて変更せず、依存順に沿って複数 PR に分ける。

分割の原則:

- 先に test と read-path を固める
- write-path 変更は後ろに送る
- runtime artifact 変更と agent docs 変更を分ける
- 各 PR は単独で review と rollback が可能な粒度にする

### PR1: Baseline and Characterization Tests

#### Goal

既存 100k 運用と、Phase 2 で必要になる互換観測点をテストで固定する。

#### Scope

- Phase 0
- Phase 2 の先行テスト追加部分

#### Files

- `tests/test_scripts.py`
- 必要なら新しい test helper fixture
- `agent/target_length_profile_refactor_plan.md` の参照更新のみ

#### Changes

- existing characterization bucket を補強する
- resolver 導入前提の先行テストを追加する
- 旧 outline 名 / 旧 state 解決の期待値を固定する

#### Must Not Change

- production scripts
- templates
- agent docs

#### Required Tests

- `python -m pytest tests/test_scripts.py -v`

#### Merge Criteria

- 既存 baseline tests が green
- 新しい legacy/canonical pre-tests が green
- production behavior に差分がない

#### Rollback Surface

- test only

---

### PR2: Resolver Layer and Read-Path Compatibility

#### Goal

新旧 state / outline を解決する共通 resolver を追加し、runtime / legacy prompt の read-path を互換化する。

#### Scope

- Phase 2 本体

#### Files

- `scripts/prompt_utils.py`
- `scripts/build_runtime_context.py`
- `scripts/build_llm_prompt.py`
- `tests/test_scripts.py`

#### Changes

- resolver API を追加する
- `resolve_outline_path()` を導入する
- `load_target_length_profile()` / `load_planning_metadata()` を canonical payload 対応にする
- runtime / llm prompt の direct path access を resolver 経由へ置換する

#### Must Not Change

- `init_project.py` の write-path
- templates の canonical filename
- agent docs

#### Required Tests

- `python -m pytest tests/test_scripts.py -k "TargetProfileResolvers or RuntimeRefactorScripts or BuildLLMPrompt" -v`
- 必要なら全体 `python -m pytest tests/test_scripts.py -v`

#### Merge Criteria

- legacy 100k runtime flow が green
- legacy outline only case が green
- canonical 30k/50k resolver tests が green
- write-path の挙動が変わっていない

#### Rollback Surface

- resolver 層と read-path のみ

---

### PR3: Bootstrap Write-Path and Canonical Templates

#### Goal

新規 project 作成時に `30000 / 50000 / 100000` を扱う canonical write-path を導入する。

#### Scope

- Phase 3 本体

#### Files

- `scripts/init_project.py`
- `templates/05_chapter_outline.md`
- `templates/01_concept_sheet.md`
- `templates/04_plot_outline.md`
- `agent/state_schema_novel.yaml`
- 必要なら project-local memory stub 生成ロジック
- `tests/test_scripts.py`

#### Changes

- `--target-total-chars` を追加する
- project-local `agent/state_schema_novel.yaml` を生成する
- project-local `agent/memory/global_notes.md` / `session_notes.md` を生成する
- canonical `05_chapter_outline.md` を生成する
- 新規 project では `05_chapter_outline_100k.md` を生成しない

#### Must Not Change

- runtime artifact format
- agent routing docs

#### Required Tests

- `python -m pytest tests/test_scripts.py -k "InitProject" -v`
- canonical 30k/50k/100k init tests
- `--from_ideas` regression

#### Merge Criteria

- new init flow for 30k/50k/100k is green
- legacy init invocation without explicit target still works with warning
- generated file inventory matches plan

#### Rollback Surface

- write-path only
- if unstable, can revert to old init while keeping PR2 resolver layer

---

### PR4: Runtime Artifact Canonicalization

#### Goal

runtime artifacts と draft prompt guard を canonical target fields に対応させる。

#### Scope

- Phase 4 本体

#### Files

- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/build_llm_prompt.py`
- `scripts/check_scene_output.py`
- `scripts/prompt_utils.py`
- `tests/test_scripts.py`

#### Changes

- `planning_gate_brief.md` に target profile / total chars を出す
- `request_compact.md` に canonical target fields を出す
- `scene_brief_compact.md` に canonical target fields を補助情報として出す
- blocked guard を `planning_gate_enabled + planning_gate_status` 基準に整理する

#### Must Not Change

- `Planning Gate:`
- `Length Band:`
- `Scene Type:`
- `Target Band:`

#### Required Tests

- `python -m pytest tests/test_scripts.py -k "RuntimeRefactorScripts or BuildLLMPrompt" -v`
- blocked 30k/50k/100k draft prompt tests
- legacy runtime snapshot checks

#### Merge Criteria

- runtime layer works for old/new projects
- existing regex-based parsers still pass
- legacy 100k artifacts remain readable

#### Rollback Surface

- runtime artifact format and guard logic only

---

### PR5: Agent Routing and Skill Docs Migration

#### Goal

agent の routing 条件と skill 文言を canonical vocabulary に移行する。

#### Scope

- Phase 5 本体

#### Files

- `agent/HUB.md`
- `agent/skills/project-bootstrap/SKILL.md`
- `agent/skills/setting-creator/SKILL.md`
- `agent/skills/scene-planner/SKILL.md`
- `agent/skills/resume-orchestrator/SKILL.md`
- `agent/skills/novel-writer/SKILL.md`
- `agent/request_template.md`
- 必要なら routing tests

#### Changes

- `long_form_100k` 条件文を canonical field ベースに置換する
- `05_chapter_outline.md` を canonical path として記述する
- `Target Total Chars` / `Target Length Profile` を主入力にする
- legacy terms は fallback 説明に縮退させる

#### Must Not Change

- router の blocked planning -> `setting-creator` 安全性
- skill の役割分担そのもの

#### Required Tests / Checks

- routing regression tests
- `rg -n "long_form_100k|05_chapter_outline_100k.md|Length Mode" agent`

#### Merge Criteria

- docs 間で canonical labels が一致
- blocked planning routing が維持
- old terms are present only as fallback explanations

#### Rollback Surface

- docs and routing heuristics only

---

### PR6: Compatibility Matrix and Expanded Regression Suite

#### Goal

新旧混在ケースを含む回帰網を完成させる。

#### Scope

- Phase 6 本体

#### Files

- `tests/test_scripts.py`
- 必要なら `tests/fixtures/*`

#### Changes

- mixed old/new compatibility tests を追加する
- invalid target/profile tests を追加する
- runtime artifact snapshot assertions を追加する

#### Must Not Change

- production behavior

#### Required Tests

- full `python -m pytest tests/test_scripts.py -v`

#### Merge Criteria

- mixed compatibility matrix green
- invalid cases fail fast as expected
- regression coverage is sufficient for rollout

#### Rollback Surface

- test only

---

### PR7: README, Walkthrough, and Migration Notes

#### Goal

shipped behavior と user-facing docs を同期する。

#### Scope

- Phase 7 本体

#### Files

- `README.md`
- `walkthrough.md`
- 必要なら `agent/decisions_log.md`
- 必要なら `agent/change_log.md`

#### Changes

- 10万字固定表現を 3 択へ更新する
- canonical outline 名と target profile 用語を反映する
- 既存 project 向け migration note を追加する

#### Must Not Change

- implementation
- tests

#### Required Checks

- docs grep for stale terminology
- manual consistency review against shipped code

#### Merge Criteria

- docs reflect actual behavior already merged in PR1-PR6
- no stale canonical/legacy confusion remains

#### Rollback Surface

- docs only

---

## PR Dependency Order

1. PR1
2. PR2
3. PR3
4. PR4
5. PR5
6. PR6
7. PR7

## Why This Order

- PR1 で安全装置を先に入れる
- PR2 で old/new read-path を先に両立させる
- PR3 で初めて new write-path を入れる
- PR4 で runtime artifact を canonical 化する
- PR5 で agent docs を実装済み behavior に合わせる
- PR6 で mixed compatibility を固める
- PR7 で user-facing docs を最後に同期する

## Done Definition

以下を満たしたら完了:

- 新規 project で `30000 / 50000 / 100000` を選べる
- state と runtime が選択値を canonical source として扱う
- agent routing が 100k 固定分岐から脱却している
- 既存 100k project が無修正で動く
- 新旧混在のテストが揃っている
- README / walkthrough / skills が shipped behavior と一致している
