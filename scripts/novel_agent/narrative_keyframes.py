"""Strict, side-effect-free contracts for external POV creative proposals.

Structural validation does not certify literary quality or turn interpretation
into canon, accepted memory, or a fact about another character's mind.
"""
import copy
import json
import os
import re
from typing import Optional

from novel_agent.errors import UserFacingError

MAX_PROPOSAL_BYTES = 65536
MAX_RENDER_CHARS = 3000
SOURCE_CATEGORIES = {'planning', 'author_context', 'pov_context', 'continuity', 'voice'}
RULES = ('創作提案（承認済みの過去事実ではない）。解釈は相手の内心の事実ではない。'
         '選んだ要所は主に台詞ににじませる／地の文に出す。省略は同等の通常選択肢ではなく、'
         '両経路が不自然・冗長・テンポを損なう具体的理由がある場合だけ。全発話や心理描写数のノルマにしない。'
         '一人称素材を本文の視点に加工し、返答・語感への暗示的反映でよい。逐語転記を要求しない。'
         '作者用情報・未来の予定をPOVの既知情報にせず、推測をcanon/fact/character_knowledgeへ登録しない。'
         '本文段階で省略に変える場合は両経路の理由をproposalに記し再登録・prompt再生成・再checkする。')


def _object(value, allowed, label, required=None):
    if not isinstance(value, dict) or set(value) - set(allowed) or (set(required or ()) - set(value)):
        raise UserFacingError('invalid {} keys/object'.format(label))
    return value


def _text(value, label, maximum=240):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or re.search(r'TODO|TBD|未記入|要記入', value, re.IGNORECASE)):
        raise UserFacingError('{} must contain specific text (1–{} characters; no TODO/未記入)'.format(label, maximum))
    return value


def _identifier(value, label):
    _text(value, label, 80)
    if any(char.isspace() for char in value):
        raise UserFacingError('{} must not contain whitespace'.format(label))
    return value


def strict_json_loads(text, label='keyframe JSON'):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise UserFacingError('duplicate JSON key in {}: {}'.format(label, key))
            result[key] = value
        return result
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError) as exc:
        raise UserFacingError('invalid {}: {}'.format(label, exc))


def _config_entry(value, label):
    _object(value, ('enabled', 'disable_reason'), label)
    if 'enabled' in value and type(value['enabled']) is not bool:
        raise UserFacingError('{} enabled must be boolean'.format(label))
    reason = value.get('disable_reason', '')
    if not isinstance(reason, str):
        raise UserFacingError('{} disable_reason must be text'.format(label))
    if value.get('enabled') is False:
        _text(reason, label + ' disable_reason')
    elif value.get('enabled') is True and reason:
        raise UserFacingError('{} enabled policy cannot have disable_reason'.format(label))
    elif reason:
        _text(reason, label + ' disable_reason')


def _read_config(project_dir):
    from novel_agent.dependencies import _path
    path, _ = _path(project_dir, 'narrative_keyframing.json')
    if not os.path.exists(path):
        return False, {}
    with open(path, encoding='utf-8') as handle:
        config = strict_json_loads(handle.read(), 'narrative_keyframing.json')
    _object(config, ('version', 'enabled', 'disable_reason', 'scenes'), 'keyframing config', ('version',))
    if type(config['version']) is not int or config['version'] != 1:
        raise UserFacingError('unsupported narrative keyframing config version')
    _config_entry({key: config[key] for key in ('enabled', 'disable_reason') if key in config}, 'project')
    scenes = config.get('scenes', {})
    if not isinstance(scenes, dict):
        raise UserFacingError('keyframing scenes must be an object')
    for key, value in scenes.items():
        if not isinstance(key, str) or not re.fullmatch(r'[1-9]\d*-[1-9]\d*', key):
            raise UserFacingError('invalid keyframing scene ID')
        _config_entry(value, 'scene ' + key)
    return True, config


def resolve_keyframing_policy(project_dir: str, *, scene_id: str,
                              enabled_override: Optional[bool] = None,
                              disable_reason: Optional[str] = None) -> dict:
    if enabled_override is not None and type(enabled_override) is not bool:
        raise UserFacingError('keyframing override must be boolean')
    if disable_reason is not None and enabled_override is not False:
        raise UserFacingError('--keyframing-reason requires --keyframing off')
    if enabled_override is False:
        _text(disable_reason, '--keyframing-reason')
    exists, config = _read_config(project_dir)
    scene = config.get('scenes', {}).get(scene_id, {})
    enabled, reason, source = True, '', 'default'
    for entry, origin in ((config, 'project'), (scene, 'scene')):
        if 'enabled' in entry:
            enabled = entry['enabled']
            reason = entry.get('disable_reason', '')
            source = origin
        elif 'disable_reason' in entry:
            reason = entry['disable_reason']
    if enabled_override is not None:
        enabled, reason, source = enabled_override, disable_reason or '', 'cli'
    if enabled and reason:
        raise UserFacingError('enabled keyframing cannot have disable_reason')
    if not enabled:
        _text(reason, 'disable_reason')
    return {'enabled': enabled, 'disable_reason': reason, 'source': source,
            'enabled_override': enabled_override, 'reason_override': disable_reason,
            'config_exists': exists,
            'project_config': {k: config[k] for k in ('version', 'enabled', 'disable_reason') if k in config},
            'scene_config': copy.deepcopy(scene)}


def keyframing_policy_value(project_dir: str, *, scene_id: str,
                           enabled_override: Optional[bool] = None,
                           disable_reason: Optional[str] = None) -> dict:
    return {'scene_id': scene_id, 'policy': resolve_keyframing_policy(
        project_dir, scene_id=scene_id, enabled_override=enabled_override, disable_reason=disable_reason),
        'source_paths': ['narrative_keyframing.json']}


def build_keyframe_contract(*, scene_id: str, pov_character_id: Optional[str], policy: dict) -> dict:
    _identifier(scene_id, 'scene_id')
    if pov_character_id is not None:
        _identifier(pov_character_id, 'pov_character_id')
    return {'version': 1, 'proposal_version': 1, 'scene_id': scene_id,
            'pov_character_id': pov_character_id, 'policy': copy.deepcopy(policy),
            'status': ('awaiting_keyframes' if pov_character_id else 'needs_pov') if policy['enabled'] else 'disabled',
            'limits': {'keyframes': 3, 'text_chars': 240, 'id_chars': 80,
                       'proposal_bytes': MAX_PROPOSAL_BYTES, 'render_chars': MAX_RENDER_CHARS}}


def _sources(value, request):
    if not isinstance(value, list) or not value:
        raise UserFacingError('source_refs must be a nonempty list')
    for source in value:
        _identifier(source, 'source_ref')
        if source not in request.get('sources', {}):
            raise UserFacingError('unknown/unselected source_ref: ' + source)
    if len(set(value)) != len(value):
        raise UserFacingError('duplicate source_refs')


def _omission(value, *, scene=False, request=None):
    fields = ('category', 'dialogue_reason', 'narration_reason')
    if scene:
        fields += ('considered_anchor', 'source_refs')
    _object(value, fields, 'omission', fields)
    if value['category'] not in ('unnatural', 'redundant', 'tempo_damage'):
        raise UserFacingError('invalid omission category')
    for field in ('dialogue_reason', 'narration_reason'):
        _text(value[field], field)
    if scene:
        _text(value['considered_anchor'], 'considered_anchor')
        _sources(value['source_refs'], request)


def validate_keyframe_proposal(proposal: dict, *, request: dict) -> dict:
    fields = ('version', 'scene_id', 'pov_character_id', 'generation_id', 'keyframes', 'scene_omission')
    _object(proposal, fields, 'proposal', fields)
    if type(proposal['version']) is not int or proposal['version'] != 1:
        raise UserFacingError('unsupported keyframe proposal version')
    for field in ('scene_id', 'pov_character_id', 'generation_id'):
        _identifier(proposal[field], field)
        if proposal[field] != request.get(field):
            raise UserFacingError('keyframe {} mismatch'.format(field))
    frames = proposal['keyframes']
    if not isinstance(frames, list) or len(frames) > 3:
        raise UserFacingError('keyframes must be a list of at most 3 (not a quota)')
    frame_fields = ('id', 'anchor', 'source_refs', 'selection_reason', 'perception', 'interpretation',
                    'response', 'realization', 'realization_note', 'omission')
    ids = set()
    for frame in frames:
        _object(frame, frame_fields, 'keyframe', frame_fields)
        if frame['id'] not in ('kf1', 'kf2', 'kf3') or frame['id'] in ids:
            raise UserFacingError('keyframe id must be unique kf1..kf3')
        ids.add(frame['id'])
        for field in ('anchor', 'selection_reason', 'perception', 'interpretation', 'response', 'realization_note'):
            _text(frame[field], field)
        _sources(frame['source_refs'], request)
        if frame['realization'] not in ('dialogue', 'narration', 'both', 'omit'):
            raise UserFacingError('invalid realization')
        if frame['realization'] == 'omit':
            _omission(frame['omission'])
        elif frame['omission'] is not None:
            raise UserFacingError('omission is only allowed for realization=omit')
    if not frames:
        _omission(proposal['scene_omission'], scene=True, request=request)
    elif proposal['scene_omission'] is not None:
        raise UserFacingError('scene_omission must be null when keyframes are present')
    render_keyframes(proposal)
    return copy.deepcopy(proposal)


def render_keyframes(proposal: dict) -> str:
    lines = ['# Narrative Keyframes', RULES]
    for frame in proposal['keyframes']:
        lines += ['## ' + frame['id'], 'source_refs: ' + ', '.join(frame['source_refs'])]
        for field in ('anchor', 'selection_reason', 'perception', 'interpretation', 'response', 'realization', 'realization_note'):
            lines.append('{}: {}'.format(field, frame[field]))
        if frame['omission']:
            lines.append('例外省略: ' + json.dumps(frame['omission'], ensure_ascii=False))
    if proposal['scene_omission']:
        lines.append('場面全体の例外省略: ' + json.dumps(proposal['scene_omission'], ensure_ascii=False))
    result = '\n'.join(lines)
    if len(result) > MAX_RENDER_CHARS:
        raise UserFacingError('keyframe rendering exceeds 3000 characters; shorten proposal explicitly')
    return result
