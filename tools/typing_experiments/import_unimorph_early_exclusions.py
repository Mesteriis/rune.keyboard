"""Exclude exact UniMorph forms of already-disclosed early targets.

Source: https://github.com/unimorph/rus at 50dcabfd0a04bd4d187ffb0d5cdd54af94863dec;
the source declares Wikipedia and CC BY-SA 3.0. No Pymorph family is inferred.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unicodedata

import holdout_ledger as ledger
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = '6c13f849fc12844b23f46e70a02a45a2f537e60c62c8ffd8798bdff3991dc880'
PARENT = 'public-early-ru-qualification-v2'
PARENTS = ('public-spelling-v7', 'public-spelling-v8', 'public-spelling-v9',
           'public-spelling-v10', 'public-spelling-v11', 'public-spelling-v12',
           'public-ranker-history-train', 'public-legacy-spelling-v6',
           PARENT, 'public-early-ru-compact-v3', 'public-early-ru-compact-v4',
           'historical-neighbor-recovery-prefix-families-v1')
TEXT_PARENTS = tuple('public-refinement-text-families-' + part for part in ('train', 'dev', 'test')) + tuple(
    'public-word-epoch-text-families-wordrank-' + part for part in ('train', 'dev', 'test')) + (
    'public-word-epoch-text-families-extra-test',)
PARENTS += TEXT_PARENTS
ENTRY = 'public-early-ru-unimorph-exclusions-v1'
ROWS = ROOT / 'tools/eval/smart-typing-0.3/qualification-v2/corpus/spelling-ru.jsonl'
FIXTURE = Path(__file__).resolve().with_name('unimorph-early-exclusions-v1.json')
LEDGER = Path(__file__).resolve().with_name('holdout-ledger.json')
WORD = re.compile(r'[а-яё]{1,32}\Z')
NEIGHBOR = 'historical-neighbor-recovery-prefix-families-v1'
NEIGHBOR_ROWS = tuple(ROOT / 'tools/typing_experiments/neighbor-history-v1' / (part + '.jsonl')
                      for part in ('train', 'calibration', 'holdout'))
TEXT_FIXTURE = Path(__file__).resolve().with_name('unimorph-historical-text-boundaries-v1.json')
TEXT_FIXTURE_SHA = '87b639162951bc50c835728b70e8054ae98566b847041f7dd050e5484ffd006f'
TEXT_ARCHIVES = (ROOT / 'tools/ci/historical-data-v1/files.tar.gz',
                 ROOT / 'tools/ci/historical-model-fixtures-v1/files.tar.gz')


def text_archive_name(parent):
    if parent.startswith('public-refinement-text-families-'):
        return 0, 'typing-refinement/data/' + parent.rsplit('-', 1)[1] + '-text.jsonl'
    if parent.startswith('public-word-epoch-text-families-wordrank-'):
        return 1, 'build/typing-word-ranking/data/' + parent.rsplit('-', 1)[1] + '-text.jsonl'
    if parent == TEXT_PARENTS[-1]:
        return 0, 'typing-extra-epochs/data/test-text.jsonl'
    raise ValueError('UNIMORPH_TEXT_PARENT')


def text_keys(entries):
    raw = TEXT_FIXTURE.read_bytes()
    if sha(raw) != TEXT_FIXTURE_SHA:
        raise ValueError('UNIMORPH_TEXT_FIXTURE')
    fixture = json.loads(raw)
    if (fixture.get('schema') != 1 or fixture.get('sourceSha256') !=
            '39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88' or
            fixture.get('unimorphSha256') != SOURCE_SHA or set(fixture.get('archiveSha256', {})) != set(TEXT_PARENTS)):
        raise ValueError('UNIMORPH_TEXT_FIXTURE')
    rows = {}
    for parent in TEXT_PARENTS:
        index, name = text_archive_name(parent)
        archive = TEXT_ARCHIVES[index]
        if entries[parent]['bindings'].get(str(archive.relative_to(ROOT))) != sha(archive.read_bytes()):
            raise ValueError('UNIMORPH_TEXT_ARCHIVE')
        with tarfile.open(archive, 'r:gz') as bundle:
            member = bundle.getmember(name)
            if not member.isfile() or member.size > 16 * 1024 * 1024:
                raise ValueError('UNIMORPH_TEXT_ARCHIVE')
            payload = bundle.extractfile(member).read()
        if sha(payload) != fixture['archiveSha256'][parent]:
            raise ValueError('UNIMORPH_TEXT_ARCHIVE')
        parsed = [json.loads(line) for line in payload.splitlines()]
        rows[parent] = {row['articleId']: row['text'] for row in parsed}
        if len(rows[parent]) != len(parsed):
            raise ValueError('UNIMORPH_TEXT_DUPLICATE')
    result = {name: set() for name in TEXT_PARENTS}
    records = fixture.get('records')
    if not isinstance(records, list) or len(records) != 63:
        raise ValueError('UNIMORPH_TEXT_FIXTURE')
    for record in records:
        if not isinstance(record, dict) or set(record) != {'parent', 'article', 'ordinal', 'surfaceKey', 'sourceStart', 'sourceEnd'}:
            raise ValueError('UNIMORPH_TEXT_RECORD')
        parent, article, ordinal, key = record['parent'], record['article'], record['ordinal'], record['surfaceKey']
        if (parent not in result or article not in rows[parent] or type(ordinal) is not int or ordinal < 0 or
                type(record['sourceStart']) is not int or type(record['sourceEnd']) is not int or record['sourceStart'] < 0):
            raise ValueError('UNIMORPH_TEXT_RECORD')
        words = list(re.finditer('[а-яё]+', rows[parent][article], re.IGNORECASE))
        if (ordinal >= len(words) or unsupported_surface_key(words[ordinal].group()) != key or
                record['sourceEnd'] - record['sourceStart'] != len(words[ordinal].group()) or
                key not in entries[parent]['unsupportedSurfaceKeys'] or key in result[parent]):
            raise ValueError('UNIMORPH_TEXT_RECORD')
        result[parent].add(key)
    if len(set().union(*result.values())) != 59:
        raise ValueError('UNIMORPH_TEXT_FIXTURE')
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def norm(value):
    return unicodedata.normalize('NFC', value).casefold()


def interior_prefix_keys(prefix):
    if not isinstance(prefix, str):
        raise ValueError('UNIMORPH_NEIGHBOR_PREFIX')
    prefix = norm(prefix)
    keys = set()
    for match in re.finditer('[а-яё]+', prefix):
        if (match.start() > 0 and match.end() < len(prefix) and
                prefix[match.start()-1].isspace() and prefix[match.end()].isspace()):
            key = unsupported_surface_key(match.group())
            if key:
                keys.add(key)
    return keys


def targets(base, raw):
    parents = [entry for entry in ledger.validate_ledger(copy.deepcopy(base))['entries'] if entry['id'] == PARENT]
    rel = str(ROWS.relative_to(ROOT))
    if len(parents) != 1 or parents[0]['bindings'].get(rel) != sha(raw):
        raise ValueError('UNIMORPH_PARENT_IDENTITY')
    unknown = set(parents[0]['unsupportedSurfaceKeys'])
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != parents[0]['rowCount']:
        raise ValueError('UNIMORPH_PARENT_COUNT')
    return {norm(target) for row in rows
            if (target := row.get('expectedSpelling') or
                (row.get('typed') if row.get('cohort') == 'correct' else None))
            and unsupported_surface_key(target) in unknown}


def parent_keys(base):
    entries = {item['id']: item for item in ledger.validate_ledger(copy.deepcopy(base))['entries']}
    if any(name not in entries or not entries[name].get('unsupportedSurfaceKeys') for name in PARENTS):
        raise ValueError('UNIMORPH_PARENT_SCOPE')
    result = {name: set(entries[name]['unsupportedSurfaceKeys']) for name in PARENTS}
    # Prefix boundaries and compounds may contain fragments. Admit only whole
    # interior words bounded by whitespace on both sides of the retained prefix.
    interior = set()
    count = 0
    for path in NEIGHBOR_ROWS:
        raw = path.read_bytes()
        if entries[NEIGHBOR]['bindings'].get(str(path.relative_to(ROOT))) != sha(raw):
            raise ValueError('UNIMORPH_NEIGHBOR_IDENTITY')
        for line in raw.splitlines():
            row = json.loads(line)
            count += 1
            interior.update(interior_prefix_keys(row.get('prefix')))
    if count != entries[NEIGHBOR]['rowCount']:
        raise ValueError('UNIMORPH_NEIGHBOR_COUNT')
    result[NEIGHBOR] &= interior
    result.update(text_keys(entries))
    return result


def capture(source, historical_keys):
    if sha(source) != SOURCE_SHA:
        raise ValueError('UNIMORPH_SOURCE_IDENTITY')
    pairs = set()
    for line in source.decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) != 3:
            continue
        lemma, form = map(norm, fields[:2])
        if WORD.fullmatch(lemma) and WORD.fullmatch(form):
            pairs.add((lemma, form))
    all_keys = set().union(*historical_keys.values())
    lemmas = {lemma for lemma, form in pairs if unsupported_surface_key(form) in all_keys}
    selected = sorted([lemma, form] for lemma, form in pairs if lemma in lemmas)
    selected_keys = {unsupported_surface_key(form) for _, form in selected}
    matches = {name: sorted(values & selected_keys) for name, values in historical_keys.items()}
    return {'schema': 2, 'sourceSha256': SOURCE_SHA, 'pairs': selected, 'matchesByParent': matches}


def entry(base, fixture):
    target_words = targets(base, ROWS.read_bytes())
    if fixture.get('schema') != 2 or fixture.get('sourceSha256') != SOURCE_SHA:
        raise ValueError('UNIMORPH_FIXTURE')
    pairs = fixture.get('pairs')
    if (not isinstance(pairs, list) or pairs != sorted(pairs) or len(pairs) != 644 or
            any(not isinstance(p, list) or len(p) != 2 or
                any(not isinstance(x, str) or not WORD.fullmatch(x) for x in p) for p in pairs) or
            len({tuple(p) for p in pairs}) != len(pairs)):
        raise ValueError('UNIMORPH_FIXTURE')
    lemmas = {lemma for lemma, _ in pairs}
    historical = parent_keys(base)
    all_keys = set().union(*historical.values())
    fixture_keys = {unsupported_surface_key(form) for _, form in pairs}
    matches = {name: sorted(values & fixture_keys) for name, values in historical.items()}
    if (len(lemmas) != 64 or len({form for _, form in pairs} & target_words) != 2 or
            fixture.get('matchesByParent') != matches or
            len(set().union(*(set(value) for value in matches.values()))) != 75 or
            any(not any(word == lemma and unsupported_surface_key(form) in all_keys
                        for word, form in pairs) for lemma in lemmas)):
        raise ValueError('UNIMORPH_TARGET_SCOPE')
    matched = {form for _, form in pairs} & target_words
    rows = [json.loads(line) for line in ROWS.read_bytes().splitlines()]
    contexts = [row for row in rows if norm(row.get('expectedSpelling') or
                (row.get('typed') if row.get('cohort') == 'correct' else '') or '') in matched]
    if len(contexts) != 2:
        raise ValueError('UNIMORPH_TARGET_SCOPE')
    paths = (Path(__file__).resolve(), FIXTURE, ROWS, Path(ledger.__file__).resolve(),
             ROOT / 'tools/typing_experiments/source_identities.py', *NEIGHBOR_ROWS, TEXT_FIXTURE,
             ROOT / 'tools/typing_experiments/audit_unimorph_text_boundaries.py',
             ROOT / 'tools/typing_experiments/selector_text_preflight_v1.py', *TEXT_ARCHIVES)
    parent_entries = {item['id']: item for item in base['entries'] if item['id'] in PARENTS}
    parent_digests = {name: sha(json.dumps(parent_entries[name], ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False).encode()) for name in PARENTS}
    return dict(id=ENTRY, usage='historical-context-exclusion', rowCount=len(contexts),
                keys={'context': sorted(ledger.keys_for(contexts, 'context'))},
                unsupportedSurfaceKeys=sorted({unsupported_surface_key(form) for _, form in pairs}),
                missingAxes=[], parentEntries=list(PARENTS), parentEntrySha256=parent_digests,
                bindings={str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths},
                notes='Two original contexts and UniMorph forms for historical targets and source-bound text; no Pymorph lemma or canonical family is inferred.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    base = json.loads(LEDGER.read_bytes())
    if args.capture:
        value = capture(args.capture.read_bytes(), parent_keys(base))
        if args.check:
            if value != json.loads(FIXTURE.read_bytes()): raise ValueError('UNIMORPH_CAPTURE_DRIFT')
            print('Source capture matches fixture; no qualification.')
        else:
            print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if not args.check: raise ValueError('UNIMORPH_SCOPE')
    expected = entry(base, json.loads(FIXTURE.read_bytes()))
    if [item for item in base['entries'] if item['id'] == ENTRY] != [expected]:
        raise ValueError('UNIMORPH_ENTRY_DRIFT')
    print(json.dumps({'contexts': expected['rowCount'], 'surfaces': len(expected['unsupportedSurfaceKeys']),
                      'independentQualification': False}))


if __name__ == '__main__':
    main()
