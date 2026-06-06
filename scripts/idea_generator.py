import os
import sys

# S1修正: スクリプトの場所を基準にプロジェクトルートを取得（実行場所に依存しない）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

def ask_question(question, example=None):
    if example:
        print(f"\n{question}\n(例: {example})")
    else:
        print(f"\n{question}")
    return input("> ")

def main():
    print("=" * 50)
    print("小説アイディア生成アシスタント (Idea Generator)")
    print("=" * 50)
    print("いくつか質問をします。思いつくままに答えてください。")
    print("※空白のままでも構いません（空白の場合は「[未設定]」に置換されます）。\n")

    genre   = ask_question("Q1. 書きたい物語の「ジャンル」と「ターゲット層」を教えてください。", "ミステリー、全年齢向け / お仕事小説、20代女性向け / SF、社会人向け")
    hero    = ask_question("Q2. 主人公はどんな人物ですか？（年齢、職業、性格など）", "32歳の編集者、慎重だが好奇心が強い / 17歳の部員、負けず嫌い")
    goal    = ask_question("Q3. 主人公が最終的に達成したい「最大の目的」は何ですか？", "失われた原稿の真相を突き止める / 閉鎖寸前の店を立て直す")
    flaw    = ask_question("Q4. 主人公の「最大の弱点」や「トラウマ」は何ですか？", "失敗を恐れて決断を先延ばしにする / 他人に頼れない")
    world   = ask_question("Q5. 物語の舞台となる世界で、一番面白い設定（独自のルールなど）は何ですか？", "記憶を売買できる都市 / 評価スコアで仕事が決まる会社")
    incident = ask_question("Q6. 日常が壊れる「転機となる事件（インサイティング・インシデント）」は何ですか？", "消えたはずの人物から手紙が届く / 重要な契約が突然白紙になる")

    # S7修正: 空回答を[未設定]に置換してログラインを整形
    def fill(val, placeholder):
        return val.strip() if val.strip() else f"[{placeholder}未設定]"

    genre_f    = fill(genre,    "ジャンル")
    hero_f     = fill(hero,     "主人公")
    goal_f     = fill(goal,     "目的")
    flaw_f     = fill(flaw,     "弱点")
    world_f    = fill(world,    "世界観")
    incident_f = fill(incident, "事件")

    # Generate logline
    logline = f"【{world_f}】を舞台に、【{flaw_f}】を抱えた【{hero_f}】が、【{incident_f}】をきっかけに、【{goal_f}】を目指す物語。"

    print("\n" + "=" * 50)
    print("生成されたログライン（あらすじの核）：")
    print(logline)
    print("=" * 50)

    # S1修正: 出力先をプロジェクトルートに固定
    out_file = os.path.join(BASE_DIR, "generated_ideas.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# 生成されたアイディアメモ\n\n")
        f.write("## ログライン\n")
        f.write(f"> {logline}\n\n")
        f.write("## 回答ログ\n")
        f.write(f"- **ジャンル/ターゲット**: {genre_f}\n")
        f.write(f"- **主人公**: {hero_f}\n")
        f.write(f"- **目的**: {goal_f}\n")
        f.write(f"- **弱点/トラウマ**: {flaw_f}\n")
        f.write(f"- **世界観**: {world_f}\n")
        f.write(f"- **転機となる事件**: {incident_f}\n")

    print(f"\n結果を '{out_file}' に保存しました。")
    print("次のステップ: `python scripts/init_project.py <タイトル> --from_ideas` でプロジェクトを作成すると")
    print("このアイデアが自動的に 01_concept_sheet.md に転記されます！")

if __name__ == "__main__":
    main()
