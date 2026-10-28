"""Read-only source/registry audit of retained disclosed conversational examples.

Default checks need only Git sources. --historical-root additionally verifies
the pinned original public data and recorded proposals, without model scoring.
"""
import argparse
import bz2
import hashlib
import json
from pathlib import Path
import re
import subprocess

from holdout_ledger import keys_for, load_ledger
import import_tatoeba_history as history

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = 'tools/typing_experiments/fixtures/'
PINS = {
    'context_ranker_regressions_20261026.jsonl': 'e34c64edfd6f80a0594a8d362c5ce028ab8f1f2dd3f548c35cf7591835a94b68',
    'conversation_supervised_false_proposals_20261026.json': 'ea5978c5ac9436087d19427bd5fea0bfbcd4c7460c3800f60484eeb0ea46d7a9',
}
CASE_FIELDS = {'id', 'typed', 'expectedSpelling', 'rejectedProposal', 'sourceSentence',
               'sourceSentenceUrl', 'sourceContributor', 'contextSha256',
               'intendedTargetWasRetrieved', 'sameLemmaAsProposal'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_fixtures(rows, document):
    if len(rows) != 35 or len({r['id'] for r in rows}) != 35:
        raise ValueError('DISCLOSED_ROW_IDENTITY')
    for row in rows:
        if (row['purpose'] != 'REGRESSION_ONLY_NOT_TRAINING' or row['split'] != 'holdout'
                or row['language'] != 'ru' or row['noAuto'] is not False
                or row['baselineRawWinner'].casefold() != row['expectedSpelling'].casefold()
                or row['rejectedRawWinner'].casefold() == row['expectedSpelling'].casefold()):
            raise ValueError('DISCLOSED_REGRESSION_ROLE')
    cases = document['cases']
    if (document['purpose'] != 'REGRESSION_ONLY_NOT_TRAINING' or len(cases) != 5
            or len({c['id'] for c in cases}) != 5):
        raise ValueError('DISCLOSED_CASE_IDENTITY')
    for case in cases:
        if (set(case) != CASE_FIELDS or not case['sourceContributor']
                or re.fullmatch('tatoeba:[0-9]+', case['sourceSentence']) is None
                or case['sourceSentenceUrl'] != 'https://tatoeba.org/en/sentences/show/' + case['sourceSentence'].split(':')[1]
                or re.fullmatch('[0-9a-f]{64}', case['contextSha256']) is None
                or case['intendedTargetWasRetrieved'] is not True
                or type(case['sameLemmaAsProposal']) is not bool
                or case['rejectedProposal'].casefold() == case['expectedSpelling'].casefold()):
            raise ValueError('DISCLOSED_CASE_SCHEMA_OR_ATTRIBUTION')


def require_registry_coverage(rows, document, ledger):
    blocked = {axis: {key for entry in ledger['entries'] for key in entry['keys'].get(axis, [])}
               for axis in ('article', 'sentence', 'context')}
    mapped = [row | dict(sourceRepository='tatoeba') for row in rows]
    counts = {}
    for axis in blocked:
        keys = keys_for(mapped, axis)
        if keys - blocked[axis]:
            raise ValueError('DISCLOSED_REGISTRY_GAP ' + axis)
        counts['cc0_' + axis] = len(keys)
    cases = [dict(sourceRepository='tatoeba', language='ru', article=c['sourceSentence'])
             for c in document['cases']]
    keys = keys_for(cases, 'article')
    if keys - blocked['article']:
        raise ValueError('DISCLOSED_REGISTRY_GAP detailed_article')
    counts['detailed_article'] = len(keys)
    return counts


def verify_historical(root, rows, document):
    root = Path(root)
    bindings = {}

    def bound(name, expected=None):
        path = root / name
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError('DISCLOSED_HISTORICAL_INPUT_IDENTITY')
        bindings[name] = digest
        return path

    lock = json.loads(bound(history.CC0_ROOT + '/tatoeba-source-lock.json', history.CC0_LOCK_SHA).read_text())
    cc0 = bound(history.CC0_ROOT + '/rus_sentences_CC0.tsv.bz2', lock['compressedSha256'])
    directory, manifest_sha, _ = history.CORPORA['context-feature']
    manifest = json.loads(bound(directory + '/manifest.json', manifest_sha).read_text())
    original = {r['id']: r for r in map(json.loads, bound(directory + '/holdout.jsonl',
                manifest['files']['holdout.jsonl']).read_text().splitlines())}
    wanted, captures = {}, {}
    for row in rows:
        if {k: v for k, v in row.items() if k not in ('baselineRawWinner', 'rejectedRawWinner', 'purpose')} != original[row['id']]:
            raise ValueError('DISCLOSED_ORIGINAL_ROW_CHANGED')
        identity = row['article'].split(':')[1]
        wanted[identity] = row['sentenceHash']
        captures.setdefault(identity, set()).add(row['prefix'])
    history.verify_sources(cc0, wanted, 4, captures)
    detail = bound(history.DETAIL_ROOT + '/rus_sentences_detailed.tsv.bz2', history.DETAIL_SHA)
    bound(history.DETAIL_ROOT + '/frozen-policy.json', document['frozenPolicySha256'])
    bound(history.DETAIL_ROOT + '/experimental-ranker.bin', document['modelSha256'])
    directory, manifest_sha, _ = history.CORPORA['promoted-followon']
    manifest = json.loads(bound(directory + '/manifest.json', manifest_sha).read_text())
    original = {r['id']: r for r in map(json.loads, bound(directory + '/holdout.jsonl',
                manifest['rowSha256']).read_text().splitlines())}
    proposals = json.loads(bound(history.DETAIL_ROOT + '/followon-proposals.json').read_text())
    wrong = {r['id']: r for r in proposals if r['correct'] is False}
    if len(wrong) != 5:
        raise ValueError('DISCLOSED_RECORDED_PROPOSAL_COUNT')
    wanted, captures, owners = {}, {}, {}
    for case in document['cases']:
        row, proposal = original[case['id']], wrong[case['id']]
        if (case['typed'] != row['typed'] or case['typed'] != proposal['typed']
                or case['expectedSpelling'] != row['expectedSpelling']
                or case['expectedSpelling'] != proposal['target']
                or case['rejectedProposal'] != proposal['proposal']
                or case['sourceSentence'] != row['article']
                or case['sourceContributor'] != row['owner']
                or case['contextSha256'] != hashlib.sha256(row['prefix'].encode()).hexdigest()):
            raise ValueError('DISCLOSED_PROPOSAL_SOURCE_CHANGED')
        identity = case['sourceSentence'].split(':')[1]
        wanted[identity] = row['sentenceHash']
        captures.setdefault(identity, set()).add(row['prefix'])
        owners[identity] = case['sourceContributor']
    history.verify_sources(detail, wanted, 6, captures)
    seen = set()
    with bz2.open(detail, 'rt', encoding='utf-8') as stream:
        for line in stream:
            fields = line.rstrip('\n').split('\t')
            if fields[0] in owners:
                if fields[3] != owners[fields[0]]:
                    raise ValueError('DISCLOSED_CONTRIBUTOR_CHANGED')
                seen.add(fields[0])
    if seen != set(owners):
        raise ValueError('DISCLOSED_CONTRIBUTOR_MISSING')
    return bindings


def audit(root=ROOT, historical_root=None):
    names = [FIXTURES + name for name in PINS]
    subprocess.run(['git', 'ls-files', '--error-unmatch', '--', *names], cwd=root,
                   stdout=subprocess.DEVNULL, check=True)
    for name, digest in PINS.items():
        if sha(root / (FIXTURES + name)) != digest:
            raise ValueError('DISCLOSED_FIXTURE_BYTES')
    rows = [json.loads(s) for s in (root / names[0]).read_text().splitlines()]
    document = json.loads((root / names[1]).read_text())
    validate_fixtures(rows, document)
    ledger_name = 'tools/typing_experiments/holdout-ledger.json'
    coverage = require_registry_coverage(rows, document, load_ledger(root / ledger_name))
    return dict(purpose='DISCLOSED_FIXTURE_SOURCE_AND_EXCLUSION_AUDIT', rows=35, cases=5,
                registryCoverage=coverage, ledgerSha256=sha(root / ledger_name),
                fixtureSha256=PINS, historicalSourcesVerified=historical_root is not None,
                historicalBindings=verify_historical(historical_root, rows, document) if historical_root is not None else {},
                modelExecutionEstablished=False, freshQualificationEstablished=False,
                canonicalFamilyCoverageEstablished=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(historical_root=args.historical_root), indent=2, sort_keys=True))
