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
import independent_corpus_guard as registry_guard
import joint_public_sources as public_sources
import joint_exclusion_inputs as exclusion_inputs

import prepare_external_spelling_holdout as common
import neighbor_recovery as recovery

ROOT = Path(__file__).resolve().parents[2]
SEED = 'rune-joint-v1-20261025'
GENERATOR = common.load_generator()
WORDS = re.compile(r'(?<![\w])[а-яёА-ЯЁ]{3,20}(?![\w])')


def partition(family):
    bucket = int(hashlib.sha256((SEED + ':family:' + family).encode()).hexdigest()[:8], 16) % 5
    return 'train' if bucket < 3 else 'calibration' if bucket == 3 else 'holdout'


def source_token_is_whole(text, match, snapshot):
    """Keep historical matching intact; reject fragments in new proposals."""
    return registry_guard.whole_selector_token(text, text, 0, match, snapshot)


def independent_resources(collector):
    """Snapshot collector helpers and the pinned dictionary before selection."""
    directory = Path(__file__).resolve().parent
    paths = [Path(collector).resolve(), Path(__file__).resolve(), Path(common.__file__).resolve(),
             Path(recovery.__file__).resolve(), Path(exclusion_inputs.__file__).resolve(),
             Path(registry_guard.__file__).resolve(), Path(public_sources.__file__).resolve(),
             common.GENERATOR.resolve(), ROOT/'tools/morphology/ranker.py']
    paths.extend(directory/name for name in ('right_context_sentence_audit.py', 'holdout_ledger.py',
                 'control_ledger.py', 'public_corpus_preparation_v1.py', 'conversation_split_checks.py',
                 'source_identities.py', 'recover_legacy_families.py'))
    paths = list(dict.fromkeys(paths))
    if len({path.name for path in paths}) != len(paths):
        raise ValueError('JOINT_HELPER_NAME_COLLISION')
    bindings = public_sources.snapshot({path.name: (path, common.sha256(path)) for path in paths})
    sys.path.insert(0, str(ROOT/'tools/morphology'))
    import ranker
    if Path(ranker.__file__).resolve() != (ROOT/'tools/morphology/ranker.py').resolve():
        raise ValueError('JOINT_DICTIONARY_HELPER_IDENTITY')
    lexicon = ranker.PymorphyLexicon(cache_size=16384)
    return bindings, lexicon, lexicon.receipt()


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


def prepare(source_root, output, *, historical_reproduction=False):
    snapshot=registry_guard.begin(historical_reproduction)
    import pyarrow.parquet as parquet
    source_root, output = source_root.resolve(), output.resolve()
    if output.exists() or not output.resolve().is_relative_to(ROOT / 'build'): raise ValueError('FRESH_OUTPUT')
    lock_path=source_root/'public-source-lock.json';lock_raw=lock_path.read_bytes();lock=json.loads(lock_raw)
    public_sources.validate_lock(lock,('0018.parquet','0019.parquet'))
    frequency = ROOT/'build/smart-typing-0.3/corpus-inputs/ru_50k.txt'
    if common.sha256(frequency) != common.FREQUENCY_SHA256: raise ValueError('FREQUENCY_IDENTITY')
    known = {line.split()[0] for line in frequency.read_text().splitlines()
             if 3 <= len(line.split()[0]) <= 20 and all(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for c in line.split()[0])}
    lemmas = morphology(known)
    pools = {part:defaultdict(list) for part in ('train','calibration','holdout')}
    articles = {part:set() for part in pools}; bindings = {}
    sources = [('train',ROOT/'build/typing-ranker-v2/ru-0011.parquet'),
               ('calibration',source_root/'0018.parquet'),('holdout',source_root/'0019.parquet')]
    training_manifest=ROOT/'build/typing-ranker-v2/external-holdout-v6-ru0011/manifest.json'
    training_raw=training_manifest.read_bytes();training_entry=json.loads(training_raw)['source']
    public_sources.validate_training_entry(training_entry)
    public_snapshot=None
    helper_snapshot=lexicon=dictionary_receipt=None
    if snapshot is not None:
        public_snapshot=public_sources.snapshot({
            'sourceLock':(lock_path,hashlib.sha256(lock_raw).hexdigest()),
            'trainingSourceManifest':(training_manifest,hashlib.sha256(training_raw).hexdigest()),
            'frequency':(frequency,common.FREQUENCY_SHA256),
            'morphology':(ROOT/'app/src/main/assets/smarttyping/lexicon/ru.morph','c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b'),
            **{part:(path,public_sources.SOURCES[str(path.relative_to(ROOT))] if part=='train' else public_sources.SOURCES[public_sources.BASE+'/'+path.name]) for part,path in sources}})
        helper_snapshot,lexicon,dictionary_receipt=independent_resources(Path(__file__))
    for part, path in sources:
        if part == 'train':
            entry=training_entry
            expected, size = entry['sha256'], entry['bytes']
        else:
            entry=next(x for x in lock['files'] if x['path']=='20231101.ru/train/'+path.name)
            expected, size = entry['lfs']['oid'], entry['size']
        if path.stat().st_size != size or common.sha256(path) != expected: raise ValueError('SOURCE_IDENTITY')
        bindings[str(path.relative_to(ROOT))] = expected
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):
            for article, text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
                articles[part].add(str(article)); text=unicodedata.normalize('NFC',text or '')
                segment_index=exclusion_inputs.segment_index(text) if snapshot is not None else None
                for ordinal, match in enumerate(WORDS.finditer(text)):
                    if not source_token_is_whole(text, match, snapshot): continue
                    word=match.group().casefold(); family=lemmas.get(word)
                    if ordinal < 4 or family is None or partition(family) != part: continue
                    prefix=GENERATOR.bounded_prefix(text[max(0,match.start()-256):match.start()]).rstrip()
                    if not prefix: continue
                    identity=hashlib.sha256((SEED+str(article)+word+prefix).encode()).hexdigest()
                    item=dict(word=word,family=family,prefix=prefix,article=str(article),source=path.name,selectionHash=identity)
                    if snapshot is not None:
                        item['contextHash']=exclusion_inputs.source_context_hash(text,match,GENERATOR)
                        item['sourceSegmentHash']=exclusion_inputs.source_segment_hash_at(text,match,segment_index)
                    bucket=pools[part][family]
                    if any(x['article']==str(article) for x in bucket):continue
                    bucket.append(item);bucket.sort(key=lambda x:x['selectionHash']);del bucket[4:]
        print('SOURCE_COMPLETE',part,len(pools[part]),flush=True)
    for left,right in [('train','calibration'),('train','holdout'),('calibration','holdout')]:
        if articles[left]&articles[right] or pools[left].keys()&pools[right].keys():raise ValueError('SPLIT_OVERLAP')
    selected_rows={part:rows_from_pool(pool,part,known) for part,pool in pools.items()}
    check_rows=[row for rows in selected_rows.values() for row in rows]
    if snapshot is not None:
        selected_rows=exclusion_inputs.canonical_registry_parts(selected_rows,lexicon)
        check_rows=[row for rows in selected_rows.values() for row in rows]
    registry_receipt=registry_guard.finish(snapshot,check_rows)
    if snapshot is not None:
        public_sources.verify(public_snapshot)
        public_sources.verify(helper_snapshot)
        if lexicon.receipt()!=dictionary_receipt:raise ValueError('JOINT_DICTIONARY_DRIFT')
        registry_receipt['containsPersonalMessages']=False
        registry_receipt['publicInputSha256']={name:digest for name,(_,digest) in public_snapshot.items()}
        registry_receipt['collectorHelperSha256']={name:digest for name,(_,digest) in helper_snapshot.items()}
        registry_receipt['canonicalFamilyDictionary']=dictionary_receipt
        registry_receipt['canonicalFamilySources']={str(p.relative_to(ROOT)):common.sha256(p) for p in (
            ROOT/'tools/morphology/ranker.py',ROOT/'tools/typing_experiments/joint_exclusion_inputs.py',
            ROOT/'tools/typing_experiments/right_context_sentence_audit.py')}
    output.mkdir(parents=True)
    manifest=dict(schema=1,seed=SEED,sourceBindings=bindings,frequency=common.sha256(frequency),
        builder=common.sha256(Path(__file__)),stage='frozen-before-model-fitting',files={},counts={})
    for part,rows in selected_rows.items():
        path=output/f'{part}.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        manifest['files'][path.name]=common.sha256(path)
        manifest['counts'][part]=dict(rows=len(rows),bands=dict(Counter(r['band'] for r in rows)),families=len({r['family'] for r in rows}))
    manifest.update(registry_receipt)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(counts=manifest['counts'],scope=manifest['scope'],independentQualification=False)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument("--historical-reproduction",action="store_true",help="Reproduce disclosed data without independent qualification.")
    args=parser.parse_args();prepare(args.source_root,args.output,historical_reproduction=args.historical_reproduction)
