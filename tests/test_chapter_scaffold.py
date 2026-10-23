"""Opt-in chapter counts retain the old layout when omitted."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from novel_agent.chapter_scaffold import render_chapter_cards, chapter_directory_name
from prompt_utils import UserFacingError, extract_chapter_block, parse_scene_ledger, parse_scene_reference, suggest_scene_output_path


def initialize(path, count=None):
    command = [sys.executable, str(SCRIPTS / 'init_project.py'), str(path), '--target-total-chars', '200000']
    if count is not None:
        command += ['--chapter-count', str(count)]
    return subprocess.run(command, capture_output=True, text=True)


@pytest.mark.parametrize('count', [3, 5, 20])
def test_explicit_chapters_match_directories_and_empty_cards(tmp_path, count):
    project = tmp_path / 'explicit'
    result = initialize(project, count)
    assert result.returncode == 0, result.stdout + result.stderr
    outline = (project / '05_chapter_outline.md').read_text()
    assert re.findall(r'^## 第(\d+)章 Chapter Card$', outline, re.M) == [str(i) for i in range(1, count + 1)]
    assert {p.name for p in project.glob('chapter_*')} == {'chapter_{}'.format(i) for i in range(1, count + 1)}
    assert not (project / 'chapter_card.md').exists()
    for chapter in range(1, count + 1):
        assert parse_scene_ledger(extract_chapter_block(outline, chapter)) == []
        assert '- part_id:' in extract_chapter_block(outline, chapter)
    ref = parse_scene_reference('{}-1'.format(count))
    assert Path(suggest_scene_output_path(str(project), ref)).parent.name == 'chapter_{}'.format(count)
    result = subprocess.run([sys.executable, str(SCRIPTS / 'build_runtime_context.py'), '--project', str(project), '--chapter', str(count), '--scene', ref['canonical_id'], '--mode', 'draft'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / 'runtime/scenes' / ref['canonical_id'] / 'draft/scene_brief_compact.md').exists()


def test_default_five_chapter_layout_unchanged(tmp_path):
    project = tmp_path / 'default'
    result = initialize(project)
    assert result.returncode == 0, result.stdout + result.stderr
    assert {p.name for p in project.glob('chapter_*')} == {
        'chapter_1_introduction', 'chapter_2_rising_action', 'chapter_3_complication', 'chapter_4_climax', 'chapter_5_resolution'}
    outline = (project / '05_chapter_outline.md').read_text()
    assert len(parse_scene_ledger(extract_chapter_block(outline, 1))) == 3
    assert '主人公と世界の提示' in outline


def test_chapter_12_output_path_uses_its_directory(tmp_path):
    (tmp_path / 'chapter_12').mkdir()
    ref = parse_scene_reference('12-1')
    assert Path(suggest_scene_output_path(str(tmp_path), ref)) == tmp_path / 'chapter_12/chapter_12_scene_1.txt'


@pytest.mark.parametrize('count', [0, -1])
def test_zero_or_negative_chapter_count_rejected(tmp_path, count):
    path = tmp_path / 'bad'
    assert initialize(path, count).returncode != 0
    assert not path.exists()
    with pytest.raises(UserFacingError):
        render_chapter_cards(count, card_template='第{{CHAPTER_NUMBER}}章')


def test_ambiguous_chapter_directory_is_not_guessed(tmp_path):
    (tmp_path / 'chapter_1').mkdir()
    (tmp_path / 'chapter_1_introduction').mkdir()
    with pytest.raises(UserFacingError, match='ambiguous'):
        suggest_scene_output_path(str(tmp_path), parse_scene_reference('1-2'))
    (tmp_path / 'chapter_1/scene_1-1.txt').write_text('唯一の既筆本文')
    assert Path(suggest_scene_output_path(str(tmp_path), parse_scene_reference('1-2'))).parent == tmp_path / 'chapter_1'
    (tmp_path / 'chapter_1_introduction/scene_1-3.txt').write_text('別の配置')
    with pytest.raises(UserFacingError, match='ambiguous'):
        suggest_scene_output_path(str(tmp_path), parse_scene_reference('1-2'))


def test_directory_name_helper_preserves_legacy_names():
    assert chapter_directory_name(3, legacy_layout=True) == 'chapter_3_complication'
    assert chapter_directory_name(12, legacy_layout=False) == 'chapter_12'


def test_outline_export_order_is_numeric_for_twenty_chapters(tmp_path):
    from novel_agent.exports import _outline_scene_order
    project = tmp_path / 'ordered'
    assert initialize(project, 20).returncode == 0
    path = project / '05_chapter_outline.md'
    text = path.read_text()
    for chapter in range(1, 21):
        block = extract_chapter_block(text, chapter)
        marker = '|---|---|---|---|---|---:|---:|---:|---|---|'
        updated = block.replace(marker, marker + '\n| {}-1 | standard |  |  |  | 1600 | 2000 | 2400 | - | planned |'.format(chapter))
        text = text.replace(block, updated)
    path.write_text(text)
    assert _outline_scene_order(str(project)) == ['{}-1'.format(i) for i in range(1, 21)]
