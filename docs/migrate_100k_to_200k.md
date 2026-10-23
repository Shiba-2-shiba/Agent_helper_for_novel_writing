# 既存10万字案件を20万字へ変更する

これは目標設定の移行であり、作品の本文・シーン数・章配分を自動的に倍増する処理ではない。元の本文txtとbody.mdは変更しない。

## 確認する変更

- target_total_chars: 100000 → 200000
- target_length_profile: novel_100k → novel_200k
- planning_target_total_chars: 100000 → 200000
- planning_gate_min_chars: 既定80000 → 既定160000
- 以前のplanning gate readyはblockedへ戻し、新しい計画で判定し直す。

旧値を残すと新しい目標より古いoverrideが優先されるため、一緒に確認する。独自のgateは黙って変更しない。

## dry-run

```sh
python scripts/migrate_project_state.py --project my_novel --target-total-chars 200000 --dry-run
```

出力のplan、変更前hash、差分、conflicts、backup先、影響するruntimeを読む。独自gateの選択が必要なら次のいずれかを明示する。

```sh
python scripts/migrate_project_state.py --project my_novel --target-total-chars 200000 --dry-run --gate-policy profile
python scripts/migrate_project_state.py --project my_novel --target-total-chars 200000 --dry-run --gate-policy preserve
```

profileは160000へ変更。preserveは独自の値を保持しcustomとして記録する。自由記述・重複ラベルを安全に特定できない場合はconflictを解決して再dry-runする。dry-runがmigration planを作ることはあるが、元の設定/outline/本文は書き換えない。

## apply

以下のPLAN_PATHとPLAN_HASHは実際に表示された値で置き換える。レビュー後に元ファイルを変更した場合はapplyを止め、再dry-runする。

```sh
python scripts/migrate_project_state.py --project my_novel --apply-plan PLAN_PATH --expected-plan-hash PLAN_HASH
```

バックアップ、移行ジャーナル、変更後の読み直しを確認する。未完了の移行を成功として扱わない。目標変更は本文を書き足さず、作者が新しい計画とLength Bandを確認する。使うruntimeは再生成する。本文hashだけの旧承認を、新しい検査条件まで保証した承認と扱わない。

## rollback

MIGRATION_IDは実際の移行IDで置き換える。

```sh
python scripts/migrate_project_state.py --project my_novel --rollback MIGRATION_ID
```

移行後にユーザーが編集したファイルがあれば、勝手に古いbackupで上書きしない。衝突を確認し、変更内容を保全してから復旧する。本文はrollbackでも変更しない。

目標変更のない従来コマンド `python scripts/migrate_project_state.py --project my_novel` は、旧形式のstate整備用として残す。20万字への変更を意図する場合は必ず明示の目標変更dry-runを使う。

apply/rollback後は設定を読み直し、読取専用healthの結果を `verification` に出します。移行自体がcommittedでも、検証にblocking issueが残れば終了コード2です。成功済みの変更を未適用と誤認して繰り返さず、JSONのstatusとverificationを別々に確認してください。
