"""Creation-time keyframe provenance and flat historical approval evidence.

Only explicit registration publishes creative material. Full runtime graphs are
checked at creation; historical approvals deliberately retain stable flat guards
instead of re-running mutable artifact ledgers (including their own approval).
"""
import copy
import hashlib
import json
import os
import re
from typing import Optional

from novel_agent.dependencies import (snapshot_dependencies, verify_dependencies, dependency_digest,
                                      compact_dependencies, _path)
from novel_agent.errors import UserFacingError
from novel_agent.consumed_inputs import check_consumed_text, check_consumed_selection
from novel_agent.ledgers import read_artifact_ledger, _register_artifact_locked
from novel_agent.narrative_keyframes import (MAX_PROPOSAL_BYTES, SOURCE_CATEGORIES, RULES,
    resolve_keyframing_policy, build_keyframe_contract, validate_keyframe_proposal,
    render_keyframes, strict_json_loads)
from novel_agent.runtime_paths import validate_runtime_identity, require_runtime_current, resolve_runtime_dir
from novel_agent.storage import read_json, text_content_hash, atomic_write_json, project_lock

CONTRACT = 'narrative_keyframe_contract.json'
PROMPT = 'narrative_keyframe_prompt.txt'
REQUEST = 'narrative_keyframe_request.json'
RESULT = 'narrative_keyframes.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def generation_id(request):
    return digest({key: request[key] for key in
                   ('scene_id', 'contract_hash', 'prompt_hash', 'inputs_digest', 'sources')})


def _read(path):
    try:
        with open(path, encoding='utf-8') as handle:
            return strict_json_loads(handle.read(), os.path.basename(path))
    except (FileNotFoundError, UnicodeError) as exc:
        raise UserFacingError('keyframe file missing/invalid; prepare or generate again: {} ({})'.format(path, exc))


def _read_bound_json(project_dir, path, guards):
    try:
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
    except (FileNotFoundError, UnicodeError) as exc:
        raise UserFacingError('keyframe input missing/invalid: {} ({})'.format(path, exc))
    check_consumed_text(project_dir, path, text, guards)
    return strict_json_loads(text, os.path.basename(path))


def _keys(payload, fields, label):
    if not isinstance(payload, dict) or set(payload) != set(fields):
        raise UserFacingError('invalid {} fields'.format(label))


def _hash(value, label):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise UserFacingError('invalid {} hash'.format(label))


def _version(payload, label):
    if type(payload.get('version')) is not int or payload['version'] != 1:
        raise UserFacingError('unsupported {} version'.format(label))


def _sources(sources):
    if not isinstance(sources, dict) or not sources:
        raise UserFacingError('keyframe source registry must be nonempty')
    for source, category in sources.items():
        if (not isinstance(source, str) or not source or len(source) > 80 or any(c.isspace() for c in source)
                or not isinstance(category, str) or category not in SOURCE_CATEGORIES):
            raise UserFacingError('invalid keyframe source registry')


def _file(project_dir, runtime_dir, name):
    return _path(project_dir, os.path.join(runtime_dir, name))[0]


def _require_artifact(project_dir, path):
    absolute, relative = _path(project_dir, path)
    record = next((r for r in read_artifact_ledger(project_dir)['artifacts'] if r['path'] == relative), None)
    if (record is None or not os.path.isfile(absolute) or record.get('content_hash') != text_content_hash(absolute)
            or not isinstance(record.get('dependencies'), list)
            or record.get('dependency_digest') != dependency_digest(record['dependencies'])):
        raise UserFacingError('unregistered or changed keyframe artifact; regenerate/register: ' + relative)
    if verify_dependencies(project_dir, record['dependencies']):
        raise UserFacingError('stale keyframe artifact; prepare again: ' + relative)
    return record


def load_keyframe_runtime(project_dir: str, runtime_dir: str, scene_id: str) -> dict:
    from prompt_utils import parse_scene_reference
    scene_id = parse_scene_reference(scene_id)["canonical_id"]
    _path(project_dir, runtime_dir)
    manifest = validate_runtime_identity(project_dir, runtime_dir, scene_id=scene_id, mode='draft')
    if manifest.get('features', {}).get('narrative_keyframing') != 1:
        raise UserFacingError('legacy runtime requires same-scene prepare --scene {} --mode draft for keyframing'.format(scene_id))
    require_runtime_current(project_dir, runtime_dir)
    selection_path = _file(project_dir, runtime_dir, 'context_selection.json')
    selection = _read(selection_path)
    check_consumed_selection(project_dir, selection_path, selection, manifest["inputs"])
    contract_path = _file(project_dir, runtime_dir, CONTRACT)
    contract = _read_bound_json(project_dir, contract_path, manifest["files"])
    static = selection.get('keyframing')
    if not isinstance(static, dict) or selection.get('version') != 2:
        raise UserFacingError('keyframing selection missing; same-scene prepare required')
    policy = static.get('policy', {})
    current_policy = resolve_keyframing_policy(project_dir, scene_id=scene_id,
        enabled_override=policy.get('enabled_override'), disable_reason=policy.get('reason_override'))
    pov = selection.get('dialogue', {}).get('pov_character_id')
    expected = build_keyframe_contract(scene_id=scene_id, pov_character_id=pov, policy=current_policy)
    expected_static = {'policy': current_policy, 'pov_character_id': pov, 'status': expected['status'],
        'contract_path': os.path.relpath(contract_path, project_dir).replace(os.sep, '/'),
        'contract_hash': text_content_hash(contract_path)}
    if (contract != expected or static != expected_static
            or selection.get('config', {}).get('pov_character_id') != pov
            or not any(r.get('path') == expected_static['contract_path'] and r.get('content_hash') == expected_static['contract_hash']
                       for r in manifest.get('files', []))):
        raise UserFacingError('keyframing contract/selection mismatch; same-scene prepare required')
    if current_policy['enabled'] and not pov:
        raise UserFacingError('keyframing needs explicit POV: prepare --scene {} --pov-character ID (or --keyframing off --keyframing-reason REASON)'.format(scene_id))
    return {'manifest': manifest, 'selection': selection, 'contract': contract, 'policy': current_policy,
            'contract_path': contract_path, 'selection_path': selection_path}


def keyframe_input_specs(project_dir, runtime_dir):
    names = ['style_contract_compact.md', 'scene_brief_compact.md', 'request_compact.md',
             'planning_gate_brief.md', 'dialogue_context_pack.md', 'continuity_pack.md',
             'story_memory_pack.md', 'related_context_pack.md']
    return [{'kind': 'artifact', 'path': _file(project_dir, runtime_dir, name)} for name in names] + [
        {'kind': 'file', 'path': _file(project_dir, runtime_dir, CONTRACT)},
        {'kind': 'file', 'path': _file(project_dir, runtime_dir, 'runtime_manifest.json')},
        {'kind': 'projection', 'selector': 'memory_selection', 'projection_version': 3,
         'path': _file(project_dir, runtime_dir, 'context_selection.json')}]


def keyframe_source_sections(project_dir, runtime_dir, selection, *, inputs):
    """Read only the already-selected scene packs, never whole originals."""
    from novel_agent.memory_context import memory_prompt_sections
    check_consumed_selection(project_dir, _file(project_dir, runtime_dir, "context_selection.json"), selection, inputs)
    specs = [('style_contract_compact.md', 'voice', True, 0),
             ('scene_brief_compact.md', 'planning', True, 0),
             ('request_compact.md', 'planning', True, 0),
             ('planning_gate_brief.md', 'planning', True, 0),
             ('dialogue_context_pack.md', 'voice', True, 1),
             ('continuity_pack.md', 'continuity', False, 8),
             ('related_context_pack.md', 'continuity', False, 9)]
    sections = []
    for name, category, required, priority in specs:
        path = _file(project_dir, runtime_dir, name)
        try:
            with open(path, encoding='utf-8') as handle:
                raw_text = handle.read()
                text = check_consumed_text(project_dir, path, raw_text, inputs).strip()
        except FileNotFoundError:
            raise UserFacingError('keyframe runtime pack missing; prepare again: ' + name)
        sections.append({'name': name, 'text': '[source: {} | {}]\n{}'.format(name, category, text),
                         'required': required, 'priority': priority, 'source_ids': [name], 'category': category})
    memory = selection.get('memory')
    if not isinstance(memory, dict):
        raise UserFacingError('keyframing requires selected memory labels; prepare again')
    for section in memory_prompt_sections(memory):
        section = dict(section)
        if section['source_ids']:
            category = 'pov_context' if section['text'].startswith('## pov_context') else 'author_context'
            section['category'] = category
            section['text'] = '[source: {} | {}]\n{}'.format(section['source_ids'][0], category, section['text'])
        sections.append(section)
    return sections


def _load_request(project_dir, runtime_dir, loaded):
    request_path = _file(project_dir, runtime_dir, REQUEST)
    prompt_path = _file(project_dir, runtime_dir, PROMPT)
    _require_artifact(project_dir, prompt_path)
    request_record = _require_artifact(project_dir, request_path)
    request = _read_bound_json(project_dir, request_path, [request_record])
    _keys(request, ('version', 'scene_id', 'pov_character_id', 'contract_hash', 'prompt_hash',
                    'inputs', 'inputs_digest', 'sources', 'generation_id', 'proposal_template'), 'keyframe request')
    _version(request, 'request')
    _sources(request['sources'])
    contract = loaded['contract']
    if (request['scene_id'] != contract['scene_id'] or request['pov_character_id'] != contract['pov_character_id']
            or request['contract_hash'] != text_content_hash(loaded['contract_path'])
            or request['prompt_hash'] != text_content_hash(prompt_path)
            or not isinstance(request['inputs'], list) or request['inputs_digest'] != dependency_digest(request['inputs'])
            or request['generation_id'] != generation_id(request)):
        raise UserFacingError('keyframe generation/contract identity mismatch; regenerate')
    if verify_dependencies(project_dir, request['inputs']):
        raise UserFacingError('stale keyframe generation inputs; prepare again')
    return request


def _stable_specs(project_dir, runtime_dir, loaded):
    policy = loaded['policy']
    specs = [{'kind': 'projection', 'selector': 'keyframing_policy', 'projection_version': 3,
              'scene_id': loaded['contract']['scene_id'], 'enabled_override': policy['enabled_override'],
              'reason_override': policy['reason_override']},
             {'kind': 'projection', 'selector': 'keyframing_selection', 'projection_version': 3,
              'scene_id': loaded['contract']['scene_id'], 'path': loaded['selection_path']},
             {'kind': 'file', 'path': loaded['contract_path']}]
    if policy['enabled']:
        specs.append({'kind': 'file', 'path': _file(project_dir, runtime_dir, RESULT)})
    return specs


def require_keyframing_current(project_dir: str, runtime_dir: str, scene_id: str) -> dict:
    loaded = load_keyframe_runtime(project_dir, runtime_dir, scene_id)
    binding = {'version': 1, 'enabled': loaded['policy']['enabled'],
               'pov_character_id': loaded['contract']['pov_character_id'],
               'contract_hash': text_content_hash(loaded['contract_path']),
               'generation_id': None, 'registration_hash': None,
               'disable_reason': loaded['policy']['disable_reason']}
    snapshot = None
    section = None
    referenced = []
    artifact_specs = []
    source_guards = []
    if binding['enabled']:
        request = _load_request(project_dir, runtime_dir, loaded)
        path = _file(project_dir, runtime_dir, RESULT)
        ledger_record = _require_artifact(project_dir, path)
        registration = _read_bound_json(project_dir, path, [ledger_record])
        _keys(registration, ('version', 'proposal', 'request_hash', 'dependencies', 'dependency_digest'), 'registration')
        _version(registration, 'registration')
        if (registration['request_hash'] != text_content_hash(_file(project_dir, runtime_dir, REQUEST))
                or registration['dependencies'] != ledger_record['dependencies']
                or registration['dependency_digest'] != ledger_record['dependency_digest']):
            raise UserFacingError('keyframe registration provenance mismatch; register again')
        proposal = validate_keyframe_proposal(registration['proposal'], request=request)
        binding.update(generation_id=request['generation_id'], registration_hash=text_content_hash(path))
        snapshot = {'version': 1, 'proposal': proposal, 'sources': request['sources'],
                    'contract_hash': binding['contract_hash'], 'prompt_hash': request['prompt_hash'],
                    'request_hash': registration['request_hash'], 'registration_hash': binding['registration_hash'],
                    'generation_id': binding['generation_id'], 'inputs_digest': request['inputs_digest']}
        snapshot['snapshot_digest'] = digest(snapshot)
        referenced = sorted({source for frame in proposal['keyframes'] for source in frame['source_refs']} |
                            set((proposal['scene_omission'] or {}).get('source_refs', [])))
        section = {'name': 'narrative_keyframes', 'text': render_keyframes(proposal),
            'required': True, 'priority': 2, 'source_ids': []}
        artifact_specs = [{'kind': 'artifact', 'path': path}]
        source_guards = request['inputs']
    return {'binding': binding, 'approval_snapshot': snapshot, 'prompt_section': section,
            'dependency_specs': _stable_specs(project_dir, runtime_dir, loaded),
            'artifact_specs': artifact_specs, 'referenced_source_ids': referenced, 'source_guards': source_guards}


def register_keyframes(project_dir: str, scene_id: str, input_path: str, *,
                       runtime_dir_arg: str = '', validate_only: bool = False) -> dict:
    from prompt_utils import parse_scene_reference
    scene_ref = parse_scene_reference(scene_id)
    scene_id = scene_ref['canonical_id']
    runtime_dir = resolve_runtime_dir(project_dir, mode='draft', scene_ref=scene_ref,
                                      runtime_dir_arg=runtime_dir_arg)
    result_path = _file(project_dir, runtime_dir, RESULT)
    if os.path.realpath(input_path) == os.path.realpath(result_path):
        raise UserFacingError('registered result cannot be its own proposal input')
    with project_lock(project_dir):
        loaded = load_keyframe_runtime(project_dir, runtime_dir, scene_id)
        if not loaded['policy']['enabled']:
            raise UserFacingError('keyframing disabled; prepare with --keyframing on before generating')
        request = _load_request(project_dir, runtime_dir, loaded)
        try:
            with open(input_path, 'rb') as handle:
                raw = handle.read(MAX_PROPOSAL_BYTES + 1)
        except OSError as exc:
            raise UserFacingError('cannot read keyframe proposal: ' + str(exc))
        if len(raw) > MAX_PROPOSAL_BYTES:
            raise UserFacingError('keyframe proposal exceeds 65536 bytes')
        try:
            submitted = strict_json_loads(raw.decode('utf-8'), 'keyframe proposal')
        except UnicodeError as exc:
            raise UserFacingError('keyframe proposal must be UTF-8: ' + str(exc))
        dependencies = snapshot_dependencies(project_dir, [
            {'kind': 'artifact', 'path': _file(project_dir, runtime_dir, REQUEST)},
            {'kind': 'artifact', 'path': _file(project_dir, runtime_dir, PROMPT)},
            {'kind': 'file', 'path': loaded['contract_path']}])
        old_result = text_content_hash(result_path)
        old_record = next((r for r in read_artifact_ledger(project_dir)['artifacts']
                           if r['path'] == os.path.relpath(result_path, project_dir).replace(os.sep, '/')), None)
        proposal = validate_keyframe_proposal(submitted, request=request)
        registration = {'version': 1, 'proposal': proposal,
                        'request_hash': text_content_hash(_file(project_dir, runtime_dir, REQUEST)),
                        'dependencies': compact_dependencies(dependencies), 'dependency_digest': dependency_digest(dependencies)}
        # External editors do not obey project_lock. Recheck captured evidence;
        # never resnapshot changed inputs and bless a stale proposal.
        load_keyframe_runtime(project_dir, runtime_dir, scene_id)
        _load_request(project_dir, runtime_dir, loaded)
        current_record = next((r for r in read_artifact_ledger(project_dir)['artifacts']
                              if r['path'] == os.path.relpath(result_path, project_dir).replace(os.sep, '/')), None)
        if (verify_dependencies(project_dir, dependencies) or text_content_hash(result_path) != old_result
                or current_record != old_record):
            raise UserFacingError('keyframe inputs/result changed during registration; retry from current generation')
        if validate_only:
            return registration
        if (os.path.isfile(result_path) and old_record is not None
                and old_record.get('content_hash') == old_result
                and old_record.get('dependencies') == dependencies
                and _read(result_path) == registration):
            _require_artifact(project_dir, result_path)
            return registration
        atomic_write_json(result_path, registration)
        _register_artifact_locked(project_dir, artifact_id='narrative_keyframes:' + scene_id,
            artifact_type='narrative_keyframes', path=result_path, dependencies=dependencies)
        return registration


def validate_keyframing_binding(binding: dict, check_inputs: list) -> None:
    _keys(binding, ('version', 'enabled', 'pov_character_id', 'contract_hash', 'generation_id',
                    'registration_hash', 'disable_reason'), 'keyframing binding')
    _version(binding, 'binding')
    if type(binding['enabled']) is not bool:
        raise UserFacingError('invalid keyframing enabled binding')
    _hash(binding['contract_hash'], 'contract')
    policy = [r for r in check_inputs if r.get('selector') == 'keyframing_policy']
    selection = [r for r in check_inputs if r.get('selector') == 'keyframing_selection']
    if (len(policy) != 1 or len(selection) != 1 or policy[0].get('projection_version') != 3
            or selection[0].get('projection_version') != 3 or policy[0].get('scene_id') != selection[0].get('scene_id')):
        raise UserFacingError('keyframing binding lacks stable policy/selection guards')
    directory = os.path.dirname(selection[0].get('path', ''))
    def require_file(name, expected):
        matches = [r for r in check_inputs if r.get('kind') == 'file' and r.get('path') == directory + '/' + name]
        if len(matches) != 1 or matches[0].get('exists') is not True or matches[0].get('content_hash') != expected:
            raise UserFacingError('keyframing binding lacks stable file guard: ' + name)
    require_file(CONTRACT, binding['contract_hash'])
    if binding['enabled']:
        _hash(binding['generation_id'], 'generation'); _hash(binding['registration_hash'], 'registration')
        if not isinstance(binding['pov_character_id'], str) or not binding['pov_character_id'] or binding['disable_reason'] != '':
            raise UserFacingError('invalid enabled keyframing binding')
        require_file(RESULT, binding['registration_hash'])
    else:
        from novel_agent.narrative_keyframes import _text
        _text(binding['disable_reason'], 'disable_reason')
        if binding['generation_id'] is not None or binding['registration_hash'] is not None:
            raise UserFacingError('disabled keyframing binding has registration')


def validate_keyframing_snapshot(snapshot: Optional[dict], binding: dict) -> None:
    if not binding['enabled']:
        if snapshot is not None:
            raise UserFacingError('disabled keyframing snapshot must be null')
        return
    _keys(snapshot, ('version', 'proposal', 'sources', 'contract_hash', 'prompt_hash', 'request_hash',
                     'registration_hash', 'generation_id', 'inputs_digest', 'snapshot_digest'), 'keyframing snapshot')
    _version(snapshot, 'snapshot')
    if snapshot['snapshot_digest'] != digest({k: v for k, v in snapshot.items() if k != 'snapshot_digest'}):
        raise UserFacingError('keyframing snapshot digest mismatch')
    _sources(snapshot['sources'])
    for key in ('contract_hash', 'registration_hash', 'generation_id'):
        if snapshot[key] != binding[key]:
            raise UserFacingError('keyframing snapshot/binding mismatch')
    for key in ('contract_hash', 'prompt_hash', 'request_hash', 'registration_hash', 'generation_id', 'inputs_digest'):
        _hash(snapshot[key], key)
    proposal = snapshot['proposal']
    if not isinstance(proposal, dict):
        raise UserFacingError('invalid keyframe snapshot proposal')
    validate_keyframe_proposal(proposal, request={'scene_id': proposal.get('scene_id'),
        'pov_character_id': binding['pov_character_id'], 'generation_id': binding['generation_id'], 'sources': snapshot['sources']})
    if snapshot['generation_id'] != generation_id(dict(snapshot, scene_id=proposal['scene_id'])):
        raise UserFacingError('keyframing snapshot generation mismatch')


def ensure_keyframing_unchanged(project_dir, runtime_dir, scene_id, captured):
    current = require_keyframing_current(project_dir, runtime_dir, scene_id)
    if (current['binding'] != captured['binding'] or current['approval_snapshot'] != captured['approval_snapshot']):
        raise UserFacingError('keyframing changed during operation; regenerate/recheck')


def add_keyframing_sections(project_dir, runtime_dir, current, sections, *, expansion=False):
    """Keep selected source sections with the material, including under budget pressure."""
    if not current['binding']['enabled']:
        return sections
    sections = copy.deepcopy(sections)
    for section in sections:
        if section['name'] == 'required_constraints_and_planning':
            section['source_ids'] = ['style_contract_compact.md', 'scene_brief_compact.md',
                                     'request_compact.md', 'planning_gate_brief.md']
        elif section['name'] == 'required_expansion_constraints_and_target':
            section['source_ids'] = ['style_contract_compact.md']
    available = {source for section in sections for source in section.get('source_ids', [])}
    required = set(current['referenced_source_ids'])
    if expansion:
        required |= {'scene_brief_compact.md', 'request_compact.md', 'planning_gate_brief.md'}
    missing = required - available
    if missing:
        selection = _read(_file(project_dir, runtime_dir, 'context_selection.json'))
        for section in keyframe_source_sections(project_dir, runtime_dir, selection, inputs=current["source_guards"]):
            if set(section.get('source_ids', [])) & missing:
                sections.append(section)
                available.update(section['source_ids'])
    if required - available:
        raise UserFacingError('referenced keyframe source missing from prompt: ' + ', '.join(sorted(required - available)))
    for section in sections:
        if set(section.get('source_ids', [])) & required:
            section['required'] = True
    material = copy.deepcopy(current['prompt_section'])
    if expansion:
        sections.append({'name': 'keyframe_expansion_rules', 'text': '既に本文へ反映された内容を重複説明せず、文字数不足への必要な局所差分だけ。意味的改稿はrevisionへ戻す。',
                         'required': True, 'priority': 2, 'source_ids': []})
    sections.append(material)
    return sections
