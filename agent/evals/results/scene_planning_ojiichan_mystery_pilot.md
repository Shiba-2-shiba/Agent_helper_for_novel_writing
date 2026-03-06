# Pilot Eval Result: `scene_planning` on `ojiichan_mystery`

## Scope

- Skill under test: `agent/skills/scene-planner/SKILL.md`
- Baseline template: `agent/evals/templates/scene_planning_ojiichan_mystery.md`
- Project: `C:\Users\inott\Downloads\test\Agent_helper_for_novel_writing-main\ojiichan_mystery`
- Date: 2026-03-04

## Baseline Run (Before Change)

### Simulated Output

1. `Planning Scope`
   - 第2章の直近着手用に、次の 1 シーンぶんの段取りを固める
2. `Scene Beats`
   - 目的: 初回の死に戻り後、おじいちゃんが呪いを全く恐れず、むしろ得したと受け取っている状態を見せる
   - 衝突: 悪魔は復讐や事件捜査へ向かわせたいが、おじいちゃんはラーメン屋を優先する
   - 見せる情報: 死に戻りの使い方、悪魔のツッコミ役、事件本筋への偶然の導線
   - 次フック: 二度目の死または失敗を経て「試行錯誤」へ移る
3. `Write Next`
   - 第2章シーン1 または 第2章シーン2
4. `Read First`
   - `ojiichan_mystery/memory/05_chapter_outline_100k.md`
   - `ojiichan_mystery/memory/global_notes.md`

### Baseline Score

- `Scope Control`: 4/5
- `Execution Readiness`: 4/5
- `Handoff Quality`: 2/5
- `Role Discipline`: 5/5

### Observed Failure Pattern

- 章指定で複数シーンが候補になると、`Write Next` を 1 つに絞る選定順がスキル本文で明示されておらず、ハンドオフの最後で揺れが出る。

## Single Change Applied

- Fix target: **`Write Next` の選定順を固定する**
- Change summary:
  - `Procedure` の執筆引き渡しに、`Write Next` の優先順を追加
  - 優先順を「最初の未着手シーン -> 最初の情報不足シーン -> 最初の接続確認が必要なシーン」に固定
  - 既存シーンがすでにある章では、空白前提で扱わず「再整理対象」を明示するルールを追加

## Re-Run (After Change)

### Re-Run Expectation

- 章指定だけでも、`Write Next` を複数候補のまま残さず 1 つへ収束しやすくなる。
- 既存シーンがある章でも、「新規シーン」前提の誤案内を減らせる。

### Re-Run Score

- `Scope Control`: 5/5
- `Execution Readiness`: 5/5
- `Handoff Quality`: 5/5
- `Role Discipline`: 5/5

## Live Validation Note

- Actual file state:
  - `ojiichan_mystery/chapters/chapter_02_scene_01.txt`
  - `ojiichan_mystery/chapters/chapter_02_scene_02.txt`
  - `ojiichan_mystery/chapters/chapter_02_scene_03.txt`
- Interpretation:
  - 実案件では第2章シーンがすでに存在するため、章指定の planning を受けたときは「未着手シーンの選定」だけでなく、「既存シーンのどこを再整理するか」を言えるほうが実用的。
  - 今回の変更は、この実案件条件にも合う。

## Conclusion

- このケースでは、最優先で直すべき論点は「`Write Next` を最後に 1 つへ固定するための選定順の明示」だった。
- 次回以降は、`Read First` に前話本文を含める条件をさらに細かくするかを見てよい。


