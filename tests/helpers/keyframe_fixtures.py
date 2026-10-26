"""Synthetic proposals only: these fixtures make no literary-quality claim."""
import copy
import json


def request_fixture():
    return {'scene_id': '1-1', 'pov_character_id': 'mira', 'generation_id': 'g1',
            'sources': {'scene': 'planning', 'dialogue': 'voice'}}


def omission_fixture():
    return {'category': 'tempo_damage', 'dialogue_reason': '無言で通り過ぎる橋渡しに発話を増やすと足が止まる。',
            'narration_reason': 'すでに示された警戒を説明し直すと移動のテンポを損なう。'}


def valid_proposal(request=None, realization='dialogue'):
    request = request or request_fixture()
    return {'version': 1, 'scene_id': request['scene_id'], 'pov_character_id': request['pov_character_id'],
            'generation_id': request['generation_id'], 'keyframes': [
                {'id': 'kf1', 'anchor': '相手が鍵の行方を尋ねる。',
                 'source_refs': [next(iter(request['sources']))], 'selection_reason': '責められたと感じ、返答を選び直す。',
                 'perception': '短い問いが耳に残った。', 'interpretation': '責めているように聞こえるが、違うかもしれない。',
                 'response': '言い訳をやめ、何を知りたいのか尋ねよう。',
                 'realization': realization, 'realization_note': '問いを返す語順と言い直しに反映する。',
                 'omission': omission_fixture() if realization == 'omit' else None}], 'scene_omission': None}


def scene_omission_proposal():
    result = valid_proposal()
    result['keyframes'] = []
    result['scene_omission'] = dict(omission_fixture(), considered_anchor='無言で路地を通り抜ける。', source_refs=['scene'])
    return result


def disable_keyframing(project):
    """Opt out only for fixtures exercising unrelated legacy behavior."""
    from pathlib import Path
    Path(project, 'narrative_keyframing.json').write_text(json.dumps(
        {'version': 1, 'enabled': False, 'disable_reason': '主観素材を扱わない既存機能の独立した回帰試験。'}, ensure_ascii=False), encoding='utf-8')


def bind_disabled_check_fixture(project, runtime, report, *, scene_id='1-1', cli_only=False):
    """Bind unrelated synthetic checks to a genuine explicit-off contract.

    This deliberately does not claim the fixture underwent prepare/prose review;
    its tests isolate approval identity, attribution or exact-span review.
    """
    import os
    from pathlib import Path
    from novel_agent.narrative_keyframes import resolve_keyframing_policy, build_keyframe_contract
    from novel_agent.keyframe_runtime import require_keyframing_current
    from novel_agent.runtime_paths import write_runtime_manifest
    from novel_agent.dependencies import snapshot_dependencies, dependency_digest
    from novel_agent.storage import atomic_write_json, text_content_hash
    project, runtime = Path(project), Path(runtime)
    if not cli_only:
        disable_keyframing(project)
    reason = '主観素材を扱わない既存機能の独立した回帰試験。'
    policy = resolve_keyframing_policy(str(project), scene_id=scene_id,
        enabled_override=False if cli_only else None, disable_reason=reason if cli_only else None)
    contract = build_keyframe_contract(scene_id=scene_id, pov_character_id=None, policy=policy)
    contract_path = runtime / 'narrative_keyframe_contract.json'
    atomic_write_json(str(contract_path), contract)
    selection = {'version': 2, 'dialogue': {'pov_character_id': None}, 'config': {'pov_character_id': None},
        'keyframing': {'policy': policy, 'pov_character_id': None, 'status': 'disabled',
                       'contract_path': str(contract_path.relative_to(project)), 'contract_hash': text_content_hash(str(contract_path))}}
    atomic_write_json(str(runtime / 'context_selection.json'), selection)
    write_runtime_manifest(str(project), str(runtime), scene_id=scene_id, mode='draft', files=[str(contract_path)],
                           inputs=snapshot_dependencies(str(project), [{"kind": "projection", "selector": "keyframing_selection",
                               "projection_version": 3, "scene_id": scene_id, "path": str(runtime / "context_selection.json")}]),
                           features={'narrative_keyframing': 1})
    current = require_keyframing_current(str(project), str(runtime), scene_id)
    report['check_inputs'] += snapshot_dependencies(str(project), current['dependency_specs'])
    report['check_inputs_digest'] = dependency_digest(report['check_inputs'])
    report['keyframing'] = current['binding']; report['keyframing_snapshot'] = None
