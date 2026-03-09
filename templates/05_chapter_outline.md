# 章カード＆シーン台帳 (Chapter Cards + Scene Ledger)

> このテンプレートは、作品全体の章役割と scene inventory を管理する canonical outline です。
> planning gate を使う案件では、執筆前にこのファイルで計画を確認してください。

---

## 全体方針

- 全体目標文字数: {{TARGET_TOTAL_CHARS}}
- 計画ゲート下限: {{PLANNING_GATE_MIN_CHARS}}
- 今回の重点レンズ:
- 今回は前面に出しすぎない要素:
- 1シーン固定ではなく、`scene_type` ごとの長さ帯で設計する

### Scene Type Bands

| scene_type | 用途 | min | target | max |
|---|---|---:|---:|---:|
| bridge | 接続、移動、軽い整理 | 1200 | 1500 | 1800 |
| standard | 通常の前進シーン | 1600 | 2000 | 2400 |
| anchor | 章の主軸になる重要シーン | 2200 | 2700 | 3200 |
| climax | 決断、対立、回収の山場 | 2600 | 3200 | 3800 |

---

## 第1章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- この章で強める要素:
- この章で抑える要素:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 1-1 | anchor | 主人公と世界の提示 | 日常 -> 転機 | 主軸の種まき | 2200 | 2700 | 3200 | - | planned |
| 1-2 | standard | 初期対立の明示 | 期待 -> 障害 | 誤解の火種を置く | 1600 | 2000 | 2400 | 1-1 | planned |
| 1-3 | climax | 章末の事件発生 | 準備 -> 破局 | 第2章の推進力 | 2600 | 3200 | 3800 | 1-2 | planned |

- scene_type では表現しない演出方針:

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第2章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- この章で強める要素:
- この章で抑える要素:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|
| 2-1 | standard |  |  |  | 1600 | 2000 | 2400 | 1-3 | planned |
| 2-2 | anchor |  |  |  | 2200 | 2700 | 3200 | 2-1 | planned |
| 2-3 | bridge |  |  |  | 1200 | 1500 | 1800 | 2-2 | planned |

- scene_type では表現しない演出方針:

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第3章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- この章で強める要素:
- この章で抑える要素:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

- scene_type では表現しない演出方針:

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第4章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- この章で強める要素:
- この章で抑える要素:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

- scene_type では表現しない演出方針:

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## 第5章 Chapter Card
- 章の役割:
- 章の感情線:
- 章末フック:
- 回収する伏線:
- 新規に撒く伏線:
- この章で強める要素:
- この章で抑える要素:
- 想定シーン数:
- 想定最小字数:
- 想定目標字数:

### Scene Ledger
| scene_id | scene_type | purpose | turn | payoff_or_seed | min | target | max | depends_on | status |
|---|---|---|---|---|---:|---:|---:|---|---|

- scene_type では表現しない演出方針:

### Chapter Gate Check
- 章の役割が他章と重複していない:
- 山場シーンが最低1つある:
- 回収だけ/説明だけの章になっていない:
- 想定字数が全体配分と整合している:

---

## Planning Totals
- planned_scene_count:
- planned_total_min_chars:
- planned_total_target_chars:
- gate_threshold: {{PLANNING_GATE_MIN_CHARS}}
- gate_result:

## Notes
- `planned_total_min_chars` が `gate_threshold` 未満なら、執筆前にシーン在庫か章配分を増やす
- つなぎシーンを無理に膨らませず、`anchor` と `climax` に厚みを持たせる
- 執筆直前の `runtime` には、対象シーンの行だけを圧縮して渡す
- planning 判断ログ:
- 保留事項:
