# 依存キャッシュの明示的な再生成

新しく生成する依存証拠はprojectionのhashとartifactの参照先digestを保持し、全outlineや上流の依存リストを再帰的に複製しない。`runtime_manifest.json` はwriter向けのID・hash・参照パスだけを保持する。元資料が変われば、hashを元資料から再計算するため失効する。

旧形式は読み取り互換で、通常のprepareでは触れたartifactだけが更新される。過去の台帳全体が自動で縮小するわけではない。旧承認に記録された全voiceファイル依存は広いまま残り、別人物のカード変更でも失効しうる。狭い条件に切り替えるには、通常のprepare、check、内容確認、明示approveが必要。再生成コマンドは承認しない。

## コピーでdry-run

原本を変更せず、作品全体を新しい作業先にコピーしてから行う。以下のパスは例。

```sh
cp -a my_novel my_novel_rebuilt
python scripts/rebuild_dependency_cache.py --project my_novel_rebuilt
```

dry-runは台帳・runtime数と旧台帳のbyte数を表示し、ファイルを変更しない。壊れた台帳は空に置き換えず停止する。

## 明示適用と再prepare

```sh
python scripts/rebuild_dependency_cache.py --project my_novel_rebuilt --apply
python scripts/build_runtime_context.py --project my_novel_rebuilt --chapter 2 --scene 2-3 --mode draft --pov-character protagonist
python scripts/build_draft_prompt.py --project my_novel_rebuilt --scene 2-3
python scripts/check_scene_output.py --project my_novel_rebuilt --text chapter_2_scene_3.txt
```

- 元の台帳と既存manifestを `<project>/.dependency_archive/<ID>/`（通常のruntime外） にそのまま保存する。元台帳内の再帰的な旧証拠も保存される。
- runtime・台帳・manifest・journal・archiveのsymlinkやproject外への参照は、lockを作る前に拒否する。
- project lockの下で、全ての旧runtimeを `cache_rebuild_required` にしてから、新しい空の生成用台帳をatomic replaceする。古いruntimeはprepareまで使えない。旧本文、承認台帳、採用済み記憶は変更しない。
- 中断時は `runtime/dependency_cache_rebuild.json` のin_progress journalと保存済みarchiveを使い、同じ `--apply` を再実行できる。archiveを上書きせず、journalに記録した元台帳・各manifestのSHA-256とarchiveのschema・依存digestを照合してから再開する。中断後にactive台帳やmanifestへ別の作業が加わった場合はreset前に拒否する。atomic reset直後の中断だけは、書込み前に記録したphaseと空台帳の正確なhashにより識別する。破損archiveは正常なactive ledgerで置き換えてごまかさない。旧runtimeをcurrent扱いしない。project lockが残る異常終了では、実行中の処理がないことを確認してから通常のlock復旧方針に従う。
- 利用するscene/modeを明示してそれぞれprepareし直す。元のCLI参加者・POV指定を保ち、任意の旧sceneのlatestを流用しない。checkのpassは承認や文学的品質の保証ではない。
- 再生成後も過去の承認を自動更新しない。既存承認が有効かは、本文・元の検査条件・選択記録を照合して別途判定される。選択や条件が変わった場合はstaleのままにし、通常手順で再確認する。

## 比較時の注意

空にした直後の台帳と25scene分の旧台帳は比較できない。全sceneについて同等のprepare・prompt・checkを再実行し、件数を揃えたactive ledgerのbyte数と定常実行時間を比較する。archiveを残すためactive ledgerの縮小はディスク容量解放を意味しない。冷たい初回再生成の時間も別に報告する。承認数・有効な採用済み記憶数と本文hashを再確認し、失効した承認を勝手に再承認しない。
