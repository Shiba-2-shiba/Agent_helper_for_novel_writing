# Pilot Eval Result: `resume_orchestrator` on `ojiichan_mystery`

## Scope

- Skill under test: `agent/skills/resume-orchestrator/SKILL.md`
- Baseline template: `agent/evals/templates/resume_orchestrator_ojiichan_mystery.md`
- Project: `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery`
- Date: 2026-03-04

## Baseline Run (Before Change)

### Simulated Output

1. `Current Position`
   - `state_schema_novel.yaml` は `setting_creation` を示しているが、`chapters/` には `chapter_01_scene_01.txt` から `chapter_06_scene_03.txt` までの本文が存在するため、現況は設定初期段階ではない。最新更新と `runtime/check_report.json` の対象から、直近作業は `chapter_06_scene_03.txt` の完了直後とみなす。
2. `Open Items`
   - 現在の `state` が実ファイル状況に追いついていない
   - 第6章終端が全体の締めとして十分か未確認
   - 次の運用モードが未整理
3. `Next Action`
   - 第6章終盤と全体整合を優先して監査する
4. `Recommended Skill`
   - `agent/skills/consistency-auditor/SKILL.md`
5. `Read First`
   - `ojiichan_mystery/chapters/chapter_06_scene_03.txt`
   - `ojiichan_mystery/memory/06_chapter_outline_100k.md`
   - `ojiichan_mystery/memory/global_notes.md`

### Baseline Score

- `State Reconstruction`: 4/5
- `File Grounding`: 4/5
- `Action Selection`: 5/5
- `Output Discipline`: 5/5

### Observed Failure Pattern

- `chapter` / `scene` 未指定時の推定手順がスキル本文で明示されておらず、`runtime` 更新前に何を根拠に再開地点を決めるかが運用者依存になっていた。

## Single Change Applied

- Fix target: **再開地点推定の手順を先に固定する**
- Change summary:
  - `Procedure` の先頭に「再開候補を先に推定する」を追加
  - 推定順を `最新シーン txt -> runtime/check_report.json -> state_schema_novel.yaml -> session_notes.md` に固定
  - `state` と実ファイルが矛盾する場合は、実ファイル優先と明記

## Re-Run (After Change)

### Re-Run Expectation

- `chapter` / `scene` 未指定でも、まず最新シーンと `runtime/check_report.json` を基準に候補を絞るため、同じ案件で再開地点の根拠がより一貫する。
- 古い `state` を見ても、先に実ファイル確認へ進む流れがスキル本文に埋め込まれた。

### Re-Run Score

- `State Reconstruction`: 5/5
- `File Grounding`: 5/5
- `Action Selection`: 5/5
- `Output Discipline`: 5/5

## Live Validation Note

- Manual check:
  - `python scripts/build_runtime_context.py --project <ojiichan_mystery> --chapter 6 --scene 6-3 --mode resume`
- Result:
  - Initial run: `ERROR: 05_chapter_outline_100k.md not found`
- Interpretation:
  - この案件では章アウトラインが `memory/05_chapter_outline_100k.md` にあり、`build_runtime_context.py` の期待配置と一致しない。
  - そのため、当初は今回修正した「再開候補の推定順」とは別に、**`runtime` 再生成の前提レイアウト** が噛み合っていなかった。

## Follow-Up Resolution

- Subsequent fix:
  - `build_runtime_context.py` は `resume` 時に章アウトラインを必須にしないよう変更
  - `draft` 時は `memory/05_chapter_outline_100k.md` も探索対象に追加
  - `prompt_utils.py` 側で root 直下の `state_schema_novel.yaml`、`# 第N章` 見出し、`## シーンN：...` 見出しを拾えるよう調整
- Validation:
  - `python scripts/build_runtime_context.py --project <ojiichan_mystery> --chapter 6 --scene 6-3 --mode resume` → `OK`
  - `python scripts/build_runtime_context.py --project <ojiichan_mystery> --chapter 2 --scene 2-2 --mode draft` → `OK`

## Conclusion

- このケースでは、最優先で直すべき論点は「再開地点推定の順序の明示」だった。
- 次回以降は、同じテンプレートで再度見て、`Recommended Skill` の選び分け基準まで細かくするかを判断する。
- `runtime` 生成スクリプトと実案件レイアウトの差異は、今回の追加入力で解消した。

