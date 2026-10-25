"""Evidence gate tests: counts retrieve candidates, they never diagnose prose."""
import copy
import hashlib
import json

import pytest

from novel_agent import text_quality
from novel_agent.approvals import approve_scene, validate_approval_current
from novel_agent.errors import UserFacingError, DataCorruptionError
from novel_agent.storage import text_content_hash
from test_approval_identity import setup_checked

TEXT = '前文。\n「どこへ」\n「城へ」\n彼女はうなずいた。\n「なぜ」\n「門を閉じるため」\n後文。'


def extraction(text):
    assert hasattr(text_quality, 'extract_dialogue_candidates'), 'source-bound candidate extractor is missing'
    return text_quality.extract_dialogue_candidates(text)


def module():
    from novel_agent import dialogue_review
    return dialogue_review


def checked(tmp_path, text=TEXT, status='pass'):
    path, report_path = setup_checked(tmp_path, status)
    path.write_text(text, encoding='utf-8')
    report = json.loads(report_path.read_text())
    report['source_hash'] = text_content_hash(str(path))
    report_path.write_text(json.dumps(report), encoding='utf-8')
    return path, report_path, report


def template(tmp_path, report):
    from prompt_utils import parse_scene_reference, find_scene_file
    ref = parse_scene_reference('1-1')
    return module().build_review_template(str(tmp_path), ref, find_scene_file(str(tmp_path), ref), report)


def fill(payload, judgment='keep'):
    for d in payload['decisions']:
        d.update(judgment=judgment, reason='情報問答の圧縮は不要。この応酬は互いに答えを渋る対立を示す。',
                 reader_effect='選択的な視点の受け止めは台詞の言い直しで伝わり、別途心理を足すと間が鈍る。',
                 next_action='' if judgment == 'keep' else '説明の反復を間接叙述に圧縮する。')
    return payload


def record(tmp_path, payload):
    return module().record_dialogue_review(str(tmp_path), '1-1', payload, reviewer_type='agent', reviewer_id='test-reviewer')


def test_extracts_maximal_source_bound_four_utterance_chain():
    cs = extraction(TEXT)
    assert len(cs) == 1
    c = cs[0]
    assert c['kind'] == 'mixed'
    assert c['link_kinds'] == ['direct', 'short_narration', 'direct']
    assert len(c['utterances']) == 4
    assert c['span']['start_char'] == 4
    assert c['span']['end_char'] == len(TEXT) - 4
    assert c['span']['start_line'] == 2 and c['span']['end_line'] == 6
    assert c['span']['quote'] == TEXT[4:-4]
    assert c['span']['quote_hash'] == hashlib.sha256(TEXT[4:-4].encode()).hexdigest()
    assert len(c['candidate_id']) == 66


@pytest.mark.parametrize('text,count', [
    ('「一」「二」「三」', 0),
    ('「一」「二」「三」「四」', 1),
    ('「一」\n\n　「二」\n「『内』三」\n「四」', 1),
    ('「一」「二」' + '地' * 81 + '「三」「四」', 0),
    ('「一」「二」' + '地' * 80 + '「三」「四」', 1),
    ('「一」「二」「三」「四」' + '地' * 81 + '「一」「二」「三」「四」', 2),
    ('「不閉\n「一」「二」「三」「四」', 0),
])
def test_retrieval_thresholds_nesting_and_no_question_mark_requirement(text, count):
    cs = extraction(text)
    assert len(cs) == count
    for a, b in zip(cs, cs[1:]):
        assert a['span']['end_char'] <= b['span']['start_char']
        assert a['candidate_id'] != b['candidate_id']


def test_missing_review_blocks_even_legacy_check_and_warning_override(tmp_path):
    checked(tmp_path, status='warning')
    with pytest.raises(UserFacingError, match='review_scene_dialogue'):
        approve_scene(str(tmp_path), '1-1', allow_warnings=True)
    assert not (tmp_path / 'runtime/approval_ledger.json').exists()


def test_empty_template_does_not_record_and_keep_snapshot_survives_sidecar_loss(tmp_path):
    _, _, report = checked(tmp_path)
    payload = template(tmp_path, report)
    with pytest.raises(UserFacingError):
        record(tmp_path, payload)
    assert not (tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json').exists()
    accepted = record(tmp_path, fill(payload))
    approved = approve_scene(str(tmp_path), '1-1')
    assert approved['dialogue_review']['review_id'] == accepted['review_id']
    (tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json').unlink()
    assert validate_approval_current(str(tmp_path), approved)['status'] == 'approved'


@pytest.mark.parametrize('mutation', ['omit', 'duplicate', 'unknown', 'quote', 'offset', 'line', 'hash', 'placeholder', 'source', 'policy', 'path', 'extractor'])
def test_incomplete_or_wrong_evidence_never_writes(tmp_path, mutation):
    _, _, report = checked(tmp_path)
    p = fill(template(tmp_path, report))
    if mutation == 'omit': p['decisions'] = []
    elif mutation == 'duplicate': p['decisions'].append(copy.deepcopy(p['decisions'][0]))
    elif mutation == 'unknown': p['decisions'][0]['candidate_id'] = 'd-unknown'
    elif mutation in ('quote', 'offset', 'line', 'hash'):
        e = p['decisions'][0]['evidence'][0]
        key, value = {'quote': ('quote', 'invented'), 'offset': ('start_char', True), 'line': ('start_line', 50), 'hash': ('quote_hash', '0' * 64)}[mutation]
        e[key] = value
    elif mutation == 'placeholder': p['decisions'][0]['reason'] = 'TODO'
    elif mutation == 'source': p['source_hash'] = '0' * 64
    elif mutation == 'policy': p['check_inputs_digest'] = '0' * 64
    elif mutation == 'path': p['source_path'] = 'other.txt'
    elif mutation == 'extractor': p['extractor_version'] = 'future'
    with pytest.raises(UserFacingError): record(tmp_path, p)
    assert not (tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json').exists()


@pytest.mark.parametrize('judgment', ['revise', 'uncertain'])
def test_nonkeep_review_records_but_never_approves(tmp_path, judgment):
    _, _, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report), judgment))
    with pytest.raises(UserFacingError, match='revise|uncertain'):
        approve_scene(str(tmp_path), '1-1', allow_warnings=True)


def test_rewrite_removing_all_candidates_still_requires_exact_comparison(tmp_path):
    path, report_path, report = checked(tmp_path)
    before = record(tmp_path, fill(template(tmp_path, report), 'revise'))
    path.write_text('城へ向かい、門を閉じる事情を聞いた。', encoding='utf-8')
    report['source_hash'] = text_content_hash(str(path))
    report_path.write_text(json.dumps(report))
    with pytest.raises(UserFacingError, match='review_scene_dialogue'):
        approve_scene(str(tmp_path), '1-1')
    p = template(tmp_path, report)
    assert p['previous_review_id'] == before['review_id']
    assert len(p['comparisons']) == 1
    with pytest.raises(UserFacingError): record(tmp_path, p)
    p['comparisons'][0].update(after=module().source_span(path.read_text(), 0, len(path.read_text())),
        change_type='compressed_information', judgment='keep', reason='反復する行先と目的の問答を一文に圧縮した。',
        reader_effect='情報は維持し、視点の受け止めが必要でない定型説明の往復を減らした。')
    record(tmp_path, p)
    approved = approve_scene(str(tmp_path), '1-1')
    assert validate_approval_current(str(tmp_path), approved)['status'] == 'approved'


def test_false_contract_rejected_and_historical_v2_not_retroactively_gated(tmp_path):
    _, report_path, report = checked(tmp_path)
    historical = dict(report, status='approved')
    assert validate_approval_current(str(tmp_path), historical)['status'] == 'approved'
    report['dialogue_review_contract'] = dict(module().build_dialogue_contract(TEXT, scene_bound=True), candidates=[], review_required=False)
    report_path.write_text(json.dumps(report))
    with pytest.raises(UserFacingError, match='contract'):
        approve_scene(str(tmp_path), '1-1')


def test_resolved_compression_is_embedded_not_dropped_when_no_current_candidates(tmp_path):
    path, rp, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report), 'revise'))
    text = '目的を確認し、城の門へ向かった。'
    path.write_text(text)
    report['source_hash'] = text_content_hash(str(path)); rp.write_text(json.dumps(report))
    p = template(tmp_path, report)
    p['comparisons'][0].update(after=module().source_span(text, 0, len(text)), judgment='keep',
        change_type='compressed_information', reason='説明問答を目的の確認としてまとめた。', reader_effect='間接叙述で情報を保つ。受け止めを足す局面ではない。')
    resolved = record(tmp_path, p)
    approved = approve_scene(str(tmp_path), '1-1')
    assert approved.get('dialogue_review_digest') == resolved['review_id']
    assert approved.get('dialogue_review_baseline', {}).get('decisions', [{}])[0]['judgment'] == 'revise'


def test_external_editor_between_review_validation_and_approval_write_is_rejected(tmp_path, monkeypatch):
    path, _, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report)))
    original = module().require_dialogue_review
    def edit_after_review(*args):
        result = original(*args)
        path.write_text(TEXT + '外部変更。')
        return result
    monkeypatch.setattr(module(), 'require_dialogue_review', edit_after_review)
    with pytest.raises(UserFacingError, match='changed'):
        approve_scene(str(tmp_path), '1-1')
    assert not (tmp_path / 'runtime/approval_ledger.json').exists()


def test_crlf_reader_and_stale_review_bindings(tmp_path):
    path, rp, report = checked(tmp_path)
    path.write_bytes(TEXT.replace('\n', '\r\n').encode())
    report['source_hash'] = text_content_hash(str(path)); rp.write_text(json.dumps(report))
    p = template(tmp_path, report)
    assert p['candidates'][0]['span']['quote'] == TEXT[4:-4]
    record(tmp_path, fill(p))
    path.write_text(TEXT + '変更。')
    report['source_hash'] = text_content_hash(str(path)); rp.write_text(json.dumps(report))
    with pytest.raises(UserFacingError, match='review_scene_dialogue'):
        approve_scene(str(tmp_path), '1-1')


@pytest.mark.parametrize('pipeline', [False, True])
def test_real_review_cli_template_submit_approve_export_and_stale_refusal(tmp_path, pipeline):
    from pathlib import Path
    import subprocess
    import sys
    project = tmp_path / '作品'
    project.mkdir()
    path, rp, report = checked(project)
    # Custom runtime is scene-verified and need not match a global latest.
    custom = project / 'custom-runtime'
    rp.parent.rename(custom)
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    def run(name, *args):
        return subprocess.run([sys.executable, str(scripts / name), *args], capture_output=True, text=True)
    output = project / 'review.json'
    prefix = ['review-dialogue'] if pipeline else []
    cli = 'run_scene_pipeline.py' if pipeline else 'review_scene_dialogue.py'
    base = prefix + ['--project', str(project), '--scene', '1-1', '--runtime_dir', str(custom)]
    result = run(cli, *base, '--output', str(output))
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'template' in result.stdout.lower()
    result = run(cli, *base, '--input', str(output), '--reviewer-type', 'automation', '--reviewer-id', 'fixture-not-literary-review')
    assert result.returncode != 0
    output.write_text(json.dumps(fill(json.loads(output.read_text())), ensure_ascii=False))
    result = run(cli, *base, '--input', str(output), '--reviewer-type', 'automation', '--reviewer-id', 'fixture-not-literary-review')
    assert result.returncode == 0, result.stdout + result.stderr
    result = run('approve_scene.py', '--project', str(project), '--scene', '1-1', '--runtime_dir', str(custom), '--reviewer-type', 'automation', '--reviewer-id', 'fixture-not-literary-review', '--allow-warnings')
    assert result.returncode == 0, result.stdout + result.stderr
    exported = project / 'export.md'
    result = run('export_manuscript.py', '--project', str(project), '--output', str(exported))
    assert result.returncode == 0, result.stdout + result.stderr
    assert TEXT in exported.read_text()
    path.write_text(TEXT + '改稿。')
    result = run('export_manuscript.py', '--project', str(project), '--output', str(project / 'stale.md'))
    assert result.returncode != 0
    assert not (project / 'stale.md').exists()


def test_actual_check_exposes_advisory_candidates_without_changing_mechanical_status(tmp_path):
    from pathlib import Path
    import subprocess
    import sys
    text = tmp_path / 'standalone.txt'; text.write_text(TEXT)
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    result = subprocess.run([sys.executable, str(scripts / 'check_scene_output.py'), '--project', str(tmp_path), '--text', str(text), '--min_chars', '1', '--target_chars', '40', '--max_chars', '200'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / 'runtime/check_report.json').read_text())
    assert report['dialogue_review_contract']['review_required'] is False
    assert len(report['dialogue_review_contract']['candidates']) == 1
    assert not any('dialogue_review' == issue.get('type') for issue in report['blocking_issues'])


@pytest.mark.parametrize('field,value', [('reviewer_type', 'unknown'), ('reviewer_id', ''), ('reviewer_id', 'TODO')])
def test_invalid_new_reviewer_never_records(tmp_path, field, value):
    _, _, report = checked(tmp_path)
    attribution = {'reviewer_type': 'agent', 'reviewer_id': 'valid'}; attribution[field] = value
    with pytest.raises(UserFacingError):
        module().record_dialogue_review(str(tmp_path), '1-1', fill(template(tmp_path, report)), **attribution)
    assert not (tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json').exists()


@pytest.mark.parametrize('field,value', [('candidate_id', []), ('judgment', []), ('evidence', {}), ('reason', {}), ('reader_effect', []), ('next_action', None)])
def test_malformed_decision_is_actionable_not_a_crash(tmp_path, field, value):
    _, _, report = checked(tmp_path)
    p = fill(template(tmp_path, report)); p['decisions'][0][field] = value
    with pytest.raises(UserFacingError): record(tmp_path, p)


def test_corrupt_explicit_ledger_is_not_treated_as_missing(tmp_path):
    _, _, report = checked(tmp_path)
    accepted = record(tmp_path, fill(template(tmp_path, report)))
    ledger = tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json'
    data = json.loads(ledger.read_text()); data['records'][0]['decisions'][0]['candidate_id'] = []
    # A recomputed hash cannot make a broken historical schema usable.
    broken = data['records'][0]
    broken['review_id'] = module().dialogue_digest({k:v for k,v in broken.items() if k != 'review_id'})
    ledger.write_text(json.dumps(data))
    before = ledger.read_bytes()
    with pytest.raises(DataCorruptionError):
        approve_scene(str(tmp_path), '1-1')
    assert ledger.read_bytes() == before


def test_unknown_contract_or_missing_saved_review_fails_closed(tmp_path):
    _, rp, report = checked(tmp_path)
    report['dialogue_review_contract'] = module().build_dialogue_contract(TEXT, scene_bound=True)
    report['dialogue_review_contract']['extractor_version'] = 'unknown'
    rp.write_text(json.dumps(report))
    with pytest.raises(UserFacingError): approve_scene(str(tmp_path), '1-1')
    historical = {k:v for k,v in report.items() if k != 'dialogue_review_contract'}
    historical.update(status='approved', dialogue_review_contract=module().build_dialogue_contract(TEXT, scene_bound=True))
    assert validate_approval_current(str(tmp_path), historical)['status'] == 'stale'


def test_multiple_nonkeep_comparisons_remain_resolvable_without_recursive_records(tmp_path):
    path, rp, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report), 'revise'))
    text = '事情を聞いて城へ向かった。'; path.write_text(text)
    report['source_hash'] = text_content_hash(str(path)); rp.write_text(json.dumps(report))
    p = template(tmp_path, report)
    p['comparisons'][0].update(after=module().source_span(text, 0, len(text)), judgment='uncertain',
        reason='行先の説明は圧縮したが、目的が落ちた。', reader_effect='目的がわからず、圧縮の効果を評価できない。')
    record(tmp_path, p)
    with pytest.raises(UserFacingError): approve_scene(str(tmp_path), '1-1')
    p = template(tmp_path, report)
    assert len(p['comparisons']) == 1
    assert p['comparisons'][0]['before']['quote'] == text
    p['comparisons'][0].update(after=module().source_span(text, 0, len(text)), judgment='keep', change_type='retained_pace',
        reason='再考。目的は直前の段落にあり、この情報の省略を保持する。', reader_effect='説明を重ねず移動へ進める。視点の受け止めはここでは不要。')
    record(tmp_path, p)
    approved = approve_scene(str(tmp_path), '1-1')
    assert validate_approval_current(str(tmp_path), approved)['status'] == 'approved'


def test_same_source_pending_review_does_not_revoke_saved_approval(tmp_path):
    _, _, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report)))
    approved = approve_scene(str(tmp_path), '1-1')
    record(tmp_path, fill(template(tmp_path, report), 'uncertain'))
    assert validate_approval_current(str(tmp_path), approved)['status'] == 'approved'
    with pytest.raises(UserFacingError): approve_scene(str(tmp_path), '1-1')


def test_wrong_before_and_invented_after_never_append(tmp_path):
    path, rp, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report), 'revise'))
    text = '城へ向かう理由を聞いた。'; path.write_text(text)
    report['source_hash'] = text_content_hash(str(path)); rp.write_text(json.dumps(report))
    good = template(tmp_path, report)
    good['comparisons'][0].update(after=module().source_span(text, 0, len(text)), judgment='keep',
        reason='情報の重複をまとめた。', reader_effect='受け止めの追加は不要で、移動の速度を保つ。')
    ledger = tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json'; before = ledger.read_bytes()
    for mutation in ('before', 'after', 'omit'):
        p = copy.deepcopy(good)
        if mutation == 'before': p['comparisons'][0]['before']['quote'] = '偽物'
        elif mutation == 'after': p['comparisons'][0]['after']['quote'] = '偽物'
        else: p['comparisons'] = []
        with pytest.raises(UserFacingError): record(tmp_path, p)
        assert ledger.read_bytes() == before


def test_approval_baseline_must_match_its_outer_source_binding(tmp_path):
    _, _, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report)))
    approve_scene(str(tmp_path), '1-1')
    path = tmp_path / 'runtime/approval_ledger.json'
    ledger = json.loads(path.read_text())
    approval = ledger['scenes']['1-1']; review = approval['dialogue_review']
    review['source_hash'] = '0' * 64
    review['review_id'] = module().dialogue_digest({k:v for k,v in review.items() if k != 'review_id'})
    approval['dialogue_review_digest'] = review['review_id']
    path.write_text(json.dumps(ledger))
    (tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json').unlink()
    with pytest.raises(UserFacingError, match='binding|mismatch'):
        template(tmp_path, report)


@pytest.mark.parametrize('version', [1, 2])
def test_historical_candidate_approval_read_and_export_is_byte_preserving(tmp_path, version):
    from novel_agent.approvals import read_approval_ledger
    from novel_agent.exports import export_manuscript
    path, _, report = checked(tmp_path)
    old = dict(report, status='approved', check_status='pass', scene_path=path.name, content_hash=text_content_hash(str(path))) if version == 2 else {
        'version': 1, 'status': 'approved', 'scene_path': path.name, 'content_hash': text_content_hash(str(path)), 'check_status': 'pass'}
    ledger = tmp_path / 'runtime/approval_ledger.json'; ledger.write_text(json.dumps({'version': 1, 'scenes': {'1-1': old}}))
    before = ledger.read_bytes()
    saved = read_approval_ledger(str(tmp_path))['scenes']['1-1']
    assert validate_approval_current(str(tmp_path), saved)['status'] == 'approved'
    assert export_manuscript(str(tmp_path))['scenes'] == ['1-1']
    assert ledger.read_bytes() == before
    with pytest.raises(UserFacingError, match='review_scene_dialogue'):
        approve_scene(str(tmp_path), '1-1', allow_warnings=True)


@pytest.mark.parametrize('prefix', ['『', '「', '』', '」'])
def test_orphan_quote_prefix_blocks_real_check_and_new_approval(tmp_path, prefix):
    from pathlib import Path
    import subprocess
    import sys
    from test_trial_cli_findings import write_outline
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    project = tmp_path / 'novel'
    def run(script, *args):
        result = subprocess.run([sys.executable, str(scripts / script), *map(str, args)], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result
    run('init_project.py', project, '--target-total-chars', '30000')
    state = project / 'agent/state_schema_novel.yaml'
    state.write_text(state.read_text().replace('planning_gate_enabled: true', 'planning_gate_enabled: false'))
    write_outline(project, ['1-1'])
    outline = project / '05_chapter_outline.md'
    outline.write_text(outline.read_text().replace('| 1000 | 1250 | 1500 |', '| 1 | 50 | 500 |'))
    source = project / 'scene_1-1.txt'; source.write_text(prefix + TEXT)
    run('run_scene_pipeline.py', 'prepare', '--project', project, '--chapter', '1', '--scene', '1-1')
    run('run_scene_pipeline.py', 'check', '--project', project, '--text', source)
    report = json.loads((project / 'runtime/scenes/1-1/draft/check_report.json').read_text())
    assert report['status'] == 'fail'
    assert 'unclosed_dialogue_detected' in report['format_violations']
    result = subprocess.run([sys.executable, str(scripts / 'approve_scene.py'), '--project', str(project), '--scene', '1-1', '--allow-warnings', '--reviewer-type', 'agent', '--reviewer-id', 'quote-regression'], capture_output=True, text=True)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (project / 'runtime/approval_ledger.json').exists()


@pytest.mark.parametrize('text,invalid', [
    ('「外に『中』がある」\n「次」', False),
    ('『外に「中」がある』\r\n「次」', False),
    ('「改行\nする台詞」', False),
    ('『改行\r\nする台詞』', False),
    ('「外『内」』', True),
    ('」「', True),
    ('』『', True),
    ('『閉じない', True),
])
def test_quote_balance_validates_both_styles_order_and_nesting(text, invalid):
    violations, _ = text_quality.collect_format_violations(text)
    assert ('unclosed_dialogue_detected' in violations) == invalid


def test_saved_explicit_review_contract_cannot_be_removed(tmp_path):
    _, _, report = checked(tmp_path)
    record(tmp_path, fill(template(tmp_path, report)))
    approved = approve_scene(str(tmp_path), '1-1')
    del approved['dialogue_review_contract']
    assert validate_approval_current(str(tmp_path), approved)['status'] == 'stale'


def test_health_rejects_schema_corrupt_dialogue_sidecar_without_mutating_it(tmp_path):
    from pathlib import Path
    import subprocess
    import sys
    from test_trial_cli_findings import write_outline
    write_outline(tmp_path, [])
    target = tmp_path / 'runtime/scenes/1-1/dialogue_review_ledger.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({'version': 1, 'scene_id': '1-1', 'records': 'BROKEN'}))
    before = target.read_bytes()
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    result = subprocess.run([sys.executable, str(scripts / 'sync_project_health.py'), '--project', str(tmp_path), '--json', '--fix-safe'], capture_output=True, text=True)
    report = json.loads(result.stdout)
    assert result.returncode != 0
    assert report['status'] == 'fail'
    assert any(i['type'] == 'data_corruption' and i['path'] == str(target) for i in report['blocking_issues'])
    assert target.read_bytes() == before


@pytest.mark.parametrize('with_contract', [False, True])
def test_old_v2_pass_cannot_waive_new_approval_quote_balance(tmp_path, with_contract):
    """Old check fixture uses real source/policy hashes, not changed conditions.

    A pre-fix checker could pass this malformed alternate quote. The current
    creation boundary must reject that still-current check, without rewriting
    or retroactively revoking the saved historical approval.
    """
    from novel_agent.approvals import validate_check_identity, read_approval_ledger
    from novel_agent.exports import export_manuscript
    from prompt_utils import parse_scene_reference
    text = '『' + TEXT
    path, rp, report = checked(tmp_path, text)
    if with_contract:
        report['dialogue_review_contract'] = module().build_dialogue_contract(text, scene_bound=True)
        assert report['dialogue_review_contract']['review_required'] is False
    rp.write_text(json.dumps(report))
    validate_check_identity(str(tmp_path), parse_scene_reference('1-1'), str(path), report)
    historical = dict(report, status='approved', check_status='pass', scene_path=path.name,
                      content_hash=report['source_hash'])
    ledger = tmp_path / 'runtime/approval_ledger.json'
    ledger.write_text(json.dumps({'version': 1, 'scenes': {'1-1': historical}}))
    before = ledger.read_bytes()
    assert validate_approval_current(str(tmp_path), historical)['status'] == 'approved'
    with pytest.raises(UserFacingError, match='quote|recheck'):
        approve_scene(str(tmp_path), '1-1', allow_warnings=True,
                      reviewer_type='automation', reviewer_id='old-check-regression')
    assert ledger.read_bytes() == before
    assert read_approval_ledger(str(tmp_path))['scenes']['1-1']['status'] == 'approved'
    assert export_manuscript(str(tmp_path))['scenes'] == ['1-1']
    assert ledger.read_bytes() == before
