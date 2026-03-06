# Evals (Common)

目的: Skill の出力が期待通りかを、最小コストで確認する。

## Success Criteria

- Outcome: 必要なファイルや成果が生成される
- Process: 手順が守られる
- Style: 指定フォーマットと文体契約が崩れない
- Continuity: 前後の文脈と整合している
- Scene Function: そのシーンや作業の目的を達成している

## Minimal Eval Prompts

Use `evals/prompts/` and check:

- Structure: 必須項目や必要セクションがある
- Constraints: 禁止事項や禁止表現が入っていない
- Clarity: 次アクションが明確

### Skill Refactor Baseline Sets (2026-03-05)

- Router smoke: `evals/prompts/skill_router_smoke_2026-03-05.md`
- Trigger QA set: `evals/prompts/skill_trigger_qa_2026-03-05.md`
- Minimum regression set: `evals/prompts/skill_regression_minimum_2026-03-05.md`
- Baseline result: `evals/results/skill_refactor_baseline_2026-03-05.md`

### Minimum Acceptance For Trigger QA

- 9 skills are covered
- each skill has 8 `should-trigger` prompts
- each skill has 8 `should-not-trigger` prompts
- false positive patterns are explicitly included for neighboring skills

### Trigger QA Run Command

```powershell
python scripts/eval_skill_trigger_qa.py `
  --input agent/evals/prompts/skill_trigger_qa_2026-03-05.md `
  --json_out agent/evals/results/skill_trigger_qa_report_2026-03-05.json `
  --md_out agent/evals/results/skill_trigger_qa_report_2026-03-05.md
```

Pass criteria:
- `should-trigger recall >= 0.90`
- `should-not-trigger false-positive-rate <= 0.10`

### Regression Minimum Run Command

```powershell
python scripts/eval_skill_regression_minimum.py `
  --input agent/evals/prompts/skill_regression_minimum_2026-03-05.md `
  --json_out agent/evals/results/skill_regression_minimum_report_2026-03-05.json `
  --md_out agent/evals/results/skill_regression_minimum_report_2026-03-05.md
```

Pass criteria:
- `skills_covered == 9`
- `missing_required_skills == []`
- `failed_cases == 0`

Result format template:
- `agent/evals/templates/skill_regression_result_template.md`

### Regression Boundary Run Command

```powershell
python scripts/eval_skill_regression_minimum.py `
  --input agent/evals/prompts/skill_regression_boundary_2026-03-05.md `
  --json_out agent/evals/results/skill_regression_boundary_report_2026-03-05.json `
  --md_out agent/evals/results/skill_regression_boundary_report_2026-03-05.md
```

Boundary pass criteria:
- `skills_covered == 9`
- `failed_cases == 0`
- Fail trigger reproduction fields are present in the JSON summary.

### One-Command Eval Suite

```powershell
python scripts/run_skill_eval_suite.py
```

Suite outputs:
- `agent/evals/results/skill_eval_suite_report_2026-03-05.json`
- `agent/evals/results/skill_eval_suite_report_2026-03-05.md`

## Review Output Format

レビュー結果は、可能なら以下の粒度で返す。

- Severity: `high / medium / low`
- Scope: `scene / chapter / setting / workflow`
- Issue: 何が問題か
- Impact: 読み味や整合性にどう影響するか
- Fix Direction: どう直すべきか

## Novel-Focused Checks

### Planning

- `long_form_100k` 案件で `planned_total_min_chars` が `planning_gate_min_chars` を下回っていない
- 章ごとの役割が分かれている
- `scene inventory` が十分にある
- 重要シーンが `anchor` / `climax` として明示されている
- `runtime` が `Scene Type` / `Length Band` / `payoff` を落とさず保持している

### Drafting

- 文字数が対象シーンの `Length Band` に概ね収まっている
- 視点がぶれていない
- キャラの口調が文体契約から逸脱していない
- シーンの目的が達成されている
- 直前シーンから自然につながっている
- 次シーンへのフックが残っている
- 説明、会話、内面の比率が極端に偏っていない
- 冒頭 3〜5 行で場面の位置と温度感が掴める

### Project Bootstrap

- プロジェクト名と保存先が明確
- 初期化後の次アクションが 1 つに絞られている
- まだ未確定の設定を勝手に固定しすぎていない
- `long_form_100k` 案件で `Planning Gate` が `blocked` から始まっている
- `long_form_100k` 案件で `setting-creator` へ handoff されている

### Scene Planning

- 対象章または対象シーンの範囲が明確
- 直近の執筆に必要な段取りへ絞れている
- 設定の大枠と本文初稿を混同していない
- `Scene Type` と `Length Band` が返されている
- `planning_gate_status` 未通過なら本文へ進めていない

### Revision

- 指定された問題が解消されている
- 残すべき要素が消えていない
- 修正の副作用で新しい矛盾が生まれていない
- 変更点が、依頼された範囲をはみ出しすぎていない
- 改稿後のほうが、依頼意図に対して明確に前進している

### Consistency Audit

- 問題点が具体的で再確認可能
- 影響範囲が示されている
- 修正方針が実行可能
- 問題点と好みの指摘を分けている
- すぐ直すべき点と、後回しでよい点を分けている

### Polish

- 冗長な説明が減っている
- 語尾、テンポ、地の文の密度が整っている
- 読後感や引きが改善している
- 構造を不用意に壊していない
- 直しすぎてキャラの持ち味を消していない

### Resume / Routing

- 現在地の要約が短く正確
- 次の推奨スキルが 1 つに絞られている
- 古い情報ではなく、現在のファイル実体に基づいている
- `runtime/planning_gate_brief.md` がある場合は、それを gate 判定の共通根拠として使っている

### Runtime Compression

- `runtime/scene_brief_compact.md` が対象シーンと一致している
- `runtime/scene_brief_compact.md` に `Scene Type` と `Length Band` がある
- `runtime/request_compact.md` に `Planning Gate` と `Target Band` がある
- `runtime/planning_gate_brief.md` に `Planning Gate` / `Planned Total Min Chars` / `Next Planning Action` がある
- 圧縮後も、対象シーンの回収 / 種まき情報が消えすぎていない

## Retry Triggers

以下は再試行または差し戻し対象とする。

- `long_form_100k` なのに `planning_gate_status != ready` のまま本文執筆へ進んでいる
- `planned_total_min_chars < planning_gate_min_chars`
- `runtime/scene_brief_compact.md` に `Scene Type` または `Length Band` がない
- `runtime/planning_gate_brief.md` がない、または `Planning Gate` / `Next Planning Action` が欠けている
- 文字数が対象シーンの `Length Band` の `min` を下回る
- 視点ぶれ
- 主要キャラの口調逸脱
- シーン目的未達
- 既存設定との明確な矛盾
- 本文中の見出し、箇条書き、メタ発言
- 依頼された範囲を超えた大規模な改変

## Practical Triage

レビュー時は、まず以下の順で見ると実運用で迷いにくい。

1. 致命的な矛盾や依頼違反があるか
2. そのシーンや作業の目的を達成しているか
3. 直す価値の高い問題が 1〜3 件に絞れるか
4. 今すぐ改稿すべきか、後で仕上げればよいか

## Skill Improvement Loop (Pilot)

小説用途では、本文の「うまさ」そのものより、まず **各スキルが自分の責務を安定して果たせているか** を評価する。

最初の改善ループ対象は以下を推奨する。

1. `agent/skills/resume-orchestrator/SKILL.md`
2. `agent/skills/scene-planner/SKILL.md`

### Pilot Baseline Project

実案件ベースの初回テンプレートは、以下の案件を基準ケースにする。

- `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery`

この案件は以下の特徴があり、評価テンプレート向き。

- `state_schema_novel.yaml` が実ファイル状況とズレている
- `runtime/` が薄く、フォールバック経路を評価しやすい
- 章アウトラインと本文が両方あり、段取りスキルの責務を見やすい

### Pilot Templates

初回の具体テンプレートは以下を使う。

- `templates/resume_orchestrator_ojiichan_mystery.md`
- `templates/scene_planning_ojiichan_mystery.md`

別案件で比較を始めるときは、以下の汎用テンプレートを土台にする。

- `templates/runtime_ready_project_comparison.md`

### How To Run The Loop

1. テンプレートのケース文をそのまま使って同じ案件で実行する
2. 出力を「Pass Conditions」と「Fail Triggers」で判定する
3. 改善点は 1 回につき 1 論点だけスキルへ反映する
4. 同じケースを再実行し、改善前後を比較する

### Planning Gate Loop

長編計画系の改善は、`resume` と同じく中間成果物を固定して回す。

1. `python scripts/build_runtime_context.py --project <project> --chapter <chapter> --scene <scene> --mode resume`
2. `runtime/planning_gate_brief.md` の `Planning Gate` / `Planned Total Min Chars` / `Next Planning Action` を確認する
3. `blocked` なら `setting-creator` へ戻す prompt を回帰ケースで再実行する
4. `ready` なら `scene-planner` または `novel-writer` のケースを再実行する
5. routing と runtime artifact の両方が揃っているか比較する

### What To Compare

- `resume_orchestrator`
  - 古い `state` を鵜呑みにしないか
  - 実ファイルから現在地を再構築できるか
  - 次アクションと推奨スキルを 1 つに絞れるか
  - `Recommended Skill` が、実際の問題種別（未着手 / 改稿 / 監査 / 設定不足）に応じた根拠で選ばれているか
  - `resume_brief.md` が対象一致でも、「着手前」記述と実ファイルが矛盾する場合に stale と判断できるか
  - 更新時刻は補助根拠として使いつつ、本文実体や検査結果の確認を省略していないか
  - `Current Position` の文言（例: `準備段階` / `完了` / `監査`）を、次行動の判断材料として一貫して読めるか
  - `Open Items` / `Next Actions` の語彙も、前工程残り / 監査寄り / 未移行の根拠として一貫して読めるか
  - `Read First` と `Next Actions` が同じ作業モードを指しているか、または整合したまま古いスナップショットとして扱えているか
  - `Recommended Skill` と最終 `Read First` が、同じ直近タスクを支える組み合わせになっているか
  - `Recommended Skill` ごとの `Read First` が、案件の主問題に対して過不足ない粒度で切り替わっているか

- `scene_planning`
  - 段取りの責務を守り、本文を書き始めないか
  - 次に書く対象を 1 つに絞れるか
  - `Read First` が 3 件以内で具体的か
  - `Read First` が、`runtime` → 章アウトライン → 対象または直前シーン → `global_notes` の順で過不足なく選ばれているか

