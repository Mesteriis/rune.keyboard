"""Check both registries against the reviewed Russian Wikisource page captures."""
import hashlib
import json
from pathlib import Path
import re

import control_ledger as control
import holdout_ledger as lexical
from public_corpus_preparation_v1 import WIKISOURCE as REPOSITORY, wikisource_page_key

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'wikisource-page-exposure-v1.json'
MANIFEST_SHA256 = '57525f5ff359d8eb8813294d6fb8a07ef2f1fe1678377b032f4b0c3ec1dd6b88'
ENTRY = 'public-ru-wikisource-page-exposure-v1'
CAPTURES = {
    'public-a4-wikisource-direct-speech-colons-v1': re.compile(r'wikisource/([0-9]+)\.html\Z'),
    'public-q5-wikisource-same-surface-names-v1': re.compile(r'ru\.wikisource\.org/\?oldid=([0-9]+)\Z'),
}


def entries(raw, control_registry):
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'sourceRepository', 'language', 'pages'} or
            type(manifest['schema']) is not int or manifest['schema'] != 1 or
            manifest['sourceRepository'] != REPOSITORY or manifest['language'] != 'ru' or
            not isinstance(manifest['pages'], list)):
        raise ValueError('WIKISOURCE_EXPOSURE_SCHEMA')
    original = {
        (entry['id'], binding): (match[1], digest)
        for entry in control_registry['entries'] if entry['id'] in CAPTURES
        for binding, digest in entry['bindings'].items()
        if (match := CAPTURES[entry['id']].fullmatch(binding)) is not None
    }
    actual = {}
    keys = set()
    page_ids = []
    for page in manifest['pages']:
        if (not isinstance(page, dict) or set(page) !=
                {'pageId', 'revisionId', 'renderedSha256', 'contextEntry', 'contextBinding'} or
                any(type(value) is not str for value in page.values())):
            raise ValueError('WIKISOURCE_EXPOSURE_ROW')
        ref = page['contextEntry'], page['contextBinding']
        key = wikisource_page_key({'sourceRepository': REPOSITORY, 'language': 'ru',
                                   'article': f"wikisource:{page['pageId']}", 'sourceRevision': page['revisionId']})
        if key in keys or ref in actual:
            raise ValueError('WIKISOURCE_EXPOSURE_IDENTITY')
        actual[ref] = page['revisionId'], page['renderedSha256']
        keys.add(key)
        page_ids.append(int(page['pageId']))
    if (not original or set(CAPTURES) != {ref[0] for ref in original} or actual != original or
            page_ids != sorted(page_ids)):
        raise ValueError('WIKISOURCE_EXPOSURE_CAPTURE_DRIFT')

    bindings = {'tools/typing_experiments/' + MANIFEST.name: hashlib.sha256(raw).hexdigest()}
    article_keys = sorted(keys)
    common = dict(id=ENTRY, rowCount=len(article_keys), bindings=bindings)
    control_entry = dict(common, kind='source', language='ru', keys=[], articleKeys=article_keys)
    lexical_entry = dict(common, usage='historical-exclusion', sourceRepository=REPOSITORY,
                         keys={'article': article_keys}, missingAxes=['family', 'sentence', 'context'])
    return control_entry, lexical_entry


def check():
    raw = MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('WIKISOURCE_EXPOSURE_MANIFEST_DRIFT')
    control_registry = control.load(ROOT / 'control-ledger.json')
    lexical_registry = lexical.load_ledger(ROOT / 'holdout-ledger.json')
    expected = entries(raw, control_registry)
    for registry, entry in zip((control_registry, lexical_registry), expected, strict=True):
        if [row for row in registry['entries'] if row['id'] == ENTRY] != [entry]:
            raise ValueError('WIKISOURCE_EXPOSURE_REGISTRY_DRIFT')
    return expected[0]['rowCount']


if __name__ == '__main__':
    print(json.dumps({'wikisourcePages': check(), 'independentQualification': False}))
