"""Quarantine dictionary analyses of words in disclosed neighbor prefixes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ci'), str(ROOT / 'tools/morphology')]
import register_neighbor_history as parent
import import_q7_regression_families as common
from holdout_ledger import pack_ledger, validate_ledger
from ranker import PymorphyLexicon

ENTRY = 'historical-neighbor-recovery-prefix-families-v1'
KEYS_SHA = '15abaeca507f91cae71ad6d9aa9f52b9e04ccafaaa1eeb268fa69bed9a986d00'
UNKNOWN_SHA = '708085a863930f5852ac422dc6707d40e2f53fb08378c9a4050b198c8c9d1969'
DICTIONARY_SHA = 'b36e032fcf52de10d76e3770931b8609e2ad0c5afb4ffbea99add060db1750a8'
WORD = re.compile('[а-яё]+')


def prefix_surfaces(rows):
    prefixes = {row['prefix'] for row in rows}
    if not prefixes or any(not isinstance(prefix, str) or not prefix for prefix in prefixes):
        raise ValueError('NEIGHBOR_PREFIX_SCHEMA')
    surfaces = {word for prefix in prefixes for word in WORD.findall(unicodedata.normalize('NFC', prefix).casefold())}
    checked = common.lexical_surfaces(surfaces)
    if len(checked) != len(surfaces):
        raise ValueError('NEIGHBOR_PREFIX_SURFACE')
    return checked, len(prefixes)


def make_entry(rows, parent_entry, lexicon, bindings, dictionary_sha):
    if parent_entry.get('id') != parent.ENTRY:
        raise ValueError('NEIGHBOR_PREFIX_PARENT')
    surfaces, prefixes = prefix_surfaces(rows)
    families, unknown, counts = common.analyze(surfaces, lexicon)
    if not families:
        raise ValueError('NEIGHBOR_PREFIX_EMPTY')
    entry = dict(id=ENTRY, usage='historical-family-exclusion', rowCount=len(rows),
                 keys={'family': families}, missingAxes=[], bindings=bindings,
                 dictionaryReceiptSha256=dictionary_sha, parentEntries=[parent.ENTRY],
                 notes='Dictionary analyses of Russian tokens in disclosed prefix text; unknowns are exact surfaces only.')
    if unknown:
        entry['unsupportedSurfaceKeys'] = unknown
    return entry, counts | {'prefixes': prefixes, 'familyKeys': len(families), 'unsupportedSurfaceKeys': len(unknown)}


def check():
    ledger = validate_ledger(json.loads(parent.LEXICAL.read_bytes()))
    expected_parent, _ = parent.entries()
    if [item for item in ledger['entries'] if item['id'] == parent.ENTRY] != [expected_parent]:
        raise ValueError('NEIGHBOR_PREFIX_PARENT')
    entries = [item for item in ledger['entries'] if item['id'] == ENTRY]
    if len(entries) != 1:
        raise ValueError('NEIGHBOR_PREFIX_MISSING')
    entry = entries[0]
    keys = entry['keys']['family']
    unknown = entry.get('unsupportedSurfaceKeys', [])
    key_sha = hashlib.sha256(json.dumps(keys, separators=(',', ':')).encode()).hexdigest()
    unknown_sha = hashlib.sha256(json.dumps(unknown, separators=(',', ':')).encode()).hexdigest()
    if (entry.get('usage') != 'historical-family-exclusion' or entry.get('rowCount') != 15000 or
            entry.get('parentEntries') != [parent.ENTRY] or len(keys) != 7903 or key_sha != KEYS_SHA or
            len(unknown) != 1163 or unknown_sha != UNKNOWN_SHA or
            entry.get('dictionaryReceiptSha256') != DICTIONARY_SHA):
        raise ValueError('NEIGHBOR_PREFIX_IDENTITY')
    for name, digest in entry['bindings'].items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('NEIGHBOR_PREFIX_DRIFT')
    return len(keys), len(unknown)


def run(base_path, output):
    base_path, output = Path(base_path), Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('NEIGHBOR_PREFIX_OUTPUT')
    base_raw = base_path.read_bytes()
    stored = json.loads(base_raw)
    logical = validate_ledger(copy.deepcopy(stored))
    expected_parent, _ = parent.entries()
    if [item for item in logical['entries'] if item['id'] == parent.ENTRY] != [expected_parent]:
        raise ValueError('NEIGHBOR_PREFIX_PARENT')
    if any(item['id'] == ENTRY for item in logical['entries']):
        raise ValueError('NEIGHBOR_PREFIX_EXISTS')
    rows, parent_bindings = parent.inputs()
    paths = [Path(__file__).resolve(), Path(common.__file__).resolve(), ROOT / 'tools/morphology/ranker.py',
             ROOT / 'tools/typing_experiments/holdout_ledger.py', ROOT / 'tools/typing_experiments/source_identities.py']
    bindings = parent_bindings | {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    dictionary = PymorphyLexicon(cache_size=16384)
    dictionary_receipt = dictionary.receipt()
    dictionary_sha = hashlib.sha256(json.dumps(dictionary_receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    entry, counts = make_entry(rows, expected_parent, dictionary, bindings, dictionary_sha)
    logical['entries'].append(entry)
    stored['entries'].append(pack_ledger(logical)['entries'][-1])
    if validate_ledger(copy.deepcopy(stored)) != logical:
        raise ValueError('NEIGHBOR_PREFIX_STORAGE')
    if (base_path.read_bytes() != base_raw or dictionary.receipt() != dictionary_receipt or
            any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest for name, digest in bindings.items())):
        raise ValueError('NEIGHBOR_PREFIX_DRIFT')
    receipt = dict(scope='disclosed-neighbor-prefix-families-not-qualification', counts=counts,
                   baseLedgerSha256=hashlib.sha256(base_raw).hexdigest(),
                   entrySha256=hashlib.sha256(json.dumps(entry, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                   dictionary=dictionary_receipt, dictionaryReceiptSha256=dictionary_sha,
                   modelCalls=0, globalCoverageComplete=False)
    output.mkdir(parents=True, mode=0o700)
    for name, value in (('ledger.json', stored), ('receipt.json', receipt)):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check and args.base is None and args.output is None:
        families, unknown = check()
        print(json.dumps({'familyKeys': families, 'unknownSurfaces': unknown, 'independentQualification': False}))
    elif not args.check and args.base is not None and args.output is not None:
        run(args.base, args.output)
    else:
        parser.error('choose --check or --base with --output')
