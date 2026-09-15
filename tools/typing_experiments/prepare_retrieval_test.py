#!/usr/bin/env python3
"""Reserve an unseen public cohort for bounded manual retrieval evaluation."""
from pathlib import Path
import argparse
import json
import re
import unicodedata
import prepare_refinement as public
import prepare_word_ranking as word

ROOT = public.ROOT
SEED = 'rune-retrieval-20260915-v1'
QUOTAS = {1: 600, 2: 600, 3: 300, 0: 300}


def prior_data():
    excluded, contexts, texts, hashes = word.prior_evidence()
    path = ROOT / 'build/typing-word-ranking/data/manifest.json'
    binding = json.loads((ROOT / 'build/typing-word-ranking/observations/manifest.json').read_text())
    if public.file_hash(path) != binding['dataManifestSha256']:
        raise ValueError('PRIOR_MANIFEST_IDENTITY')
    manifest = json.loads(path.read_text())
    if manifest.get('containsPersonalMessages') is not False:
        raise ValueError('PUBLIC_PRIOR_REQUIRED')
    hashes[str(path.relative_to(ROOT))] = public.file_hash(path)
    for part in ('train', 'dev', 'test'):
        excluded.update(map(str, manifest['partitions'][part]['articles']))
        for kind in ('rows', 'text'):
            source = path.parent / f'{part}-{kind}.jsonl'
            if public.file_hash(source) != manifest['files'][source.name]:
                raise ValueError('PRIOR_DATA_IDENTITY')
            for line in source.read_text().splitlines():
                row = json.loads(line)
                if kind == 'rows':
                    contexts.add(public.digest((row['prefix'].lower() + '\0' + row['expectedSpelling']).encode()))
                else:
                    texts.add(public.digest(row['text'].encode()))
    return excluded, contexts, texts, hashes, manifest['scannedArticles']


def prepare(parquet, frequency, output):
    import pyarrow.parquet as pq
    lock = json.loads((ROOT / 'tools/model/rune-text-0.2/source-lock.json').read_text())
    source = lock['wikipediaContext']['files']['ru-0007.parquet']
    if parquet.stat().st_size != source['bytes'] or public.file_hash(parquet) != source['sha256']:
        raise ValueError('PUBLIC_PARQUET_IDENTITY')
    if public.file_hash(frequency) != lock['frequencyWords']['files']['ru_50k.txt']:
        raise ValueError('PUBLIC_FREQUENCY_IDENTITY')
    excluded, contexts, texts, hashes, skip = prior_data()
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'build'):
        raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    vocab = {unicodedata.normalize('NFC', s.rsplit(' ', 1)[0]).lower() for s in frequency.read_text().splitlines()}
    rows, articles, counts, word_counts = [], set(), dict.fromkeys(QUOTAS, 0), {}
    scanned = 0
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=['id', 'text']):
        for article, text in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist()):
            scanned += 1
            article = str(article)
            if scanned <= skip or article in excluded:
                continue
            normalized = unicodedata.normalize('NFC', text or '')
            text_hash = public.digest(' '.join(public.WORD.findall(normalized.lower())).encode())
            if text_hash in texts:
                continue
            texts.add(text_hash)
            selected = set()
            for sentence in re.split(r'(?<=[.!?])\s+|\n+', normalized):
                for ordinal, match in enumerate(public.WORD.finditer(sentence)):
                    target = match.group()
                    if ordinal < 3 or target != target.lower() or not 5 <= len(target) <= 12 or target not in vocab:
                        continue
                    if target in selected or word_counts.get(target, 0) >= 4:
                        continue
                    prefix = sentence[:match.start()][-128:].lstrip()
                    if not prefix or not prefix[-1].isspace():
                        continue
                    identity = public.digest((prefix.lower() + '\0' + target).encode())
                    if identity in contexts:
                        continue
                    rid = public.digest((SEED + ':' + article + ':' + identity).encode())
                    errors = (1, 1, 2, 2, 3, 0)[int(rid[:8], 16) % 6]
                    if counts[errors] == QUOTAS[errors]:
                        continue
                    mutation = word.mutate(target, rid, errors, vocab)
                    if mutation is None:
                        continue
                    typed, operations = mutation
                    contexts.add(identity)
                    selected.add(target)
                    articles.add(article)
                    word_counts[target] = word_counts.get(target, 0) + 1
                    counts[errors] += 1
                    rows.append(dict(id='retrieval-' + rid[:24], articleId=article, language='ru', partition='test',
                        split='holdout', family=target, template='article-' + article, typed=typed, prefix=prefix,
                        cohort='correct' if errors == 0 else 'typo', noAuto=errors == 0,
                        expectedSpelling=target, category=f'edit-{errors}', errorCount=errors, operations=operations))
                    if len(selected) == 12:
                        break
                if len(selected) == 12:
                    break
            if counts == QUOTAS:
                break
        if counts == QUOTAS or scanned >= 30000:
            break
    if counts != QUOTAS:
        raise ValueError('INSUFFICIENT_FRESH_TEST')
    row_path = output / 'test-rows.jsonl'
    row_path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows))
    manifest = dict(schema=1, seed=SEED, containsPersonalMessages=False, sourceSha256=source['sha256'],
        sourceRepository=lock['wikipediaContext']['repository'], sourceRevision=lock['wikipediaContext']['parquetRevision'],
        sourcePath=source['repositoryPath'], license=lock['wikipediaContext']['licenses'],
        frequencySha256=public.file_hash(frequency), excludedInitialArticles=skip,
        excludedPriorArticles=len(excluded), priorManifestSha256=hashes, scannedArticles=scanned,
        articles=sorted(articles), counts=counts, rows=len(rows), preparationScriptSha256=public.file_hash(Path(__file__)),
        files={row_path.name: public.file_hash(row_path)})
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(rows=len(rows), counts=counts, articles=len(articles), scannedArticles=scanned)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('parquet', 'frequency', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.parquet, args.frequency, args.output)
