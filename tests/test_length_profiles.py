"""Canonical target profiles, including legacy fallback and scene-band compatibility."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from prompt_utils import UserFacingError, resolve_scene_type_band
from novel_agent.length_profiles import (
    TARGET_PROFILE_SPECS, build_target_profile_payload, compute_gate_threshold,
    compute_target_length_profile, resolve_target_profile_from_state,
)


@pytest.mark.parametrize('total,profile,gate', [
    (30000, 'novel_30k', 24000), (50000, 'novel_50k', 40000),
    (100000, 'novel_100k', 80000), (200000, 'novel_200k', 160000),
])
def test_profile_contract(total, profile, gate):
    assert compute_target_length_profile(total) == profile
    assert compute_gate_threshold(total) == gate
    assert build_target_profile_payload(total, source='test')['planning_target_total_chars'] == total
    assert set(TARGET_PROFILE_SPECS) == {30000, 50000, 100000, 200000}


def test_unsupported_and_conflicting_canonical_values_rejected():
    for text in ['targets:\n  target_total_chars: 120000\n',
                 'targets:\n  target_total_chars: 200000\n  target_length_profile: novel_100k\n',
                 'targets:\n  target_total_chars: nonsense\n']:
        with pytest.raises(UserFacingError):
            resolve_target_profile_from_state(text)
    with pytest.raises(UserFacingError):
        compute_target_length_profile(True)


def test_canonical_wins_over_legacy_and_legacy_100k_still_reads():
    text = 'targets:\n  target_total_chars: 200000\n  planning_target_total_chars: 100000\n  total_chars: 100000\n  length_mode: long_form_100k\n'
    assert resolve_target_profile_from_state(text)['target_total_chars'] == 200000
    assert resolve_target_profile_from_state('targets:\n  length_mode: long_form_100k\n')['target_total_chars'] == 100000


def test_initialize_200k_preserves_scene_type_bands(tmp_path):
    project = tmp_path / '長編'
    result = subprocess.run([sys.executable, str(SCRIPTS / 'init_project.py'), str(project), '--target-total-chars', '200000'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    state = (project / 'agent/state_schema_novel.yaml').read_text()
    assert resolve_target_profile_from_state(state)['planning_gate_min_chars'] == 160000
    assert resolve_scene_type_band('standard', state_schema_text=state) == {'scene_type': 'standard', 'min': 1600, 'target': 2000, 'max': 2400}
    assert len(list(project.glob('chapter_*'))) == 5
