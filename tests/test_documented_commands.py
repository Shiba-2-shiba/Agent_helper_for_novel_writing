"""Executable documentation contracts; no real author project is modified."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_entry_links_resolve():
    entry = ROOT / 'AGENTS.md'
    assert entry.is_file()
    for path in ['agent/HUB.md', 'agent/AGENT_GUIDE.md',
                 'docs/long_novel_workflow.md', 'docs/story_memory_format.md',
                 'docs/migrate_100k_to_200k.md']:
        assert (ROOT / path).is_file(), path
    assert 'agent/HUB.md' in entry.read_text(encoding='utf-8')


@pytest.mark.parametrize('script,options', [
    ('init_project.py', ['--target-total-chars', '200000', '--chapter-count']),
    ('build_draft_prompt.py', ['--scene']),
    ('build_runtime_context.py', ['--pov-character', '--entity', '--thread']),
    ('migrate_project_state.py', ['--dry-run', '--apply-plan', '--expected-plan-hash', '--rollback']),
    ('import_story_memory.py', ['--input', '--validate-only']),
    ('review_story_memory.py', ['--batch', '--accept', '--expected-revision']),
])
def test_documented_cli_options_exist(script, options):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    for option in options:
        assert option in result.stdout, (script, option)


def test_current_guides_separate_machine_and_semantic_quality():
    text = (ROOT / 'docs/long_novel_workflow.md').read_text(encoding='utf-8')
    assert '機械検査' in text and '文学的' in text
    assert '未実施' in text
    memory = (ROOT / 'docs/story_memory_format.md').read_text(encoding='utf-8')
    assert '承認済み' in memory and 'supersedes' in memory
    assert '未来' in memory and '明示' in memory


def test_bootstrap_lists_all_supported_profiles():
    from novel_agent.length_profiles import TARGET_PROFILE_SPECS
    text=(ROOT/'agent/skills/project-bootstrap/SKILL.md').read_text(encoding='utf-8')
    for profile in TARGET_PROFILE_SPECS.values():
        assert profile['target_length_profile'] in text
