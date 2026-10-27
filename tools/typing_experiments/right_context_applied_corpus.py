"""Authored full/short-adjective role contrasts in existing training families.

Both retention and repair are represented, including a wrong full adjective
repaired to a short predicate. No natural failure words/sentences, label-based
candidate injection or rule that every role transition is wrong.
"""
import hashlib
import json

from grammar_contrast_corpus import shared_variants, one_edit_cost
from right_context_contrast_corpus import PAIRS

_FRAMES = (
    ('это ', 'full_adjective_attributive', 'full'),
    ('вот эта ', 'full_adjective_with_modifier', 'full'),
    ('насколько ', 'short_predicate_degree_question', 'short'),
    ('почему ', 'short_predicate_reason_question', 'short'),
)


def generate(lexicon, paradigms, *, pairs=PAIRS):
    rows = {}
    skipped = []
    for masculine, _ in pairs:
        lemmas = {a.lemma for a in lexicon.analyses(masculine) if a.pos == 'ADJS' and a.number == 'sing' and a.gender == 'masc'}
        if len(lemmas) != 1:
            raise ValueError('APPLIED_CORPUS_PARADIGM')
        family = next(iter(lemmas))
        forms = {}
        for key, part in [('short', 'ADJS'), ('full', 'ADJF')]:
            forms[key] = sorted({word for word in paradigms.get(masculine, ()) if any(
                a.pos == part and a.lemma == family and a.number == 'sing' and a.gender == 'femn'
                and not {'Supr', 'Cmp2'} & set(getattr(a, 'grammemes', ()))
                and (part == 'ADJS' or a.case == 'nomn') for a in lexicon.analyses(word))},
                key=lambda word: (len(word), word))
        if not forms['short'] or not forms['full']:
            skipped.append(dict(family=family, reason='MISSING_FULL_OR_SHORT_FORM'))
            continue
        short, full = forms['short'][0], forms['full'][0]
        variants = [word for word in shared_variants(short, full, lexicon, edit_profiles=True) if 3 <= len(word) <= 32][:2]
        if not variants:
            skipped.append(dict(family=family, reason='NO_SHARED_UNKNOWN_CORRUPTION'))
            continue

        def add(original, applied, target, left, right, kind, scenario):
            row = dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train', language='ru',
                family=family, original=original, applied=applied, expectedApplied=target,
                candidateForms=[short, full], leftContext=left, rightContext=right,
                kind=kind, scenario=scenario)
            if kind != 'correct_original':
                row['contrastEditCosts'] = [one_edit_cost(original, word) for word in (short, full)]
            row['id'] = 'right-applied-role-' + hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            rows[row['id']] = row

        for left, scenario, role in _FRAMES:
            target = short if role == 'short' else full
            suffix = ' девочка?' if role == 'short' else ' девочка.'
            for original in variants:
                for applied in (original, short, full):
                    add(original, applied, target, left, suffix, 'unknown_original', scenario)
                    add(original, applied, applied, left, ' девочка ', 'insufficient_right_evidence', scenario + '_unfinished_clause')
            for original in (short, full):
                for right in (suffix, ' девочка '):
                    add(original, original, original, left, right, 'correct_original', scenario)
    if not rows:
        raise ValueError('EMPTY_APPLIED_ROLE_CORPUS')
    return list(rows.values()), skipped
