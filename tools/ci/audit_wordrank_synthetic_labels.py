"""Reproduce disclosed word-ranking labels with a hash-bound helper candidate.

The historical manifest binds the selector, not the helper imported at runtime.
Matching the rows is evidence of compatibility, not proof of historical execution
or of natural typo labels. No corpus, model or registry is modified.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unicodedata

import historical_model_fixtures as fixtures
from frozen_source_identity import read_frozen_source

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = 'tools/typing_experiments/prepare_word_ranking.py'
HELPER = 'tools/typing_experiments/prepare_refinement.py'
HELPER_SHA = 'd2d84c3f328771fd0b9908a9216ee428eb2877079c8dacb481c42a0dafe11bab'
VOCABULARY = ROOT / 'tools/ci/product-replay-v1/sources/ru_50k.txt'
PREFIX = 'build/typing-word-ranking/data/'


def functions(raw, names, namespace):
    """Compile only the named, hash-verified pure functions and constants."""
    tree = ast.parse(raw)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            selected.append(node)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names:
            selected.append(node)
    found = {node.name if isinstance(node, ast.FunctionDef) else node.targets[0].id for node in selected}
    if found != set(names) or len(selected) != len(names):
        raise ValueError('WORDRANK_AUDIT_SOURCE_SCOPE')
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<verified-wordrank-source>', 'exec'), namespace)


def check_rows(rows, selector, helper, vocabulary):
    counts = Counter()
    seen = set()
    for row in rows:
        try:
            article, word, prefix = row['articleId'], row['expectedSpelling'], row['prefix']
            if not all(isinstance(value, str) and value for value in (article, word, prefix)):
                raise ValueError('WORDRANK_AUDIT_ROW')
            context = helper.digest((prefix.lower() + '\0' + word).encode())
            identity = helper.digest((selector['SEED'] + ':' + article + ':' + context).encode())
            edits = (1, 1, 2, 2, 3, 0)[int(identity[:8], 16) % 6]
            expected_id = 'wordrank-' + identity[:24]
            mutation = selector['mutate'](word, identity, edits, vocabulary)
            if (row['id'] != expected_id or row['id'] in seen or
                    row['partition'] != selector['partition'](article) or
                    row['language'] != 'ru' or row['family'] != word or
                    row['template'] != 'article-' + article or
                    row['split'] != {'train': 'calibration', 'dev': 'diagnostic', 'test': 'holdout'}[row['partition']] or
                    type(row['errorCount']) is not int or row['errorCount'] != edits or
                    row['category'] != f'edit-{edits}' or
                    row['cohort'] != ('correct' if edits == 0 else 'typo') or
                    type(row['noAuto']) is not bool or row['noAuto'] != (edits == 0) or
                    mutation is None or (row['typed'], row['operations']) != mutation):
                raise ValueError('WORDRANK_AUDIT_ROW')
            seen.add(row['id'])
            counts[row['partition']] += 1
            counts[f'edit-{edits}'] += 1
        except (KeyError, TypeError, AttributeError, IndexError) as exc:
            raise ValueError('WORDRANK_AUDIT_ROW') from exc
    if not seen:
        raise ValueError('WORDRANK_AUDIT_EMPTY')
    return dict(sorted(counts.items()))


def audit():
    root = ROOT
    _, payloads = fixtures.verify()
    manifest = json.loads(payloads[PREFIX + 'manifest.json'])
    selector_sha = manifest['preparationScriptSha256']
    selector_raw = read_frozen_source(root, SELECTOR, selector_sha)
    helper_raw = read_frozen_source(root, HELPER, HELPER_SHA)
    frequency_path = root / VOCABULARY.relative_to(ROOT)
    frequency_raw = frequency_path.read_bytes()
    frequency_sha = hashlib.sha256(frequency_raw).hexdigest()
    if frequency_sha != manifest['frequencySha256']:
        raise ValueError('WORDRANK_AUDIT_FREQUENCY')
    vocabulary = {unicodedata.normalize('NFC', line.rsplit(' ', 1)[0]).lower()
                  for line in frequency_raw.decode().splitlines()}
    helper_namespace = {'hashlib': hashlib}
    functions(helper_raw, ('KEY_ROWS', 'digest', 'perturb'), helper_namespace)
    helper = SimpleNamespace(digest=helper_namespace['digest'], perturb=helper_namespace['perturb'])
    selector = {'public': helper}
    functions(selector_raw, ('SEED', 'partition', 'distance', 'mutate'), selector)
    all_rows = payloads[PREFIX + 'all-rows.jsonl']
    if all_rows != b''.join(payloads[PREFIX + part + '-rows.jsonl'] for part in ('train', 'dev', 'test')):
        raise ValueError('WORDRANK_AUDIT_PARTITION_CONTENT')
    rows = [json.loads(line) for line in all_rows.splitlines()]
    counts = check_rows(rows, selector, helper, vocabulary)
    if any(counts.get(part, 0) != manifest['partitions'][part]['rows'] for part in ('train', 'dev', 'test')):
        raise ValueError('WORDRANK_AUDIT_COUNTS')
    if (frequency_path.read_bytes() != frequency_raw or
            read_frozen_source(root, SELECTOR, selector_sha) != selector_raw or
            read_frozen_source(root, HELPER, HELPER_SHA) != helper_raw):
        raise ValueError('WORDRANK_AUDIT_INPUT_DRIFT')
    return {'scope': 'disclosed-wordrank-synthetic-label-compatibility', 'rows': len(rows),
            'counts': counts, 'selectorSha256': selector_sha, 'helperCandidateSha256': HELPER_SHA,
            'frequencySha256': frequency_sha,
            'manifestSha256': hashlib.sha256(payloads[PREFIX + 'manifest.json']).hexdigest(),
            'rowsSha256': hashlib.sha256(all_rows).hexdigest(),
            'auditSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'historicalHelperIdentityEstablished': False,
            'historicalExecutionEstablished': False, 'independentQualification': False}


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True, indent=2))
