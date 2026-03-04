# 小説作成フレームワーク (Light Novel Writing Framework)

10万字のライトノベル完成を目標とした、**構造化テンプレート**と**自動化スクリプト**、そして**Antigravity自律エージェント連携**のセットプロジェクトです。
アイディア出しから設定の構築、そしてエージェントによる自動執筆ループまで、執筆の全工程をサポートします。

---

## 🚀 推奨ワークフロー：Antigravityエージェントによる自律執筆 (Continuous Writing Loop)

このプロジェクトは、Antigravity環境の自律エージェントと連携して動作するように設計されています。現行の推奨運用は `runtime-first` です。エージェントは、まず `runtime/` 配下の圧縮文脈を優先参照し、それに沿って本文の執筆、見直し、必要なら不足分の拡張を行います。

### エージェント運用での使い方

**💡 コマンドハブ (`agent/HUB.md`) による自動ルーティング**
プロンプト内に `agent/HUB.md` への参照を含めることで、エージェントが依頼文を解析し、「企画立ち上げ」か「本文執筆」か適切な自律機能を自動で選択して実行します。新規本文と再開整理は、`HUB.md` と各スキル定義により `runtime-first` で処理されます。

**💡 `runtime-first` の意味**
- 本文執筆では、毎回フル文脈を読み直さず、`runtime/draft_prompt.txt` または `runtime/*.md` の圧縮済み文脈を優先します
- 再開時は、`runtime/resume_brief.md` を優先して現在地を確認します
- `runtime/` が未生成・欠損・対象不一致のときだけ、従来の広い文脈参照へフォールバックします

1. **設定・プロットの準備（エージェントとの対話型立ち上げ）**:
   アイディアが固まっていない状態からでも、Antigravityエージェントに壁打ち相手になってもらうことができます。
   *プロンプト例:*
   > 「`agent/HUB.md` を参照して、新しい小説の企画を一緒に考えて立ち上げて」
   エージェントがHUBのルールに従って対話ロジックを起動し、ログラインの作成から設定ファイル（`01_concept_sheet.md` ～ `05_chapter_outline_100k.md`）の記入までインタラクティブにサポートします。

   ※もちろん、手動でMDファイルを直接編集して設定を作り込むことも可能です。

2. **エージェントへの指示（Antigravityチャットにて）**:
   テンプレート（特に `05_chapter_outline_100k.md` のシーンマイルストーン）が用意できたら、チャットを通じてエージェントに自律執筆のループを開始させます。
   *プロンプト例:*
   > 「`agent/HUB.md` を参照して、{プロジェクト名}の第1章の執筆ループを開始して。」

   この依頼では、エージェントは必要に応じて以下を先に行います。
   - `python scripts/build_runtime_context.py --project <project> --chapter <chapter> --scene <scene> --mode draft`
   - `python scripts/build_draft_prompt.py --project <project>`
   - 初稿保存後に `python scripts/check_scene_output.py --project <project> --text <scene_txt_path>`
   - `needs_expand=true` の場合のみ `python scripts/build_expand_prompt.py --project <project> --draft_text <scene_txt_path>`（途中差し込みも含む局所差分だけを生成）
   - 差分案を採用する場合は `python scripts/apply_expand_edits.py --project <project> --text <scene_txt_path> --edits <expand_response_path>` で反映する

3. **執筆・レビューの並走**:
   エージェントが各シーンを執筆するごとに、あなたは結果をレビューし、必要に応じて設定（MDファイル群）を微調整したり、エージェントへ直接フィードバックを与えたりして物語を進めます。

### 再開時の指示

中断後の再開では、以下のように依頼します。

> 「`agent/HUB.md` を参照して、{プロジェクト名}の現在地を整理して次の作業を決めて。」

この依頼では、エージェントは必要に応じて以下を先に行います。
- `python scripts/build_runtime_context.py --project <project> --chapter <chapter> --scene <scene> --mode resume`
- `runtime/resume_brief.md` を優先して現在地を整理する
- 次に呼ぶべきスキルを 1 つに絞って案内する

---

## 🔧 初期構築＆手動ワークフロー (Scripts)

手動でプロジェクトをセットアップしたり、外部のローカルLLM（LM Studioなど）と連携する場合は、以下のPythonスクリプトを使用します。日常執筆の原則は軽量な `runtime` 系スクリプトで、`build_llm_prompt.py` はフル文脈確認が必要なときだけ使う legacy 手段として扱います。

### 必要環境 (手動スクリプト実行時)
- **Python 3.8 以上**（標準ライブラリのみ使用）
- テストを実行する場合: `pip install pytest`

### スクリプトによる初期化手順

#### ステップ1: アイディアを出す
```bash
python scripts/idea_generator.py
```
いくつかの質問に答えると、物語のログラインが `generated_ideas.md` に保存されます。

#### ステップ2: プロジェクトを作成する
```bash
# --from_ideas を付けると、ログラインが 01_concept_sheet.md に自動転記されます
python scripts/init_project.py my_novel --from_ideas
```

#### ステップ3: 標準の `runtime` フローで日常執筆を回す
```bash
python scripts/build_runtime_context.py --project my_novel --chapter 2 --scene 2-3 --mode draft
python scripts/build_draft_prompt.py --project my_novel
python scripts/check_scene_output.py --project my_novel --text draft_scene.txt
python scripts/build_expand_prompt.py --project my_novel --draft_text draft_scene.txt
python scripts/apply_expand_edits.py --project my_novel --text draft_scene.txt --edits expand_response.txt
```
`runtime/` 配下に圧縮済み文脈とチェック結果がまとまるため、毎回フル文脈を読み込ませずに執筆できます。文字数不足時も、全文再生成ではなく「途中差し込み」または「末尾追記」の局所差分だけを要求するため、再試行のクレジット消費を抑えやすくなります。
`build_draft_prompt.py` と `build_expand_prompt.py` は、生成したプロンプトの概算トークン数も標準出力に出し、`runtime` としては重くなりすぎた場合に警告します。
差分返答では、`ANCHOR:` に `Existing Paragraph Map` の該当抜粋をそのまま使う前提です。

#### ステップ4: 補助の legacy フル文脈プロンプトを使う（高コスト・手動運用のみ）
```bash
# テンプレート全体を読み込むため、常用せず必要時だけ使う
python scripts/build_llm_prompt.py --project my_novel --chapter 1
```
生成された `llm_prompt_output.txt` をローカルLLM等に貼り付けることで、設定を把握したAIと手動で壁打ちができます。スクリプト実行時にも legacy 経路である旨を警告表示します。

---

## 📁 ファイル構成

```
小説作成/
├── agent/                      # ★ Antigravityエージェント用設定・記憶（重要）
│   ├── skills/SKILL_novel.md   # 自律執筆（Continuous Writing Loop）の手順書
│   ├── skills/SKILL_resume_orchestrator.md # 再開整理の手順書
│   ├── state_schema_novel.yaml # エージェントが管理する文字数・文体・進行状態
│   └── memory/                 # エージェントが学習した文脈（global/session notes）
├── scripts/                    # 手動運用・補助スクリプト群
│   ├── idea_generator.py       
│   ├── init_project.py         
│   ├── build_llm_prompt.py     
│   ├── build_runtime_context.py
│   ├── build_draft_prompt.py
│   ├── check_scene_output.py
│   ├── build_expand_prompt.py
│   └── apply_expand_edits.py
├── templates/                  # 各プロジェクトにコピーされるテンプレート
│   ├── 01_concept_sheet.md     
│   ├── 02_character_sheet.md   
│   ├── ...
│   └── 05_chapter_outline_100k.md  
├── [your_project_name]/        # init_project.py が生成する執筆用フォルダ
│   ├── 01_concept_sheet.md
│   ├── ...
│   ├── chapter_1_introduction/body.md
│   ├── runtime/
│   │   ├── style_contract_compact.md
│   │   ├── scene_brief_compact.md
│   │   ├── continuity_pack.md
│   │   ├── request_compact.md
│   │   ├── draft_prompt.txt
│   │   ├── check_report.json
│   │   ├── expand_instruction.md
│   │   ├── expand_prompt.txt
│   │   └── resume_brief.md
│   └── agent/                  # プロジェクト単位のエージェント記憶域
└── README.md
```

---

## 💡 10万字達成のコツ（エージェント・人間共通）

途中で挫折しない最大のコツは、`05_chapter_outline_100k.md` を使った進捗管理です。
「今日は第1章のシーン3（約1000〜1500文字）だけを書く／エージェントに書かせる」というように、短いマイルストーンを日々クリアしていくことを意識してください。
1シーンを短めに刻み、シーン数を増やして合計10万字へ積み上げるほうが、再送する文脈と再試行コストを抑えやすくなります。
エージェントに執筆させる場合でも、このアウトラインファイルが正確であればあるほど、出力のブレがなくなり長期連載が安定します。
