"""Exclude attested Wiktionary forms of already-disclosed historical surfaces.

Source: https://huggingface.co/datasets/SergeyShk/rumorph-wiktionary at
768e78b0f415f51c60d73c15362218452e30dbcc, derived from Russian Wiktionary;
the source declares CC BY-SA 4.0. These are conservative exact exclusions,
not Pymorph lemmas, historical intent, or complete linguistic families.
"""
import argparse
import copy
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import tarfile
import unicodedata

import holdout_ledger as ledger
import import_unimorph_early_exclusions as previous
from source_identities import unsupported_surface_key

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = '0ff28409baca56faf67d83fdfc47e967dd6e61b30e5d9afc32c65af80a5a62c5'
SOURCE_BYTES = 24457732
SOURCE_ENTRIES = 250917
FIXTURE = Path(__file__).resolve().with_name('wiktionary-historical-exclusions-v1.json')
LEDGER = previous.LEDGER
ENTRY = 'public-historical-wiktionary-surfaces-v1'
WORD = re.compile(r'[а-яё]{1,32}\Z')
TEXT_FIXTURE = Path(__file__).resolve().with_name('wiktionary-historical-text-boundaries-v1.json')
TEXT_FIXTURE_SHA = 'cb464a1d545cecc8009b85500992f95448527655eda0097bd23e0a182510dd50'


def text_keys(entries):
    raw = TEXT_FIXTURE.read_bytes()
    if sha(raw) != TEXT_FIXTURE_SHA:
        raise ValueError('WIKTIONARY_TEXT_FIXTURE')
    fixture = json.loads(raw)
    if (fixture.get('schema') != 1 or fixture.get('sourceSha256') !=
            '39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88' or
            fixture.get('dictionarySha256') != SOURCE_SHA or
            set(fixture.get('archiveSha256', {})) != set(previous.TEXT_PARENTS)):
        raise ValueError('WIKTIONARY_TEXT_FIXTURE')
    rows = {}
    for parent in previous.TEXT_PARENTS:
        index, name = previous.text_archive_name(parent)
        archive = previous.TEXT_ARCHIVES[index]
        if entries[parent]['bindings'].get(str(archive.relative_to(ROOT))) != sha(archive.read_bytes()):
            raise ValueError('WIKTIONARY_TEXT_ARCHIVE')
        with tarfile.open(archive, 'r:gz') as bundle:
            member = bundle.getmember(name)
            if not member.isfile() or member.size > 16 * 1024 * 1024:
                raise ValueError('WIKTIONARY_TEXT_ARCHIVE')
            payload = bundle.extractfile(member).read()
        if sha(payload) != fixture['archiveSha256'][parent]:
            raise ValueError('WIKTIONARY_TEXT_ARCHIVE')
        parsed = [json.loads(line) for line in payload.splitlines()]
        rows[parent] = {row['articleId']: row['text'] for row in parsed}
        if len(rows[parent]) != len(parsed):
            raise ValueError('WIKTIONARY_TEXT_DUPLICATE')
    result = {name: set() for name in previous.TEXT_PARENTS}
    records = fixture.get('records')
    if not isinstance(records, list) or len(records) != 1957:
        raise ValueError('WIKTIONARY_TEXT_FIXTURE')
    for record in records:
        if not isinstance(record, dict) or set(record) != {'parent', 'article', 'ordinal', 'surfaceKey', 'sourceStart', 'sourceEnd'}:
            raise ValueError('WIKTIONARY_TEXT_RECORD')
        parent, article, ordinal, key = record['parent'], record['article'], record['ordinal'], record['surfaceKey']
        if (parent not in result or article not in rows[parent] or type(ordinal) is not int or ordinal < 0 or
                type(record['sourceStart']) is not int or type(record['sourceEnd']) is not int or record['sourceStart'] < 0):
            raise ValueError('WIKTIONARY_TEXT_RECORD')
        words = list(re.finditer('[а-яё]+', rows[parent][article], re.IGNORECASE))
        if (ordinal >= len(words) or unsupported_surface_key(words[ordinal].group()) != key or
                record['sourceEnd'] - record['sourceStart'] != len(words[ordinal].group()) or
                key not in entries[parent]['unsupportedSurfaceKeys'] or key in result[parent]):
            raise ValueError('WIKTIONARY_TEXT_RECORD')
        result[parent].add(key)
    if len(set().union(*result.values())) != 1778:
        raise ValueError('WIKTIONARY_TEXT_FIXTURE')
    return result


def parent_keys(base):
    result = previous.parent_keys(base)
    entries = {item['id']: item for item in ledger.validate_ledger(copy.deepcopy(base))['entries']}
    result.update(text_keys(entries))
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def norm(word):
    # Remove stress marks only; preserve ё and other distinctions.
    return unicodedata.normalize('NFC', unicodedata.normalize('NFC', word).replace('\u0301', '')).casefold()


def capture(raw, parents):
    if len(raw) != SOURCE_BYTES or sha(raw) != SOURCE_SHA:
        raise ValueError('WIKTIONARY_SOURCE_IDENTITY')
    target = set().union(*parents.values())
    pairs = set()
    titles = set()
    entries = 0
    with lzma.LZMAFile(io.BytesIO(raw)) as source:
        for line in source:
            row = json.loads(line)
            entries += 1
            if not isinstance(row, dict) or not isinstance(row.get('word'), str) or not isinstance(row.get('forms'), list):
                raise ValueError('WIKTIONARY_SOURCE_ROW')
            lemma = norm(row['word'])
            if not WORD.fullmatch(lemma):
                continue
            forms = {lemma}
            for form in row['forms']:
                if not isinstance(form, list) or not form or not isinstance(form[0], str):
                    raise ValueError('WIKTIONARY_SOURCE_FORM')
                value = norm(form[0])
                if WORD.fullmatch(value):
                    forms.add(value)
            matched = {unsupported_surface_key(form) for form in forms} & target
            if matched:
                pairs.update((lemma, form) for form in forms)
                titles.add((lemma, row['word']))
    if entries != SOURCE_ENTRIES:
        raise ValueError('WIKTIONARY_SOURCE_COUNT')
    selected = {unsupported_surface_key(form) for _, form in pairs}
    return dict(schema=1, sourceSha256=SOURCE_SHA, entries=entries, pairs=sorted([list(pair) for pair in pairs]),
                sourceTitles=sorted([list(pair) for pair in titles]),
                matchesByParent={name: sorted(keys & selected) for name, keys in parents.items()})


def entry(base, fixture):
    prior = [item for item in base['entries'] if item['id'] == previous.ENTRY]
    if (len(prior) != 1 or
            prior[0] != previous.entry(base, json.loads(previous.FIXTURE.read_bytes()))):
        raise ValueError('WIKTIONARY_PARENT')
    parents = parent_keys(base)
    if fixture.get('schema') != 1 or fixture.get('sourceSha256') != SOURCE_SHA or fixture.get('entries') != SOURCE_ENTRIES:
        raise ValueError('WIKTIONARY_FIXTURE')
    pairs = fixture.get('pairs')
    if (not isinstance(pairs, list) or len(pairs) != 16077 or pairs != sorted(pairs) or
            len({tuple(pair) for pair in pairs if isinstance(pair, list)}) != len(pairs) or
            any(not isinstance(pair, list) or len(pair) != 2 or
                any(not isinstance(x, str) or not WORD.fullmatch(x) for x in pair) for pair in pairs)):
        raise ValueError('WIKTIONARY_FIXTURE')
    surface = {unsupported_surface_key(form) for _, form in pairs}
    matches = {name: sorted(keys & surface) for name, keys in parents.items()}
    allkeys = set().union(*parents.values())
    lemmas = {lemma for lemma, _ in pairs}
    titles = fixture.get('sourceTitles')
    if (not isinstance(titles, list) or titles != sorted(titles) or
            any(not isinstance(item, list) or len(item) != 2 or
                any(not isinstance(value, str) for value in item) or norm(item[1]) != item[0] or
                any(unicodedata.category(char).startswith('C') for char in item[1]) for item in titles) or
            {item[0] for item in titles} != lemmas or len({tuple(item) for item in titles}) != len(titles)):
        raise ValueError('WIKTIONARY_TITLES')
    if (len(lemmas) != 1774 or len(surface) != 15833 or
            len(set().union(*(set(value) for value in matches.values()))) != 2158 or
            fixture.get('matchesByParent') != matches or
            {head for head, form in pairs if unsupported_surface_key(form) in allkeys} != lemmas):
        raise ValueError('WIKTIONARY_TARGET_SCOPE')
    prior_raw = json.dumps(prior[0], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    paths = (Path(__file__).resolve(), FIXTURE, Path(previous.__file__).resolve(), TEXT_FIXTURE,
             ROOT / 'tools/typing_experiments/audit_wiktionary_text_boundaries.py')
    bindings = dict(prior[0]['bindings'])
    bindings.update({str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths})
    return dict(id=ENTRY, usage='historical-context-exclusion', rowCount=prior[0]['rowCount'],
                keys=copy.deepcopy(prior[0]['keys']), unsupportedSurfaceKeys=sorted(surface), missingAxes=[],
                parentEntries=[previous.ENTRY], parentEntrySha256=sha(prior_raw), bindings=bindings,
                notes='Exact Wiktionary forms related to disclosed historical surfaces; no Pymorph lemma or intended sense is inferred.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw_ledger = LEDGER.read_bytes()
    base = json.loads(raw_ledger)
    if args.capture:
        source = args.capture.read_bytes()
        helper = Path(__file__).read_bytes()
        parents = parent_keys(base)
        value = capture(source, parents)
        if (args.capture.read_bytes() != source or LEDGER.read_bytes() != raw_ledger or
                Path(__file__).read_bytes() != helper or parent_keys(base) != parents):
            raise ValueError('WIKTIONARY_INPUT_DRIFT')
        if args.check:
            if value != json.loads(FIXTURE.read_bytes()): raise ValueError('WIKTIONARY_CAPTURE_DRIFT')
            print('Source capture matches fixture; no qualification.')
        else:
            print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))
        return
    if not args.check: raise ValueError('WIKTIONARY_SCOPE')
    expected = entry(base, json.loads(FIXTURE.read_bytes()))
    if [item for item in base['entries'] if item['id'] == ENTRY] != [expected]:
        raise ValueError('WIKTIONARY_ENTRY_DRIFT')
    print(json.dumps({'surfaces': len(expected['unsupportedSurfaceKeys']), 'independentQualification': False}))


if __name__ == '__main__':
    main()
