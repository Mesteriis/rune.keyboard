#!/usr/bin/env python3
"""Aggregate previously disclosed A4 forms in a pinned public Wikipedia shard.

Raw matches are not verified abbreviations, independent labels or accuracy.
No article text, IDs or source positions are emitted.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
CONTROLS = ROOT / 'tools/typing_experiments/a4_controls/controls-v1.jsonl'
LOCK = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/source-lock.json'
SHARD = '0011.parquet'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def targets(path=CONTROLS):
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]
    forms = [row['typed'] for row in rows if row.get('family') == 'abbreviation']
    if len(forms) != 54 or len(set(forms)) != 54 or any(
            not isinstance(s, str) or not re.fullmatch('[а-яё]{2,20}', s) for s in forms):
        raise ValueError('A4_FREQUENCY_CONTROLS')
    return sorted(forms)


def scan(rows, forms):
    if not forms or len(set(forms)) != len(forms) or any(not re.fullmatch('[а-яё]{2,20}', s) for s in forms):
        raise ValueError('A4_FREQUENCY_FORMS')
    pattern = re.compile(r'(?<![\w-])(' + '|'.join(map(re.escape, sorted(forms, key=len, reverse=True))) +
                         r')\.(?=\s|$|[),;:!?])', re.IGNORECASE)
    occurrences, articles, ids = Counter(), Counter(), set()
    for article, text in rows:
        article = str(article)
        if not article.isascii() or not article.isdecimal() or int(article) <= 0 or not isinstance(text, str):
            raise ValueError('A4_FREQUENCY_SOURCE_ROWS')
        article = str(int(article))
        if article in ids: raise ValueError('A4_FREQUENCY_SOURCE_ROWS')
        ids.add(article)
        matches = [match.group(1).lower() for match in pattern.finditer(unicodedata.normalize('NFC', text))]
        occurrences.update(matches)
        articles.update(set(matches))
    if not ids:
        raise ValueError('A4_FREQUENCY_EMPTY_SOURCE')
    return {'sourceRows': len(ids), 'forms': {form: {'occurrences': occurrences[form], 'articles': articles[form]}
                                             for form in sorted(forms)}}


def run(source):
    import pyarrow.parquet as parquet
    source = Path(source).resolve(strict=True)
    lock_before, controls_before, own_before = sha(LOCK), sha(CONTROLS), sha(__file__)
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    shards = [item for item in lock['shards'] if item['name'] == SHARD]
    if len(shards) != 1: raise ValueError('A4_FREQUENCY_SOURCE_LOCK')
    shard = shards[0]
    if source.stat().st_size != shard['bytes'] or sha(source) != shard['sha256']:
        raise ValueError('A4_FREQUENCY_SOURCE_IDENTITY')
    def rows():
        for batch in parquet.ParquetFile(source).iter_batches(batch_size=64, columns=['id', 'text']):
            yield from zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True)
    report = scan(rows(), targets())
    if (source.stat().st_size != shard['bytes'] or sha(source) != shard['sha256'] or
            sha(LOCK) != lock_before or sha(CONTROLS) != controls_before or sha(__file__) != own_before):
        raise ValueError('A4_FREQUENCY_INPUT_DRIFT')
    report.update(schema=1, sourceRepository=lock['repository'], sourceRevision=lock['revision'],
                  sourceShard=SHARD, sourceSha256=shard['sha256'], sourceLockSha256=lock_before,
                  controlsSha256=controls_before, helperSha256=own_before,
                  sourceDecoderAttested=False, independentlyQualified=False,
                  interpretation='raw token-dot occurrences, not meaning or verified abbreviation frequency')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2, ensure_ascii=False, sort_keys=True); out.write('\n')
    print(json.dumps({'sourceRows': report['sourceRows'],
        'observedForms': sum(v['occurrences'] > 0 for v in report['forms'].values()),
        'independentlyQualified': False}))


if __name__ == '__main__':
    main()
