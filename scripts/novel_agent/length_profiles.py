"""Single source of truth for supported novel lengths and planning gates."""
import re

from novel_agent.errors import UserFacingError


TARGET_PROFILE_SPECS = {
    30000: {'target_length_profile': 'novel_30k', 'planning_gate_min_chars': 24000},
    50000: {'target_length_profile': 'novel_50k', 'planning_gate_min_chars': 40000},
    100000: {'target_length_profile': 'novel_100k', 'planning_gate_min_chars': 80000},
    200000: {'target_length_profile': 'novel_200k', 'planning_gate_min_chars': 160000},
}
TARGET_TOTAL_CHARS_BY_PROFILE = {
    spec['target_length_profile']: total for total, spec in TARGET_PROFILE_SPECS.items()
}


def compute_target_length_profile(target_total_chars: int) -> str:
    if type(target_total_chars) is not int or target_total_chars not in TARGET_PROFILE_SPECS:
        raise UserFacingError('unsupported target_total_chars: {}'.format(target_total_chars))
    return TARGET_PROFILE_SPECS[target_total_chars]['target_length_profile']


def compute_gate_threshold(target_total_chars: int) -> int:
    compute_target_length_profile(target_total_chars)
    return TARGET_PROFILE_SPECS[target_total_chars]['planning_gate_min_chars']


def _compute_target_total_chars_from_profile(target_length_profile: str) -> int:
    if target_length_profile not in TARGET_TOTAL_CHARS_BY_PROFILE:
        raise UserFacingError('unsupported target_length_profile: {}'.format(target_length_profile))
    return TARGET_TOTAL_CHARS_BY_PROFILE[target_length_profile]


def build_target_profile_payload(target_total_chars: int, *, source: str, planning_gate_enabled: bool = True) -> dict:
    return {
        'target_total_chars': target_total_chars,
        'target_length_profile': compute_target_length_profile(target_total_chars),
        'planning_gate_enabled': bool(planning_gate_enabled),
        'planning_gate_min_chars': compute_gate_threshold(target_total_chars),
        'planning_target_total_chars': target_total_chars,
        'source': source,
    }


def _scalar(text, key):
    matches = re.findall(r'(?m)^\s*' + re.escape(key) + r':[^\S\r\n]*(.*?)[^\S\r\n]*(?:#.*)?$', text)
    if len(matches) > 1:
        raise UserFacingError('duplicate target field: {}'.format(key))
    return matches[0].strip().strip('"\'') if matches else ''


def resolve_target_profile_from_state(state_schema_text: str, *, fallback_total_chars: int = 100000) -> dict:
    raw_total = _scalar(state_schema_text, 'target_total_chars')
    profile = _scalar(state_schema_text, 'target_length_profile')
    gate_raw = _scalar(state_schema_text, 'planning_gate_enabled').lower()
    gate_enabled = gate_raw not in {'false', 'no', 'off', '0'}
    if raw_total:
        if not re.fullmatch(r'\d+', raw_total):
            raise UserFacingError('invalid target_total_chars: {}'.format(raw_total))
        total = int(raw_total)
        result = build_target_profile_payload(total, source='canonical_state', planning_gate_enabled=gate_enabled)
        if profile and _compute_target_total_chars_from_profile(profile) != total:
            raise UserFacingError('target_total_chars and target_length_profile conflict')
        return result
    if profile:
        return build_target_profile_payload(_compute_target_total_chars_from_profile(profile), source='canonical_state', planning_gate_enabled=gate_enabled)
    for key, source in [('planning_target_total_chars', 'legacy_planning_target'), ('total_chars', 'legacy_total_chars')]:
        raw = _scalar(state_schema_text, key).replace(',', '')
        if raw.isdigit() and int(raw) in TARGET_PROFILE_SPECS:
            return build_target_profile_payload(int(raw), source=source)
    if _scalar(state_schema_text, 'length_mode') == 'long_form_100k':
        return build_target_profile_payload(100000, source='legacy_length_mode')
    return build_target_profile_payload(fallback_total_chars, source='fallback')
