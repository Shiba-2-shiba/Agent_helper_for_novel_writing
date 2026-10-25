import re


META_PATTERNS = [
    ("meta_preface_detected", re.compile(r"(?m)^\s*(?:以下に|以下、|それでは|承知しました|了解しました)")),
    ("meta_output_notice_detected", re.compile(r"(?:生成しました|出力します|出力しました|修正版|補足|注:)")),
]

FAIL_FORMAT_TYPES = {
    "heading_detected",
    "bullet_list_detected",
    "meta_preface_detected",
    "meta_output_notice_detected",
    "unclosed_dialogue_detected",
}


def detect_unclosed_dialogue(text):
    """Reject malformed quote balance for both styles, including wrong order.

    Counts alone accept an orphan alternate-style opener that consumes later
    valid utterances in candidate extraction. A shared stack interpretation
    keeps that extraction uncertainty mechanically blocking, without repairing
    source or turning valid nested/multiline dialogue into separate utterances.
    """
    pairs = {'「': '」', '『': '』'}
    stack = []
    failure_offset = None
    for offset, char in enumerate(text):
        if char in pairs:
            stack.append((pairs[char], offset))
        elif char in ('」', '』'):
            if not stack or stack[-1][0] != char:
                failure_offset = offset
                break
            stack.pop()
    if failure_offset is None and stack:
        failure_offset = stack[0][1]
    if failure_offset is None:
        return None
    line_start = text.rfind('\n', 0, failure_offset) + 1
    line_end = text.find('\n', failure_offset)
    if line_end < 0:
        line_end = len(text)
    return {
        'type': 'unclosed_dialogue_detected',
        'match': text[line_start:line_end].strip()[:80],
        'open_count': text.count('「') + text.count('『'),
        'close_count': text.count('」') + text.count('』'),
    }


def split_paragraphs(text):
    """Count hard line breaks as Japanese prose paragraphs, ignoring empty lines.

    Ideographic indentation is optional. Soft wrapping in an editor is not a
    line break in the source and therefore does not affect paragraph boundaries.
    """
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def detect_duplicate_paragraphs(text):
    paragraphs = split_paragraphs(text)
    seen = {}
    duplicates = []

    for index, paragraph in enumerate(paragraphs, start=1):
        normalized = re.sub(r"\s+", " ", paragraph)
        if len(normalized) < 20:
            continue
        if normalized in seen:
            duplicates.append(
                {
                    "type": "duplicate_paragraph_detected",
                    "match": normalized[:80],
                    "first_paragraph": seen[normalized],
                    "duplicate_paragraph": index,
                }
            )
            continue
        seen[normalized] = index

    return duplicates


def collect_format_violations(text):
    violations = []
    details = []

    heading_match = re.search(r"(?m)^\s*#+\s+(.+)$", text)
    if heading_match:
        violations.append("heading_detected")
        details.append(
            {
                "type": "heading_detected",
                "match": heading_match.group(0).strip(),
            }
        )

    bullet_match = re.search(r"(?m)^\s*(?:[-*]\s+|\d+\.\s+)(.+)$", text)
    if bullet_match:
        violations.append("bullet_list_detected")
        details.append(
            {
                "type": "bullet_list_detected",
                "match": bullet_match.group(0).strip(),
            }
        )

    for violation_type, pattern in META_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if "meta_commentary_detected" not in violations:
            violations.append("meta_commentary_detected")
        details.append(
            {
                "type": violation_type,
                "match": match.group(0).strip(),
            }
        )

    unclosed_dialogue = detect_unclosed_dialogue(text)
    if unclosed_dialogue:
        violations.append("unclosed_dialogue_detected")
        details.append(unclosed_dialogue)

    duplicate_paragraphs = detect_duplicate_paragraphs(text)
    if duplicate_paragraphs:
        violations.append("duplicate_paragraph_detected")
        details.extend(duplicate_paragraphs)

    return violations, details


def detect_format_violations(text):
    violations, _ = collect_format_violations(text)
    return violations


def paragraph_count(text):
    return len(split_paragraphs(text))


def dialogue_ratio_hint(text):
    if not text:
        return 0.0
    dialogue_chars = sum(len(match.group(0)) for match in re.finditer(r"「[^」]*」", text, re.DOTALL))
    return round(dialogue_chars / len(text), 3)


def detect_dialogue_ratio_warning(text, ratio):
    if len(text) < 400:
        return None
    if ratio > 0.75:
        return {
            "type": "dialogue_ratio_high",
            "message": "dialogue ratio is very high for a prose scene",
            "value": ratio,
        }
    return None


def classify_quality(*, actual_chars, min_chars, max_chars, format_details, forbidden_hits, paragraph_count_value, dialogue_ratio):
    blocking_issues = []
    warnings = []
    info = [
        {"type": "paragraph_count", "value": paragraph_count_value, "definition": "nonempty_source_lines"},
        {"type": "dialogue_ratio_hint", "value": dialogue_ratio},
    ]

    if actual_chars < min_chars:
        blocking_issues.append(
            {
                "type": "under_min_chars",
                "message": "actual_chars is below the required minimum",
                "actual": actual_chars,
                "minimum": min_chars,
            }
        )
    if actual_chars > max_chars:
        blocking_issues.append(
            {
                "type": "over_max_chars",
                "message": "actual_chars is above the allowed maximum",
                "actual": actual_chars,
                "maximum": max_chars,
            }
        )

    for detail in format_details:
        detail_type = detail.get("type", "")
        if detail_type in FAIL_FORMAT_TYPES:
            blocking_issues.append(
                {
                    "type": detail_type,
                    "message": "blocking format issue detected",
                    "match": detail.get("match", ""),
                }
            )
        elif detail_type == "duplicate_paragraph_detected":
            warnings.append(
                {
                    "type": detail_type,
                    "message": "duplicate paragraph detected",
                    "match": detail.get("match", ""),
                }
            )

    for hit in forbidden_hits:
        blocking_issues.append(
            {
                "type": "forbidden_hit",
                "message": "forbidden style or format rule matched",
                "rule": hit,
            }
        )

    dialogue_warning = detect_dialogue_ratio_warning("", dialogue_ratio)
    # The text length check belongs to the caller's text, but this function keeps
    # the warning shape centralized. Callers pass short text through actual_chars.
    if actual_chars >= 400:
        dialogue_warning = detect_dialogue_ratio_warning("x" * actual_chars, dialogue_ratio)
    if dialogue_warning:
        warnings.append(dialogue_warning)

    if blocking_issues:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    mechanical_penalty = min(10, len(blocking_issues) * 2 + len(warnings))
    return {
        "status": status,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "info": info,
        "quality_score_hint": {
            "mechanical_penalty": mechanical_penalty,
            "max_penalty": 10,
        },
    }


DIALOGUE_EXTRACTOR_VERSION = 'dialogue-candidates-v1'


def dialogue_digest(value):
    """Canonical JSON identity, not an authentication or literary guarantee."""
    import hashlib
    import json
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def source_span(text, start, end):
    import hashlib
    quote = text[start:end]
    return {'start_char': start, 'end_char': end,
            'start_line': text.count('\n', 0, start) + 1,
            'end_line': text.count('\n', 0, end - 1) + 1,
            'quote': quote, 'quote_hash': hashlib.sha256(quote.encode('utf-8')).hexdigest()}


def extract_dialogue_candidates(text):
    """Retrieve maximal >=4-utterance chains. This is not defect detection.

    Offsets refer to the decoded source (universal newlines at the reader).
    The 80 non-whitespace character bridge is versioned retrieval provenance,
    not a requirement to add narration or thoughts at any fixed frequency.
    """
    closes = {'「': '」', '『': '』'}
    stack, utterances = [], []
    start = None
    for offset, char in enumerate(text):
        if char in closes:
            if not stack:
                start = offset
            stack.append(closes[char])
        elif char in ('」', '』'):
            if not stack or char != stack[-1]:
                stack, start = [], None
                continue
            stack.pop()
            if not stack:
                utterances.append(source_span(text, start, offset + 1))
                start = None
    candidates, chain, links = [], [], []

    def emit():
        if len(chain) < 4:
            return
        span = source_span(text, chain[0]['start_char'], chain[-1]['end_char'])
        identity = {'extractor_version': DIALOGUE_EXTRACTOR_VERSION,
                    'start_char': span['start_char'], 'end_char': span['end_char'],
                    'quote_hash': span['quote_hash']}
        candidates.append({'candidate_id': 'd-' + dialogue_digest(identity), 'span': span,
                           'utterances': list(chain), 'link_kinds': list(links),
                           'kind': links[0] if len(set(links)) == 1 else 'mixed'})

    for utterance in utterances:
        if chain:
            gap = text[chain[-1]['end_char']:utterance['start_char']]
            nonspace = ''.join(gap.split())
            if len(nonspace) <= 80 and not any(c in gap for c in '「」『』'):
                links.append('direct' if not nonspace else 'short_narration')
            else:
                emit()
                chain, links = [], []
        chain.append(utterance)
    emit()
    return candidates
