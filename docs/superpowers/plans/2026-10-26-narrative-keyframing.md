# Narrative Keyframing Implementation Plan

**Goal:** 基本有効の選択的な POV 創作素材を外部エージェントが生成・登録し、台詞／地の文への反映を主とする既存執筆フローへ接続する。

**Architecture:** prepare の不変契約と、後生成する未登録 proposal／登録済み artifact を分離する。Python は provenance と鮮度を検証し、意味・文学的判断は外部エージェントと既存 exact-span レビューへ残す。作成時の runtime 全体検証と、承認履歴の安定した依存を分け、自己 stale と旧承認の遡及破壊を防ぐ。

**Tech Stack:** Python 3.8/3.12、標準ライブラリ、既存 pytest、Markdown/JSON。新規実行時依存・LLM API なし。

**Spec:** `docs/superpowers/specs/2026-10-26-narrative-keyframing-design.md`

**Status:** 全6 taskを実施済み。Python 3.8/3.12で各696件の全体回帰、独立レビュー指摘の修正、隔離した日本語4例の実CLI検証を完了した。人間による品質評価・長編実作での有効性評価は未実施。詳細は[検証報告](../../validation/2026-10-26-narrative-keyframing.md)を参照。

## Global Constraints

- **基本有効。設定ファイルがない案件も、新しく prepare する際は有効。**
- **選んだ主観素材は、台詞ににじませる／地の文に出すことを主とする。省略を同等の通常選択肢にしない。**
- 省略には台詞と地の文の両方が適さない具体的理由を要求する。全発話・心理描写数のノルマにしない。
- POV は既存の明示指定を共有し、推測しない。不明なら生成停止。解釈・現在 scene の創作提案を canon/accepted memory に昇格しない。
- 提出 version 1、最大 3 keyframes、自然文 1〜240 Unicode 文字、ID 最大 80 文字、提出最大 65,536 bytes、素材レンダリング最大 3,000 文字、各 prompt 最大 16,000 文字。
- projection v1/v2 の意味を変更しない。新 selection/policy は v3。既存 v1/v2 approval の読込・export に新作成ゲートを遡及適用しない。
- `repair` は文字数不足への局所増補のまま。`--force`／`--allow-warnings`／automation で keyframing ゲートを免除しない。
- Python は文学的品質・意味的真実を保証しない。既存本文を自動書換えしない。push、外部 API、作品全体の書換えは行わない。

## Review Focus

1. 設定なし、旧 runtime、auto-prepare check が中間工程を迂回しないこと（Task 2/4）。
2. 空提出・全 omit が省略の通常化にならず、両経路の理由が必要なこと（Task 1/6）。
3. 登録時／prompt 保存時／approve 直前の外部変更が失敗扱いになり、旧 artifact を現行として祝福しないこと（Task 3/4）。
4. approval_ledger の自分自身の更新で新承認が stale にならず、過去承認の byte-preserving export が保たれること（Task 4/6）。
5. optional source の予算落ち、未来・別 POV 情報、三人称本文への暗示的反映を誤って扱わないこと（Task 3/4/6）。

---

## 実行前提・ファイル責務

この文書は2026-10-25 UTCに承認された実装計画。チェックボックスは実施状況を示し、実測結果は [検証報告](../../validation/2026-10-26-narrative-keyframing.md) に記録する。既存の隔離済み clone を使い、不要な作業コピーを追加しない。以下の行番号は `22a2dba` 時点の目安で、関数名を検索して編集する。

| ファイル | 責務 |
|---|---|
| 新 `scripts/novel_agent/narrative_keyframes.py` | 設定解決、契約／proposal の厳密な形検証、省略規則、短いレンダリング |
| 新 `scripts/novel_agent/keyframe_runtime.py` | 対象 runtime 読込、生成 provenance、登録、現行性、安定した check binding |
| 新 `scripts/build_keyframe_prompt.py` | 同一 scene の限定された資料から中間 prompt/request と未完成 proposal を作る CLI |
| 新 `scripts/register_keyframes.py` | validate-only／明示登録 CLI |
| 既存 `dependencies.py`、`build_runtime_context.py`、`runtime_paths.py` | version-aware guard と prepare 契約 |
| 既存 draft/expand/check/approvals、pipeline | 共通ゲートと素材受け渡し。現在の責務を維持 |
| 新 `tests/test_narrative_keyframes.py`、`test_keyframe_runtime.py`、`test_keyframe_workflow.py` | 純粋規則、provenance、実 CLI の三層 |
| 新 `tests/helpers/keyframe_fixtures.py` | 決定論的で未完成と完成を区別する合成 proposal、明示 off fixture |
| 新 `docs/narrative_keyframing.md`、`agent/evals/narrative_keyframing_cases.md` | 正本手順と未実施の実エージェント評価ケース |

### 共通データ契約

関数の `dict` は設計 §5〜9 の strict JSON object。Python 3.8 互換の `Optional`／`Dict` 等を使い、`str | None` は使わない。

- `Policy`: `enabled, disable_reason, source(default|project|scene|cli), enabled_override, reason_override` と依存投影用の適用設定情報。
- `Contract`: version 1、scene、POV、Policy、上限。時刻・ランダム値・登録結果を入れない。同一入力の再 prepare は同じ契約になる。
- `Request`: version 1、scene/POV、contract hash、prompt hash、compact `inputs/inputs_digest`、採用済み `sources` (ID→区分)、generation ID、未完成 `proposal_template`。
- generation ID: `scene_id/contract_hash/prompt_hash/inputs_digest/sources` の sorted compact canonical JSON の SHA-256。request 自体の hash を自己参照させない。
- `Registration`: version 1、検証済み proposal、request hash、作成時の compact `dependencies/dependency_digest`。外部 JSON をそのまま registered file にコピーしない。
- `Binding`: `version=1, enabled, pov_character_id, contract_hash, generation_id, registration_hash, disable_reason`。無効時 generation/registration は null。
- `ApprovalSnapshot`: 平坦な `version/proposal/sources/contract_hash/prompt_hash/request_hash/registration_hash/generation_id/inputs_digest/snapshot_digest`。snapshot_digest はそれ自身を除く canonical JSON の SHA-256。dependencies や台帳履歴を含めない。enabled=false の場合のみ snapshot は null。
- `Current`: `binding, approval_snapshot, prompt_section, dependency_specs, referenced_source_ids`。`dependency_specs` は**安定した check 用**で、全 runtime の artifact graph ではない。

## Task 1: default-on 方針と省略を含む提出 schema

**Files:**
- Create: `scripts/novel_agent/narrative_keyframes.py`
- Create: `tests/test_narrative_keyframes.py`, `tests/helpers/keyframe_fixtures.py`

**Interfaces:**
- Produces: `resolve_keyframing_policy(project_dir: str, *, scene_id: str, enabled_override: Optional[bool] = None, disable_reason: Optional[str] = None) -> dict`
- Produces: `keyframing_policy_value(project_dir: str, *, scene_id: str, enabled_override: Optional[bool] = None, disable_reason: Optional[str] = None) -> dict`（依存投影。無関係 scene を含めない）
- Produces: `build_keyframe_contract(*, scene_id: str, pov_character_id: Optional[str], policy: dict) -> dict`
- Produces: `validate_keyframe_proposal(proposal: dict, *, request: dict) -> dict`（正規化された新 dict を返し、入力を変更しない）
- Produces: `render_keyframes(proposal: dict) -> str`

- [x] **Step 1: 失敗する規則テストを書く。** 以下を parameterize し、正常例は dialogue/narration/both、omit、scene_omission をそれぞれ含める。

```python
assert resolve_keyframing_policy(str(tmp_path), scene_id="1-1")["enabled"] is True
assert validate_keyframe_proposal(valid_dialogue(), request=request)["keyframes"][0]["realization"] == "dialogue"
# test_omit_requires_both_routes: dialogue_reason/narration_reason の片方を空にすると UserFacingError
# test_empty_is_not_skip: keyframes=[] + scene_omission=None は UserFacingError
# test_scene_omission_requires_specific_anchor_and_both_routes: 正しい例だけ受理
# test_limits: 4件、241文字、未知source、重複ID、未知キー、version=True を拒否
# test_explicit_off_requires_reason: off+具体的理由は受理、理由のみ/空/TODO は拒否
# test_no_semantic_promotion: 素材検証・render 前後で accepted.json/本文は不変
```

- [x] **Step 2: RED を確認する。** `python -m pytest tests/test_narrative_keyframes.py -q` → 新 module/API 不在または期待 assertion で FAIL。
- [x] **Step 3: 純粋検証と設定解決を実装する。** 設計 §5/7 の厳密キー・型・長さ・省略理由を実装。`realization=omit` でのみ omission object を許す。ゼロ件の例外も anchor/source と両経路理由を必須とし、「私は」の文字列を強制する検査や意味分類器は作らない。render に「創作提案／相手の内心の事実ではない」と優先反映規則を含める。
- [x] **Step 4: GREEN を確認する。** 同じコマンド → PASS。render 3,000 字超過は明示エラー、入力 dict と作品ファイルに副作用がないことを確認。
- [x] **Step 5: commit。** `git add scripts/novel_agent/narrative_keyframes.py tests/test_narrative_keyframes.py tests/helpers/keyframe_fixtures.py && git commit -m "feat: define default-on narrative keyframe contracts"`

## Task 2: version-aware 依存と prepare の不変契約

**Files:**
- Modify: `scripts/novel_agent/dependencies.py` (`_SELECTORS`, `_projection`, `_snapshot_one`, `compact_dependencies`)
- Modify: `scripts/novel_agent/runtime_paths.py:74-98` (`write_runtime_manifest`)
- Modify: `scripts/build_runtime_context.py:540-854` (`main`, `_build_runtime_context_locked`)
- Test: `tests/test_keyframe_runtime.py` (new), `tests/test_compact_dependencies.py`, `tests/test_runtime_context_contracts.py`

**Interfaces:**
- Consumes: Task 1 policy/contract API。
- Produces: `keyframing_policy` / `keyframing_selection` projection v3。spec に `enabled_override/reason_override` を保存し、cache key・snapshot・再検証で同じ値を扱う。
- Produces: `memory_selection` v3（`version/config/memory/dialogue/keyframing`）。既存 selector の v1/v2 既定動作はそのまま、新規 prepare/prompt から v3 を明示指定する。
- Extends: `write_runtime_manifest(..., features: Optional[dict] = None)`。従来呼出しの出力は変更しない。
- Produces: prepare CLI `--keyframing {on,off}` / `--keyframing-reason`、draft contract、manifest feature marker、context_selection v2。

- [x] **Step 1: 失敗する互換・鮮度テストを書く。** `test_prepare_without_config_is_enabled_and_pending`、`test_missing_pov_is_not_inferred`、`test_resume_is_inspection_only`、`test_v3_selection_tampering_is_stale`、`test_legacy_v1_v2_projection_hashes_are_unchanged`。各 assert は順に enabled=True、POV=None/needs_pov、resume 成功、改変後 UserFacingError、旧 snapshot の verify が `[]`。CLI off→次回指定なしは再び default on、対象外 scene 設定の正常編集は verify `[]`、対象設定変更は非空を検証。
- [x] **Step 2: RED。** `python -m pytest tests/test_keyframe_runtime.py tests/test_compact_dependencies.py tests/test_runtime_context_contracts.py -q` → 新契約／v3 のテストが FAIL。
- [x] **Step 3: prepare に接続する。** policy guard を正本を読む前に capture。既存 dialogue が選んだ POV を渡し、契約を `written_files` と manifest に含める。選択情報は静的フィールドだけ。in_progress→complete と保存前再検証を維持。依存投影は explicit version 分岐し、古い hash を新意味で計算し直さない。
- [x] **Step 4: GREEN。** 同じテスト → PASS。`final_prompt/keyframe_prompt/expand_prompt` レポート追記だけでは runtime を stale にしないテストも通す。contract 改変・削除は stale。
- [x] **Step 5: commit。** Task 2 の実装・テストファイルだけ add し `git commit -m "feat: prepare versioned narrative keyframe inputs"`。

## Task 3: 中間 prompt と外部 proposal の検証・登録

**Files:**
- Create: `scripts/novel_agent/keyframe_runtime.py`, `scripts/build_keyframe_prompt.py`, `scripts/register_keyframes.py`
- Modify: `scripts/run_scene_pipeline.py:22-164`（prepare flags、keyframe-prompt/register-keyframes、NEXT）
- Test: `tests/test_keyframe_runtime.py`, `tests/test_keyframe_workflow.py` (new)

**Interfaces:**
- Consumes: Task 1/2、既存 `assemble_prompt/memory_prompt_sections`、`project_lock`、`_register_artifact_locked`、`snapshot_dependencies/verify_dependencies`。
- Produces: `load_keyframe_runtime(project_dir: str, runtime_dir: str, scene_id: str) -> dict`（identity/current/feature/contract/selection を検証して返す。enabled 時の POV 不足は生成に向けたエラー）
- Produces: `register_keyframes(project_dir: str, scene_id: str, input_path: str, *, runtime_dir_arg: str = "", validate_only: bool = False) -> dict`
- Produces: `require_keyframing_current(project_dir: str, runtime_dir: str, scene_id: str) -> dict`（Current。enabled は登録必須、disabled は理由付き binding）
- Produces: `validate_keyframing_binding(binding: dict, check_inputs: list) -> None`（履歴の shape/hash と安定 guard の対応だけ検査。作成時 runtime graph を再実行しない）
- Produces: `validate_keyframing_snapshot(snapshot: Optional[dict], binding: dict) -> None`（有効時は snapshot digest、proposal schema、source 区分と Binding 対応を検証。無効時は null を要求。mutable ledger を読まない）
- Produces: `build_keyframe_prompt.py::build_keyframe_prompt(project_dir: str, runtime_dir: str, scene_id: str, *, output_path: Optional[str] = None) -> dict`

- [x] **Step 1: 失敗する生成・登録テストを書く。** `test_request_contains_only_selected_source_ids`（future/他 POV/予算落ち source がない）、`test_pending_template_is_not_registered`、`test_validate_only_writes_nothing`（全ファイル hash 不変）、`test_registration_preserves_prepare_manifest_bytes`、`test_missing_pov_blocks_prompt`、`test_generation_scene_pov_and_source_mismatch_rejected` を追加する。
- [x] **Step 2: RED。** `python -m pytest tests/test_keyframe_runtime.py tests/test_keyframe_workflow.py -q` → CLI/API 不在で FAIL。
- [x] **Step 3: prompt/request を実装する。** 必須 style/brief/request/planning/dialogue/知識ラベルと任意 memory/continuity/related を同じ scene から読む。実際の `assembled.selected` だけを source registry にする。前掲の generation ID を作り、request・prompt を台帳登録する。未完成 output は任意、既存ファイルや保護対象への上書きは拒否する。JSON 以外の説明を提出させない指示を含める。
- [x] **Step 4: register と共通 loader を実装する。** 65,536 bytes 上限を読込前に確認し、JSON の重複キーを拒否し、対象と全 strict schema、generation、request/prompt/contract hash、ledger 登録、現在依存を検証。project_lock 内で再検証→atomic result write→ledger 登録。validate-only は trace/ledger を含め書かない。登録先を input とする自己登録、および registered output／依存パスの案件外への escape を拒否（ユーザーが明示した外部 proposal ファイルの読込は許可）。正確に同じ登録の再提出は idempotent にし、別の valid proposal の明示提出は置換可能（旧 check は hash で stale）。
- [x] **Step 5: エラー経路を足して GREEN。** `test_revalidate_before_registration_write`、`test_partial_registration_never_loads`、`test_result_without_ledger_is_not_trusted`、`test_wrong_scene_runtime_is_not_latest_fallback`、`test_prompt_required_budget_fails_without_partial_outputs` を追加。同じコマンド → PASS。prompt/request 登録が prepare manifest の bytes を変更しないことを再確認。
- [x] **Step 6: commit。** Task 3 ファイルを add し `git commit -m "feat: generate and register external narrative keyframes"`。

## Task 4: draft/expand/check/approve と履歴の安全な接続

**Files:**
- Modify: `scripts/build_draft_prompt.py:78-221`, `scripts/build_expand_prompt.py:112-249`
- Modify: `scripts/check_scene_output.py:137-294`, `scripts/novel_agent/approvals.py:110-227`
- Modify: `scripts/build_runtime_context.py:614-636`（過去 memory source approval の新 stable guards）
- Modify: `scripts/novel_agent/keyframe_runtime.py`（必要な共通 section 再解決）
- Test: `tests/test_keyframe_workflow.py`, `tests/test_approval_identity.py`, `tests/test_dialogue_review.py`, `tests/test_compact_dependencies.py`, `tests/test_reliability_integration.py`

**Interfaces:**
- Consumes: Task 3 `require_keyframing_current` と `validate_keyframing_binding`。
- Produces: check/新 approval の `keyframing: Binding` と `keyframing_snapshot: Optional[ApprovalSnapshot]`。
- Produces: stable check dependency specs = v3 policy/selection + `kind=file` contract（enabled 時のみ result も追加）。**registered artifact の推移的 dependencies は check_inputs に入れない。** draft/expand 生成には artifact guard を使い、approve 作成時は full freshness を別途確認する。

- [x] **Step 1: 全入口の RED テストを書く。** `@pytest.mark.parametrize("entry", ["draft", "expand", "check", "approve"])` で missing/result改変/contract削除/policy変更/selection変更/POV変更を拒否。check の runtime 不在 auto-prepare 後も未登録を拒否。force/allow-warnings/automation でも拒否。旧 runtime の新操作は same-scene prepare を案内する。
- [x] **Step 2: RED を確認。** `python -m pytest tests/test_keyframe_workflow.py -q` → 迂回できる入口の assertion が FAIL。
- [x] **Step 3: draft/expand を接続する。** Current.prompt_section を required 追加し、素材が source_refs で使った section も required に昇格。見つからない参照は停止、予算超過時に素材だけ残さない。従来の局所差分形式、Length Band、planning gate と品質予算を保つ。素材は逐語転記せず主に台詞／地の文へ反映し、既存の表現を重複説明しないと指示する。本文段階で omit へ変更する場合も理由を更新して再登録・再check する手順を含める。
- [x] **Step 4: check/approve を接続する。** capture した stable specs、Binding と平坦な ApprovalSnapshot を report に保存し、保存直前も full runtime と Binding を再検証。新 approve は旧 check に Binding がなければ recheck を要求し、review-dialogue の既存ゲートを実施後、保存直前に再検証する。新承認には snapshot もコピーする。historical `validate_approval_current` は拡張を持つ場合だけ保存 snapshot の digest/形と Binding/stable guards を検証し、full runtime-current や mutable artifact ledger の履歴を読まない。一方だけ欠けた新拡張は破損として拒否する。
- [x] **Step 5: 自己 stale と後方互換を検証する。** `test_approval_remains_current_after_own_ledger_write`、`test_approving_other_scene_does_not_stale_keyframe_approval`、`test_historical_v1_v2_export_does_not_require_keyframes`、`test_new_approval_rejects_old_check_without_binding` を追加。旧承認 bytes・本文 hash は前後同一、新承認 status は approved、対象 policy/result 変更時は stale。`test_saved_keyframe_snapshot_survives_artifact_ledger_loss` と `test_identical_reprepare_preserves_source_approval` で台帳の後日整理や同一契約の再prepareだけでは承認を失効させないことも確認する。既存 setup_checked の新承認用 fixture は**明示 off 理由と現行 Binding**を作る helper を使い、historical fixture は元の bytes のまま別 helper とする。
- [x] **Step 6: source approval の検証範囲を保つ。** 過去 memory 出典の check_inputs から keyframing policy/selection と contract/result file guards を元のスコープのまま引き継ぐ。target/未来は追加しない。`test_prior_source_keyframing_change_invalidates_prepared_memory` と `test_target_prepare_does_not_self_invalidate` を通す。
- [x] **Step 7: GREEN と commit。** `python -m pytest tests/test_keyframe_workflow.py tests/test_approval_identity.py tests/test_dialogue_review.py tests/test_compact_dependencies.py tests/test_reliability_integration.py -q` → PASS。`git commit -m "feat: enforce keyframe provenance through scene approval"`（対象ファイルを選んで add）。

## Task 5: 手順・既存ルーブリック・合成 fixture の更新

**Files:**
- Create: `docs/narrative_keyframing.md`, `agent/evals/narrative_keyframing_cases.md`
- Modify: `README.md`, `docs/long_novel_workflow.md`, `docs/dialogue_context.md`, `agent/AGENT_GUIDE.md`
- Modify: `agent/skills/novel-writer/SKILL.md`, `agent/skills/revision-editor/SKILL.md`, `agent/skills/consistency-auditor/SKILL.md`, `agent/skills/prose-polisher/SKILL.md`, `agent/skills/resume-orchestrator/SKILL.md`
- Modify: `scripts/novel_agent/dialogue_context.py::GUIDANCE`, `scripts/review_scene_dialogue.py`（NEXT 説明のみ）, `scripts/eval_long_novel_runtime.py`
- Modify: `tests/test_scripts.py::create_runtime_project`, `tests/helpers/long_novel_fixture.py`, `tests/helpers/keyframe_fixtures.py`, `tests/test_documented_commands.py`
- Adjust callers if needed: `tests/test_dialogue_context.py`, `tests/test_memory_context.py`, `tests/test_long_novel_e2e.py`, `tests/test_scene_status.py`, `tests/test_story_memory.py`, `tests/test_japanese_text_quality.py`, `tests/test_approval_attribution.py`。

**Interfaces:**
- Produces: ユーザー向け正本手順と新 CLI help 契約。
- Produces: fixture helper `write_keyframing_disabled_fixture(project: Path) -> None`（具体的な合成試験理由を持つ off config）。既存の非 keyframing 試験を隔離するためだけに明示使用。
- Extends: `create_runtime_project(..., keyframing: str = "disabled_fixture")`。`keyframing="default"` は config を作らず、新機能の no-config テストで必ず使用する。実製品の init_project の既定値は変えない。

- [x] **Step 1: docs 契約の RED を作る。** help に新 flags/subcommands、正本手順に default-on／両経路理由／外部生成／登録と承認の差／未実施評価がある assertion を追加。`python -m pytest tests/test_documented_commands.py -q` → FAIL。
- [x] **Step 2: ドキュメントと guidance を更新する。** 設計 §10 のコマンド列、no-config の導入、POV不足、off例、旧承認と新規操作の違いを書く。「効果がなければ省略」の並列的な表現を、選んだ素材を主に台詞・地の文へ、どちらも不適切な場合だけ理由付き省略へ揃える。既存候補抽出 schema は変えない。legacy full-context `build_llm_prompt.py` は保証対象外の旧入口で、そこから作った scene も新 check/approve ゲートを通ると明記する。
- [x] **Step 3: 合成試験だけを明示的に適応する。** unrelated fixture は helper により理由付き off を設定する。feature テストでは default/no-config または明示 on を使い、この helper に依存して黙って off にならない assertion を置く。evaluator は隔離 copy の runtime prepare でのみ `--keyframing off --keyframing-reason "決定論的な機械検査の計測であり外部創作生成は未実施"` を指定し、結果 JSON にその測定範囲を記録する。作者の正本・config は変えない。
- [x] **Step 4: 文章評価のケースを記す。** 誤解、暗示的台詞、自然な地の文、妥当な例外省略、POV/秘密の禁止例、局所増補を用意。各ケースに短い入力、期待する読み、exact-span＋判断理由の記録欄を付け、状態は `not_run`。逐語転記を合格条件にしない。ユーザー作品を試験用に書き換えない。
- [x] **Step 5: GREEN と commit。** `python -m pytest tests/test_documented_commands.py tests/test_scripts.py tests/test_dialogue_context.py tests/test_long_novel_e2e.py -q` → PASS。`git commit -m "docs: integrate the default-on keyframing workflow"`（記載の変更のみ add）。

## Task 6: 統合回帰・安全境界・最終レビュー

**Files:**
- Test: `tests/test_keyframe_workflow.py`, `tests/test_dependency_performance.py`, `tests/test_compact_dependencies.py`, `tests/test_long_novel_e2e.py`
- Create: `docs/validation/2026-10-26-narrative-keyframing.md`（実施した短い日本語例と証跡。未実施なら未実施と記す）
- Review: Task 1〜5 の全変更。

**Interfaces:**
- Consumes: 新 CLI 全経路と既存 export/review API。新しい製品 API は追加しない。

- [x] **Step 1: 最後の RED 統合ケースを追加する。** no-config prepare→keyframe-prompt→外部作成を模した fixture→validate-only→register→draft→本文保存→check→必要な exact-span review→approve→export を CLI で実行する。default enabled、登録前停止、既存本文無変更、prompt≤16000、承認直後 approved、export 本文一致を assert。既存 short draft の expand で registered material を必須保持し、full rewrite 指示がないことも確認する。
- [x] **Step 2: 異常・性能回帰を確認する。** request/result の別scene入替、CRLF/Unicode、path traversal/symlink escape、提出サイズ超過、入力を assembly 後に書き換える monkeypatch、登録後の削除をテスト。compact record が upstream values/再帰 dependencies を埋め込まず、diamond graph の既存観測回数上限を破らないことを確認する。必要な失敗修正だけ各責務の module に戻す。
- [x] **Step 3: focused GREEN。** `python -m pytest tests/test_narrative_keyframes.py tests/test_keyframe_runtime.py tests/test_keyframe_workflow.py tests/test_compact_dependencies.py tests/test_dependency_performance.py -q` → PASS。
- [x] **Step 4: 全体検証。** `python -m pytest tests -q` と `python -m compileall -q scripts` → 全 PASS／exit 0。可能なら既存 CI と同じ Python 3.8/3.12 両方で実行。片方しか動かせなければ未実施を明記し、通ったと扱わない。
- [x] **Step 5: 短い実エージェント例を実行して比較する。** 新しい外部エージェントの文脈で、作者の作品ではない隔離した短い日本語 scene を 3〜4 件用意し、実 CLI の prepare→keyframe-prompt→外部生成→register→draft→check→必要な review→approve を試す。台詞に暗示する例、地の文に出す例、両方が不自然／冗長／テンポを損なうため省略する例を含める。有料 API は呼ばず、現在利用できる外部エージェントで実施する。記録先に実際の prompt、生成素材、実本文、適用／省略の対応比較、正確な本文 span と判断理由、CLI 結果を保存する。レビュー主体は agent と記録し、人間承認や一般的な品質改善の証明にしない。既存レビューの候補外は記録中の自己評価として区別する。実施するまでは protocol の状態を not_run のままにし、実施不能なら制約と必要な次の操作を明記する。
- [x] **Step 6: 全差分の独立レビュー。** default-on／両経路理由、過去承認、TOCTOU、自己 stale、16,000 文字、秘密・未来の扱いを重点にレビューし、指摘修正後に関係検査を再実行する。合成 fixture と文学的評価の結果を分ける。
- [x] **Step 7: commit と引渡し。** `git diff --check` → 無出力。対象の回帰テスト・修正を commit。変更概要、正確なテスト結果、実エージェント評価の実施有無、残る制約を報告。push/merge はしない。

## 設計・計画の自己レビュー結果

- §1〜3 の主方針・非目標 → Task 1/4/5。§5〜7 の方針/schema/成果物 → Task 1〜3。§8 の区分・予算 → Task 3/4。§9 の鮮度・互換 → Task 2/4/6。§10〜12 の手順・レビュー・受入 → Task 5/6。
- `Policy/Contract/Request/Registration/Binding/ApprovalSnapshot/Current` と CLI 名を統一した。中間素材が canon になる経路、無理由 skip、本文自動編集は追加していない。
- 設計レビューで見つかった approval_ledger の自己 stale を修正し、作成時 graph と stable check_inputs を区別した。これを Task 4 の固有回帰テストにした。
- Review Focus の五項目にはすべて担当 task とテストがある。新たな全場面文学的判定器、全 keyframe 実現台帳、LLM SDK は追加しない。
- 実装の function body は計画に転記せず、決定事項・接口・assertions・実行コマンドに留めた。未実施項目は未チェックのまま。

## 計画作成時点の検証状況

対象は `22a2dba`。隔離環境の Python 3.12 baseline が **557 passed in 272.88s**。`python -m compileall -q scripts` も exit 0。これは変更前の基準であり、新機能実装の成功ではない。この計画作成では設計・計画文書以外の tracked file は変更していない。

承認時の実行方針：6 task は同じ provenance 接口を順番に通すため、実装担当者が連続して進め、最後に別の担当者が全体をレビューする方法を推奨する。どの実行方式でも上記 TDD と全体検証を省かない。
