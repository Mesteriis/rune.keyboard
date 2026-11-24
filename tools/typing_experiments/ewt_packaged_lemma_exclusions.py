"""Quarantine exact disclosed EWT lemmas present in the packaged public trie.

Only public packaged dictionary words are projected. Keys are unsalted and not
anonymization; exact lemmas do not establish complete English morphology.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata

import english_family_keys as family
import ewt_lemma_exclusions as prior
import holdout_ledger as lexical

ROOT = Path(__file__).resolve().parents[2]
TRIE = ROOT/'app/src/main/assets/smarttyping/lexicon/en.trie'
MANIFEST = ROOT/'app/src/main/assets/smarttyping/lexicon/provenance/packed-asset-manifest.json'
FIXTURE = ROOT/'tools/typing_experiments/ewt-packaged-lemma-exclusions-v1.json'
TRIE_SHA = '2c81c9b4d317f802567297aecaee18927c756175b8f42bca7d01227bbfefbebc'
MANIFEST_SHA = '7ce207ab7d05b8800a1d8921f6e55fe81f429f8158bf8ebcebf581cbee7255f0'
PRIOR_SHA = 'dce6b748ce81e68f0356c59c9ca87da3897aacbb7365834bcb0da377cfef5d02'
FIXTURE_SHA = '7a80f480bcd0f4162490086a851587d3ff83ce48a9830e69ed041bc59ec61a9e'
ENTRY = 'public-ud-english-ewt-2.18-packaged-lemma-exclusion-v1'
HASH = re.compile(r'[0-9a-f]{64}\Z')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class Trie:
    """Lookup terminal words in the hash-pinned RTR1 public dictionary."""
    def __init__(self, raw):
        if len(raw) < 16:
            raise ValueError('EWT_PACKAGED_TRIE_HEADER')
        magic, self.words, self.nodes, stride = struct.unpack_from('<4sIII', raw)
        if (magic != b'RTR1' or not self.words or self.nodes < 2 or stride != 16 or
                len(raw) != 16 + self.nodes*16):
            raise ValueError('EWT_PACKAGED_TRIE_HEADER')
        self.raw = raw
        self.cache = {}
        cp, child, sibling, terminal = self.node(0)
        if cp or sibling or terminal or not child:
            raise ValueError('EWT_PACKAGED_TRIE_ROOT')

    def node(self, index):
        if not 0 <= index < self.nodes:
            raise ValueError('EWT_PACKAGED_TRIE_NODE')
        cp, child, sibling, terminal = struct.unpack_from('<IIII', self.raw, 16 + index*16)
        if (cp > 0x10ffff or 0xd800 <= cp <= 0xdfff or child >= self.nodes or
                sibling >= self.nodes or terminal > self.words):
            raise ValueError('EWT_PACKAGED_TRIE_NODE')
        return cp, child, sibling, terminal

    def contains(self, word):
        if word in self.cache:
            return self.cache[word]
        node = 0
        for char in word:
            cp = ord(char)
            first = self.node(node)[1]
            previous = -1
            steps = 0
            while first:
                label, child, sibling, terminal = self.node(first)
                if label <= previous or steps >= self.nodes:
                    raise ValueError('EWT_PACKAGED_TRIE_ORDER')
                if label >= cp:
                    break
                previous = label
                first = sibling
                steps += 1
            if not first or label != cp:
                self.cache[word] = False
                return False
            node = first
        self.cache[word] = bool(self.node(node)[3])
        return self.cache[word]


def verify_assets(raw, manifest):
    if sha(raw) != TRIE_SHA or sha(manifest) != MANIFEST_SHA:
        raise ValueError('EWT_PACKAGED_ASSET_IDENTITY')
    values = json.loads(manifest)
    entries = [e for e in values if e.get('language') == 'ENGLISH']
    if len(entries) != 1:
        raise ValueError('EWT_PACKAGED_ASSET_MANIFEST')
    entry = entries[0]
    if (entry.get('trie') != {'path':'smarttyping/lexicon/en.trie', 'bytes':len(raw), 'sha256':TRIE_SHA} or
            entry.get('words') != 121255 or entry.get('nodes') != 272385):
        raise ValueError('EWT_PACKAGED_ASSET_MANIFEST')
    trie = Trie(raw)
    if trie.words != entry['words'] or trie.nodes != entry['nodes']:
        raise ValueError('EWT_PACKAGED_ASSET_MANIFEST')
    return trie


def scan(data, trie, old_keys):
    matched, new = set(), set()
    counts = Counter()
    for name in sorted(data):
        for line in data[name].decode('utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            fields = line.split('\t')
            if len(fields) != 10:
                raise ValueError('EWT_PACKAGED_TOKEN_SCHEMA')
            if re.fullmatch(r'[1-9][0-9]*', fields[0]) is None:
                if re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*|\.[1-9][0-9]*)', fields[0]) is None:
                    raise ValueError('EWT_PACKAGED_TOKEN_ID')
                continue
            if fields[3] not in prior.POS:
                raise ValueError('EWT_PACKAGED_TOKEN_SCHEMA')
            try:
                key = family.key_for(fields[2])
            except ValueError:
                continue
            value = unicodedata.normalize('NFC', fields[2]).casefold().replace('’', "'")
            if trie.contains(value):
                counts['matchedTokenRows'] += 1
                matched.add(key)
                if key not in old_keys:
                    counts['newTokenRows'] += 1
                    new.add(key)
    return sorted(new), {'matchedTokenRows':counts['matchedTokenRows'], 'newTokenRows':counts['newTokenRows'],
                         'matchedDistinctLemmas':len(matched), 'newDistinctLemmas':len(new)}


def generate(data, lock, vocab, ledger, old_raw, trie_raw, manifest_raw):
    if sha(old_raw) != PRIOR_SHA:
        raise ValueError('EWT_PACKAGED_PRIOR_IDENTITY')
    old = prior.fixture(old_raw)
    if prior.extract(data, lock, vocab, ledger) != old:
        raise ValueError('EWT_PACKAGED_PRIOR_REPRODUCTION')
    keys, counts = scan(data, verify_assets(trie_raw, manifest_raw), set(old['keys']))
    return dict(schema='ewt-public-packaged-lemmas-v1', sourceLockSha256=prior.sha(lock),
        parentEntrySha256=prior.PARENT_SHA, priorFixtureSha256=PRIOR_SHA,
        trieSha256=TRIE_SHA, assetManifestSha256=MANIFEST_SHA,
        counts=counts, keys=keys, independentQualification=False, familyCoverageComplete=False)


def entry(ledger, raw):
    if sha(raw) != FIXTURE_SHA:
        raise ValueError('EWT_PACKAGED_FIXTURE_IDENTITY')
    old_raw = prior.FIXTURE.read_bytes()
    expected = prior.entry(ledger, old_raw)
    logical = lexical.validate_ledger(copy.deepcopy(ledger))
    if [e for e in logical['entries'] if e['id'] == prior.ENTRY] != [expected] or sha(old_raw) != PRIOR_SHA:
        raise ValueError('EWT_PACKAGED_PRIOR_ENTRY')
    verify_assets(TRIE.read_bytes(), MANIFEST.read_bytes())
    value = json.loads(raw)
    if (value.get('schema') != 'ewt-public-packaged-lemmas-v1' or value.get('sourceLockSha256') != prior.LOCK_SHA or
            value.get('parentEntrySha256') != prior.PARENT_SHA or value.get('priorFixtureSha256') != PRIOR_SHA or
            value.get('trieSha256') != TRIE_SHA or value.get('assetManifestSha256') != MANIFEST_SHA or
            value.get('independentQualification') is not False or value.get('familyCoverageComplete') is not False or
            value.get('counts') != {'matchedTokenRows':212479, 'newTokenRows':1469,
                                    'matchedDistinctLemmas':10803, 'newDistinctLemmas':850} or
            not isinstance(value.get('keys'),list) or len(value['keys']) != 850 or
            value['keys'] != sorted(set(value['keys'])) or
            any(not isinstance(key,str) or not HASH.fullmatch(key) for key in value['keys']) or
            set(value['keys']) & set(prior.fixture(old_raw)['keys'])):
        raise ValueError('EWT_PACKAGED_FIXTURE')
    paths = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(family.__file__).resolve(),
             Path(lexical.__file__).resolve(), Path(prior.ewt.__file__).resolve(),
             ROOT/'tools/typing_experiments/source_identities.py', prior.ewt.LOCK, prior.VOCAB,
             prior.FIXTURE, FIXTURE, TRIE, MANIFEST)
    bindings = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}
    if bindings[str(FIXTURE.relative_to(ROOT))] != sha(raw):
        raise ValueError('EWT_PACKAGED_FIXTURE_DRIFT')
    return dict(id=ENTRY, usage='historical-family-exclusion', keys={'family':value['keys']}, missingAxes=[],
        bindings=bindings, rowCount=value['counts']['newTokenRows'], parentEntries=[prior.ENTRY],
        notes='Additional exact public EWT lemmas present in the packaged English dictionary; no complete-family or independent qualification claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--generate', type=Path); group.add_argument('--register', type=Path); group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    ledger_raw = prior.LEDGER.read_bytes(); ledger = json.loads(ledger_raw)
    if args.generate:
        if args.source_directory is None:
            raise ValueError('EWT_PACKAGED_SCOPE')
        lock = prior.ewt.LOCK.read_bytes(); hashes = json.loads(lock)['files']
        paths = {name:args.source_directory/name for name in hashes}
        data = {name:path.read_bytes() for name,path in paths.items()}
        vocab, old_raw, trie_raw, manifest_raw = (p.read_bytes() for p in (prior.VOCAB, prior.FIXTURE, TRIE, MANIFEST))
        helpers = (Path(__file__).resolve(), Path(prior.__file__).resolve(), Path(family.__file__).resolve(),
                   Path(lexical.__file__).resolve(), Path(prior.ewt.__file__).resolve(),
                   ROOT/'tools/typing_experiments/source_identities.py',
                   ROOT/'tools/typing_experiments/conversation_split_checks.py')
        helper_hashes = {path:sha(path.read_bytes()) for path in helpers}
        result = generate(data, lock, vocab, ledger, old_raw, trie_raw, manifest_raw)
        if (prior.LEDGER.read_bytes() != ledger_raw or prior.ewt.LOCK.read_bytes() != lock or
                any(paths[name].read_bytes() != raw for name,raw in data.items()) or
                any(sha(path.read_bytes()) != digest for path,digest in helper_hashes.items()) or
                any(path.read_bytes() != raw for path,raw in zip((prior.VOCAB, prior.FIXTURE, TRIE, MANIFEST),
                                                                  (vocab, old_raw, trie_raw, manifest_raw), strict=True))):
            raise ValueError('EWT_PACKAGED_INPUT_DRIFT')
        with args.generate.open('xb') as stream:
            stream.write((json.dumps(result, sort_keys=True, indent=2)+'\n').encode())
        print(json.dumps(result['counts'], sort_keys=True)); return
    if args.source_directory is not None:
        raise ValueError('EWT_PACKAGED_SCOPE')
    expected = entry(ledger, FIXTURE.read_bytes())
    if args.check:
        found = [e for e in lexical.validate_ledger(ledger)['entries'] if e['id'] == ENTRY]
        if found != [expected]:
            raise ValueError('EWT_PACKAGED_LEDGER_DRIFT')
        print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False})); return
    output = args.register.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):
        raise ValueError('EWT_PACKAGED_OUTPUT')
    if any(e['id'] == ENTRY for e in ledger['entries']):
        raise ValueError('EWT_PACKAGED_EXISTS')
    ledger['entries'].append(expected)
    lexical.validate_ledger(copy.deepcopy(ledger))
    if prior.LEDGER.read_bytes() != ledger_raw or entry(json.loads(ledger_raw), FIXTURE.read_bytes()) != expected:
        raise ValueError('EWT_PACKAGED_INPUT_DRIFT')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(ledger,stream,ensure_ascii=False,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'keys':len(expected['keys']['family']), 'independentQualification':False}))


if __name__ == '__main__':
    main()
