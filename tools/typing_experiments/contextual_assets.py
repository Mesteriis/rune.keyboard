"""Deterministic front-coded assets for the trained contextual feature inputs.

Public word counts and dictionary-only analyses; no evaluation labels or user text.
Records: prefix/suffix u8, payload bytes u16, UTF-8 suffix, opaque payload.
Header: magic[8], block width/count/blocks/data offset u32; relative offsets u32.
The trailer is SHA-256 of all preceding bytes. All integers are little endian.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import sys
import tempfile

BLOCK = 32
COUNT_MAGIC = b'RUCNTX01'
GRAMMAR_MAGIC = b'RUGRM001'
POS = (None, 'NOUN', 'ADJF', 'ADJS', 'VERB', 'INFN', 'PRTF', 'PRTS', 'GRND',
       'NPRO', 'ADVB', 'PRED', 'PREP', 'NUMR', 'CONJ', 'PRCL', 'INTJ', 'COMP')
CASES = (None, 'nomn', 'gent', 'datv', 'accs', 'ablt', 'loct', 'voct')
NUMBERS = (None, 'sing', 'plur')
GENDERS = (None, 'masc', 'femn', 'neut')
PERSONS = (None, '1per', '2per', '3per')


def write_index(records, output, magic):
    if len(magic) != 8:
        raise ValueError('INDEX_MAGIC')
    offsets, count, previous = [], 0, b''
    with tempfile.TemporaryFile() as body:
        for key, payload in records:
            key = key.encode('utf-8')
            if not 1 <= len(key) <= 255 or not 1 <= len(payload) <= 1024:
                raise ValueError('INDEX_RECORD_BOUNDS')
            if count and key <= previous:
                raise ValueError('INDEX_RECORD_ORDER')
            prefix = 0
            if count % BLOCK == 0:
                offsets.append(body.tell())
            else:
                while prefix < min(len(previous), len(key)) and previous[prefix] == key[prefix]:
                    prefix += 1
            suffix = key[prefix:]
            body.write(struct.pack('<BBH', prefix, len(suffix), len(payload)))
            body.write(suffix); body.write(payload)
            previous = key; count += 1
        if not count:
            raise ValueError('INDEX_EMPTY')
        offsets.append(body.tell())
        header = magic + struct.pack('<IIII', BLOCK, count, len(offsets) - 1, 24 + 4 * len(offsets))
        digest = hashlib.sha256()
        output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('wb') as target:
            for chunk in [header, struct.pack('<' + 'I' * len(offsets), *offsets)]:
                target.write(chunk); digest.update(chunk)
            body.seek(0)
            for chunk in iter(lambda: body.read(65536), b''):
                target.write(chunk); digest.update(chunk)
            target.write(digest.digest())
    return dict(records=count, bytes=output.stat().st_size,
                sha256=hashlib.sha256(output.read_bytes()).hexdigest())


def count_records(source):
    rows = [json.loads(line) for line in Path(source).read_text().splitlines() if line.strip()]
    from word_context_features import WordContextFeatures
    # Reuse the training source validation before computing its exact denominators.
    table = WordContextFeatures(rows)
    for previous, word, count, documents in sorted(rows, key=lambda r: (r[0] + '\0' + r[1]).encode()):
        values = count, documents, table.words[word], table.prefixes[previous]
        if any(type(value) is not int or not 0 < value < 2**31 for value in values):
            raise ValueError('COUNT_PAYLOAD_BOUNDS')
        yield previous + '\0' + word, struct.pack('<IIII', *values)


def analysis_code(analysis):
    from grammar_context_features import _MODALS, _ACCUSATIVE_VERBS, _case
    values = (POS.index(analysis.pos), CASES.index(_case(analysis)),
              NUMBERS.index(analysis.number), GENDERS.index(analysis.gender), PERSONS.index(analysis.person))
    flags = int(analysis.lemma in _MODALS) | (int(analysis.lemma in _ACCUSATIVE_VERBS) << 1)
    return values[0] | values[1] << 5 | values[2] << 8 | values[3] << 10 | values[4] << 12 | flags << 14


def grammar_payload(analyses):
    codes = sorted({analysis_code(a) for a in analyses})
    if not codes or len(codes) > 255:
        raise ValueError('GRAMMAR_ANALYSES_BOUNDS')
    # Distinct full lemma/tag analyses can project to identical compact codes.
    # Preserve the training ambiguity count separately from that projection.
    return bytes((min(len(analyses), 8), len(codes))) + struct.pack('<' + 'H' * len(codes), *codes)


def grammar_records(lexicon):
    lexicon._load()
    keys = set()
    word_pattern = re.compile(r'[а-яё]{1,32}\Z')
    for word, _ in itertools.groupby(lexicon._analyzer.dictionary.words.iteritems(), key=lambda row: row[0]):
        if not word_pattern.fullmatch(word):
            continue
        # DictionaryAnalyzer allows е->ё substitutions. Export every such query
        # spelling and use the same analyzer, preserving its ambiguity semantics.
        variants = ['']
        for letter in word:
            variants = [prefix + char for prefix in variants for char in ('её' if letter == 'ё' else letter)]
        keys.update(variants)
    print('GRAMMAR_QUERY_KEYS', len(keys), flush=True)
    for index, word in enumerate(sorted(keys)):
        analyses = lexicon.analyses(word)
        if not analyses:
            raise ValueError('GRAMMAR_DICTIONARY_QUERY_MISSING')
        yield word, grammar_payload(analyses)
        if index and index % 50000 == 0:
            print('GRAMMAR_RECORDS', index, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--counts', type=Path)
    parser.add_argument('--grammar', action='store_true')
    args = parser.parse_args()
    if bool(args.counts) == args.grammar:
        parser.error('Choose exactly one of --counts or --grammar')
    if args.output.exists():
        parser.error('Output must be new')
    if args.grammar:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'morphology'))
        from ranker import PymorphyLexicon
        lexicon = PymorphyLexicon(cache_size=16384); receipt = lexicon.receipt()
        result = write_index(grammar_records(lexicon), args.output, GRAMMAR_MAGIC)
        if lexicon.receipt() != receipt:
            raise ValueError('GRAMMAR_DICTIONARY_CHANGED')
        result.update(dictionary=receipt, license='CC-BY-SA-3.0', source='https://opencorpora.org/')
    else:
        result = write_index(count_records(args.counts), args.output, COUNT_MAGIC)
        result.update(sourceSha256=hashlib.sha256(args.counts.read_bytes()).hexdigest())
    result['exporterSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.with_suffix(args.output.suffix + '.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('records', 'bytes', 'sha256')}), flush=True)


if __name__ == '__main__':
    main()
