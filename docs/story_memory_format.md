# 出典付き物語記憶

## 正本と責務

物語記憶は外部エージェントによる提案を、形式・出典・参照・時点について検証し、明示的に採用する。Pythonは日本語本文の意味的正しさを自動判定しない。本文承認と記憶採用は別操作。

- 未採用: `story_memory/proposals/<batch_id>.json`
- 採用済み: `story_memory/accepted.json`（version/revision/records）
- 派生した鮮度判定: `runtime/story_memory_status.json`

起きた事実の根拠にできるのは、有効な承認を持つ承認済みscene txtだけ。設定Markdown・アウトラインの結末予定を既成事実のsourceにしない。作者用設定とplanningは別ラベルで渡す。出典はproject相対パス、本文hash、1始まりの行範囲。外部パス、symlink経由の範囲外参照、未来を過去と偽る日時/scene指定を拒否する。

## 記録の種類

共通項目はid、kind、text、entity_ids、available_after_scene、sources、supersedes。

| kind | 追加項目 | 内容 |
|---|---|---|
| fact | subject_id, predicate | 本文で成立した事実 |
| character_knowledge | character_id, fact_id | その人物が知った事実 |
| thread_event | thread_id, event | opened/progressed/resolved/abandoned |
| scene_outcome | scene_id | シーンで実際に変化したこと |
| chapter_summary | chapter, covered_scenes | 既筆章の要約 |
| part_summary | part_id, covered_scenes | 既筆の部の要約 |

提案テンプレートは `templates/story_memory_proposal.json`。サンプルの出典hash・人物名等は実作品の値へ置換してから検証する。文字列の意味がsourceに裏付けられるかは外部エージェントとレビュー担当者が確認する。章・部要約は覆うsceneを列挙し、全sourceを持つ。全範囲でなければpartialと表示する。

## 失効と訂正

本文改稿・承認失効でsourceが有効でなくなれば記憶は利用不可となる。記録は削除せず、再提案が必要。factの失効は参照するcharacter_knowledgeへ、構成sceneの失効は要約へ伝播する。

訂正は新しいIDと `supersedes` で追跡する。未来の訂正を全時点に先に適用しない。第15章で分かった訂正は、第5章の執筆時点で有効だった旧記録を消してはならず、第16章では適格な新記録を使う。対象時点の選択はaccepted全件と参照関係から導出し、全体表示のsuperseded一覧をそのままfilterにしない。

## 視点と情報漏出

対象sceneより前に成立した記録だけを選び、参照fact・source・covered_scenesにも同じ判定を伝播する。available_after_sceneはsourceの最終sceneより前にできない。作者用author_contextと人物用pov_contextを分離する。人物知識は明示的なcharacter_knowledgeだけを根拠とし、視点不明なら全人物の知識をまとめて渡さない。

scene順は読者が読む順序であり、作中時刻と同一ではない。回想や並行時系列は人間が意味を確認する。将来計画を読む必要がある場合はplanningとして区別し、既成事実として採用しない。

提案→validate-only→import→review→acceptの具体的コマンドは `docs/long_novel_workflow.md` を参照。採用時には期待revisionと出典を再確認する。競合や破損を `--force` 相当の処理で無視しない。
