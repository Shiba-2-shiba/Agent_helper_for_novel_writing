"""Real CLI workflows: creative proposal registration is not prose approval."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from novel_agent.errors import UserFacingError
from novel_agent.runtime_paths import require_runtime_current
from helpers.keyframe_fixtures import valid_proposal
from test_keyframe_runtime import project_fixture, prepare, cli, read, write


def generated(tmp_path):
    from build_keyframe_prompt import build_keyframe_prompt
    project = project_fixture(tmp_path)
    runtime = prepare(project, '--pov-character', 'mira')
    request = build_keyframe_prompt(str(project), str(runtime), '2-3')
    proposal_path = project / 'proposal.json'
    write(proposal_path, valid_proposal(request))
    return project, runtime, request, proposal_path


def registered(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    register_keyframes(str(project), '2-3', str(proposal_path))
    return project, runtime, request, proposal_path


def tree_bytes(project):
    return {str(p.relative_to(project)): p.read_bytes() for p in project.rglob('*') if p.is_file()}


def test_request_contains_only_selected_source_ids(tmp_path):
    project, runtime, request, proposal_path = generated(tmp_path)
    assert request['pov_character_id'] == 'mira'
    selection = read(runtime / 'context_selection.json')['keyframe_prompt']
    selected = {s for section in selection['selected'] for s in section['source_ids']}
    assert set(request['sources']) == selected
    assert request['sources']['scene_brief_compact.md'] == 'planning'
    assert request['sources']['dialogue_context_pack.md'] == 'voice'
    assert len((runtime / 'narrative_keyframe_prompt.txt').read_text()) <= 16000
    assert 'canon' in (runtime / 'narrative_keyframe_prompt.txt').read_text()


def test_pending_template_is_not_registered(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    write(proposal_path, request['proposal_template'])
    with pytest.raises(UserFacingError):
        register_keyframes(str(project), '2-3', str(proposal_path))
    assert not (runtime / 'narrative_keyframes.json').exists()


def test_validate_only_writes_nothing(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    before = tree_bytes(project)
    register_keyframes(str(project), '2-3', str(proposal_path), validate_only=True)
    assert tree_bytes(project) == before


def test_registration_preserves_prepare_manifest_and_is_idempotent(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes, require_keyframing_current
    project, runtime, request, proposal_path = generated(tmp_path)
    before = (runtime / 'runtime_manifest.json').read_bytes()
    register_keyframes(str(project), '2-3', str(proposal_path))
    first = tree_bytes(project)
    register_keyframes(str(project), '2-3', str(proposal_path))
    assert tree_bytes(project) == first
    assert (runtime / 'runtime_manifest.json').read_bytes() == before
    current = require_keyframing_current(str(project), str(runtime), '2-3')
    assert current['binding']['enabled'] is True
    assert current['binding']['generation_id'] == request['generation_id']
    assert current['approval_snapshot']['proposal'] == read(proposal_path)
    require_runtime_current(str(project), str(runtime))


@pytest.mark.parametrize('field,value', [('scene_id', '1-1'), ('pov_character_id', 'other'), ('generation_id', 'old')])
def test_generation_scene_pov_mismatch_rejected(tmp_path, field, value):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    proposal = read(proposal_path); proposal[field] = value; write(proposal_path, proposal)
    with pytest.raises(UserFacingError, match='mismatch'):
        register_keyframes(str(project), '2-3', str(proposal_path))


def test_unselected_source_is_rejected(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    proposal = read(proposal_path); proposal['keyframes'][0]['source_refs'] = ['future-secret']; write(proposal_path, proposal)
    with pytest.raises(UserFacingError, match='source'):
        register_keyframes(str(project), '2-3', str(proposal_path))


def test_missing_pov_and_resume_block_generation(tmp_path):
    from build_keyframe_prompt import build_keyframe_prompt
    project = project_fixture(tmp_path)
    runtime = prepare(project)
    with pytest.raises(UserFacingError, match='pov-character'):
        build_keyframe_prompt(str(project), str(runtime), '2-3')
    resume = prepare(project, '--pov-character', 'mira', mode='resume')
    with pytest.raises(UserFacingError, match='mode|draft'):
        build_keyframe_prompt(str(project), str(resume), '2-3')


@pytest.mark.parametrize('artifact', ['narrative_keyframes.json', 'narrative_keyframe_request.json', 'narrative_keyframe_prompt.txt'])
def test_result_or_generation_without_ledger_is_not_trusted(tmp_path, artifact):
    from novel_agent.keyframe_runtime import require_keyframing_current
    project, runtime, request, proposal_path = registered(tmp_path)
    ledger_path = project / 'runtime/artifact_ledger.json'
    ledger = read(ledger_path)
    ledger['artifacts'] = [r for r in ledger['artifacts'] if not r['path'].endswith('/' + artifact)]
    write(ledger_path, ledger)
    with pytest.raises(UserFacingError):
        require_keyframing_current(str(project), str(runtime), '2-3')


def test_partial_registration_never_loads(tmp_path, monkeypatch):
    import novel_agent.keyframe_runtime as api
    project, runtime, request, proposal_path = generated(tmp_path)
    def fail(*args, **kwargs):
        raise UserFacingError('simulated ledger failure')
    monkeypatch.setattr(api, '_register_artifact_locked', fail)
    with pytest.raises(UserFacingError, match='ledger'):
        api.register_keyframes(str(project), '2-3', str(proposal_path))
    assert (runtime / 'narrative_keyframes.json').is_file()
    with pytest.raises(UserFacingError):
        api.require_keyframing_current(str(project), str(runtime), '2-3')


def test_revalidate_before_registration_write(tmp_path, monkeypatch):
    import novel_agent.keyframe_runtime as api
    project, runtime, request, proposal_path = generated(tmp_path)
    original = api.validate_keyframe_proposal
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        (project / 'agent/memory/global_notes.md').write_text('外部編集された文体')
        return result
    monkeypatch.setattr(api, 'validate_keyframe_proposal', mutate)
    with pytest.raises(UserFacingError, match='stale|changed'):
        api.register_keyframes(str(project), '2-3', str(proposal_path))
    assert not (runtime / 'narrative_keyframes.json').exists()


def test_wrong_scene_runtime_is_not_latest_fallback(tmp_path):
    from novel_agent.keyframe_runtime import load_keyframe_runtime
    project, runtime, request, proposal_path = generated(tmp_path)
    with pytest.raises(UserFacingError, match='identity'):
        load_keyframe_runtime(str(project), str(runtime), '1-1')


def test_prompt_required_budget_fails_without_partial_outputs(tmp_path):
    from build_keyframe_prompt import build_keyframe_prompt
    project = project_fixture(tmp_path)
    (project / 'agent/memory/global_notes.md').write_text('- 口調: ' + '長' * 17000, encoding='utf-8')
    runtime = prepare(project, '--pov-character', 'mira')
    before = tree_bytes(project)
    with pytest.raises(UserFacingError, match='budget'):
        build_keyframe_prompt(str(project), str(runtime), '2-3', output_path=str(project / 'proposal.json'))
    assert tree_bytes(project) == before


@pytest.mark.parametrize('kind', ['body', 'contract', 'registered', 'exists'])
def test_proposal_output_cannot_overwrite_protected_or_existing_files(tmp_path, kind):
    from build_keyframe_prompt import build_keyframe_prompt
    project, runtime, request, proposal_path = generated(tmp_path)
    target = {'body': project / 'chapter_2_scene_2.txt', 'contract': runtime / 'narrative_keyframe_contract.json',
              'registered': runtime / 'narrative_keyframes.json', 'exists': proposal_path}[kind]
    before = tree_bytes(project)
    with pytest.raises(UserFacingError):
        build_keyframe_prompt(str(project), str(runtime), '2-3', output_path=str(target))
    assert tree_bytes(project) == before


def test_cli_generation_validate_register(tmp_path):
    project = project_fixture(tmp_path)
    result = cli('run_scene_pipeline.py', 'prepare', '--project', project, '--chapter', 2, '--scene', '2-3', '--pov-character', 'mira')
    assert result.returncode == 0 and 'keyframe-prompt' in result.stdout
    proposal_path = project / 'proposal.json'
    result = cli('run_scene_pipeline.py', 'keyframe-prompt', '--project', project, '--scene', '2-3', '--output', proposal_path)
    assert result.returncode == 0, result.stdout
    runtime = project / 'runtime/scenes/2-3/draft'
    request = read(runtime / 'narrative_keyframe_request.json')
    assert read(proposal_path) == request['proposal_template']
    write(proposal_path, valid_proposal(request))
    for extra in [('--validate-only',), ()]:
        result = cli('run_scene_pipeline.py', 'register-keyframes', '--project', project, '--scene', '2-3', '--input', proposal_path, *extra)
        assert result.returncode == 0, result.stdout


def scene_and_check(project, runtime, text=None):
    body = project / 'chapter_2_scene_3.txt'
    body.write_text(text or 'あ' * 1300, encoding='utf-8')
    result = cli('check_scene_output.py', '--project', project, '--text', body)
    assert result.returncode == 0, result.stdout + result.stderr
    return body, read(runtime / 'check_report.json')


def consumer(project, entry):
    body = project / 'chapter_2_scene_3.txt'
    if entry == 'draft': return cli('build_draft_prompt.py', '--project', project, '--scene', '2-3')
    if entry == 'expand': return cli('build_expand_prompt.py', '--project', project, '--draft_text', body, '--force')
    if entry == 'check': return cli('check_scene_output.py', '--project', project, '--text', body)
    return cli('approve_scene.py', '--project', project, '--scene', '2-3', '--allow-warnings', '--reviewer-type', 'automation', '--reviewer-id', 'synthetic-test')


@pytest.mark.parametrize('entry', ['draft', 'expand', 'check', 'approve'])
@pytest.mark.parametrize('change', ['missing', 'tamper', 'contract', 'policy', 'selection', 'pov'])
def test_all_consumers_reject_missing_or_changed_keyframes(tmp_path, entry, change):
    project, runtime, request, proposal_path = registered(tmp_path)
    body, report = scene_and_check(project, runtime, '短い本文。')
    if change == 'missing': (runtime / 'narrative_keyframes.json').unlink()
    elif change == 'tamper':
        path = runtime / 'narrative_keyframes.json'; path.write_text(path.read_text() + ' ')
    elif change == 'contract': (runtime / 'narrative_keyframe_contract.json').unlink()
    elif change == 'policy': write(project / 'narrative_keyframing.json', {'version': 1, 'enabled': False, 'disable_reason': '外的記録に変更。'})
    elif change == 'selection':
        selection = read(runtime / 'context_selection.json'); selection['keyframing']['status'] = 'disabled'; write(runtime / 'context_selection.json', selection)
    else: write(project / 'dialogue_voice.json', {'version': 1, 'characters': {}, 'scenes': {'2-3': {'pov_character_id': 'other'}}})
    result = consumer(project, entry)
    assert result.returncode != 0, result.stdout
    assert any(word in result.stdout.lower() for word in ['keyfram', 'stale', 'changed', 'prepare']), result.stdout


def test_check_auto_prepare_cannot_bypass_default_on(tmp_path):
    project = project_fixture(tmp_path)
    body = project / 'chapter_2_scene_3.txt'; body.write_text('あ' * 1300)
    result = consumer(project, 'check')
    assert result.returncode != 0 and 'pov-character' in result.stdout
    assert not (project / 'runtime/scenes/2-3/draft/check_report.json').exists()


def test_old_runtime_requires_same_scene_prepare(tmp_path):
    project, runtime, request, proposal_path = registered(tmp_path)
    body, report = scene_and_check(project, runtime)
    manifest = read(runtime / 'runtime_manifest.json'); manifest.pop('features'); write(runtime / 'runtime_manifest.json', manifest)
    for entry in ['draft', 'expand', 'check', 'approve']:
        result = consumer(project, entry)
        assert result.returncode != 0 and 'prepare' in result.stdout, result.stdout


def test_approval_remains_current_after_own_ledger_write(tmp_path):
    from novel_agent.approvals import approve_scene, validate_approval_current
    from novel_agent.exports import export_manuscript
    project, runtime, request, proposal_path = registered(tmp_path)
    body, report = scene_and_check(project, runtime)
    assert report['keyframing']['enabled'] is True
    assert all(r['kind'] != 'artifact' for r in report['check_inputs'])
    assert not any(r['path'] == 'runtime/approval_ledger.json' for r in report['check_inputs'])
    record = approve_scene(str(project), '2-3', allow_warnings=True, reviewer_type='agent', reviewer_id='fixture')
    assert record['keyframing'] == report['keyframing']
    assert record['keyframing_snapshot']['proposal'] == read(proposal_path)
    assert validate_approval_current(str(project), record)['status'] == 'approved'
    assert export_manuscript(str(project), include_warnings=True)['scenes'] == ['2-3']
    assert 'dependencies' not in json.dumps(record['keyframing_snapshot'])


def test_saved_snapshot_survives_artifact_ledger_loss_and_identical_reprepare(tmp_path):
    from novel_agent.approvals import approve_scene, validate_approval_current
    project, runtime, request, proposal_path = registered(tmp_path)
    scene_and_check(project, runtime)
    record = approve_scene(str(project), '2-3', allow_warnings=True)
    (project / 'runtime/artifact_ledger.json').unlink()
    assert validate_approval_current(str(project), record)['status'] == 'approved'
    prepare(project, '--pov-character', 'mira')
    assert validate_approval_current(str(project), record)['status'] == 'approved'
    result = read(runtime / 'narrative_keyframes.json'); result['proposal']['keyframes'][0]['response'] = '変えた返答。'; write(runtime / 'narrative_keyframes.json', result)
    assert validate_approval_current(str(project), record)['status'] == 'stale'


def test_approving_other_scene_does_not_stale_approval(tmp_path):
    from novel_agent.approvals import approve_scene, validate_approval_current
    project, runtime, request, proposal_path = registered(tmp_path)
    scene_and_check(project, runtime)
    record = approve_scene(str(project), '2-3', allow_warnings=True)
    # A second real approval modifies the shared ledger, not the first binding.
    from helpers.keyframe_fixtures import bind_disabled_check_fixture
    other_body = project / 'scene_3-1.txt'; other_body.write_text('別の場面。')
    from novel_agent.dependencies import snapshot_dependencies, dependency_digest
    from novel_agent.storage import text_content_hash
    guards = snapshot_dependencies(str(project), [{'kind': 'projection', 'selector': 'check_policy', 'scene_id': '3-1'}])
    other_report = dict(version=2, scope='scene', scene_id='3-1', source_path='scene_3-1.txt', source_hash=text_content_hash(str(other_body)),
        hash_algorithm='sha256-utf8-text-v1', check_inputs=guards, check_inputs_digest=dependency_digest(guards), status='pass')
    other_runtime = project / 'runtime/scenes/3-1/draft'; other_runtime.mkdir(parents=True)
    bind_disabled_check_fixture(project, other_runtime, other_report, scene_id='3-1', cli_only=True)
    write(other_runtime / 'check_report.json', other_report)
    approve_scene(str(project), '3-1')
    assert validate_approval_current(str(project), record)['status'] == 'approved'


def test_new_approval_rejects_old_check_without_binding(tmp_path):
    from novel_agent.approvals import approve_scene
    project, runtime, request, proposal_path = registered(tmp_path)
    body, report = scene_and_check(project, runtime)
    report.pop('keyframing', None); report.pop('keyframing_snapshot', None)
    write(runtime / 'check_report.json', report)
    with pytest.raises(UserFacingError, match='keyfram|recheck'):
        approve_scene(str(project), '2-3', allow_warnings=True)


def test_draft_expand_keep_material_and_referenced_source(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    proposal = read(proposal_path); proposal['keyframes'][0]['source_refs'] = ['continuity_pack.md']; write(proposal_path, proposal)
    register_keyframes(str(project), '2-3', str(proposal_path))
    result = consumer(project, 'draft')
    assert result.returncode == 0, result.stdout
    draft = (runtime / 'draft_prompt.txt').read_text()
    assert proposal['keyframes'][0]['interpretation'] in draft
    body, report = scene_and_check(project, runtime, '短い本文。')
    result = consumer(project, 'expand')
    assert result.returncode == 0, result.stdout
    expand = (runtime / 'expand_prompt.txt').read_text()
    assert proposal['keyframes'][0]['interpretation'] in expand
    assert '全文再掲や冒頭からの書き直しは禁止' in expand
    assert len(expand) <= 16000 and len(draft) <= 16000
    for field in ['final_prompt', 'expand_prompt']:
        selected = read(runtime / 'context_selection.json')[field]['selected']
        assert any('continuity_pack.md' in s['source_ids'] and s['required'] for s in selected)


def test_approval_snapshot_tamper_and_partial_extension_fail_closed(tmp_path):
    from novel_agent.approvals import approve_scene, validate_approval_current
    project, runtime, request, proposal_path = registered(tmp_path)
    scene_and_check(project, runtime)
    record = approve_scene(str(project), '2-3', allow_warnings=True)
    bad = copy.deepcopy(record); bad['keyframing_snapshot']['proposal']['keyframes'][0]['anchor'] = '改変'
    assert validate_approval_current(str(project), bad)['status'] == 'stale'
    for field in ['keyframing', 'keyframing_snapshot']:
        bad = copy.deepcopy(record); bad.pop(field)
        assert validate_approval_current(str(project), bad)['status'] == 'stale'


def test_prior_source_keyframing_change_invalidates_prepared_memory(tmp_path):
    from test_dialogue_context import memory_source_project, prepare_project
    project, _ = memory_source_project(tmp_path)
    runtime = prepare_project(project)
    assert 'STALE_APPROVAL_MEMORY' in (runtime / 'story_memory_pack.md').read_text()
    require_runtime_current(str(project), str(runtime))
    policy = read(project / 'narrative_keyframing.json')
    policy['scenes'] = {'2-1': {'enabled': True}}
    write(project / 'narrative_keyframing.json', policy)
    with pytest.raises(UserFacingError, match='stale'):
        require_runtime_current(str(project), str(runtime))


def test_approve_revalidates_after_review_before_write(tmp_path, monkeypatch):
    from novel_agent.approvals import approve_scene
    import novel_agent.dialogue_review as review
    project, runtime, request, proposal_path = registered(tmp_path)
    scene_and_check(project, runtime)
    original = review.require_dialogue_review
    def change_after_review(*args, **kwargs):
        value = original(*args, **kwargs)
        (runtime / 'narrative_keyframes.json').unlink()
        return value
    monkeypatch.setattr(review, 'require_dialogue_review', change_after_review)
    with pytest.raises(UserFacingError, match='changed|keyfram|stale'):
        approve_scene(str(project), '2-3', allow_warnings=True)
    assert not (project / 'runtime/approval_ledger.json').exists()


@pytest.mark.parametrize('entry', ['keyframe', 'draft', 'expand'])
def test_transient_consumed_pack_edit_is_not_blessed(tmp_path, monkeypatch, entry):
    """An editor's edit/undo must not pair consumed new text with old hashes."""
    import builtins
    import io
    import sys
    project, runtime, request, proposal_path = registered(tmp_path)
    if entry == 'expand': scene_and_check(project, runtime, '短い本文。')
    target = runtime / ('scene_brief_compact.md' if entry == 'keyframe' else 'style_contract_compact.md')
    original_open = builtins.open
    count = [0]
    marker = 'TRANSIENT FUTURE SECRET THAT WAS NEVER PREPARED'
    # Patch the actual consumption boundary, not all dependency observations.
    if entry == 'keyframe':
        import build_keyframe_prompt as module
        original = module.keyframe_source_sections
        def consume(*args, **kwargs):
            original_bytes = target.read_bytes()
            target.write_text(marker, encoding='utf-8')
            try: return original(*args, **kwargs)
            finally: target.write_bytes(original_bytes)
        monkeypatch.setattr(module, 'keyframe_source_sections', consume)
        call = lambda: module.build_keyframe_prompt(str(project), str(runtime), '2-3')
    else:
        if entry == 'draft':
            import build_draft_prompt as module
            args = ['build_draft_prompt.py', '--project', str(project), '--scene', '2-3']
        else:
            import build_expand_prompt as module
            args = ['build_expand_prompt.py', '--project', str(project), '--draft_text', str(project / 'chapter_2_scene_3.txt')]
        original = module.read_text_file
        def consume(path, *args, **kwargs):
            if Path(path) != target: return original(path, *args, **kwargs)
            original_bytes = target.read_bytes(); target.write_text(marker, encoding='utf-8')
            try: return original(path, *args, **kwargs)
            finally: target.write_bytes(original_bytes)
        monkeypatch.setattr(module, 'read_text_file', consume)
        monkeypatch.setattr(sys, 'argv', args)
        call = module.main
    with pytest.raises(UserFacingError, match='consumed|changed|stale|input'):
        call()


def test_rendered_material_in_consumer_obeys_3000_character_limit(tmp_path):
    from novel_agent.narrative_keyframes import render_keyframes
    from novel_agent.keyframe_runtime import register_keyframes, require_keyframing_current
    project, runtime, request, proposal_path = generated(tmp_path)
    proposal = read(proposal_path)
    first = proposal['keyframes'][0]
    proposal['keyframes'] = [dict(copy.deepcopy(first), id='kf{}'.format(i)) for i in range(1, 4)]
    fields = ['anchor', 'selection_reason', 'perception', 'interpretation', 'response', 'realization_note']
    # Fill only the valid text budget until the renderer is within a few chars
    # of its cap; consumers may not quietly append beyond that cap.
    for frame in proposal['keyframes']:
        for field in fields:
            while len(frame[field]) < 240:
                frame[field] += 'あ'
                try: render_keyframes(proposal)
                except UserFacingError:
                    frame[field] = frame[field][:-1]
                    break
    assert 2990 <= len(render_keyframes(proposal)) <= 3000
    write(proposal_path, proposal)
    register_keyframes(str(project), '2-3', str(proposal_path))
    current = require_keyframing_current(str(project), str(runtime), '2-3')
    assert len(current['prompt_section']['text']) <= 3000


@pytest.mark.parametrize('alias', ['chapter_2_scene_3', '02-03', ' 2-3 '])
@pytest.mark.parametrize('pipeline', [False, True])
def test_supported_scene_aliases_preserve_keyframe_identity(tmp_path, alias, pipeline):
    project, runtime, request, proposal_path = registered(tmp_path)
    command = ['run_scene_pipeline.py', 'prompt'] if pipeline else ['build_draft_prompt.py']
    result = cli(command[0], *command[1:], '--project', project, '--scene', alias)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Narrative Keyframes' in (runtime / 'draft_prompt.txt').read_text()


def test_policy_dependency_cannot_follow_symlink_outside_project(tmp_path):
    project = project_fixture(tmp_path)
    external = tmp_path / 'external-policy.json'
    write(external, {'version': 1, 'enabled': False, 'disable_reason': '別案件の外的記録。'})
    (project / 'narrative_keyframing.json').symlink_to(external)
    result = cli('build_runtime_context.py', '--project', project, '--chapter', 2, '--scene', '2-3', '--mode', 'draft')
    assert result.returncode != 0 and 'escap' in result.stdout.lower(), result.stdout
    assert not (project / 'runtime/scenes/2-3/draft/narrative_keyframe_contract.json').exists()


@pytest.mark.parametrize('mutation', ['remove_both', 'downgrade_version'])
def test_historical_keyframing_evidence_cannot_be_downgraded(tmp_path, mutation):
    from novel_agent.approvals import approve_scene, validate_approval_current
    project, runtime, request, proposal_path = registered(tmp_path)
    scene_and_check(project, runtime)
    record = approve_scene(str(project), '2-3', allow_warnings=True)
    if mutation == 'remove_both':
        record.pop('keyframing'); record.pop('keyframing_snapshot')
    else:
        record['version'] = 1
    assert validate_approval_current(str(project), record)['status'] == 'stale'


def test_failed_replacement_can_be_retried_from_external_proposal(tmp_path, monkeypatch):
    import novel_agent.keyframe_runtime as api
    project, runtime, request, proposal_path = registered(tmp_path)
    proposal = read(proposal_path); proposal['keyframes'][0]['response'] = '問いの順を変えて確かめよう。'; write(proposal_path, proposal)
    original = api._register_artifact_locked
    def fail(*args, **kwargs): raise UserFacingError('simulated ledger failure')
    monkeypatch.setattr(api, '_register_artifact_locked', fail)
    with pytest.raises(UserFacingError, match='ledger'):
        api.register_keyframes(str(project), '2-3', str(proposal_path))
    with pytest.raises(UserFacingError):
        api.require_keyframing_current(str(project), str(runtime), '2-3')
    monkeypatch.setattr(api, '_register_artifact_locked', original)
    api.register_keyframes(str(project), '2-3', str(proposal_path))
    assert api.require_keyframing_current(str(project), str(runtime), '2-3')['approval_snapshot']['proposal'] == proposal


@pytest.mark.parametrize('problem', ['duplicate_json_key', 'oversize', 'self_input', 'result_symlink'])
def test_untrusted_submission_boundaries(tmp_path, problem):
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    target = runtime / 'narrative_keyframes.json'
    if problem == 'duplicate_json_key':
        proposal_path.write_text(proposal_path.read_text().replace('"version": 1', '"version": 1, "version": 1'))
    elif problem == 'oversize': proposal_path.write_bytes(b' ' * 65537)
    elif problem == 'self_input':
        target.write_bytes(proposal_path.read_bytes()); proposal_path = target
    else:
        outside = tmp_path / 'outside-result.json'; outside.write_text('must stay unchanged')
        target.symlink_to(outside)
    before = tree_bytes(project)
    with pytest.raises(UserFacingError):
        register_keyframes(str(project), '2-3', str(proposal_path))
    assert tree_bytes(project) == before


def test_explicit_external_proposal_and_crlf_unicode_are_supported(tmp_path):
    from novel_agent.keyframe_runtime import register_keyframes, require_keyframing_current
    project, runtime, request, proposal_path = generated(tmp_path)
    external = tmp_path / '提案.json'
    external.write_bytes(json.dumps(read(proposal_path), ensure_ascii=False, indent=2).replace('\n', '\r\n').encode('utf-8'))
    register_keyframes(str(project), '2-3', str(external))
    assert require_keyframing_current(str(project), str(runtime), '2-3')['approval_snapshot']['proposal'] == read(proposal_path)


def test_budget_omitted_source_cannot_be_referenced(tmp_path, monkeypatch):
    import build_keyframe_prompt as module
    from novel_agent.keyframe_runtime import register_keyframes
    project = project_fixture(tmp_path); runtime = prepare(project, '--pov-character', 'mira')
    original = module.assemble_prompt
    def required_only(sections):
        minimum = original([s for s in sections if s['required']])['chars']
        return original(sections, max_chars=minimum)
    monkeypatch.setattr(module, 'assemble_prompt', required_only)
    request = module.build_keyframe_prompt(str(project), str(runtime), '2-3')
    assert 'continuity_pack.md' not in request['sources']
    assert any('continuity_pack.md' in s['source_ids'] for s in read(runtime / 'context_selection.json')['keyframe_prompt']['omitted'])
    proposal = valid_proposal(request); proposal['keyframes'][0]['source_refs'] = ['continuity_pack.md']
    proposal_path = project / 'proposal.json'; write(proposal_path, proposal)
    with pytest.raises(UserFacingError, match='source'):
        register_keyframes(str(project), '2-3', str(proposal_path))


def test_future_and_other_pov_knowledge_are_not_generation_sources(tmp_path):
    from build_keyframe_prompt import build_keyframe_prompt
    from test_story_memory import approved_scene, accept, proposal, fact
    project = project_fixture(tmp_path)
    past = approved_scene(project, '1-1', 'AUTHOR_ONLY秘密。')
    future = approved_scene(project, '9-1', 'FUTURE_ONLY秘密。')
    accept(project, proposal(fact(past, 'author_fact', text='AUTHOR_ONLY秘密。'),
        fact(past, 'other_knowledge', kind='character_knowledge', character_id='other', fact_id='author_fact', text='別人だけが知る。'),
        fact(future, 'future_fact', scene='9-1', text='FUTURE_ONLY秘密。')))
    runtime = prepare(project, '--pov-character', 'mira')
    request = build_keyframe_prompt(str(project), str(runtime), '2-3')
    assert request['sources']['author_fact'] == 'author_context'
    assert 'other_knowledge' not in request['sources'] and 'future_fact' not in request['sources']
    text = (runtime / 'narrative_keyframe_prompt.txt').read_text()
    assert 'FUTURE_ONLY' not in text and 'author_context' in text


def test_referenced_source_budget_failure_leaves_no_draft(tmp_path, monkeypatch):
    import build_draft_prompt as module
    import sys
    from novel_agent.keyframe_runtime import register_keyframes
    project, runtime, request, proposal_path = generated(tmp_path)
    proposal = read(proposal_path); proposal['keyframes'][0]['source_refs'] = ['continuity_pack.md']; write(proposal_path, proposal)
    register_keyframes(str(project), '2-3', str(proposal_path))
    original = module.assemble_prompt
    def without_reference_budget(sections):
        budget = original([s for s in sections if s['required'] and 'continuity_pack.md' not in s['source_ids']])['chars']
        return original(sections, max_chars=budget)
    monkeypatch.setattr(module, 'assemble_prompt', without_reference_budget)
    monkeypatch.setattr(sys, 'argv', ['build_draft_prompt.py', '--project', str(project), '--scene', '2-3'])
    with pytest.raises(UserFacingError, match='budget'):
        module.main()
    assert not (runtime / 'draft_prompt.txt').exists()
