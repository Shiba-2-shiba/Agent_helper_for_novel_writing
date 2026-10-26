"""Build an external-agent generation request, never call a model or write prose."""
import argparse
import copy
import json
import os
import sys
from typing import Optional

from novel_agent.dependencies import snapshot_dependencies, verify_dependencies, dependency_digest
from novel_agent.errors import UserFacingError
from novel_agent.keyframe_runtime import (load_keyframe_runtime, keyframe_source_sections, keyframe_input_specs,
    generation_id, _file, CONTRACT, PROMPT, REQUEST, RESULT)
from novel_agent.ledgers import _register_artifacts_locked
from novel_agent.memory_context import assemble_prompt
from novel_agent.narrative_keyframes import RULES
from novel_agent.storage import project_lock, text_content_hash, atomic_write_text, atomic_write_json
from novel_agent.runtime_paths import resolve_runtime_dir
from prompt_utils import resolve_project_path, parse_scene_reference


def _template(scene_id, pov):
    return {'version': 1, 'scene_id': scene_id, 'pov_character_id': pov, 'generation_id': '',
            'keyframes': [{'id': 'kf1', 'anchor': '未記入', 'source_refs': [], 'selection_reason': '未記入',
                'perception': '未記入', 'interpretation': '未記入', 'response': '未記入',
                'realization': 'dialogue', 'realization_note': '未記入', 'omission': None}], 'scene_omission': None}


def _output_path(project_dir, runtime_dir, output_path, manifest):
    if output_path is None:
        return None
    path = os.path.abspath(output_path)
    protected = [os.path.join(project_dir, f['path']) for f in manifest['files']]
    protected += [os.path.join(runtime_dir, name) for name in (CONTRACT, PROMPT, REQUEST, RESULT, 'context_selection.json', 'runtime_manifest.json')]
    if os.path.lexists(path) or any(os.path.realpath(path) == os.path.realpath(p) for p in protected):
        raise UserFacingError('proposal output must be new and not a protected runtime/scene file: ' + path)
    # Even a not-yet-written canonical scene is not a proposal destination.
    import re
    if re.fullmatch(r'(?:chapter_?\d+_scene_?\d+|scene_\d+-\d+)\.txt', os.path.basename(path), re.IGNORECASE):
        raise UserFacingError('proposal output cannot be a scene text path')
    return path


def build_keyframe_prompt(project_dir: str, runtime_dir: str, scene_id: str, *, output_path: Optional[str] = None) -> dict:
    with project_lock(project_dir):
        loaded = load_keyframe_runtime(project_dir, runtime_dir, scene_id)
        scene_id = loaded['contract']['scene_id']
        if not loaded['policy']['enabled']:
            raise UserFacingError('keyframing disabled; use draft prompt or prepare --keyframing on')
        output = _output_path(project_dir, runtime_dir, output_path, loaded['manifest'])
        inputs = snapshot_dependencies(project_dir, keyframe_input_specs(project_dir, runtime_dir))
        sections = keyframe_source_sections(project_dir, runtime_dir, loaded['selection'], inputs=inputs)
        template = _template(scene_id, loaded['contract']['pov_character_id'])
        instructions = ('# Narrative Keyframe Generation\n外部エージェントがJSON創作素材を作る。本文・承認・記憶は変更しない。\n' + RULES +
            '\n明示POV: ' + loaded['contract']['pov_character_id'] +
            '\nsourceの区分は参照可能性だけを示す。planningは現在sceneの予定、author_contextは作者用でPOVの知識ではない。'
            '\n重要な要所を最大3件。これは上限でありノルマではない。perception/interpretation/responseは視点人物として短い一人称創作素材。'
            '\n台詞(dialogue)／地の文(narration)／両方(both)への反映を主とする。各自然文1〜240字、ID80字以下、レンダリング3000字以下。'
            '\nomitのみomission={category: unnatural|redundant|tempo_damage, dialogue_reason: 具体的理由, narration_reason: 具体的理由}。'
            '\nkeyframesが空ならscene_omissionにconsidered_anchor, source_refsとomissionの三項目を直接含める。'
            '\nkeyframesがある場合scene_omission=null。通常のomission=null。未知キーは不可。空欄/TODO/未記入は登録不可。'
            '\n返答はJSONだけ。別添requestのgeneration_idと採用済みsourcesを使い、次の未完成形を完成させる。\n' +
            json.dumps(template, ensure_ascii=False, indent=2))
        sections.append({'name': 'keyframe_generation_contract', 'text': instructions,
                         'required': True, 'priority': 0, 'source_ids': []})
        assembled = assemble_prompt(sections)
        selected_names = {s['name'] for s in assembled['selected']}
        sources = {source: section['category'] for section in sections if section['name'] in selected_names
                   for source in section['source_ids']}
        import hashlib
        request = {'version': 1, 'scene_id': scene_id, 'pov_character_id': loaded['contract']['pov_character_id'],
                   'contract_hash': text_content_hash(loaded['contract_path']),
                   'prompt_hash': hashlib.sha256(assembled['prompt'].encode('utf-8')).hexdigest(),
                   'inputs': inputs, 'inputs_digest': dependency_digest(inputs), 'sources': sources}
        request['generation_id'] = generation_id(request)
        template['generation_id'] = request['generation_id']
        request['proposal_template'] = template
        # Validate the exact captured inputs again, not newly captured substitutes.
        load_keyframe_runtime(project_dir, runtime_dir, scene_id)
        if verify_dependencies(project_dir, inputs):
            raise UserFacingError('runtime changed during keyframe prompt generation; prepare again')
        _output_path(project_dir, runtime_dir, output, loaded['manifest'])
        prompt_path = _file(project_dir, runtime_dir, PROMPT)
        request_path = _file(project_dir, runtime_dir, REQUEST)
        atomic_write_text(prompt_path, assembled['prompt'])
        atomic_write_json(request_path, request)
        _register_artifacts_locked(project_dir, [
            {'artifact_id': name + ':' + scene_id, 'artifact_type': name, 'path': path, 'dependencies': inputs}
            for name, path in (('narrative_keyframe_prompt', prompt_path), ('narrative_keyframe_request', request_path))])
        selection = loaded['selection']
        selection['keyframe_prompt'] = {k: v for k, v in assembled.items() if k != 'prompt'}
        atomic_write_json(loaded['selection_path'], selection)
        if output is not None:
            # O_EXCL also prevents an editor racing the final destination check.
            os.makedirs(os.path.dirname(output), exist_ok=True)
            try:
                with open(output, 'x', encoding='utf-8') as handle:
                    handle.write(json.dumps(template, ensure_ascii=False, indent=2) + '\n')
            except FileExistsError:
                raise UserFacingError('proposal output appeared during generation; refusing overwrite: ' + output)
        return request


def main():
    parser = argparse.ArgumentParser(description='Build a selected POV keyframe prompt for an external agent (no model API).')
    parser.add_argument('--project', required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--runtime_dir', default='')
    parser.add_argument('--output', default=None, help='New external proposal template path; never overwritten')
    args = parser.parse_args()
    project = resolve_project_path(args.project)
    scene = parse_scene_reference(args.scene)
    runtime = resolve_runtime_dir(project, mode='draft', scene_ref=scene, runtime_dir_arg=args.runtime_dir)
    request = build_keyframe_prompt(project, runtime, scene['canonical_id'], output_path=args.output)
    print('OK: keyframe prompt generated at ' + os.path.join(runtime, PROMPT))
    print('OK: generation_id=' + request['generation_id'])
    print('NEXT: external agent completes proposal JSON, then register-keyframes --input PATH (registration is not prose approval)')


if __name__ == '__main__':
    try:
        main()
    except UserFacingError as exc:
        print('ERROR: ' + str(exc)); sys.exit(1)
