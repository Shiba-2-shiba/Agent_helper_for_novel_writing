import json

import pytest

from novel_agent.errors import UserFacingError
from prompt_utils import find_scene_file, parse_scene_reference, resolve_runtime_dir


def brief(path, scene_id):
    path.mkdir(parents=True)
    (path / 'scene_brief_compact.md').write_text('# Brief\n- Scene ID: ' + scene_id + '\n')


def test_explicit_runtime_mismatch_rejected(tmp_path):
    runtime = tmp_path / 'runtime' / 'scenes' / '1-1' / 'draft'
    brief(runtime, '1-1')
    with pytest.raises(UserFacingError):
        resolve_runtime_dir(str(tmp_path), mode='draft', scene_ref=parse_scene_reference('1-2'), runtime_dir_arg=str(runtime))


def test_missing_scene_runtime_never_uses_latest_other_scene(tmp_path):
    runtime = tmp_path / 'runtime' / 'scenes' / '1-1' / 'draft'
    brief(runtime, '1-1')
    (tmp_path / 'runtime' / 'runtime_index.json').write_text(json.dumps({'latest_by_mode': {'draft': {'runtime_dir': str(runtime)}}}))
    with pytest.raises(UserFacingError):
        resolve_runtime_dir(str(tmp_path), mode='draft', scene_ref=parse_scene_reference('1-2'))


def test_legacy_flat_matching_scene_works(tmp_path):
    runtime = tmp_path / 'runtime'
    brief(runtime, '1-1')
    assert resolve_runtime_dir(str(tmp_path), mode='draft', scene_ref=parse_scene_reference('1-1')) == str(runtime)


def test_duplicate_scene_paths_rejected(tmp_path):
    (tmp_path / 'scene_1-1.txt').write_text('A')
    (tmp_path / 'chapter_1_scene_1.txt').write_text('B')
    with pytest.raises(UserFacingError):
        find_scene_file(str(tmp_path), parse_scene_reference('1-1'))


def test_latest_runtime_index_must_match_manifest_identity(tmp_path):
    from novel_agent.runtime_paths import write_runtime_manifest
    runtime = tmp_path / 'runtime/scenes/1-1/draft'
    brief(runtime, '1-1')
    write_runtime_manifest(str(tmp_path), str(runtime), scene_id='1-1', mode='draft', files=[], inputs=[])
    (tmp_path / 'runtime/runtime_index.json').write_text(json.dumps({'latest_by_mode': {'draft': {'scene_id': '1-2', 'runtime_dir': str(runtime)}}}))
    with pytest.raises(UserFacingError, match='identity'):
        resolve_runtime_dir(str(tmp_path), mode='draft')
