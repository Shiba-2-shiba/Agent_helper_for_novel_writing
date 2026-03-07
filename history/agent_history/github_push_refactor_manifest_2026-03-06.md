# GitHub Push Refactor Manifest (2026-03-06)

## Purpose

今回までの refactor で追加・整備したファイル群を、GitHub push 用にまとめる。

注意:
- このワークスペースでは `.git` が見つからなかったため、厳密な git diff ではなく既存 tracker / handoff / status docs を根拠に整理している
- 以下は `created during refactor` と `updated during refactor` を分けており、push 対象の判断に使えるようにしてある

## Sources Used

- `agent/current_refactor_status.md`
- `agent/skill_refactor_handoff_final_2026-03-05.md`
- `agent/skill_refactor_phase6_completion_2026-03-05.md`
- `agent/long_form_planning_refactor_tracker.md`

## Push First: New Files Added During Refactor

### Skills

- `agent/skills/project-bootstrap/SKILL.md`
- `agent/skills/scene-planner/SKILL.md`
- `agent/skills/revision-editor/SKILL.md`
- `agent/skills/consistency-auditor/SKILL.md`
- `agent/skills/prose-polisher/SKILL.md`
- `agent/skills/resume-orchestrator/SKILL.md`

### Runtime / Validation Scripts

- `scripts/prompt_utils.py`
- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/check_scene_output.py`
- `scripts/build_expand_prompt.py`
- `scripts/apply_expand_edits.py`
- `scripts/eval_skill_trigger_qa.py`
- `scripts/eval_skill_regression_minimum.py`
- `scripts/run_skill_eval_suite.py`

### Eval Prompts / Templates

- `agent/evals/prompts/skill_router_smoke_2026-03-05.md`
- `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`
- `agent/evals/prompts/skill_regression_minimum_2026-03-05.md`
- `agent/evals/prompts/skill_regression_boundary_2026-03-05.md`
- `agent/evals/templates/runtime_ready_project_comparison.md`

### Refactor Tracking / Handoff Docs

- `agent/skill_refactor_rollback_runbook.md`
- `agent/skill_refactor_phase6_completion_2026-03-05.md`
- `agent/skill_refactor_handoff_final_2026-03-05.md`
- `agent/skill_refactor_restart_prompt_template.md`
- `agent/skills_inventory_snapshot_2026-03-05.txt`
- `agent/long_form_planning_refactor_tracker.md`
- `agent/github_push_refactor_manifest_2026-03-06.md`

## Push Too: Existing Files Heavily Updated During Refactor

### Core Routing / Shared Docs

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`
- `agent/current_refactor_status.md`
- `agent/request_template.md`
- `agent/evals/README.md`

### Existing Skills Updated

- `agent/skills/idea-generator/SKILL.md`
- `agent/skills/setting-creator/SKILL.md`
- `agent/skills/novel-writer/SKILL.md`

### State / Template / Tests

- `agent/state_schema_novel.yaml`
- `templates/05_chapter_outline_100k.md`
- `tests/test_scripts.py`

## Optional Push: Evaluation Evidence

必要なら「今回までの refactor が通っている証跡」として push する。

### Baseline / Suite

- `agent/evals/results/skill_refactor_baseline_2026-03-05.md`
- `agent/evals/results/skill_eval_suite_report_2026-03-05.json`
- `agent/evals/results/skill_eval_suite_report_2026-03-05.md`
- `agent/evals/results/skill_trigger_qa_report_2026-03-05.json`
- `agent/evals/results/skill_trigger_qa_report_2026-03-05.md`
- `agent/evals/results/skill_regression_minimum_report_2026-03-05.json`
- `agent/evals/results/skill_regression_minimum_report_2026-03-05.md`
- `agent/evals/results/skill_regression_boundary_report_2026-03-05.json`
- `agent/evals/results/skill_regression_boundary_report_2026-03-05.md`

### Latest 2026-03-06 Evidence

- `agent/evals/results/skill_eval_suite_report_2026-03-06.json`
- `agent/evals/results/skill_eval_suite_report_2026-03-06.md`
- `agent/evals/results/skill_trigger_qa_report_2026-03-06.json`
- `agent/evals/results/skill_trigger_qa_report_2026-03-06.md`
- `agent/evals/results/skill_regression_minimum_report_2026-03-06.json`
- `agent/evals/results/skill_regression_minimum_report_2026-03-06.md`
- `agent/evals/results/skill_regression_boundary_report_2026-03-06.json`
- `agent/evals/results/skill_regression_boundary_report_2026-03-06.md`

### Iteration Evidence

- `agent/evals/results/scene_planning_ojiichan_mystery_pilot.md`
- `agent/evals/results/scene_planning_ojiichan_mystery_second_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_pilot.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_second_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_third_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_fourth_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_fifth_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_sixth_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_seventh_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_eighth_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_ninth_pass.md`
- `agent/evals/results/resume_orchestrator_ojiichan_mystery_tenth_pass.md`

## Usually Exclude Or Recheck Before Push

- `__pycache__/`
- 各プロジェクト配下の `runtime/` 生成物
- 各プロジェクト配下のサンプル `check_report.json` や一時 draft 出力
- ローカル実験用の案件本文が、refactor 自体のソースではない場合

## Recommended Push Grouping

### Commit 1: Core Skill Refactor

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`
- `agent/skills/**`
- `agent/state_schema_novel.yaml`
- `agent/request_template.md`

### Commit 2: Runtime / Checker / Eval Automation

- `scripts/prompt_utils.py`
- `scripts/build_runtime_context.py`
- `scripts/build_draft_prompt.py`
- `scripts/check_scene_output.py`
- `scripts/build_expand_prompt.py`
- `scripts/apply_expand_edits.py`
- `scripts/eval_skill_trigger_qa.py`
- `scripts/eval_skill_regression_minimum.py`
- `scripts/run_skill_eval_suite.py`
- `tests/test_scripts.py`

### Commit 3: Long-Form Planning Refactor

- `templates/05_chapter_outline_100k.md`
- `agent/long_form_planning_refactor_tracker.md`
- `agent/evals/README.md`
- `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`
- `agent/evals/prompts/skill_regression_boundary_2026-03-05.md`

### Commit 4: Docs / Handoff / Evidence

- `agent/current_refactor_status.md`
- `agent/skill_refactor_phase6_completion_2026-03-05.md`
- `agent/skill_refactor_handoff_final_2026-03-05.md`
- `agent/skill_refactor_rollback_runbook.md`
- `agent/skill_refactor_restart_prompt_template.md`
- `agent/skills_inventory_snapshot_2026-03-05.txt`
- 必要なら `agent/evals/results/*`

## Minimum Safe Push Set

証跡を除いて最小構成で push するなら、少なくとも以下を含める。

- `agent/HUB.md`
- `agent/AGENT_GUIDE.md`
- `agent/skills/`
- `agent/state_schema_novel.yaml`
- `agent/request_template.md`
- `agent/evals/README.md`
- `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`
- `agent/evals/prompts/skill_regression_minimum_2026-03-05.md`
- `agent/evals/prompts/skill_regression_boundary_2026-03-05.md`
- `scripts/`
- `templates/05_chapter_outline_100k.md`
- `tests/test_scripts.py`
