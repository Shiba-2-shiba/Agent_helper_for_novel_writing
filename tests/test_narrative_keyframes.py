import copy
import json

import pytest

from novel_agent.errors import UserFacingError
from novel_agent.narrative_keyframes import (resolve_keyframing_policy, keyframing_policy_value,
    build_keyframe_contract, validate_keyframe_proposal, render_keyframes)
from helpers.keyframe_fixtures import valid_proposal, request_fixture, scene_omission_proposal


def write_config(tmp_path, value):
    (tmp_path / 'narrative_keyframing.json').write_text(json.dumps(value), encoding='utf-8')


def test_default_on_and_deterministic_contract(tmp_path):
    policy = resolve_keyframing_policy(str(tmp_path), scene_id='1-1')
    assert policy['enabled'] is True and policy['source'] == 'default'
    contract = build_keyframe_contract(scene_id='1-1', pov_character_id=None, policy=policy)
    assert contract['status'] == 'needs_pov'
    assert contract == build_keyframe_contract(scene_id='1-1', pov_character_id=None, policy=policy)


def test_policy_precedence_and_scope(tmp_path):
    write_config(tmp_path, {'version': 1, 'enabled': False, 'disable_reason': '外的な記録のみ。',
                            'scenes': {'1-1': {'enabled': True}}})
    assert resolve_keyframing_policy(str(tmp_path), scene_id='1-1')['enabled'] is True
    assert resolve_keyframing_policy(str(tmp_path), scene_id='1-2')['enabled'] is False
    assert resolve_keyframing_policy(str(tmp_path), scene_id='1-1', enabled_override=False, disable_reason='視点のない年表。')['source'] == 'cli'
    before = keyframing_policy_value(str(tmp_path), scene_id='1-1')
    config = json.loads((tmp_path / 'narrative_keyframing.json').read_text())
    config['scenes']['9-9'] = {'enabled': False, 'disable_reason': '外的記録のみ。'}
    write_config(tmp_path, config)
    assert before == keyframing_policy_value(str(tmp_path), scene_id='1-1')


@pytest.mark.parametrize('kwargs', [
    {'enabled_override': False}, {'disable_reason': '理由だけ'},
    {'enabled_override': False, 'disable_reason': 'TODO'},
    {'enabled_override': True, 'disable_reason': '有効時は無用'}, {'enabled_override': 1}])
def test_explicit_off_requires_reason(tmp_path, kwargs):
    with pytest.raises(UserFacingError):
        resolve_keyframing_policy(str(tmp_path), scene_id='1-1', **kwargs)


@pytest.mark.parametrize('config', [{'version': True}, {'version': 2}, {'enabled': 1},
    {'version': 1, 'unknown': True}, {'version': 1, 'scenes': []},
    {'version': 1, 'scenes': {'1-1': {'unknown': True}}}, {'version': 1, 'enabled': False}])
def test_config_strict(tmp_path, config):
    write_config(tmp_path, config)
    with pytest.raises(UserFacingError):
        resolve_keyframing_policy(str(tmp_path), scene_id='1-1')


@pytest.mark.parametrize('realization', ['dialogue', 'narration', 'both', 'omit'])
def test_valid_proposal_and_no_mutation(realization):
    proposal = valid_proposal(realization=realization)
    before = copy.deepcopy(proposal)
    result = validate_keyframe_proposal(proposal, request=request_fixture())
    assert result == before and result is not proposal
    assert result['keyframes'][0]['realization'] == realization
    rendered = render_keyframes(result)
    assert '創作提案' in rendered and '相手の内心の事実ではない' in rendered
    assert proposal == before


@pytest.mark.parametrize('route', ['dialogue_reason', 'narration_reason'])
@pytest.mark.parametrize('reason', ['', 'TODO', '未記入', 'TBD'])
def test_omit_requires_both_routes(route, reason):
    proposal = valid_proposal(realization='omit')
    proposal['keyframes'][0]['omission'][route] = reason
    with pytest.raises(UserFacingError):
        validate_keyframe_proposal(proposal, request=request_fixture())


def test_empty_is_not_skip():
    proposal = valid_proposal()
    proposal['keyframes'] = []
    with pytest.raises(UserFacingError):
        validate_keyframe_proposal(proposal, request=request_fixture())


def test_scene_omission_requires_anchor_sources_and_both_routes():
    proposal = scene_omission_proposal()
    assert validate_keyframe_proposal(proposal, request=request_fixture()) == proposal
    for key in ['considered_anchor', 'source_refs', 'dialogue_reason', 'narration_reason']:
        invalid = copy.deepcopy(proposal)
        invalid['scene_omission'][key] = [] if key == 'source_refs' else ''
        with pytest.raises(UserFacingError):
            validate_keyframe_proposal(invalid, request=request_fixture())


@pytest.mark.parametrize('mutation', ['over_count', 'over_text', 'unknown_source', 'duplicate_source', 'duplicate_id',
    'unknown_key', 'bool_version', 'non_string', 'bad_id', 'omit_without_reason', 'normal_with_omission', 'wrong_scene', 'wrong_pov', 'old_generation'])
def test_strict_limits(mutation):
    p = valid_proposal()
    k = p['keyframes'][0]
    if mutation == 'over_count': p['keyframes'] *= 4
    elif mutation == 'over_text': k['anchor'] = 'あ' * 241
    elif mutation == 'unknown_source': k['source_refs'] = ['future']
    elif mutation == 'duplicate_source': k['source_refs'] *= 2
    elif mutation == 'duplicate_id': p['keyframes'] *= 2
    elif mutation == 'unknown_key': k['facts'] = []
    elif mutation == 'bool_version': p['version'] = True
    elif mutation == 'non_string': k['perception'] = 7
    elif mutation == 'bad_id': k['id'] = 'kf 1'
    elif mutation == 'omit_without_reason': k['realization'] = 'omit'
    elif mutation == 'normal_with_omission': k['omission'] = {'category': 'redundant'}
    elif mutation == 'wrong_scene': p['scene_id'] = '1-2'
    elif mutation == 'wrong_pov': p['pov_character_id'] = 'other'
    elif mutation == 'old_generation': p['generation_id'] = 'old'
    with pytest.raises(UserFacingError):
        validate_keyframe_proposal(p, request=request_fixture())


def test_render_budget_is_explicit_not_truncation():
    p = valid_proposal()
    p['keyframes'] = [dict(copy.deepcopy(p['keyframes'][0]), id='kf{}'.format(i)) for i in range(1, 4)]
    for k in p['keyframes']:
        for field in ['anchor', 'selection_reason', 'perception', 'interpretation', 'response', 'realization_note']:
            k[field] = 'あ' * 240
    with pytest.raises(UserFacingError, match='3000'):
        render_keyframes(p)


def test_no_semantic_promotion(tmp_path):
    body = tmp_path / 'scene_1-1.txt'
    memory = tmp_path / 'accepted.json'
    body.write_text('既存本文', encoding='utf-8'); memory.write_text('{}', encoding='utf-8')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    render_keyframes(validate_keyframe_proposal(valid_proposal(), request=request_fixture()))
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
