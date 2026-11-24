"""Check historical v6 family flags without scoring or exporting corpus text."""

import argparse
import bz2
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for, load_ledger
from noun_case_focus_forms import accusative_contrast
from recover_available_v6_articles import LEDGER, ROOT
from recover_natural_frozen_corpus import PARTS, digest, encode
from recover_side_context_corpora import EVIDENCE, FREQUENCY, FREQUENCY_SHA
from right_context_grammar_features import completed_following_words

sys.path.insert(0, str(ROOT / 'tools/ci'))
from historical_data_fixtures import read_bundle

PROVENANCE = Path(__file__).with_name('historical_provenance_sources')
MANIFEST = PROVENANCE / 'available_clean_v6_manifest.json'
PARENT_PLAN = PROVENANCE / 'v6-inputs/sentence-pairs-v2-v6-plan.json'
SPELLING_RECEIPT = PROVENANCE / 'v6-inputs/legacy-spelling-rows-recovery.json'
DERIVED_HISTORY = ROOT / 'docs/acceptance/2026-10-27-tatoeba-derived-history-evidence.json'
NOUN_CASE = ROOT / 'docs/acceptance/2026-10-26-noun-case-training-evidence.json'
FLAGS = ('not_previously_bound', 'previously_bound')


def prior_families(directory, bindings):
    locations = {
        'right-context-natural-frozen-20261027': directory / 'natural-frozen',
        'right-context-side-20261027': directory / 'side-context-verified/right-context-side-20261027',
    }
    families, checks = set(), {}
    for corpus, path in locations.items():
        for part in PARTS:
            name = f'corpus/{part}.jsonl'
            binding = f'build/{corpus}/{name}'
            raw = (path / name).read_bytes()
            checks[binding] = digest(raw)
            if checks[binding] != bindings[binding]:
                raise ValueError('V6_FAMILY_BOUND_PAYLOAD:' + binding)
            for row in map(json.loads, raw.splitlines()):
                families.add(row['family'])
                families.update(row.get('families', []))
    return families, checks


def refinement_families(bindings):
    archive = read_bundle()
    parts = {part: archive[f'typing-refinement/data/{part}-rows.jsonl']
             for part in ('train', 'dev', 'test')}
    prefix = 'build/typing-ranker-v2/'
    checks = {f'{prefix}data/{part}-rows.jsonl': digest(payload) for part, payload in parts.items()}
    combined = digest(b''.join(parts.values()))
    for name in ('data/all-rows.jsonl', 'candidates-current/rows.jsonl',
                 'candidates-current-v2/rows.jsonl', 'candidates-current-v2-failed-compile/rows.jsonl',
                 'candidates-current-v2-failed-compile2/rows.jsonl'):
        checks[prefix + name] = combined
    for path, sha256 in checks.items():
        if bindings.get(path) != sha256:
            raise ValueError('V6_FAMILY_REFINEMENT_BINDING:' + path)
    families = {row['family'] for payload in parts.values()
                for row in map(json.loads, payload.splitlines())}
    if any(not isinstance(family, str) or not family for family in families):
        raise ValueError('V6_FAMILY_REFINEMENT_SCHEMA')
    return families, checks


def legacy_spelling_families(directory, bindings):
    receipt = json.loads(SPELLING_RECEIPT.read_bytes())
    families, checks = set(), {}
    for version, record in receipt['corpora'].items():
        original_path = record['originalPath']
        raw = (directory / 'legacy-spelling-rows' / f'v{version}-rows.jsonl').read_bytes()
        if digest(raw) != record['sha256'] or bindings.get(original_path) != record['sha256']:
            raise ValueError('V6_FAMILY_SPELLING_BINDING:' + original_path)
        rows = raw.splitlines()
        declared = {row['family'] for row in map(json.loads, rows)}
        if len(rows) != record['rows'] or len(declared) != record['families']:
            raise ValueError('V6_FAMILY_SPELLING_COUNT:' + original_path)
        families.update(declared)
        checks[original_path] = record['sha256']
    if set(receipt['corpora']) != set(map(str, range(6, 13))) or len(families) != receipt['distinctFamilies']:
        raise ValueError('V6_FAMILY_SPELLING_SCOPE')
    return families, checks


def noun_case_family_keys(entries):
    history = json.loads(DERIVED_HISTORY.read_bytes())['receipt']
    original = json.loads(NOUN_CASE.read_bytes())['cohortManifest']
    result = set()
    # The original generator takes the sole dictionary lemma of the source
    # accusative noun. These dictionary projections include that lemma and
    # have the same cardinality as the original declared sets.
    for part in PARTS:
        count = original['counts'][part]['families']
        path = f'build/noun-case-focus-v3-20261026/corpus/{part}.jsonl'
        entry = entries['public-tatoeba-history-noun-case-v3-' + part]
        keys = entry['keys']['family']
        if (len(keys) != count or history['counts']['noun-case-v3/' + part]['dictionaryFamilies'] != count
                or history['bindings'][path] != original['files'][part + '.jsonl']
                or entry['bindings'][path] != original['files'][part + '.jsonl']):
            raise ValueError('V6_FAMILY_NOUN_CASE_BINDING:' + part)
        result.update(keys)
    return result


def possible_instrumental(lexicon):
    frequency = FREQUENCY.read_bytes()
    if digest(frequency) != FREQUENCY_SHA:
        raise ValueError('V6_FAMILY_FREQUENCY_BINDING')
    candidates = {}
    for line in frequency.decode().splitlines():
        word = line.split()[0]
        if word.endswith(('у', 'ю')) and (forms := accusative_contrast(word, lexicon)):
            lemma, = {tag.lemma for tag in lexicon.analyses(word)}
            candidates.setdefault(forms['instrumental'], []).append(lemma)
    # Only an upper bound. The original generator also applied prior
    # exclusions, context validation and source-sentence selection.
    return {families[0] for families in candidates.values() if len(families) == 1}


def serialize(item, ids, flag):
    forms = [(item['typed'], 'typo', False, False, item['rightContext']),
             (item['typed'], 'unfinished', False, True, ' ' + completed_following_words(item['rightContext'])[0]),
             (item['word'], 'correct', True, False, item['rightContext']),
             ('@' + item['word'], 'protected', True, False, item['rightContext'])]
    if item['rival']:
        forms.append((item['rival'], 'correct_rival', True, False, item['rightContext']))
    rows = [dict(item, familyExposure=flag, id=row_id, split=item['part'], language='ru',
                 typed=typed, group=group, noAuto=control, retainBaseline=retain, rightContext=suffix,
                 expectedSpelling=typed if control else item['word'])
            for row_id, (typed, group, control, retain, suffix) in zip(ids, forms, strict=True)]
    return ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows).encode()


def assignment_masks(groups, known, optional):
    floor = sum(1 << index for index, families in enumerate(groups) if families & known)
    masks = {floor}
    for family in optional:
        affected = sum(1 << index for index, families in enumerate(groups) if family in families)
        masks.update(mask | affected for mask in tuple(masks))
    return floor, masks


def tsv_digest(options):
    hasher = hashlib.sha256()
    index = 0
    for payload, _ in options:
        for row in map(json.loads, payload.splitlines()):
            columns = [str(index), encode(row['id']), row['split'], row['language'],
                       encode(row['prefix']), encode(row['typed'])]
            hasher.update(('\t'.join(columns) + '\n').encode())
            index += 1
    return hasher.hexdigest()


def audit(directory, lexicon):
    manifest = json.loads(MANIFEST.read_bytes())
    evidence = json.loads(EVIDENCE.read_bytes())['receipt']['bindings']
    entries = {e['id']: e for e in load_ledger(LEDGER)['entries']}
    prior, bindings = prior_families(directory, evidence)
    parent = json.loads(PARENT_PLAN.read_bytes())
    refinement, refinement_bindings = refinement_families(parent['exclusionBindings'])
    spelling, spelling_bindings = legacy_spelling_families(directory, parent['exclusionBindings'])
    noun = noun_case_family_keys(entries)
    instrumental = possible_instrumental(lexicon)
    report = dict(schema=1, modelCalls=0, independentQualification=False,
                  originalInputs=bindings | refinement_bindings | spelling_bindings,
                  candidateArchives={}, parts={})
    for part in PARTS:
        name = part + '-context-candidates.json.bz2'
        raw = (directory / name).read_bytes()
        report['candidateArchives'][name] = digest(raw)
        contexts = json.loads(bz2.decompress(raw))
        items = [group['entries'][0]['item'] for group in contexts]
        if (any(len(group['entries']) != 1 for group in contexts)
                or any(item['familyExposure'] is not None or item['part'] != part for item in items)
                or len(items) != manifest['counts'][part]['contexts']
                or sum(len(group['ids']) for group in contexts) != manifest['counts'][part]['rows']):
            raise ValueError('V6_FAMILY_CANDIDATE_SCHEMA:' + part)
        groups = [set(item['families']) for item in items]
        families = set().union(*groups)
        known = prior | {family for family in families if keys_for([{'family': family}], 'family') <= noun}
        prior_exposed = sum(bool(group & known) for group in groups)
        known |= refinement
        refinement_exposed = sum(bool(group & known) for group in groups)
        known |= spelling
        optional = (instrumental & families) - known
        if len(optional) > 16:
            raise ValueError('V6_FAMILY_PROBE_TOO_LARGE:' + part)
        floor, masks = assignment_masks(groups, known, optional)
        options = [tuple(serialize(item, group['ids'], flag) for flag in FLAGS)
                   for item, group in zip(items, contexts, strict=True)]
        projection = tsv_digest(options)
        if projection != manifest['files'][part + '.tsv']:
            raise ValueError('V6_FAMILY_TSV_DIGEST:' + part)
        matches = 0
        for mask in masks:
            hasher = hashlib.sha256()
            for index, payload in enumerate(options):
                hasher.update(payload[(mask >> index) & 1])
            matches += hasher.hexdigest() == manifest['files'][part + '.jsonl']
        counts = Counter(item['sideGroup'] for i, item in enumerate(items) if (floor >> i) & 1)
        report['parts'][part] = dict(contexts=len(items), confirmedExposed=floor.bit_count(),
                                     additionalRefinementExposed=refinement_exposed - prior_exposed,
                                     additionalLegacySpellingExposed=floor.bit_count() - refinement_exposed,
                                     exactTsvSha256=projection,
                                     confirmedExposedByGroup=dict(sorted(counts.items())),
                                     matchingDeclaredFamilies=len(known & families),
                                     optionalInstrumentalFamilies=len(optional),
                                     distinctAssignmentsChecked=len(masks), exactJsonlMatches=matches)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon
    print(json.dumps(audit(args.input_dir, PymorphyLexicon(cache_size=16384)), indent=2))


if __name__ == '__main__':
    main()
