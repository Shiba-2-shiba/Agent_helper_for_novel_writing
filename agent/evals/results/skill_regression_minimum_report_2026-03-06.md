# Skill Regression Minimum Report

## Summary
- Total cases: 9
- Passed: 9
- Failed: 0
- Pass rate: 1.0
- Skills covered: 9
- Missing required skills: none
- Failed case IDs: none
- Overall pass: True

## Fail Trigger Reproduction
- Re-run command:
  - `python scripts/eval_skill_regression_minimum.py --input <dataset.md> --json_out <report.json> --md_out <report.md>`
- Fail trigger fields:
  - type, repro_input, expected_skill, predicted_skill

## Case Results
### Case 1 - idea-generator
- Input: 新しい小説を書きたい。都市伝説ホラーで短編向けの案を3つ出して。
- Expected: 発想の発散とログライン候補提示。プロジェクト初期化への導線がある。
- Predicted Skill: idea-generator
- Status: pass

### Case 2 - project-bootstrap
- Input: このログラインで案件作成したい。プロジェクト名は `night_echo` で保存先も決めて。
- Expected: 初期条件確認、初期化手順、次スキルの提案がある。
- Predicted Skill: project-bootstrap
- Status: pass

### Case 3 - setting-creator
- Input: 設定とプロットの土台を再設計したい。キャラ動機の矛盾を解消して。
- Expected: 設定ファイル順の確認と、因果補強の具体指示がある。
- Predicted Skill: setting-creator
- Status: pass

### Case 4 - scene-planner
- Input: 第4章の次の2シーンだけ段取りしたい。本文はまだ書かない。
- Expected: 範囲固定、Write Next の単一選定、執筆準備情報の提示がある。
- Predicted Skill: scene-planner
- Status: pass

### Case 5 - novel-writer
- Input: 第4章2シーンを書いて。1000-1500文字で。
- Expected: runtime-first 前提で新規本文執筆に入る。構造化メタ出力を避ける。
- Predicted Skill: novel-writer
- Status: pass

### Case 6 - revision-editor
- Input: このシーンを改稿して。テンポを改善しつつ結末は維持して。
- Expected: 保持点/変更点を分離し、既存稿を前提に改稿する。
- Predicted Skill: revision-editor
- Status: pass

### Case 7 - consistency-auditor
- Input: 第5章の矛盾チェックをして。優先度付きで問題点を出して。
- Expected: 監査結果と修正方向を分離し、再確認可能な指摘を返す。
- Predicted Skill: consistency-auditor
- Status: pass

### Case 8 - prose-polisher
- Input: このシーンの文体を整えて。語尾の揺れを減らして読みやすくしたい。
- Expected: 構造変更を避けた表現改善に限定する。
- Predicted Skill: prose-polisher
- Status: pass

### Case 9 - resume-orchestrator
- Input: どこから再開すべき？今の状態から次にやることを1つ決めて。
- Expected: 現在地要約、推奨スキル1つ、Read First 3件以内を返す。
- Predicted Skill: resume-orchestrator
- Status: pass
