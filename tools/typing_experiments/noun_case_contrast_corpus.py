"""Authored noun-case contrasts for training, never independent qualification.

Opposing accusative/instrumental contexts share dictionary-unknown corruptions.
Correctly spelled forms are retention examples even in a disagreeing context.
Disclosed failures and the earlier eight object paradigms are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from grammar_contrast_corpus import shared_variants, one_edit_cost

OBJECTS = (
    ('песню', 'песней'), ('книгу', 'книгой'), ('картину', 'картиной'),
    ('машину', 'машиной'), ('задачу', 'задачей'), ('работу', 'работой'),
    ('квартиру', 'квартирой'), ('комнату', 'комнатой'), ('улицу', 'улицей'),
    ('страну', 'страной'), ('музыку', 'музыкой'), ('команду', 'командой'),
    ('программу', 'программой'), ('систему', 'системой'), ('причину', 'причиной'),
    ('ошибку', 'ошибкой'), ('идею', 'идеей'), ('позицию', 'позицией'),
    ('операцию', 'операцией'), ('ситуацию', 'ситуацией'), ('компанию', 'компанией'),
    ('организацию', 'организацией'), ('реакцию', 'реакцией'), ('мелодию', 'мелодией'),
)
ACCUSATIVE_CONTEXTS = ('я вижу', 'он показал мне', 'мы нашли', 'она купила',
                       'я помню', 'ты получил')
INSTRUMENTAL_CONTEXTS = ('с', 'вместе с', 'рядом с', 'он доволен',
                         'мы гордимся', 'она любуется')


def generate(lexicon):
    rows, skipped = [], []
    for accusative, instrumental in OBJECTS:
        left, right = lexicon.analyses(accusative), lexicon.analyses(instrumental)
        if (not any(a.pos == 'NOUN' and a.case == 'accs' for a in left)
                or not any(a.pos == 'NOUN' and a.case == 'ablt' for a in right)
                or not ({a.lemma for a in left} & {a.lemma for a in right})):
            raise ValueError('NOUN_CASE_DICTIONARY_MISMATCH:' + accusative)
        variants = shared_variants(accusative, instrumental, lexicon, edit_profiles=True)
        if not variants:
            skipped.append(dict(forms=[accusative, instrumental], reason='NO_UNKNOWN_SHARED_ONE_EDIT'))
            continue
        for target, contexts in ((accusative, ACCUSATIVE_CONTEXTS),
                                 (instrumental, INSTRUMENTAL_CONTEXTS)):
            for prefix in contexts:
                for typed, no_auto in ([(v, False) for v in variants] +
                                       [(accusative, True), (instrumental, True)]):
                    row = dict(purpose='AUTHORED_CONTRAST_TRAINING_ONLY',
                               source='rune-authored-noun-case-v1', split='train',
                               family='noun-case:' + accusative, contrastKind='object',
                               language='ru', prefix=prefix, typed=typed,
                               expectedSpelling=typed if no_auto else target,
                               word=typed if no_auto else target, noAuto=no_auto,
                               group='correct' if no_auto else 'shared_one_edit',
                               cohort='correct' if no_auto else 'typo',
                               contrastCandidates=[accusative, instrumental])
                    if not no_auto:
                        row['contrastEditCosts'] = [one_edit_cost(typed, w)
                                                    for w in (accusative, instrumental)]
                    row['id'] = 'noun-case-contrast-' + hashlib.sha256(
                        json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
                    rows.append(row)
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('EMPTY_OR_DUPLICATE_NOUN_CASE_CONTRASTS')
    return rows, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New directory, never overwritten')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
    from ranker import PymorphyLexicon
    lexicon = PymorphyLexicon()
    rows, skipped = generate(lexicon)
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows).encode()
    receipt = dict(schemaVersion=1, purpose='TRAINING_ONLY_NOT_QUALIFICATION',
                   origin='Authored templates and dictionary-verified paradigms; no downloaded/owner text',
                   rows=len(rows), typoRows=sum(not r['noAuto'] for r in rows),
                   retentionRows=sum(r['noAuto'] for r in rows),
                   families=len({r['family'] for r in rows}), skipped=skipped,
                   corpusSha256=hashlib.sha256(payload).hexdigest(), dictionary=lexicon.receipt(),
                   generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   corruptionSelectorSha256=hashlib.sha256(Path(__file__).with_name('grammar_contrast_corpus.py').read_bytes()).hexdigest(),
                   limitations=['Synthetic training only; no automatic admission or precision claim',
                                'Exclude these contexts and lemma families from independent evaluation'])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'train.jsonl').write_bytes(payload)
    (args.output / 'manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ['rows', 'typoRows', 'retentionRows', 'families', 'skipped']}))


if __name__ == '__main__':
    main()
