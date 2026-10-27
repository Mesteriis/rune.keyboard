"""Authored instrumental-noun/predicate competition after a left copula.

Wider spelling contrasts are declarations only: training selection must obtain
both forms in a complete native pool. No one-edit cost is invented for the
two/three-edit predicate competitor. Natural calibration is never consulted.
"""
import hashlib
import json

from grammar_contrast_corpus import one_edit_words
from prepare_word_ranking import distance

PAIRS = (
    ('зол', 'зал', 'здания'), ('зол', 'пол', 'здания'),
    ('силён', 'салон', 'красоты'), ('слаб', 'штаб', 'объединения'),
    ('верен', 'ветер', 'перемен'), ('важен', 'вагон', 'поезда'),
    ('щедр', 'кедр', 'леса'),
    ('умён', 'ум', 'города'), ('богат', 'бог', 'войны'),
    ('беден', 'беда', 'района'), ('болен', 'боль', 'утраты'),
)


def generate(lexicon, paradigms, *, pairs=PAIRS):
    rows = {}; skipped = []
    for adjective, noun, complement in pairs:
        adjective_tags = tuple(lexicon.analyses(adjective))
        noun_tags = tuple(lexicon.analyses(noun))
        lemmas = {a.lemma for a in adjective_tags if a.pos == 'ADJS' and a.number == 'sing' and a.gender == 'masc'}
        noun_lemmas = {a.lemma for a in noun_tags if a.pos == 'NOUN' and a.case == 'nomn' and a.number == 'sing'}
        if len(lemmas) != 1 or not noun_lemmas or not any(
                a.pos == 'NOUN' and a.case == 'gent' for a in lexicon.analyses(complement)):
            raise ValueError('INSTRUMENTAL_CORPUS_DICTIONARY')
        forms = []
        for word in paradigms.get(noun, ()):
            tags = tuple(lexicon.analyses(word))
            if tags and all(a.pos == 'NOUN' and a.case == 'ablt' and a.number == 'sing'
                            and a.lemma in noun_lemmas for a in tags):
                forms.append(word)
        if not forms:
            skipped.append(dict(noun=noun, reason='NO_PURE_INSTRUMENTAL_FORM'))
            continue
        instrumental = min(forms, key=lambda word: (len(word), word))
        variants = [word for word in one_edit_words(instrumental) if 3 <= len(word) <= 32
                    and 1 <= distance(word, adjective) <= 3 and not lexicon.analyses(word)]
        variants.sort(key=lambda word: (distance(word, adjective), hashlib.sha256(
            ('instrumental-contrast-v1:' + word).encode()).hexdigest()))
        variants = variants[:24]
        if not variants:
            skipped.append(dict(noun=noun, reason='NO_UNKNOWN_BOUNDED_CONTRAST'))
            continue
        family = next(iter(lemmas))
        families = sorted({a.lemma for a in adjective_tags} | noun_lemmas)

        def add(original, applied, target, left, right, kind, scenario):
            row = dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train', language='ru',
                family=family, contrastFamilies=families, original=original, applied=applied,
                expectedApplied=target, leftContext=left, rightContext=right,
                candidateForms=[adjective, instrumental], kind=kind, scenario=scenario,
                authoringProfile='instrumental-contrast-v1')
            if kind != 'correct_original':
                row['contrastUnitDistances'] = [distance(original, w) for w in (adjective, instrumental)]
            row['id'] = 'right-instrumental-' + hashlib.sha256(
                json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            rows[row['id']] = row

        for left in ('он был ', 'раньше он был '):
            for target, right, scenario in (
                    (instrumental, ' ' + complement + '.', 'instrumental_noun_genitive_complement'),
                    (adjective, ' всегда.', 'predicate_after_left_copula')):
                for original in variants:
                    for applied in (original, adjective, instrumental):
                        add(original, applied, target, left, right, 'unknown_original', scenario)
                for original in (adjective, instrumental):
                    add(original, original, original, left, right, 'correct_original', scenario)
            for original in variants:
                for applied in (original, adjective, instrumental):
                    add(original, applied, applied, left, ' ', 'insufficient_right_evidence', 'instrumental_unfinished_suffix')
    if not rows:
        raise ValueError('EMPTY_INSTRUMENTAL_CORPUS')
    return list(rows.values()), skipped
