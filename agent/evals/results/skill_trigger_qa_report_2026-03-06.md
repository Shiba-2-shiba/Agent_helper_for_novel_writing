# Skill Trigger QA Report

## Summary
- Skills covered: 9
- should-trigger recall: 0.9861
- should-not-trigger false-positive-rate: 0.0
- Overall pass: True

## Per Skill
### idea-generator
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### project-bootstrap
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### setting-creator
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### scene-planner
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### novel-writer
- should-trigger: 7/8 (recall=0.875)
- should-not-trigger: 8/8 (tnr=1.0)
- false negatives:
  - predicted=setting-creator prompt=planning gate ready なので直前シーンを受けて続きを執筆して。

### revision-editor
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### consistency-auditor
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### prose-polisher
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)

### resume-orchestrator
- should-trigger: 8/8 (recall=1.0)
- should-not-trigger: 8/8 (tnr=1.0)
