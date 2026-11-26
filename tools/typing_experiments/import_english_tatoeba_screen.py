"""Register every public sentence in the disclosed A1 source; never qualify it."""
import bz2
import copy
import hashlib
import json
from pathlib import Path
import unicodedata

from holdout_ledger import keys_for, validate_ledger

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'tools/typing_experiments/public_sources/tatoeba-en-cc0-20261024/eng_sentences_CC0.tsv.bz2'
DIGEST = 'a144a0c52f8be13bee7cc30eb109eb5836803f22128a8ef8376c1ca5c6c5cf8a'
ENTRY = 'public-tatoeba-english-a1-screen-source'


def rows_from_bytes(data):
    rows = []
    ids = set()
    for line in bz2.decompress(data).decode('utf-8').splitlines():
        fields = line.split('\t')
        if (len(fields) != 4 or fields[1] != 'eng' or not fields[0].isascii()
                or not fields[0].isdecimal() or int(fields[0]) <= 0 or not fields[2].strip()):
            raise ValueError('EN_TATOEBA_ROW')
        identity = str(int(fields[0]))
        if identity in ids:
            raise ValueError('EN_TATOEBA_DUPLICATE')
        ids.add(identity)
        normalized = ' '.join(unicodedata.normalize('NFC', fields[2]).casefold().split())
        rows.append(dict(sourceRepository='tatoeba', language='en', article='tatoeba:' + identity,
                         sentenceHash=hashlib.sha256(normalized.encode()).hexdigest()))
    if not rows:
        raise ValueError('EN_TATOEBA_EMPTY')
    return rows


def build(ledger, data, bindings):
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError('EN_TATOEBA_SOURCE_DIGEST')
    result = copy.deepcopy(validate_ledger(ledger))
    if any(entry['id'] == ENTRY for entry in result['entries']):
        raise ValueError('EN_TATOEBA_ALREADY_IMPORTED')
    rows = rows_from_bytes(data)
    result['entries'].append(dict(id=ENTRY, usage='historical-source-exclusion',
        keys={axis: sorted(keys_for(rows, axis)) for axis in ('article', 'sentence')},
        missingAxes=[], bindings=bindings, rowCount=len(rows), sourceRepository='tatoeba',
        notes='Full disclosed English CC0 snapshot; no author/template independence or training consumption is asserted.'))
    return validate_ledger(result)


if __name__ == '__main__':
    import sys
    ledger_path = ROOT / 'tools/typing_experiments/holdout-ledger.json'
    source = (ROOT / SOURCE).read_bytes()
    bindings = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                (SOURCE, 'tools/typing_experiments/import_english_tatoeba_screen.py',
                 'tools/typing_experiments/source_identities.py', 'tools/typing_experiments/holdout_ledger.py')}
    if len(sys.argv) != 2:
        raise SystemExit('Provide a new output path')
    output = Path(sys.argv[1])
    result = build(json.loads(ledger_path.read_text()), source, bindings)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
