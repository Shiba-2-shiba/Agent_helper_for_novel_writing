# Skill Regression Result Template

## Summary
- Total cases: <number>
- Passed: <number>
- Failed: <number>
- Pass rate: <0.0000>
- Skills covered: <number>
- Missing required skills: <none or list>
- Failed case IDs: <none or list>
- Overall pass: <True/False>

## Fail Trigger Reproduction
- Re-run command:
  - `python scripts/eval_skill_regression_minimum.py --input <dataset.md> --json_out <report.json> --md_out <report.md>`
- Fail trigger fields:
  - `type`, `repro_input`, `expected_skill`, `predicted_skill`

## Case Results
### Case <n> - <skill>
- Input: <prompt>
- Expected: <expected behavior>
- Predicted Skill: <skill or unknown>
- Status: <pass/fail>
- Fail Trigger (only when failed):
  - type=<ROUTER_MISMATCH|UNKNOWN_ROUTE>
  - expected=<skill>
  - predicted=<skill or unknown>
  - repro_input=<prompt>
