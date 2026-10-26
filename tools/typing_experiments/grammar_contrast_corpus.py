"""Authored grammar contrasts for TRAINING ONLY, never independent qualification.

Each pair shares an unknown one-edit corruption but has opposing left contexts.
Correct dictionary forms are retention controls even in a disagreeing context.
No owner text, disclosed failure words, corpus downloads or model scores are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


ALPHABET = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
# These paradigms deliberately exclude the five disclosed failure targets.
VERBS = (
    ('говорить', 'говоришь'), ('любить', 'любишь'),
    ('курить', 'куришь'), ('варить', 'варишь'),
    ('дарить', 'даришь'), ('смотреть', 'смотришь'),
    ('носить', 'носишь'), ('водить', 'водишь'),
    ('ходить', 'ходишь'), ('спешить', 'спешишь'),
    ('решить', 'решишь'), ('купить', 'купишь'),
    ('просить', 'просишь'), ('хранить', 'хранишь'),
    ('строить', 'строишь'), ('чинить', 'чинишь'),
    ('трудиться', 'трудишься'), ('учиться', 'учишься'),
    ('стремиться', 'стремишься'), ('торопиться', 'торопишься'),
)
PREDICATES = (
    ('готов', 'готовы'), ('рад', 'рады'), ('прав', 'правы'),
    ('согласен', 'согласны'), ('доволен', 'довольны'),
    ('свободен', 'свободны'), ('спокоен', 'спокойны'),
)
OBJECTS = (
    ('историю', 'историей'), ('теорию', 'теорией'),
    ('станцию', 'станцией'), ('лекцию', 'лекцией'),
    ('коллекцию', 'коллекцией'), ('инструкцию', 'инструкцией'),
    ('копию', 'копией'), ('линию', 'линией'),
)


def one_edit_words(word):
    """Finite ordinary insertion/deletion/substitution neighborhood, no transposes."""
    result = {word[:i] + word[i + 1:] for i in range(len(word))}
    result.update(word[:i] + letter + word[i + 1:]
                  for i, old in enumerate(word) for letter in ALPHABET if letter != old)
    result.update(word[:i] + letter + word[i:]
                  for i in range(len(word) + 1) for letter in ALPHABET)
    return result - {word, ''}


def _valid_pair(kind, left, right):
    if kind == 'infinitive':
        return any(a.pos == 'INFN' for a in left) and any(
            a.pos == 'VERB' and a.person == '2per' and a.number == 'sing' for a in right)
    if kind == 'predicate':
        return any(a.pos == 'ADJS' and a.number == 'sing' and a.gender == 'masc' for a in left) and any(
            a.pos == 'ADJS' and a.number == 'plur' for a in right)
    return any(a.pos == 'NOUN' and a.case == 'accs' for a in left) and any(
        a.pos == 'NOUN' and a.case == 'ablt' for a in right)


def generate(lexicon):
    rows, skipped = [], []
    specifications = (
        ('infinitive', VERBS, ('тебе нужно', 'я хочу', 'можно'), ('ты', 'ты уже', 'ты снова')),
        ('predicate', PREDICATES, ('он', 'он уже', 'он теперь'), ('они', 'они уже', 'они теперь')),
        ('object', OBJECTS, ('я вижу', 'он показал', 'я помню'), ('с', 'вместе с', 'рядом с')),
    )
    for kind, pairs, left_contexts, right_contexts in specifications:
        for left, right in pairs:
            left_tags, right_tags = lexicon.analyses(left), lexicon.analyses(right)
            if not _valid_pair(kind, left_tags, right_tags) or not (
                    {a.lemma for a in left_tags} & {a.lemma for a in right_tags}):
                raise ValueError('PARADIGM_DICTIONARY_MISMATCH:' + left)
            candidates = one_edit_words(left) & one_edit_words(right)
            ordered = sorted(candidates, key=lambda word: (
                len(word), hashlib.sha256(('grammar-contrast-v1:' + word).encode()).hexdigest()))
            typed = next((word for word in ordered if not lexicon.analyses(word)), None)
            if typed is None:
                skipped.append(dict(kind=kind, forms=[left, right], reason='NO_UNKNOWN_SHARED_ONE_EDIT'))
                continue
            family = kind + ':' + left
            for target, rival, contexts in ((left, right, left_contexts), (right, left, right_contexts)):
                for prefix in contexts:
                    # Both already-correct forms stay unchanged, including grammatical disagreement.
                    for source, no_auto in ((typed, False), (target, True), (rival, True)):
                        row = dict(purpose='AUTHORED_CONTRAST_TRAINING_ONLY',
                                   source='rune-authored-grammar-contrast-v1', split='train',
                                   family=family, contrastKind=kind, language='ru', prefix=prefix,
                                   typed=source, expectedSpelling=source if no_auto else target,
                                   word=source if no_auto else target, noAuto=no_auto,
                                   group='correct' if no_auto else 'shared_one_edit',
                                   cohort='correct' if no_auto else 'typo',
                                   contrastCandidates=[left, right])
                        row['id'] = 'grammar-contrast-' + hashlib.sha256(
                            json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
                        rows.append(row)
    if not rows or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('EMPTY_OR_DUPLICATE_CONTRASTS')
    return rows, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New output directory; never overwritten')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon()
    rows, skipped = generate(lexicon)
    payload = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows).encode()
    receipt = dict(schemaVersion=1, purpose='TRAINING_ONLY_NOT_QUALIFICATION',
                   origin='Authored templates and dictionary-validated paradigms; no downloaded sentences',
                   rows=len(rows), typoRows=sum(not row['noAuto'] for row in rows),
                   families=len({row['family'] for row in rows}), skipped=skipped,
                   corpusSha256=hashlib.sha256(payload).hexdigest(),
                   generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   dictionary=lexicon.receipt(),
                   limitations=['Synthetic distribution; does not establish real typing precision',
                                'Must exclude overlapping families/contexts from future independent evaluation',
                                'Not a candidate retrieval or correction admission certificate'])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'train.jsonl').write_bytes(payload)
    (args.output / 'manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: receipt[key] for key in ('rows', 'typoRows', 'families', 'skipped')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
