import json
from pathlib import Path
import subprocess
import sys

import pytest

from novel_agent.anti_ai_style import analyze_anti_ai_style, split_paragraphs, split_sentences
from novel_agent.text_quality import detect_duplicate_paragraphs, paragraph_count


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_nonempty_japanese_lines_are_paragraphs_without_blank_lines(newline):
    text = newline.join(["　玄関の鍵を閉めた。", "「もう行くの」", "　彼は振り向いた。", "", "　雨が降っていた。"])

    assert paragraph_count(text) == 4
    assert split_paragraphs(text) == ["玄関の鍵を閉めた。", "「もう行くの」", "彼は振り向いた。", "雨が降っていた。"]
    assert paragraph_count("\n　\n\t\r\n") == 0


def test_duplicate_japanese_paragraphs_are_detected_without_blank_lines():
    repeated = "駅前の古い時計台を見上げると、昨日と同じ時刻を指していた。"
    warnings = detect_duplicate_paragraphs("　" + repeated + "\n　彼は歩き始めた。\n　" + repeated)

    assert len(warnings) == 1
    assert warnings[0]["first_paragraph"] == 1
    assert warnings[0]["duplicate_paragraph"] == 3


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("opening,closing", [("「", "」"), ("『", "』")])
def test_dialogue_closing_quote_followed_by_newline_ends_sentence(newline, opening, closing):
    text = opening + "聞くのが、少し" + closing + "　 " + newline + opening + "袋のことを" + closing

    assert split_sentences(text) == [opening + "聞くのが、少し" + closing, opening + "袋のことを" + closing]


def test_sentence_terminal_punctuation_stays_with_its_closing_quotes():
    assert split_sentences("「帰る。」「本当に？」\n　彼はうなずいた！") == ["「帰る。」", "「本当に？」", "彼はうなずいた！"]


def test_separate_dialogue_lines_do_not_create_a_triadic_listing_warning():
    text = (
        "「持ち主だと思う人と、一緒に見ればいいわ」\n"
        "「聞くのが、少し」\n"
        "「袋の持ち主を聞くのと、コロッケを盗ったか聞くのは違うでしょう」\n"
        "　そんな言い方をされると、昨夜の自分はずいぶん大げさだった。"
    )

    warnings = analyze_anti_ai_style(text)["warnings"]

    assert not any(warning["type"] == "triadic_listing_pattern" for warning in warnings)


def test_real_triadic_listing_still_warns_with_exact_source_line_range():
    text = "　彼は立ち止まった。\n\n　皿と、箸と、椀を、\n順番に、机へ並べた。\n「できた」"

    warning = next(item for item in analyze_anti_ai_style(text)["warnings"] if item["type"] == "triadic_listing_pattern")

    assert warning["start_line"] == 3
    assert warning["end_line"] == 4
    assert warning["evidence"] == "皿と、箸と、椀を、 順番に、机へ並べた。"


def test_repeated_endings_are_not_hidden_by_preserved_dialogue_quotes():
    text = "\n".join(["「それは昨日だった。」", "「雨の日だった。」", "「日曜だった。」", "「休日だった。」", "「静かだった。」"])

    warnings = analyze_anti_ai_style(text)["warnings"]

    assert any(warning["type"] == "repeated_sentence_ending" and warning["evidence"] == "った" for warning in warnings)


def test_genuine_explanatory_connective_warning_remains():
    text = "つまり彼は理由を説明した。なぜならそれは必要だった。要するに状況は変わらなかった。"

    assert any(warning["type"] == "over_explain_pattern" for warning in analyze_anti_ai_style(text)["warnings"])


def test_five_average_length_lines_do_not_make_a_varied_scene_uniform():
    text = "\n".join("あ" * length for length in [50, 50, 50, 50, 50, 40, 40, 40, 40, 90])

    assert not any(warning["type"] == "uniform_paragraph_length" for warning in analyze_anti_ai_style(text)["warnings"])


def test_genuinely_uniform_japanese_paragraphs_still_warn():
    text = "\n".join("あ" * length for length in [50, 51, 50, 49, 50])

    assert any(warning["type"] == "uniform_paragraph_length" for warning in analyze_anti_ai_style(text)["warnings"])


def test_check_report_explains_paragraph_count_and_keeps_warning_source_lines(tmp_path):
    text = "　彼は立ち止まった。\n\n　皿と、箸と、椀を、\n順番に、机へ並べた。\n「できた」"
    (tmp_path / "draft.txt").write_text(text, encoding="utf-8")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "style_contract_compact.md").write_text("# Style\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_scene_output.py"

    result = subprocess.run([
        sys.executable, str(script), "--project", str(tmp_path), "--text", "draft.txt",
        "--min_chars", "1", "--target_chars", "50", "--max_chars", "1000",
    ], capture_output=True, text=True)

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((runtime / "check_report.json").read_text(encoding="utf-8"))
    warning = next(item for item in report["warnings"] if item["type"] == "anti_ai_style:triadic_listing_pattern")
    assert (warning["start_line"], warning["end_line"]) == (3, 4)
    assert report["paragraph_count"] == 4
    paragraph_info = next(item for item in report["info"] if item["type"] == "paragraph_count")
    assert paragraph_info["definition"] == "nonempty_source_lines"


def test_expansion_edit_targets_keep_their_existing_blank_line_block_numbering():
    from apply_expand_edits import apply_edits
    from build_expand_prompt import build_paragraph_map

    text = "最初の行。\n二行目。\n\n次のブロック。"

    assert paragraph_count(text) == 3
    assert build_paragraph_map(text) == "- P1: 最初の行。\n二行目。\n- P2: 次のブロック。"
    assert apply_edits(text, [{"target": "after P1", "anchor": "二行目。", "text": "追加文。"}]) == "最初の行。\n二行目。\n\n追加文。\n\n次のブロック。\n"
