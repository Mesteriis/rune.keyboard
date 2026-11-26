#!/usr/bin/env python3
"""Reproducible article-stratified sample for A4 meaning review; not a holdout."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import unicodedata

import a4_abbreviation_frequency as base

FORMS = ('спб', 'мск', 'адм', 'пгт', 'экон')
SAMPLE_SIZE = 10
SEED = 'rune-a4-meaning-sample-v1'


def sample(rows):
    pattern = re.compile(r'(?<![\w-])(' + '|'.join(FORMS) + r')\.(?=\s|$|[),;:!?])', re.IGNORECASE)
    seen, candidates = set(), {form: [] for form in FORMS}
    for article, raw_text in rows:
        article = str(article)
        if not article.isascii() or not article.isdecimal() or int(article) <= 0 or not isinstance(raw_text, str):
            raise ValueError('A4_SAMPLE_SOURCE_ROW')
        article = str(int(article))
        if article in seen: raise ValueError('A4_SAMPLE_DUPLICATE_ARTICLE')
        seen.add(article)
        text = unicodedata.normalize('NFC', raw_text)
        first = {}
        for match in pattern.finditer(text): first.setdefault(match.group(1).lower(), match)
        for form, match in first.items():
            rank = hashlib.sha256(json.dumps([SEED, form, article], ensure_ascii=False,
                    separators=(',', ':')).encode()).hexdigest()
            start, end = match.start(), match.end()
            matched = match.group(1)
            case = 'lower' if matched.islower() else 'upper' if matched.isupper() else 'mixed'
            excerpt = text[max(0, start-96):min(len(text), end+128)]
            candidates[form].append((rank, {'form': form, 'article': article, 'start': start, 'end': end,
                'case': case, 'excerptSha256': hashlib.sha256(excerpt.encode()).hexdigest()}, excerpt))
    if not seen: raise ValueError('A4_SAMPLE_EMPTY')
    chosen = [item for form in FORMS for item in sorted(candidates[form], key=lambda x: x[0])[:SAMPLE_SIZE]]
    return len(seen), [row for _, row, _ in chosen], [excerpt for _, _, excerpt in chosen]


def run(source):
    import pyarrow.parquet as parquet
    source = Path(source).resolve(strict=True)
    lock_sha, controls_sha, helper_sha = base.sha(base.LOCK), base.sha(base.CONTROLS), base.sha(__file__)
    frequency_helper_sha = base.sha(base.__file__)
    lock = json.loads(base.LOCK.read_text())
    shard = next(item for item in lock['shards'] if item['name'] == base.SHARD)
    if source.stat().st_size != shard['bytes'] or base.sha(source) != shard['sha256']:
        raise ValueError('A4_SAMPLE_SOURCE_IDENTITY')
    def rows():
        for batch in parquet.ParquetFile(source).iter_batches(batch_size=64, columns=['id', 'text']):
            yield from zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(), strict=True)
    count, records, excerpts = sample(rows())
    if (source.stat().st_size != shard['bytes'] or base.sha(source) != shard['sha256'] or
            base.sha(base.LOCK) != lock_sha or base.sha(base.CONTROLS) != controls_sha or base.sha(__file__) != helper_sha or
            base.sha(base.__file__) != frequency_helper_sha):
        raise ValueError('A4_SAMPLE_INPUT_DRIFT')
    return {'schema': 1, 'seed': SEED, 'sampleSizePerForm': SAMPLE_SIZE,
        'sourceRows': count, 'sourceSha256': shard['sha256'], 'sourceLockSha256': lock_sha,
        'controlsSha256': controls_sha, 'helperSha256': helper_sha, 'frequencyHelperSha256': frequency_helper_sha,
        'pythonVersion': platform.python_version(), 'unicodeVersion': unicodedata.unidata_version,
        'pyarrowVersion': importlib.metadata.version('pyarrow'), 'records': records,
        'sourceDecoderAttested': False, 'independentlyQualified': False}, excerpts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--review-contexts', type=Path, required=True,
                        help='temporary, untracked output; contains public source excerpts')
    args = parser.parse_args()
    report, excerpts = run(args.source)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, sort_keys=True); out.write('\n')
    with args.review_contexts.open('x', encoding='utf-8') as out:
        for index, (record, excerpt) in enumerate(zip(report['records'], excerpts, strict=True)):
            out.write(json.dumps({'index': index, 'form': record['form'], 'excerpt': excerpt}, ensure_ascii=False) + '\n')
    print(json.dumps({'articlesScanned': report['sourceRows'], 'samples': len(excerpts)}))


if __name__ == '__main__': main()
