"""Source-bound, evidence-complete dialogue reviews; no literary classifier.

The sidecar is a flat append-only list of validated snapshots. Hashes bind
coverage and source evidence, not reviewer honesty, identity or quality.
"""
import copy
import hashlib
import os

from novel_agent.errors import DataCorruptionError, UserFacingError
from novel_agent.storage import read_json, project_lock, atomic_write_json
from novel_agent.text_quality import (
    DIALOGUE_EXTRACTOR_VERSION, dialogue_digest, extract_dialogue_candidates,
    source_span, detect_unclosed_dialogue,
)
from novel_agent.ledgers import utc_now
from prompt_utils import (
    parse_scene_reference, find_scene_file, read_text_file, runtime_root_dir,
)

HASH_ALGORITHM = 'sha256-utf8-text-v1'
JUDGMENTS = ('keep', 'revise', 'uncertain')
REVIEWER_TYPES = ('human', 'agent', 'automation')
RECORD_KEYS = {'version', 'scene_id', 'source_path', 'source_hash', 'hash_algorithm',
               'check_inputs_digest', 'extractor_version', 'candidate_digest',
               'candidates', 'reviewer_type', 'reviewer_id', 'decisions',
               'previous_review_id', 'comparisons', 'recorded_at', 'review_id'}
BINDING_KEYS = ('scene_id', 'source_path', 'source_hash', 'hash_algorithm', 'check_inputs_digest')


def _fail(message):
    raise UserFacingError('dialogue review: ' + message)


def _text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _nonblank(value, label):
    if (not isinstance(value, str) or not value.strip()
            or value.strip().lower().strip('.:：') in ('todo', 'tbd', 'placeholder', 'n/a', '待記入', '未記入')):
        _fail(label + ' must be a specific nonblank explanation (not a placeholder)')


def _exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail('invalid ' + label + ' schema')


def validate_span(text, span, container=None):
    _exact_keys(span, ('start_char', 'end_char', 'start_line', 'end_line', 'quote', 'quote_hash'), 'span')
    start, end = span['start_char'], span['end_char']
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
            or type(span['start_line']) is not int or type(span['end_line']) is not int):
        _fail('invalid evidence range')
    if span != source_span(text, start, end):
        _fail('evidence quote, hash or line numbers do not match exact source')
    if container and not container['start_char'] <= start < end <= container['end_char']:
        _fail('evidence is not contained in its candidate')


def build_dialogue_contract(text, *, scene_bound, unresolved=False):
    candidates = extract_dialogue_candidates(text)
    return {'version': 1, 'extractor_version': DIALOGUE_EXTRACTOR_VERSION,
            'candidate_digest': dialogue_digest({'extractor_version': DIALOGUE_EXTRACTOR_VERSION,
                                                 'candidates': candidates}),
            'candidates': candidates, 'review_required': bool(scene_bound and (candidates or unresolved))}


def dialogue_review_ledger_path(project_dir, scene_id):
    scene_id = parse_scene_reference(scene_id)['canonical_id']
    return os.path.join(runtime_root_dir(project_dir), 'scenes', scene_id, 'dialogue_review_ledger.json')


def _span_snapshot(span):
    """Validate a captured span without pretending to possess its old source."""
    _exact_keys(span, ('start_char', 'end_char', 'start_line', 'end_line', 'quote', 'quote_hash'), 'span')
    for key in ('start_char', 'end_char', 'start_line', 'end_line'):
        if type(span[key]) is not int:
            _fail('invalid captured span integer')
    if (not isinstance(span['quote'], str) or not span['quote']
            or span['start_char'] < 0 or span['end_char'] - span['start_char'] != len(span['quote'])
            or span['start_line'] < 1
            or span['end_line'] != span['start_line'] + span['quote'][:-1].count('\n')
            or span['quote_hash'] != _text_hash(span['quote'])):
        _fail('invalid captured quote, range, lines or hash')


def _decision_shape(decision):
    _exact_keys(decision, ('candidate_id', 'judgment', 'evidence', 'reason', 'reader_effect', 'next_action'), 'decision')
    if not isinstance(decision['candidate_id'], str) or decision['judgment'] not in JUDGMENTS:
        _fail('invalid decision candidate ID or judgment')
    _nonblank(decision['reason'], 'reason')
    _nonblank(decision['reader_effect'], 'reader_effect')
    if not isinstance(decision['next_action'], str):
        _fail('next_action must be a string')
    if decision['judgment'] != 'keep':
        _nonblank(decision['next_action'], 'next_action')
    if not isinstance(decision['evidence'], list) or not decision['evidence']:
        _fail('nonempty exact evidence required')
    for span in decision['evidence']:
        _span_snapshot(span)


def _record_integrity(record):
    _exact_keys(record, RECORD_KEYS, 'record')
    if type(record['version']) is not int or record['version'] != 1 or record['extractor_version'] != DIALOGUE_EXTRACTOR_VERSION:
        _fail('unsupported review version or extractor')
    if record['hash_algorithm'] != HASH_ALGORITHM:
        _fail('unsupported source hash algorithm')
    if record['reviewer_type'] not in REVIEWER_TYPES:
        _fail('reviewer type must be human, agent, or automation')
    _nonblank(record['reviewer_id'], 'reviewer ID')
    _nonblank(record['recorded_at'], 'record timestamp')
    if not isinstance(record['candidates'], list) or not isinstance(record['decisions'], list) or not isinstance(record['comparisons'], list):
        _fail('candidate, decision and comparison arrays required')
    if record['review_id'] != dialogue_digest({k: v for k, v in record.items() if k != 'review_id'}):
        _fail('record hash mismatch')
    expected = dialogue_digest({'extractor_version': DIALOGUE_EXTRACTOR_VERSION, 'candidates': record['candidates']})
    if record['candidate_digest'] != expected:
        _fail('record candidate digest mismatch')
    for key in ('scene_id', 'source_path', 'source_hash', 'check_inputs_digest'):
        _nonblank(record[key], key)
    if record['previous_review_id'] is not None and not isinstance(record['previous_review_id'], str):
        _fail('invalid previous review ID')
    candidates, last_end = {}, -1
    for candidate in record['candidates']:
        _exact_keys(candidate, ('candidate_id', 'span', 'utterances', 'link_kinds', 'kind'), 'candidate')
        cid = candidate['candidate_id']
        if not isinstance(cid, str) or cid in candidates:
            _fail('invalid captured candidate ID')
        _span_snapshot(candidate['span'])
        if candidate['span']['start_char'] < last_end:
            _fail('overlapping captured candidates')
        last_end = candidate['span']['end_char']
        # Re-extract the captured full candidate and translate local offsets.
        local = extract_dialogue_candidates(candidate['span']['quote'])
        if len(local) != 1 or local[0]['span']['quote'] != candidate['span']['quote']:
            _fail('invalid captured candidate extraction')
        expected_candidate = local[0]
        for span in [expected_candidate['span']] + expected_candidate['utterances']:
            span['start_char'] += candidate['span']['start_char']
            span['end_char'] += candidate['span']['start_char']
            span['start_line'] += candidate['span']['start_line'] - 1
            span['end_line'] += candidate['span']['start_line'] - 1
        span = expected_candidate['span']
        expected_candidate['candidate_id'] = 'd-' + dialogue_digest({
            'extractor_version': DIALOGUE_EXTRACTOR_VERSION, 'start_char': span['start_char'],
            'end_char': span['end_char'], 'quote_hash': span['quote_hash']})
        if candidate != expected_candidate:
            _fail('invalid captured candidate identity or spans')
        candidates[cid] = candidate
    seen = set()
    for decision in record['decisions']:
        _decision_shape(decision)
        cid = decision['candidate_id']
        if cid not in candidates or cid in seen:
            _fail('unknown or duplicate captured decision')
        seen.add(cid)
        container = candidates[cid]['span']
        for span in decision['evidence']:
            start = span['start_char'] - container['start_char']
            end = span['end_char'] - container['start_char']
            if not 0 <= start < end <= len(container['quote']) or container['quote'][start:end] != span['quote']:
                _fail('captured evidence outside candidate')
    if seen != set(candidates):
        _fail('incomplete captured decisions')
    seen = set()
    for comparison in record['comparisons']:
        _exact_keys(comparison, ('before_review_id', 'before_candidate_id', 'before_source_hash', 'before', 'after',
                                'change_type', 'judgment', 'reason', 'reader_effect'), 'comparison')
        cid = comparison['before_candidate_id']
        if not isinstance(cid, str) or cid in seen or comparison['judgment'] not in JUDGMENTS:
            _fail('invalid captured comparison ID or judgment')
        seen.add(cid)
        if comparison['change_type'] not in ('compressed_information', 'pov_reception', 'retained_pace', 'other'):
            _fail('invalid captured comparison change type')
        _nonblank(comparison['before_review_id'], 'before review ID')
        _nonblank(comparison['before_source_hash'], 'before source hash')
        _nonblank(comparison['reason'], 'comparison reason')
        _nonblank(comparison['reader_effect'], 'comparison reader_effect')
        _span_snapshot(comparison['before'])
        _span_snapshot(comparison['after'])


def read_dialogue_review_ledger(project_dir, scene_id):
    scene_id = parse_scene_reference(scene_id)['canonical_id']
    path = dialogue_review_ledger_path(project_dir, scene_id)
    payload = read_json(path, default_factory=lambda: {'version': 1, 'scene_id': scene_id, 'records': []})
    try:
        _exact_keys(payload, ('version', 'scene_id', 'records'), 'ledger')
        if type(payload['version']) is not int or payload['version'] != 1 or payload['scene_id'] != scene_id or not isinstance(payload['records'], list):
            _fail('invalid ledger identity/version')
        seen = set()
        for record in payload['records']:
            _record_integrity(record)
            if record['scene_id'] != scene_id or record['review_id'] in seen:
                _fail('invalid ledger record identity')
            if record['previous_review_id'] is not None and record['previous_review_id'] not in seen:
                # An approval snapshot may restore a missing sidecar baseline.
                # Such baseline records are inserted flat before their successor.
                _fail('missing previous review in ledger')
            seen.add(record['review_id'])
    except (UserFacingError, ValueError, TypeError, KeyError) as exc:
        raise DataCorruptionError('invalid dialogue ledger at {}: {}'.format(path, exc))
    return payload


def _baseline(project_dir, scene_id, ledger):
    latest = ledger['records'][-1] if ledger['records'] else None
    # A saved approval is independent evidence, not dependent on the sidecar.
    from novel_agent.approvals import read_approval_ledger
    approved = read_approval_ledger(project_dir).get('scenes', {}).get(scene_id, {})
    snapshot = approved.get('dialogue_review')
    if snapshot is not None:
        _record_integrity(snapshot)
        if approved.get('dialogue_review_digest') != snapshot['review_id']:
            _fail('approval review snapshot digest mismatch')
        if any(snapshot[key] != approved.get(key) for key in BINDING_KEYS):
            _fail('approval review snapshot binding mismatch')
        if latest is None:
            latest = snapshot
        elif snapshot['review_id'] != latest['review_id']:
            ids = [r['review_id'] for r in ledger['records']]
            if snapshot['review_id'] not in ids:
                _fail('approval review is absent from sidecar history; consistency repair required')
    return latest


def _nonkeep(record):
    return bool(record and any(d.get('judgment') != 'keep' for d in record['decisions'] + record['comparisons']))


def _needed_comparisons(text, baseline):
    if baseline is None:
        return []
    nonkeep = {d['candidate_id'] for d in baseline['decisions'] if d['judgment'] != 'keep'}
    # A nonkeep comparison must remain an obligation, even if its candidate was
    # already removed. Retain its original baseline candidate in the next step.
    needed = []
    for candidate in baseline['candidates']:
        span = candidate['span']
        if (candidate['candidate_id'] in nonkeep
                or text[span['start_char']:span['end_char']] != span['quote']):
            needed.append(candidate)
    known = {c['candidate_id'] for c in needed}
    for comparison in baseline['comparisons']:
        if comparison['judgment'] != 'keep' and comparison['before_candidate_id'] not in known:
            needed.append({'candidate_id': comparison['before_candidate_id'], 'span': comparison['after']})
    return needed


def _bindings(scene_ref, scene_path, project_dir, report):
    return {'scene_id': scene_ref['canonical_id'],
            'source_path': os.path.relpath(scene_path, project_dir).replace(os.sep, '/'),
            'source_hash': report['source_hash'], 'hash_algorithm': HASH_ALGORITHM,
            'check_inputs_digest': report['check_inputs_digest']}


def build_review_template(project_dir, scene_ref, scene_path, check_report):
    from novel_agent.approvals import validate_check_identity
    validate_check_identity(project_dir, scene_ref, scene_path, check_report)
    text = read_text_file(scene_path)
    ledger = read_dialogue_review_ledger(project_dir, scene_ref['canonical_id'])
    baseline = _baseline(project_dir, scene_ref['canonical_id'], ledger)
    contract = build_dialogue_contract(text, scene_bound=True)
    return dict(_bindings(scene_ref, scene_path, project_dir, check_report), version=1,
        extractor_version=DIALOGUE_EXTRACTOR_VERSION, candidate_digest=contract['candidate_digest'],
        candidates=contract['candidates'], previous_review_id=baseline['review_id'] if baseline else None,
        decisions=[{'candidate_id': c['candidate_id'], 'judgment': 'uncertain',
                    'evidence': [copy.deepcopy(c['span'])], 'reason': '', 'reader_effect': '', 'next_action': ''}
                   for c in contract['candidates']],
        comparisons=[{'before_review_id': baseline['review_id'], 'before_candidate_id': c['candidate_id'],
                      'before_source_hash': baseline['source_hash'], 'before': copy.deepcopy(c['span']),
                      'after': None, 'change_type': 'other', 'judgment': 'uncertain', 'reason': '', 'reader_effect': ''}
                     for c in _needed_comparisons(text, baseline)])


def _validate_contract(text, report, unresolved):
    if 'dialogue_review_contract' in report:
        contract = report['dialogue_review_contract']
        expected = build_dialogue_contract(text, scene_bound=report.get('scope') == 'scene', unresolved=unresolved)
        # The check may predate a new review or its resolution. For an empty
        # candidate list, the boolean reflects obligations at check time; the
        # approval gate recomputes obligations rather than trusting that flag.
        if isinstance(contract, dict) and type(contract.get('review_required')) is bool:
            if report.get('scope') == 'scene' and not expected['candidates']:
                expected['review_required'] = contract['review_required']
        if (not isinstance(contract, dict) or contract != expected or type(contract.get('version')) is not int):
            _fail('check dialogue contract does not match source/version')


def validate_dialogue_review(text, check_report, review_record, *, baseline_record=None):
    _record_integrity(review_record)
    for key in BINDING_KEYS:
        if review_record[key] != check_report.get(key):
            _fail('review ' + key + ' is stale or mismatched')
    if _text_hash(text) != review_record['source_hash']:
        _fail('review source is stale; recheck and review again')
    contract = build_dialogue_contract(text, scene_bound=True)
    if review_record['candidates'] != contract['candidates'] or review_record['candidate_digest'] != contract['candidate_digest']:
        _fail('review candidates do not match complete extraction')
    _validate_contract(text, check_report, False)
    candidates = {c['candidate_id']: c for c in contract['candidates']}
    seen = set()
    for decision in review_record['decisions']:
        _exact_keys(decision, ('candidate_id', 'judgment', 'evidence', 'reason', 'reader_effect', 'next_action'), 'decision')
        cid = decision['candidate_id']
        if not isinstance(cid, str) or cid not in candidates or cid in seen:
            _fail('unknown or duplicate candidate decision')
        seen.add(cid)
        if decision['judgment'] not in JUDGMENTS:
            _fail('invalid decision judgment')
        _nonblank(decision['reason'], 'reason')
        _nonblank(decision['reader_effect'], 'reader_effect')
        if not isinstance(decision['next_action'], str):
            _fail('next_action must be a string')
        if decision['judgment'] != 'keep':
            _nonblank(decision['next_action'], 'next_action')
        if not isinstance(decision['evidence'], list) or not decision['evidence']:
            _fail('nonempty exact evidence required for every decision')
        for span in decision['evidence']:
            validate_span(text, span, candidates[cid]['span'])
    if seen != set(candidates):
        _fail('every candidate needs exactly one decision')
    if review_record['previous_review_id'] is None:
        if baseline_record is not None or review_record['comparisons']:
            _fail('unexpected baseline or comparisons')
        return
    if baseline_record is None:
        _fail('previous review evidence unavailable')
    _record_integrity(baseline_record)
    if (review_record['previous_review_id'] != baseline_record['review_id']
            or any(review_record[key] != baseline_record[key] for key in ('scene_id', 'source_path', 'hash_algorithm'))):
        _fail('wrong before review baseline')
    needed = {c['candidate_id']: c for c in _needed_comparisons(text, baseline_record)}
    seen = set()
    for comparison in review_record['comparisons']:
        _exact_keys(comparison, ('before_review_id', 'before_candidate_id', 'before_source_hash', 'before', 'after',
                                'change_type', 'judgment', 'reason', 'reader_effect'), 'comparison')
        cid = comparison['before_candidate_id']
        if cid not in needed or cid in seen:
            _fail('unknown or duplicate before candidate comparison')
        seen.add(cid)
        if (comparison['before_review_id'] != baseline_record['review_id']
                or comparison['before_source_hash'] != baseline_record['source_hash']
                or comparison['before'] != needed[cid]['span']):
            _fail('before evidence does not match stored baseline')
        validate_span(text, comparison['after'])
        if comparison['change_type'] not in ('compressed_information', 'pov_reception', 'retained_pace', 'other') or comparison['judgment'] not in JUDGMENTS:
            _fail('invalid comparison change_type or judgment')
        _nonblank(comparison['reason'], 'comparison reason')
        _nonblank(comparison['reader_effect'], 'comparison reader_effect')
    if seen != set(needed):
        _fail('every changed or unresolved before candidate needs an exact comparison')


def record_dialogue_review(project_dir, scene_raw, review_input, *, reviewer_type, reviewer_id, runtime_dir_arg=''):
    from novel_agent.approvals import validate_check_identity, resolve_check_report_path, _load_check_report
    if reviewer_type not in REVIEWER_TYPES:
        _fail('reviewer type must be human, agent, or automation')
    _nonblank(reviewer_id, 'reviewer ID')
    with project_lock(project_dir):
        ref = parse_scene_reference(scene_raw)
        path = find_scene_file(project_dir, ref)
        if not path:
            _fail('scene text not found')
        report = _load_check_report(resolve_check_report_path(project_dir, ref, runtime_dir_arg))
        validate_check_identity(project_dir, ref, path, report)
        ledger = read_dialogue_review_ledger(project_dir, ref['canonical_id'])
        baseline = _baseline(project_dir, ref['canonical_id'], ledger)
        input_keys = RECORD_KEYS - {'reviewer_type', 'reviewer_id', 'recorded_at', 'review_id'}
        _exact_keys(review_input, input_keys, 'review input')
        record = copy.deepcopy(review_input)
        record.update(reviewer_type=reviewer_type, reviewer_id=reviewer_id.strip(), recorded_at=utc_now())
        record['review_id'] = dialogue_digest(record)
        expected = _bindings(ref, path, project_dir, report)
        if any(record[k] != v for k, v in expected.items()):
            _fail('review source/scene/path/check inputs mismatch')
        if record['previous_review_id'] != (baseline['review_id'] if baseline else None):
            _fail('review baseline changed; emit a new template')
        validate_dialogue_review(read_text_file(path), report, record, baseline_record=baseline)
        validate_check_identity(project_dir, ref, path, report)
        if baseline and not ledger['records']:
            # Restore flat ancestry from a saved approval if sidecar was removed.
            # An ancestor-bearing baseline needs its own captured predecessor.
            if baseline['previous_review_id'] is not None:
                _fail('sidecar ancestry unavailable; restore ledger before recording')
            ledger['records'].append(copy.deepcopy(baseline))
        ledger['records'].append(record)
        atomic_write_json(dialogue_review_ledger_path(project_dir, ref['canonical_id']), ledger)
        return record


def review_baseline_for_record(project_dir, scene_id, record):
    if record['previous_review_id'] is None:
        return None
    for prior in read_dialogue_review_ledger(project_dir, scene_id)['records']:
        if prior['review_id'] == record['previous_review_id']:
            return prior
    _fail('before evidence unavailable in ledger')


def require_dialogue_review(project_dir, scene_ref, scene_path, check_report):
    text = read_text_file(scene_path)
    # New approval must not inherit an old checker's quote-balance blind spot.
    # Do not put this creation guard in validate_approval_current: unchanged
    # historical approvals retain their original mechanical guarantee.
    if detect_unclosed_dialogue(text) is not None:
        _fail('malformed quote balance; repair the source and recheck before new approval')
    ledger = read_dialogue_review_ledger(project_dir, scene_ref['canonical_id'])
    latest = _baseline(project_dir, scene_ref['canonical_id'], ledger)
    _validate_contract(text, check_report, _nonkeep(latest))
    candidates = extract_dialogue_candidates(text)
    changed = bool(latest and (latest['source_hash'] != _text_hash(text)
                              or latest['check_inputs_digest'] != check_report['check_inputs_digest']))
    required = bool(candidates or latest)
    if not required:
        return None
    command = 'python scripts/review_scene_dialogue.py --project {} --scene {}'.format(project_dir, scene_ref['canonical_id'])
    if latest is None or changed:
        _fail('current evidence required; run ' + command)
    baseline = None
    if latest['previous_review_id']:
        baseline = review_baseline_for_record(project_dir, scene_ref['canonical_id'], latest)
    validate_dialogue_review(text, check_report, latest, baseline_record=baseline)
    if _nonkeep(latest):
        _fail('revise/uncertain judgments remain unresolved; run ' + command)
    return copy.deepcopy(latest)


def build_scene_dialogue_contract(project_dir, scene_ref, text):
    """Check-time state is advisory; approval always recomputes the gate."""
    if scene_ref is None:
        return build_dialogue_contract(text, scene_bound=False)
    ledger = read_dialogue_review_ledger(project_dir, scene_ref['canonical_id'])
    latest = _baseline(project_dir, scene_ref['canonical_id'], ledger)
    unresolved = bool(latest and (_nonkeep(latest) or _needed_comparisons(text, latest)))
    return build_dialogue_contract(text, scene_bound=True, unresolved=unresolved)
