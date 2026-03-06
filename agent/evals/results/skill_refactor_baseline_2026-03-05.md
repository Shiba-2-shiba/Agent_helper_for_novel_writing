# Skill Refactor Baseline Result (2026-03-05)

## Scope
- `agent/skills` structure migration
- router document migration (`agent/HUB.md`, `agent/AGENT_GUIDE.md`)
- eval dataset expansion for 9 skills

## Structural Gate
- Canonical skill files found: 9 / 9
- Legacy compatibility files found: 10 / 10
- Canonical frontmatter keys (`name`, `description`) only: 9 / 9
- Result: pass

## Routing Gate
- `agent/HUB.md` canonical mapping paths: 9 / 9 valid
- `agent/HUB.md` target file paths: 9 / 9 valid
- `agent/AGENT_GUIDE.md` skill path notation updated: yes
- Result: pass

## Trigger QA Dataset Gate
- Dataset file: `agent/evals/prompts/skill_trigger_qa_2026-03-05.md`
- Skills covered: 9
- Per-skill cases: should-trigger 8, should-not-trigger 8
- Execution:
  - `agent/evals/results/skill_trigger_qa_report_2026-03-05.json`
  - `agent/evals/results/skill_trigger_qa_report_2026-03-05.md`
- Measured result:
  - should-trigger recall: `1.0`
  - should-not-trigger false-positive-rate: `0.0`
- Result: pass

## Regression Coverage Gate
- Router smoke prompts: `agent/evals/prompts/skill_router_smoke_2026-03-05.md` (9 cases)
- Skill minimum regression prompts: `agent/evals/prompts/skill_regression_minimum_2026-03-05.md` (9 cases)
- Skill boundary regression prompts: `agent/evals/prompts/skill_regression_boundary_2026-03-05.md` (18 cases)
- Execution:
  - `agent/evals/results/skill_regression_minimum_report_2026-03-05.json`
  - `agent/evals/results/skill_regression_minimum_report_2026-03-05.md`
  - `agent/evals/results/skill_regression_boundary_report_2026-03-05.json`
  - `agent/evals/results/skill_regression_boundary_report_2026-03-05.md`
- Measured result:
  - minimum set: skills covered `9`, failed cases `0`, overall pass `True`
  - boundary set: skills covered `9`, failed cases `0`, overall pass `True`
- Result: pass

## Eval Suite Gate
- Runner: `scripts/run_skill_eval_suite.py`
- Suite report:
  - `agent/evals/results/skill_eval_suite_report_2026-03-05.json`
  - `agent/evals/results/skill_eval_suite_report_2026-03-05.md`
- Measured result:
  - trigger QA pass: `True`
  - regression minimum pass: `True`
  - regression boundary pass: `True`
  - suite overall pass: `True`
- Result: pass

## Known Risks
- Deterministic router heuristics are a baseline proxy, not a full LLM-behavior substitute.
- Legacy redirect files are compatibility pointers only (not full skill content).

## Next Action
1. Keep `python scripts/run_skill_eval_suite.py` as the default pre-merge regression check for skill doc edits.
2. Add new boundary prompts only when real misrouting examples are observed in live usage.
