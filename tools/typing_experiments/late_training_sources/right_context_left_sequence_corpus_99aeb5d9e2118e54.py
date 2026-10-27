"""Authored finite/linking/coordination contrasts, never natural calibration.

Reuse dictionary-certified forms and corruption profiles from applied-role
authoring. Rows still require actual complete native retrieval before training;
candidateForms is a contrast declaration, not permission to inject candidates.
"""
import hashlib
import json

from right_context_applied_corpus import generate as generate_applied
from right_context_contrast_corpus import PAIRS

_FRAMES = {
    'full_adjective_attributive': (
        ('появилась ', 'full_after_ordinary_finite'),
        ('умная и не ', 'full_adjective_coordination'),
        ('умная, но очень ', 'full_adjective_adversative_degree'),
    ),
    'short_predicate_degree_question': (
        ('оказалась ', 'short_after_linking_finite'),
        ('умна и не ', 'short_predicate_coordination'),
        ('умна, но очень ', 'short_predicate_adversative_degree'),
    ),
}


def generate(lexicon, paradigms, *, pairs=PAIRS):
    parents, skipped = generate_applied(lexicon, paradigms, pairs=pairs)
    rows = {}
    for parent in parents:
        scenario = parent['scenario'].removesuffix('_unfinished_clause')
        for left, frame in _FRAMES.get(scenario, ()):
            row = dict(parent)
            row.pop('id')
            row['leftContext'] = left
            row['scenario'] = frame + ('_unfinished_clause' if parent['kind'] == 'insufficient_right_evidence' else '')
            row['authoringProfile'] = 'left-sequence-v1'
            row['id'] = 'right-left-sequence-' + hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            rows[row['id']] = row
    if not rows:
        raise ValueError('EMPTY_LEFT_SEQUENCE_CORPUS')
    return list(rows.values()), skipped
