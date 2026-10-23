import re

from novel_agent.text_quality import split_paragraphs


_SENTENCE_END = re.compile(
    r"[。!?！？]+[」』”’）)]*|[」』”’][^\S\r\n]*(?=\r?\n)|\r?\n[^\S\r\n]*\r?\n"
)


def _sentence_spans(text):
    """Yield sentences with source offsets, keeping punctuation and close quotes."""
    text = text or ""
    start = 0
    for end in [match.end() for match in _SENTENCE_END.finditer(text)] + [len(text)]:
        fragment = text[start:end]
        sentence = fragment.strip()
        if sentence:
            yield sentence, start + len(fragment) - len(fragment.lstrip()), start + len(fragment.rstrip())
        start = end


def split_sentences(text):
    return [sentence for sentence, _, _ in _sentence_spans(text)]


def _short_evidence(text, limit=80):
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def detect_over_explain(sentences):
    markers = ("つまり", "なぜなら", "要するに", "言い換えれば", "それは", "ということだった")
    hits = [sentence for sentence in sentences if any(marker in sentence for marker in markers)]
    if len(hits) >= 3:
        return {
            "type": "over_explain_pattern",
            "message": "explanatory connective patterns appear repeatedly",
            "evidence": _short_evidence(hits[0]),
        }
    return None


def detect_triadic_listing(text):
    for sentence, start, end in _sentence_spans(text):
        comma_count = sentence.count("、")
        if comma_count >= 4 and re.search(r"(?:と|や).*(?:と|や)", sentence):
            return {
                "type": "triadic_listing_pattern",
                "message": "list-like prose rhythm detected inside a sentence",
                "evidence": _short_evidence(sentence),
                "start_line": text.count("\n", 0, start) + 1,
                "end_line": text.count("\n", 0, end) + 1,
            }
    return None


def detect_uniform_paragraph_length(paragraphs):
    lengths = [len(paragraph) for paragraph in paragraphs if len(paragraph) >= 40]
    if len(lengths) < 5:
        return None
    average = sum(lengths) / len(lengths)
    if average <= 0:
        return None
    close = [length for length in lengths if abs(length - average) / average <= 0.12]
    # A few near-average lines are normal in a long scene. Require the pattern
    # to describe most paragraphs, not merely a fixed-size subset of them.
    if len(close) >= 5 and len(close) / len(lengths) >= 0.8:
        return {
            "type": "uniform_paragraph_length",
            "message": "paragraph lengths are unusually uniform",
            "evidence": f"paragraph_lengths={lengths[:8]}",
        }
    return None


def detect_repeated_sentence_ending(sentences):
    endings = []
    for sentence in sentences:
        cleaned = sentence.rstrip("。!?！？」』”’）) 　")
        if len(cleaned) >= 2:
            endings.append(cleaned[-2:])
    if len(endings) < 5:
        return None
    for index in range(0, len(endings) - 3):
        window = endings[index:index + 4]
        if len(set(window)) == 1:
            return {
                "type": "repeated_sentence_ending",
                "message": "same sentence ending repeats across nearby sentences",
                "evidence": window[0],
            }
    return None


def detect_scene_summary_imbalance(text, paragraphs):
    if len(text) < 600 or not paragraphs:
        return None
    summary_markers = ("その後", "やがて", "しばらくして", "結局", "結果として")
    marker_count = sum(text.count(marker) for marker in summary_markers)
    dialogue_count = text.count("「")
    if marker_count >= 4 and dialogue_count <= 1:
        return {
            "type": "scene_summary_imbalance",
            "message": "scene reads like summary with little dramatized exchange",
            "evidence": f"summary_markers={marker_count} dialogue_count={dialogue_count}",
        }
    return None


def detect_dialogue_as_exposition(sentences):
    dialogue_sentences = [sentence for sentence in sentences if "「" in sentence and "」" in sentence]
    long_expository = [
        sentence
        for sentence in dialogue_sentences
        if len(sentence) >= 90 and any(marker in sentence for marker in ("つまり", "なぜなら", "だから", "ということ"))
    ]
    if long_expository:
        return {
            "type": "dialogue_as_exposition",
            "message": "dialogue appears to carry explanatory prose",
            "evidence": _short_evidence(long_expository[0]),
        }
    return None


def detect_negative_assertion_repetition(sentences):
    hits = [sentence for sentence in sentences if "ではない" in sentence or "じゃない" in sentence]
    if len(hits) >= 4:
        return {
            "type": "negative_assertion_repetition",
            "message": "negative assertion pattern repeats frequently",
            "evidence": _short_evidence(hits[0]),
        }
    return None


def analyze_anti_ai_style(text):
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)
    detectors = [
        lambda: detect_over_explain(sentences),
        lambda: detect_triadic_listing(text),
        lambda: detect_uniform_paragraph_length(paragraphs),
        lambda: detect_repeated_sentence_ending(sentences),
        lambda: detect_scene_summary_imbalance(text, paragraphs),
        lambda: detect_dialogue_as_exposition(sentences),
        lambda: detect_negative_assertion_repetition(sentences),
    ]
    warnings = []
    for detector in detectors:
        result = detector()
        if result:
            warnings.append(result)
    return {
        "status": "warning" if warnings else "pass",
        "warnings": warnings,
    }

