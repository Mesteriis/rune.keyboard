#!/usr/bin/env python3
"""Add language-qualified EN/ES historical spelling articles to Q6 controls."""
import argparse
import hashlib
import json
from pathlib import Path

import check_historical_qualification_archives as archives
import control_ledger as control
from recover_early_ru_sources import archived_source
from register_historical_qualification_controls import V2, inputs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROL = HERE / 'control-ledger.json'
PREFIX = 'historical-spelling-articles-'
MAPS = {
    ('v3', 'en'): 'a6e1c372ac9aaa57c0ff6a32d33d165892ddfeb92f4400ad036ac82f2e63c288',
    ('v3', 'es'): 'd27aebca87ef795dc4f74c966a3a912d0baea37e6375d84655f2ca5ea83ae0da',
    ('v4', 'en'): '4c7d6cefa2f945a69e599830791a20673ecb818d069e0ca01d9cf03c895d696d',
    ('v4', 'es'): '52829200603faad738dfac521037e3a91c1f82ec88112b4e4eee0fe4c2d33c3f',
    ('v2', 'en'): '010e73b16cef526a35ae7c5fac85cdef1333f339ead676ffa8e4de1403696ce1',
    ('v2', 'es'): '791567744f7f5f7d08afc7afa041f94941c8552e24af9a71653634109ac9ffdf',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def derive():
    sources = inputs()
    for (version, language), expected in MAPS.items():
        data = sources[version]
        manifest = json.loads(data['manifest.json'])
        path = archives.ROOT / 'article-maps' / f'{version}-{language}.json'
        raw = path.read_bytes()
        if digest(raw) != expected:
            raise ValueError('HISTORICAL_ARTICLE_MAP_IDENTITY')
        report = json.loads(raw)
        filename = f'spelling-{language}.jsonl'
        ids = {json.loads(line)['id'] for line in data[filename].splitlines()}
        frozen = {}
        for suffix in ('generate_corpus.py', 'source-lock.json'):
            original, sha = next((p, h) for p, h in manifest['sources'].items() if p.endswith('/' + suffix))
            frozen[suffix] = archived_source(ROOT, original, sha)
        lock = json.loads(frozen['source-lock.json'].read_bytes())
        shard = lock['files'][lock['languageFiles'][language]]
        counts = manifest['sourceReceipts'][language]
        matches = report['matchingArticlesByRow']
        if (report['version'] != version or report['language'] != language
                or report['rowsSha256'] != manifest['files'][filename]
                or report['sourceLockSha256'] != digest(frozen['source-lock.json'].read_bytes())
                or report['generatorSha256'] != digest(frozen['generate_corpus.py'].read_bytes())
                or report['sourceShardSha256'] != shard['sha256']
                or report['sourceRevision'] != lock['parquetRevision']
                or report['sourcePath'] != shard['repositoryPath']
                or report['sourceArticlesScanned'] != counts['articlesScanned']
                or report['eligibleArticles'] != counts['articlesSelected']
                or report['missingRows'] or set(matches) != ids or report['rows'] != len(ids)
                or any(not articles for articles in matches.values())
                or report['ambiguousRows'] != sum(len(articles) > 1 for articles in matches.values())):
            raise ValueError('HISTORICAL_ARTICLE_MAP_BINDINGS')
        keys = {control.article_key({'language': language, 'article': article})
                for articles in matches.values() for article in articles}
        corpus_paths = ((V2 / 'manifest.json', V2 / filename) if version == 'v2' else
                        (archives.ROOT / f'qualification-{version}.tar.bz2', archives.ROOT / 'catalog.json'))
        paths = (*corpus_paths, path, *frozen.values(), Path(__file__),
                 HERE / 'control_ledger.py', HERE / 'recover_historical_spelling_articles.py')
        yield {
            'id': f'{PREFIX}{version}-{language}', 'kind': 'source', 'language': language,
            'rowCount': len(keys), 'keys': [], 'articleKeys': sorted(keys),
            'bindings': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
            'semantics': 'All matching articles for disclosed historical spelling rows, including ambiguous matches.',
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--output', type=Path)
    args = parser.parse_args()
    original = CONTROL.read_bytes()
    ledger = control.validate(json.loads(original))
    entries = list(derive())
    present = [entry for entry in ledger['entries'] if entry['id'].startswith(PREFIX)]
    if args.check:
        if present != entries:
            raise ValueError('HISTORICAL_ARTICLE_REGISTRY_DRIFT')
    else:
        output = args.output.resolve()
        if present or not output.is_relative_to(ROOT / 'build'):
            raise ValueError('HISTORICAL_ARTICLE_REGISTRY_OUTPUT')
        ledger['entries'].extend(entries)
        control.validate(ledger)
        if CONTROL.read_bytes() != original or list(derive()) != entries:
            raise ValueError('HISTORICAL_ARTICLE_REGISTRY_INPUT_DRIFT')
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'entries': len(entries),
                      'articleKeys': len({k for entry in entries for k in entry['articleKeys']})}))


if __name__ == '__main__':
    main()
