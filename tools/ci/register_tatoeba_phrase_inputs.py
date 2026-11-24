"""Register exact inputs for disclosed full-session Tatoeba regression replay."""
import argparse
import bz2
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import chat_corpus as corpus
import control_ledger as control
import holdout_ledger as lexical
from import_tatoeba_history import CC0_LOCK_SHA

SOURCE = ROOT / 'tools/typing_experiments/public_sources/tatoeba-ru-cc0-20261024/rus_sentences_CC0.tsv.bz2'
LOCK = SOURCE.with_name('tatoeba-source-lock.json')
IDS = ROOT / 'tools/typing_experiments/chat_regression/tatoeba-full-phrase-ids-v1.json'
CONTROL = ROOT / 'tools/typing_experiments/control-ledger.json'
LEXICAL = ROOT / 'tools/typing_experiments/holdout-ledger.json'
ENTRY = 'tatoeba-full-phrase-inputs-v1'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cases(ledger):
    if digest(LOCK) != CC0_LOCK_SHA:
        raise ValueError('TATOEBA_PHRASE_LOCK')
    lock = json.loads(LOCK.read_bytes())
    if (lock.get('url') != corpus.URL or lock.get('license') != 'CC0-1.0' or
            digest(SOURCE) != lock.get('compressedSha256')):
        raise ValueError('TATOEBA_PHRASE_SOURCE')
    selection = json.loads(IDS.read_bytes())
    ids = selection.get('ids')
    if (selection.get('schema') != 1 or selection.get('purpose') != 'disclosed-regression-not-qualification' or
            not isinstance(ids, list) or len(ids) != 9543 or ids != sorted(set(ids))):
        raise ValueError('TATOEBA_PHRASE_IDS')
    articles = {key for entry in ledger['entries'] for key in entry['keys'].get('article', [])}
    with bz2.open(SOURCE, 'rt', encoding='utf-8') as stream:
        rows, _ = corpus.generate(stream, articles)
    rows = {row['id']: row for row in rows if row['edit_kind'] == 'control' and row['id'] in ids}
    if set(rows) != set(ids):
        raise ValueError('TATOEBA_PHRASE_MISSING_SOURCE_OR_EXCLUSION')
    result = [(name, rows[name]['prefix'] + ' ' + rows[name]['typed']) for name in ids]
    if sum(len(phrase.split()) for _, phrase in result) != 42153:
        raise ValueError('TATOEBA_PHRASE_SCOPE')
    return result


def entries(ledger):
    selected = cases(ledger)
    stages = []
    for _, phrase in selected:
        words = phrase.split(' ')
        for index, word in enumerate(words):
            stages.append(dict(language='ru', prefix=' '.join(words[:index]), typed=word, expectedSpelling=word))
    paths = (Path(__file__).resolve(), SOURCE, LOCK, IDS, Path(corpus.__file__).resolve(),
             Path(control.__file__).resolve(), Path(lexical.__file__).resolve(),
             ROOT / 'tools/typing_experiments/source_identities.py',
             ROOT / 'tools/typing_experiments/import_tatoeba_history.py',
             ROOT / 'tools/typing_experiments/recover_legacy_families.py')
    bindings = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    c = dict(id=ENTRY, kind='regression', language='ru', rowCount=len(stages), bindings=bindings,
             keys=sorted({control.key_for(row, 'regression') for row in stages}),
             semantics='Full-session input stages from disclosed public source; not independent qualification.')
    l = dict(id=ENTRY+'-contexts', usage='historical-context-exclusion', rowCount=len(stages), bindings=bindings,
             keys={'context': sorted(lexical.keys_for(stages, 'context'))}, missingAxes=[],
             notes='Source-derived input stages only; modified contexts from replay require separate registration.')
    return c, l


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true'); group.add_argument('--register', type=Path)
    args = p.parse_args()
    old_control = CONTROL.read_bytes(); old_lexical = LEXICAL.read_bytes()
    a = control.validate(json.loads(old_control)); b = json.loads(old_lexical)
    expanded = lexical.validate_ledger(copy.deepcopy(b))
    first, second = entries(expanded)
    if args.check:
        if [e for e in a['entries'] if e['id'] == ENTRY] != [first] or [e for e in expanded['entries'] if e['id'] == second['id']] != [second]:
            raise ValueError('TATOEBA_PHRASE_REGISTRY_DRIFT')
    else:
        output = args.register.resolve()
        if output.exists() or not output.is_relative_to(ROOT / 'build'):
            raise ValueError('TATOEBA_PHRASE_OUTPUT')
        if any(e['id'] == ENTRY for e in a['entries']) or any(e['id'] == second['id'] for e in b['entries']):
            raise ValueError('TATOEBA_PHRASE_EXISTS')
        a['entries'].append(first); b['entries'].append(second)
        control.validate(a); lexical.validate_ledger(copy.deepcopy(b))
        if CONTROL.read_bytes() != old_control or LEXICAL.read_bytes() != old_lexical or entries(lexical.validate_ledger(copy.deepcopy(b))) != (first, second):
            raise ValueError('TATOEBA_PHRASE_INPUT_DRIFT')
        output.mkdir(parents=True, mode=0o700)
        for name, value in (('control-ledger.json', a), ('holdout-ledger.json', b)):
            (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'phrases': 9543, 'stages': first['rowCount'], 'controlKeys': len(first['keys']),
                      'contextKeys': len(second['keys']['context']), 'independentQualification': False}))


if __name__ == '__main__':
    main()
