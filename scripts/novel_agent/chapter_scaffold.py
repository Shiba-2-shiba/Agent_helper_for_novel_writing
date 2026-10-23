"""Opt-in numeric chapter scaffolds; no existing project is re-rendered."""
import re

from novel_agent.errors import UserFacingError

LEGACY_CHAPTER_NAMES = {
    1: 'chapter_1_introduction', 2: 'chapter_2_rising_action',
    3: 'chapter_3_complication', 4: 'chapter_4_climax',
    5: 'chapter_5_resolution',
}


def _positive(value):
    if type(value) is not int or value < 1:
        raise UserFacingError('chapter count/number must be a positive integer')


def chapter_directory_name(chapter: int, *, legacy_layout: bool) -> str:
    _positive(chapter)
    return LEGACY_CHAPTER_NAMES.get(chapter, 'chapter_{}'.format(chapter)) if legacy_layout else 'chapter_{}'.format(chapter)


def render_chapter_cards(chapter_count: int, *, card_template: str) -> str:
    _positive(chapter_count)
    return '\n\n---\n\n'.join(card_template.replace('{{CHAPTER_NUMBER}}', str(chapter)).strip() for chapter in range(1, chapter_count + 1)) + '\n\n---\n\n'


def render_outline_chapters(outline_template: str, chapter_count: int, *, card_template: str) -> str:
    """Retain common header/tail; replace only template sample chapter cards."""
    _positive(chapter_count)
    first = re.search(r'(?m)^## 第\d+章 Chapter Card$', outline_template)
    tail = re.search(r'(?m)^## Planning Totals$', outline_template)
    if not first or not tail or tail.start() <= first.start():
        raise UserFacingError('outline template is missing Chapter Card or Planning Totals boundaries')
    return outline_template[:first.start()] + render_chapter_cards(chapter_count, card_template=card_template) + outline_template[tail.start():]
