# ライトノベル執筆フレームワークの使い方 (Walkthrough)

初めてのライトノベル執筆をサポートするための「構造化テンプレート」および「自動化スクリプト」のセットアップが完了しました。
ここでは、3万字 / 5万字 / 10万字のいずれかをゴールに見すえ、この環境をどう活用していくかをステップ・バイ・ステップで解説します。

---

## ステップ 1: アイディア出し (Idea Generation)
まだ何を書きたいかぼんやりしている段階では、以下のスクリプトを使ってアイディアの種を作ります。

```bash
cd "."
python scripts/idea_generator.py
```

CLI上で「主人公の目的は？」「設定の面白さは？」などの質問に答えていくと、物語のコアとなるログラインが `generated_ideas.md` に自動出力されます。

## ステップ 2: プロジェクトの初期化 (Init Project)
アイディアが固まってきたら、執筆用の空のプロジェクト（フォルダ）を作成します。

```bash
python scripts/init_project.py [あなたの小説のタイトル] --target-total-chars [30000|50000|100000]
# 例: python scripts/init_project.py my_first_novel --target-total-chars 50000
```

これを実行すると、指定したタイトルのフォルダが作られ、中に **5つの設定テンプレート** と **第1章〜第5章のフォルダ** が自動生成されます。`--target-total-chars` を省略した場合は、互換運用のため `100000` に fallback します。

## ステップ 3: テンプレートを埋める (Fill Templates)
作成されたプロジェクトフォルダに入り、以下の順番でマークダウンファイルを埋めていきましょう。
初めから完璧にする必要はありません。思いついたところから書いてOKです。

1. [01_concept_sheet.md](templates/01_concept_sheet.md): 物語のテーマやターゲット（ステップ1の出力をコピペしてもOK）
2. [02_character_sheet.md](templates/02_character_sheet.md): 主人公や登場人物の設定
3. [03_world_building.md](templates/03_world_building.md): 世界観の簡単なルール
4. [04_plot_outline.md](templates/04_plot_outline.md): 物語全体の大まかな流れ（起承転結）
5. [05_chapter_outline.md](templates/05_chapter_outline.md): 全体計画の正本です。ここを見ながら、「第1章にはシーンがいくつあるか」「今はどのシーンを書いているか」を管理します。

## ステップ 4: 本文の執筆 ＆ ローカルLLMの活用 (Writing & AI Prompting)
章フォルダ内のシーン単位 `txt` を本文の正本として育てていきます。`body.md` は通常運用では本文追記先ではなく、章メモや大幅改稿の補助用途です。
もし執筆に行き詰まったり、ローカルLLM（3万トークン程度）に展開の相談をしたくなったら、以下のスクリプトを使います。

```bash
# 例: my_first_novel の 第1章のプロンプトを作る場合
python scripts/build_llm_prompt.py --project my_first_novel --chapter 1
```

※ もし直前のシーンの続きを書かせたい場合は、`--previous_text` に直前のテキストファイルを指定します。

このスクリプトは、コンテキスト制限（3万トークン）に配慮し、**「物語のコア設定」「キャラクター情報」「現在の章のプロット情報」だけを抽出したプロンプト**を `llm_prompt_output.txt` に出力します。
このテキストをコピーして、お使いのローカルLLMツール（LM StudioやLlama.cppなど）に貼り付けるだけで、設定を正確に理解したAIと壁打ちや続きの執筆が可能になります。

---

> [!TIP]
> **目標文字数を書き切るコツ**
> 「今日は第1章のシーン3だけを書く」というように、[05_chapter_outline.md](templates/05_chapter_outline.md) で設定した小さなマイルストーンを日々クリアしていくことを意識すると、途中で挫折せずに完結までたどり着きやすくなります。本文長は `Target Length Profile` ではなく `Length Band` を基準に調整します。

---

## 変更サマリー（2026-02-25）
以下の観点でテンプレートをブラッシュアップしました。

- **複数軸の運用**: 主軸/副軸/補助軸の比率を明示できるように追加
- **コメディのバリエーション**: 鉄板とズレの型を切り替えられる設計を追加
- **型の見える化**: コメディの型リストをチェックボックス化
- **幕・章・キャラ単位の管理**: 幕ごとの型チェック、章ごとの型チェック、キャラ×型の相性表を追加

対象ファイル:
- `templates/01_concept_sheet.md`
- `templates/02_character_sheet.md`
- `templates/03_world_building.md`
- `templates/04_plot_outline.md`
- `templates/05_chapter_outline.md`
