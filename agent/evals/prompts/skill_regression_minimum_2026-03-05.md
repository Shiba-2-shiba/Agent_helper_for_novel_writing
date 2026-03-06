# Skill Regression Minimum Set (2026-03-05)

## 1. idea-generator
- Input: 新しい小説を書きたい。都市伝説ホラーで短編向けの案を3つ出して。
- Expected: 発想の発散とログライン候補提示。プロジェクト初期化への導線がある。

## 2. project-bootstrap
- Input: このログラインで案件作成したい。プロジェクト名は `night_echo` で保存先も決めて。
- Expected: 初期条件確認、初期化手順、次スキルの提案がある。

## 3. setting-creator
- Input: 設定とプロットの土台を再設計したい。キャラ動機の矛盾を解消して。
- Expected: 設定ファイル順の確認と、因果補強の具体指示がある。

## 4. scene-planner
- Input: 第4章の次の2シーンだけ段取りしたい。本文はまだ書かない。
- Expected: 範囲固定、Write Next の単一選定、執筆準備情報の提示がある。

## 5. novel-writer
- Input: 第4章2シーンを書いて。1000-1500文字で。
- Expected: runtime-first 前提で新規本文執筆に入る。構造化メタ出力を避ける。

## 6. revision-editor
- Input: このシーンを改稿して。テンポを改善しつつ結末は維持して。
- Expected: 保持点/変更点を分離し、既存稿を前提に改稿する。

## 7. consistency-auditor
- Input: 第5章の矛盾チェックをして。優先度付きで問題点を出して。
- Expected: 監査結果と修正方向を分離し、再確認可能な指摘を返す。

## 8. prose-polisher
- Input: このシーンの文体を整えて。語尾の揺れを減らして読みやすくしたい。
- Expected: 構造変更を避けた表現改善に限定する。

## 9. resume-orchestrator
- Input: どこから再開すべき？今の状態から次にやることを1つ決めて。
- Expected: 現在地要約、推奨スキル1つ、Read First 3件以内を返す。
