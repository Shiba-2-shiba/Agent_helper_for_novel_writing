# 試作で見つかった診断・書き出しの注意点

## health の終了コード

`python scripts/sync_project_health.py --project <project> --json` は、正常な JSON を表示して `runtime/health_report.json` を保存した後、`status=fail` なら終了コード 1、`warning` / `pass` なら 0 を返す。JSON を保存できたことと、作品の状態が正常なことは別である。

`--fix-safe` は安全に再生成できる派生物だけを対象とする。破損した永続データを空データで上書きする機能ではない。blocking issue があれば先にその原因を確認する。

## 部分書き出しと全体書き出し

既定の export はこれまでどおり部分書き出しを許可する。未承認シーンや、`--include-warnings` を指定していない警告付き承認シーンは含まれない。CLI は `complete=false` と省略したシーン ID・理由を必ず表示する。部分書き出しの成功を全編完成と扱わない。

全体書き出しには `--require-complete` を指定する。

```sh
python scripts/export_manuscript.py --project <project> --require-complete
```

警告の内容を確認し、その承認済み本文も含めると判断した場合だけ、明示的に次を使う。

```sh
python scripts/export_manuscript.py --project <project> --require-complete --include-warnings
```

`--include-warnings` は警告の解消、検査、承認を代行しない。`--require-complete` は Scene Ledger の予定シーンに欠落、未検査・未承認、除外対象の警告付き承認があれば、出力先の作成・上書き前に失敗する。stale approval は部分・全体のどちらでも失敗する。

API `export_manuscript(project_dir, *, include_warnings=False, output_path="", title=None, require_complete=False)` は、従来の `output_path` / `scene_count` / `scenes` に加え、次を返す。

- `complete`: 判定対象シーンを省略せず書き出せたか。
- `omitted_scenes`: `scene_id` と `reason` の一覧。理由は `scene_missing`（本文なし）、`not_approved`（本文はあるが承認なし）、`warning_excluded`（警告付き承認の除外）。

Scene Ledger の予定シーンが取れない場合は、従来どおり検出したシーン txt の一覧を判定対象にする。この場合の `complete=true` は「検出した本文を省略していない」という意味だけで、未記載の予定シーンや全編構成の完成を保証しない。全編の欠落を確実に検出するには、先に Scene Ledger を整備する。

## 新しい章の保存先

対象シーンの本文が既にある場合は、その保存先を優先する。本文がまだない章では、既存の他章がすべて `scene_1-1.txt` 形式なら、その形式を引き継ぐ。他章の命名形式が混在する場合は推測で統一せず、既定の `chapter_2_scene_1.txt` 形式を提案する。同じ章番号の候補ディレクトリが複数ある場合は曖昧として停止する。既存本文の改名・移動は行わない。

## 最終場面の決着と余韻

Scene Brief は既知の次シーンの目的を優先する。次の目的が不明な場合は「場面の決着と余韻（続きがある場合のみ接続）」を使い、未解決の問いを必ず追加するよう要求しない。これは自動的な小説終端判定ではない。章末・最終場面の意図や、回収すべき要素は Scene Ledger と執筆指示で明示する。

## 人物知識・設定参照・計画判定の範囲

この修正は、作中の日時から人物知識を自動推論したり、設定の意味検索で必要事項を網羅したりする機能を追加しない。重要な設定は、採用済みの資料の正確なファイル・節と、その場面で必要な事実を指定する。人物の知識は「誰が、いつ、どの承認済み場面で知ったか」を確認し、後の場面で判明する情報や未採用の提案を過去の既知事実として扱わない。

planning gate の判定根拠が不明なら、自動承認されたものと解釈しない。既存の setting-creator の手順で章配分・Scene Ledger・必要な設定を確認し、根拠を伴って人が `ready` を判断してから、対象 scene の runtime を再生成する。
