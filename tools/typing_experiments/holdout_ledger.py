"""Durable public-data exclusions, independent of ignored corpus directories.

Hashes identify public records; they do not anonymize private text. The bootstrap
ledger is deliberately incomplete. Known overlaps are rejected immediately;
absence of overlap cannot certify freshness until historical coverage is complete.
No old generator or qualification requirement is changed by this module.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from conversation_split_checks import target_context_key

SCHEMA = 1
KEY_SCHEMA = 'rune-public-exclusions-v1'
KINDS = ('article', 'family', 'sentence', 'context')
USAGES = ('supervised', 'disclosed', 'reserved', 'historical-exclusion', 'historical-family-exclusion')
_HASH = re.compile(r'[0-9a-f]{64}\Z')


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('LEDGER_KEY_SCHEMA')
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def _digest(kind, value):
    encoded = json.dumps([KEY_SCHEMA, kind, value], ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def keys_for(rows, kind):
    if kind not in KINDS:
        raise ValueError('LEDGER_KEY_KIND')
    result = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('LEDGER_ROW_SCHEMA')
        if kind == 'article':
            article = row.get('article')
            if (not isinstance(article, str) or not 1 <= len(article) <= 20
                    or not article.isascii() or not article.isdecimal()):
                raise ValueError('LEDGER_ARTICLE_SCHEMA')
            result.add(_digest(kind, ['wikipedia', str(int(article))]))
        elif kind == 'family':
            families = row.get('families', [row.get('family')])
            if not isinstance(families, (list, tuple)) or not families:
                raise ValueError('LEDGER_FAMILY_SCHEMA')
            for family in families:
                result.add(_digest(kind, ['pymorph-lemma-ru', _text(family)]))
        elif kind == 'sentence':
            value = row.get('contextHash')
            if not isinstance(value, str) or not _HASH.fullmatch(value):
                raise ValueError('LEDGER_SENTENCE_SCHEMA')
            result.add(_digest(kind, ['right-context-source-hash-v1', value]))
        else:
            # Same typo-independent normalization as the existing split guard.
            prefix, target = target_context_key(row)
            result.add(_digest(kind, [prefix, target]))
    return result


def validate_ledger(ledger):
    if (not isinstance(ledger, dict) or type(ledger.get('schema')) is not int or ledger.get('schema') != SCHEMA
            or ledger.get('keySchema') != KEY_SCHEMA or ledger.get('publicDataOnly') is not True):
        raise ValueError('LEDGER_SCHEMA')
    coverage = ledger.get('coverage')
    if (not isinstance(coverage, dict) or type(coverage.get('complete')) is not bool
            or not isinstance(coverage.get('pending'), list)
            or any(not isinstance(p, str) or not p for p in coverage['pending'])
            or (coverage['complete'] and coverage['pending'])):
        raise ValueError('LEDGER_COVERAGE')
    entries = ledger.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ValueError('LEDGER_ENTRIES')
    ids = set()
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not entry['id']
                or entry['id'] in ids or entry.get('usage') not in USAGES
                or not isinstance(entry.get('bindings'), dict) or not entry['bindings']
                or any(not isinstance(p, str) or not p or not isinstance(h, str)
                       or not _HASH.fullmatch(h) for p, h in entry['bindings'].items())):
            raise ValueError('LEDGER_ENTRY')
        ids.add(entry['id'])
        generators = entry.get('generatorBindings')
        if generators is not None and (not isinstance(generators, dict) or not generators
                or any(not isinstance(p, str) or not p or not isinstance(h, str)
                       or not _HASH.fullmatch(h) for p, h in generators.items())):
            raise ValueError('LEDGER_GENERATOR_BINDING')
        keys = entry.get('keys'); missing = entry.get('missingAxes')
        if (not isinstance(keys, dict) or not keys or not set(keys) <= set(KINDS)
                or not isinstance(missing, list) or any(k not in KINDS for k in missing)
                or set(keys) & set(missing) or (coverage['complete'] and missing)):
            raise ValueError('LEDGER_ENTRY_KEYS')
        if entry['usage'] in ('supervised', 'historical-family-exclusion'):
            if set(keys) != {'family'} or missing:
                raise ValueError('LEDGER_SUPERVISED_FAMILY_SCOPE')
        elif set(keys) | set(missing) != set(KINDS):
            raise ValueError('LEDGER_ENTRY_AXES_UNDECLARED')
        for values in keys.values():
            if (not isinstance(values, list) or not values or
                    any(not isinstance(v, str) or not _HASH.fullmatch(v) for v in values)
                    or values != sorted(set(values))):
                raise ValueError('LEDGER_ENTRY_KEYS')
    return ledger


def load_ledger(path):
    return validate_ledger(json.loads(Path(path).read_text()))


def assert_disjoint(rows, ledger, *, kinds, usages=None, require_complete=True):
    validate_ledger(ledger)
    if (not isinstance(kinds, (tuple, list)) or not kinds or not set(kinds) <= set(KINDS)
            or (usages is not None and (not isinstance(usages, (tuple, list))
                or not usages or not set(usages) <= set(USAGES)))
            or type(require_complete) is not bool):
        raise ValueError('LEDGER_CHECK_PROFILE')
    rows = tuple(rows)
    if not rows:
        raise ValueError('LEDGER_EMPTY_ROWS')
    for kind in kinds:
        proposed = keys_for(rows, kind)
        blocked = {v for e in ledger['entries'] if usages is None or e['usage'] in usages
                   for v in e['keys'].get(kind, [])}
        if proposed & blocked:
            raise ValueError('LEDGER_OVERLAP:' + kind)
    if require_complete and not ledger['coverage']['complete']:
        raise ValueError('LEDGER_INCOMPLETE')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=Path(__file__).with_name('holdout-ledger.json'))
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--rows', type=Path)
    parser.add_argument('--profile', choices=('new-sentences', 'new-families'), default='new-sentences')
    args = parser.parse_args()
    ledger = load_ledger(args.ledger)
    if args.validate_only:
        if args.rows:
            parser.error('--validate-only does not check rows')
        print(json.dumps(dict(schemaValid=True, freshnessCoverageComplete=ledger['coverage']['complete'],
                              entries=len(ledger['entries']))))
        return
    if args.rows is None:
        parser.error('--rows is required for a freshness check')
    rows = [json.loads(line) for line in args.rows.read_text().splitlines() if line.strip()]
    # Existing new-sentence protocol allows previously evaluated families, but
    # never supervised families. Legacy family-novel protocols exclude all.
    assert_disjoint(rows, ledger, kinds=('family',),
                    usages=('supervised',) if args.profile == 'new-sentences' else None,
                    require_complete=False)
    assert_disjoint(rows, ledger, kinds=('article', 'sentence', 'context'))
    print('LEDGER_DISJOINT')


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from error
