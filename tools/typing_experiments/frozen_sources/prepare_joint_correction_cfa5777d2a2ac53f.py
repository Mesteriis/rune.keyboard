#!/usr/bin/env python3
"""Freeze source- and lemma-disjoint short/long correction train/calibration/holdout rows."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import unicodedata

import prepare_external_spelling_holdout as common
import neighbor_recovery as recovery

ROOT = Path(__file__).resolve().parents[2]
SEED = 'rune-joint-v1-20261025'
GENERATOR = common.load_generator()
WORDS = re.compile(r'(?<![\w])[а-яёА-ЯЁ]{3,20}(?![\w])')


def partition(family):
    bucket = int(hashlib.sha256((SEED + ':family:' + family).encode()).hexdigest()[:8], 16) % 5
    return 'train' if bucket < 3 else 'calibration' if bucket == 3 else 'holdout'


def morphology(known):
    path = ROOT / 'app/src/main/assets/smarttyping/lexicon/ru.morph'
    blob = path.read_bytes()
    if common.sha256(path) != 'c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b':
        raise ValueError('MORPHOLOGY_IDENTITY')
    width, count, _, start = struct.unpack_from('<IIII', blob, 8)
    wanted = {word.encode(): word for word in known}
    result = {}; position = start; previous = b''
    for index in range(count):
        if index % width == 0: previous = b''
        prefix, size, lemma = struct.unpack_from('<BBI', blob, position)
        previous = previous[:prefix] + blob[position + 6:position + 6 + size]
        position += 6 + size
        if lemma and previous in wanted: result[wanted[previous]] = str(lemma)
    if position != len(blob) - 32: raise ValueError('MORPHOLOGY_LENGTH')
    return result


def variants(word, known, salt):
    values = GENERATOR.safe_typos(word, 'ru', known, salt)
    # Include physical-neighbour substitutions instead of relying solely on arbitrary letters.
    for index, char in enumerate(word):
        for other in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя':
            if recovery.adjacent(char, other):
                value = word[:index] + other + word[index + 1:]
                if value not in known: values.append((value, 'adjacent1'))
    seen = set(); result = []
    for value, kind in sorted(values, key=lambda item: hashlib.sha256((salt + str(item)).encode()).digest()):
        if len(value) >= 3 and value not in seen:
            result.append((value, kind)); seen.add(value)
    return result


def rows_from_pool(pool, part, known):
    rows = []
    for band, quota in [('short', 160), ('long', 500)]:
        families = sorted((family for family, items in pool.items()
            if (len(items[0]['word']) <= 4) == (band == 'short')),
            key=lambda family: hashlib.sha256((SEED + part + family).encode()).digest())[:quota]
        for family in families:
            for item in sorted(pool[family], key=lambda x:x['selectionHash'])[:4 if band == 'short' else 1]:
                word = item['word']; salt = SEED + item['selectionHash']
                forms = variants(word, known, salt)[:4]
                if band == 'long':
                    for group in recovery.GROUPS:
                        value = recovery.typo(word, group, salt, known)
                        if value: forms.append((value, group))
                forms += [(word, 'correct'), ('@' + word, 'protected')]
                for typed, group in forms:
                    control = group in ('correct','protected')
                    rows.append(dict(item, id=f'joint-{part}-{len(rows):06d}', split=part, language='ru',
                        family=family, band=band, group=group, typed=typed,
                        expectedSpelling=typed if control else word, cohort=group if control else 'typo', noAuto=control))
    return rows


def prepare(source_root, output):
    import pyarrow.parquet as parquet
    source_root, output = source_root.resolve(), output.resolve()
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'): raise ValueError('FRESH_OUTPUT')
    lock = json.loads((source_root/'public-source-lock.json').read_text())
    frequency = ROOT/'build/smart-typing-0.3/corpus-inputs/ru_50k.txt'
    if common.sha256(frequency) != common.FREQUENCY_SHA256: raise ValueError('FREQUENCY_IDENTITY')
    known = {line.split()[0] for line in frequency.read_text().splitlines()
             if 3 <= len(line.split()[0]) <= 20 and all(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in line.split()[0])}
    lemmas = morphology(known)
    pools = {part:defaultdict(list) for part in ('train','calibration','holdout')}
    articles = {part:set() for part in pools}; bindings = {}
    sources = [('train',ROOT/'build/typing-ranker-v2/ru-0011.parquet'),
               ('calibration',source_root/'0018.parquet'),('holdout',source_root/'0019.parquet')]
    for part, path in sources:
        if part == 'train':
            entry=json.loads((ROOT/'build/typing-ranker-v2/external-holdout-v6-ru0011/manifest.json').read_text())['source']
            expected, size = entry['sha256'], entry['bytes']
        else:
            entry=next(x for x in lock['files'] if x['path'].endswith(path.name))
            expected, size = entry['lfs']['oid'], entry['size']
        if path.stat().st_size != size or common.sha256(path) != expected: raise ValueError('SOURCE_IDENTITY')
        bindings[str(path.relative_to(ROOT))] = expected
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):
            for article, text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
                articles[part].add(str(article)); text=unicodedata.normalize('NFC',text or '')
                for ordinal, match in enumerate(WORDS.finditer(text)):
                    word=match.group().casefold(); family=lemmas.get(word)
                    if ordinal < 4 or family is None or partition(family) != part: continue
                    prefix=GENERATOR.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip()
                    if not prefix: continue
                    identity=hashlib.sha256((SEED+str(article)+word+prefix).encode()).hexdigest()
                    item=dict(word=word,family=family,prefix=prefix,article=str(article),source=path.name,selectionHash=identity)
                    bucket=pools[part][family]
                    if any(x['article']==str(article) for x in bucket):continue
                    bucket.append(item);bucket.sort(key=lambda x:x['selectionHash']);del bucket[4:]
        print('SOURCE_COMPLETE',part,len(pools[part]),flush=True)
    for left,right in [('train','calibration'),('train','holdout'),('calibration','holdout')]:
        if articles[left]&articles[right] or pools[left].keys()&pools[right].keys():raise ValueError('SPLIT_OVERLAP')
    output.mkdir(parents=True)
    manifest=dict(schema=1,seed=SEED,sourceBindings=bindings,frequency=common.sha256(frequency),
        builder=common.sha256(Path(__file__)),stage='frozen-before-model-fitting',files={},counts={})
    for part in pools:
        rows=rows_from_pool(pools[part],part,known)
        path=output/f'{part}.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        manifest['files'][path.name]=common.sha256(path)
        manifest['counts'][part]=dict(rows=len(rows),bands=dict(Counter(r['band'] for r in rows)),families=len({r['family'] for r in rows}))
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['counts']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();prepare(args.source_root,args.output)
