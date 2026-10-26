"""Authored training-only previous-predicate revisions from completed right context.

This is not an independent qualification set or a source-admission certificate.
Every row explicitly names the original input and already applied word. Correct
originals and insufficient evidence must retain that applied word, even when a
surface grammar match would favor the rival. No disclosed failure is training.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from grammar_contrast_corpus import shared_variants, one_edit_cost

PAIRS = (
    ('беден', 'бедны'), ('богат', 'богаты'), ('силён', 'сильны'), ('слаб', 'слабы'),
    ('здоров', 'здоровы'), ('болен', 'больны'), ('умён', 'умны'), ('глуп', 'глупы'),
    ('красив', 'красивы'), ('счастлив', 'счастливы'), ('несчастен', 'несчастны'),
    ('весел', 'веселы'), ('серьёзен', 'серьёзны'), ('опасен', 'опасны'),
    ('полезен', 'полезны'), ('важен', 'важны'), ('нужен', 'нужны'),
    ('верен', 'верны'), ('правдив', 'правдивы'), ('честен', 'честны'),
    ('вежлив', 'вежливы'), ('скромен', 'скромны'), ('щедр', 'щедры'), ('зол', 'злы'),
)
CONTEXTS = (('к тому времени ', ' будет он ', ' будут они '),
            ('тогда ', ' был он ', ' были они '), ('', ' он ', ' они '))
COPULA_CONTEXTS = (('к тому времени ', ' будет ', ' будут '),
                   ('тогда ', ' был ', ' были '),
                   ('как оказалось ', ' будет завтра ', ' будут завтра '),
                   ('к тому времени ', ' будет не только он ', ' будут не только они '))
WEAK_SUFFIXES = (' ', ' бу', ' будет', ', будут ', ' будут_тест ', ' где они ')


def _paradigm(lexicon, singular, plural):
    left = [a for a in lexicon.analyses(singular) if a.pos == 'ADJS' and a.number == 'sing' and a.gender == 'masc']
    right = [a for a in lexicon.analyses(plural) if a.pos == 'ADJS' and a.number == 'plur']
    lemmas = {a.lemma for a in left} & {a.lemma for a in right}
    if not left or not right or len(lemmas) != 1:
        raise ValueError('RIGHT_CONTEXT_PARADIGM_MISMATCH:' + singular)
    return next(iter(lemmas))


def generate(lexicon, *, copula_coverage=False):
    rows, skipped = [], []
    for singular, plural in PAIRS:
        lemma = _paradigm(lexicon, singular, plural)
        variants = shared_variants(singular, plural, lexicon, edit_profiles=True)
        if not variants:
            skipped.append(dict(forms=[singular, plural], reason='NO_UNKNOWN_SHARED_ONE_EDIT'))
            continue
        def add(original, applied, target, prefix, suffix, kind):
            row = dict(purpose='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY', split='train', language='ru',
                       family=lemma, original=original, applied=applied, expectedApplied=target,
                       leftContext=prefix, rightContext=suffix, candidateForms=[singular, plural], kind=kind)
            if kind != 'correct_original':
                row['contrastEditCosts'] = [one_edit_cost(original, w) for w in (singular, plural)]
            row['id'] = 'right-context-' + hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            rows.append(row)
        contexts = CONTEXTS + COPULA_CONTEXTS if copula_coverage else CONTEXTS
        for prefix, singular_right, plural_right in contexts:
            for target, suffix in [(singular, singular_right), (plural, plural_right)]:
                for typo in variants:
                    for applied in (singular, plural):
                        add(typo, applied, target, prefix, suffix, 'unknown_original')
                for original in (singular, plural):
                    add(original, original, original, prefix, suffix, 'correct_original')
        for suffix in WEAK_SUFFIXES:
            for typo in variants:
                for applied in (singular, plural):
                    add(typo, applied, applied, '', suffix, 'insufficient_right_evidence')
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('EMPTY_OR_DUPLICATE_RIGHT_CONTEXT_CONTRASTS')
    return rows, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New directory, never overwritten')
    parser.add_argument('--copula-coverage', action='store_true', help='Include copula-only and intervening-word contrasts')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon()
    rows, skipped = generate(lexicon, copula_coverage=args.copula_coverage)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()
    manifest = dict(schema=1, purpose='TRAINING_ONLY_NOT_QUALIFICATION',
                    origin='Authored templates, dictionary-only paradigms; no owner or downloaded sentence text',
                    copulaCoverage=args.copula_coverage, rows=len(rows), families=len({r['family'] for r in rows}), skipped=skipped,
                    corpusSha256=hashlib.sha256(payload).hexdigest(),
                    generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    corruptionSelectorSha256=hashlib.sha256(Path(__file__).with_name('grammar_contrast_corpus.py').read_bytes()).hexdigest(),
                    dictionary=lexicon.receipt(),
                    limitations=['No retrieved candidate pool or independent precision measurement',
                                 'Future qualification must exclude all these families and templates',
                                 'Correct-original controls require source protection independent of grammar scores'])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'train.jsonl').write_bytes(payload)
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: manifest[key] for key in ['rows', 'families', 'skipped', 'corpusSha256']}))


if __name__ == '__main__':
    main()
