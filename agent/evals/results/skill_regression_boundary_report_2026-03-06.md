# Skill Regression Minimum Report

## Summary
- Total cases: 22
- Passed: 22
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
- Input: 設定はまだ白紙。先に企画の方向性だけ3案ほしい。
- Expected: 設定確定前の発想フェーズとして案出しを返す。
- Predicted Skill: idea-generator
- Status: pass

### Case 2 - idea-generator
- Input: まだ案件は作らない。まずログライン候補を比較したい。
- Expected: 初期化に進まず、ログライン比較を返す。
- Predicted Skill: idea-generator
- Status: pass

### Case 3 - project-bootstrap
- Input: ログラインは決まった。保存先とプロジェクト名を確定して案件を作成したい。
- Expected: 初期化フェーズとして作成手順を返す。
- Predicted Skill: project-bootstrap
- Status: pass

### Case 4 - project-bootstrap
- Input: 既存フォルダに agent 運用だけ追加したい。新規本文はまだ書かない。
- Expected: 初期化/運用整備として扱い、執筆へ直行しない。
- Predicted Skill: project-bootstrap
- Status: pass

### Case 5 - setting-creator
- Input: 章を進める前に世界観ルールの矛盾を整理し直したい。
- Expected: 設定土台の見直しとして扱う。
- Predicted Skill: setting-creator
- Status: pass

### Case 6 - setting-creator
- Input: 04_plot_outline を再構成して因果をつなぎ直したい。
- Expected: 骨格設計の修正として扱う。
- Predicted Skill: setting-creator
- Status: pass

### Case 7 - setting-creator
- Input: long_form_100k の planning gate が blocked なので、scene inventory を増やしてから進めたい。
- Expected: scene-planner や novel-writer に進めず、計画ゲートの補強として扱う。
- Predicted Skill: setting-creator
- Status: pass

### Case 8 - scene-planner
- Input: 本文は書かないので、次の2シーンの段取りだけ決めて。
- Expected: Write Next を1つに絞る段取り出力を返す。
- Predicted Skill: scene-planner
- Status: pass

### Case 9 - scene-planner
- Input: 第6章の着手順を決めたい。シーン候補を比較して選びたい。
- Expected: 執筆前計画としてシーン選定を返す。
- Predicted Skill: scene-planner
- Status: pass

### Case 10 - novel-writer
- Input: 第6章2シーンを1000-1500文字で新規執筆して。
- Expected: 新規本文執筆として扱う。
- Predicted Skill: novel-writer
- Status: pass

### Case 11 - novel-writer
- Input: runtime-first で続きを本文として書いて。
- Expected: 新規執筆フローとして扱う。
- Predicted Skill: novel-writer
- Status: pass

### Case 12 - revision-editor
- Input: 方向性は維持して、このシーンのテンポだけ改稿して。
- Expected: 既存稿の改稿として扱う。
- Predicted Skill: revision-editor
- Status: pass

### Case 13 - revision-editor
- Input: 既存本文の保持点を残して弱点だけリライトしたい。
- Expected: 保持点/変更点分離の改稿として扱う。
- Predicted Skill: revision-editor
- Status: pass

### Case 14 - consistency-auditor
- Input: この章の問題点を優先度付きで診断して。改稿はまだ不要。
- Expected: 監査結果中心で返す。
- Predicted Skill: consistency-auditor
- Status: pass

### Case 15 - consistency-auditor
- Input: 違和感の原因を洗い出して、矛盾箇所を特定したい。
- Expected: 監査・診断として扱う。
- Predicted Skill: consistency-auditor
- Status: pass

### Case 16 - prose-polisher
- Input: 構造は変えず、語尾と文体のノイズだけ整えて。
- Expected: 表現仕上げとして扱う。
- Predicted Skill: prose-polisher
- Status: pass

### Case 17 - prose-polisher
- Input: 読みやすさを上げたい。冗長な言い回しを圧縮して。
- Expected: 推敲として扱う。
- Predicted Skill: prose-polisher
- Status: pass

### Case 18 - resume-orchestrator
- Input: 中断していたので、どこから再開するかと次アクションを1つ決めたい。
- Expected: 再開整理として扱う。
- Predicted Skill: resume-orchestrator
- Status: pass

### Case 19 - resume-orchestrator
- Input: 現在地を整理して、読むべきファイルを先に3つ教えて。
- Expected: 再開判断と Read First 提示として扱う。
- Predicted Skill: resume-orchestrator
- Status: pass

### Case 20 - resume-orchestrator
- Input: runtime の resume_brief と scene_brief が古そう。現在地を再確認して再開方針を1つに絞りたい。
- Expected: runtime 不整合の再開整理として扱う。
- Predicted Skill: resume-orchestrator
- Status: pass

### Case 21 - resume-orchestrator
- Input: scene_brief が見当たらない。いまの本文進捗から再開地点を整理して。
- Expected: runtime 部分欠落の再開整理として扱う。
- Predicted Skill: resume-orchestrator
- Status: pass

### Case 22 - scene-planner
- Input: 第6章は既存シーンが複数ある。情報不足の1シーンを選んで段取りだけ固めて。
- Expected: 既存シーン再整理の計画として扱う。
- Predicted Skill: scene-planner
- Status: pass
