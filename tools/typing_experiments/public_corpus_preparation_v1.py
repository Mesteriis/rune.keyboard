"""Versioned finalization of source-extracted proposals behind BOTH exclusion registries.

This gate establishes exclusion checks only, never label/source/model quality.
Current incomplete registries deliberately prevent final corpus publication.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re

import control_ledger as control
import english_family_keys
import ewt_surface_exclusions_v1 as english_surfaces
from holdout_ledger import keys_for,load_ledger,validate_ledger,require_source_segment
from recover_legacy_families import sha
from source_identities import unsupported_surface_key

TASKS=('spelling','punctuation','protected')
APOSTROPHES="'’ʼ"
WIKISOURCE = 'wikimedia/wikisource'
WIKISOURCE_PAGE = re.compile(r'wikisource:([1-9][0-9]{0,19})\Z')
WIKISOURCE_REVISION = re.compile(r'[1-9][0-9]{0,19}\Z')


def wikisource_page_key(row):
    if not isinstance(row, dict) or row.get('sourceRepository') != WIKISOURCE or row.get('language') != 'ru':
        raise ValueError('WIKISOURCE_PAGE_SCOPE')
    article = row.get('article')
    revision = row.get('sourceRevision')
    if not isinstance(article, str) or not isinstance(revision, str) or not WIKISOURCE_REVISION.fullmatch(revision):
        raise ValueError('WIKISOURCE_PAGE_IDENTITY')
    page = WIKISOURCE_PAGE.fullmatch(article)
    if page is None:
        raise ValueError('WIKISOURCE_PAGE_IDENTITY')
    # Revisions identify the captured text. Exclusions apply across revisions of the same page.
    identity = ['rune-public-wikisource-page-v1', 'ru.wikisource.org', page[1]]
    return hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()


def english_surface_variants(value):
    """Conservatively check equivalent apostrophe forms without changing old keys."""
    if not isinstance(value, str):
        return (value,)
    positions = [i for i, char in enumerate(value) if char in APOSTROPHES]
    if len(positions) > 4:
        raise ValueError('ENGLISH_APOSTROPHE_VARIANTS_UNSUPPORTED')
    variants = set()
    for replacement in itertools.product(APOSTROPHES, repeat=len(positions)):
        chars = list(value)
        for index, char in zip(positions, replacement):
            chars[index] = char
        variants.add(''.join(chars))
    return tuple(sorted(variants))


def registry_bindings_v1(lexical_bytes,control_bytes):
    """Bind exact snapshots and canonical full entries, including provenance.

    These are public-record identifiers, not privacy-preserving hashes or proof
    of complete exclusions. Report consumers must still inspect gate status.
    """
    result={'schema':'rune-acceptance-registry-bindings-v1','registries':{}}
    for name,raw,validator,coverage in (
            ('lexical-ledger.json',lexical_bytes,validate_ledger,lambda x:x['coverage']['complete']),
            ('control-ledger.json',control_bytes,control.validate,lambda x:x['coverageComplete'])):
        ledger=validator(json.loads(raw))
        entries={e['id']:hashlib.sha256(json.dumps(e,ensure_ascii=False,sort_keys=True,
                    separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
                 for e in ledger['entries']}
        result['registries'][name]=dict(sha256=hashlib.sha256(raw).hexdigest(),
            coverageComplete=coverage(ledger),entrySha256=entries)
    return result


def english_surface_bindings():
    """Bind the required public sidecar and all code used to identify it."""
    english_surfaces.load()
    names=('ewt_surface_exclusions_v1.py','ewt-surface-exclusions-v1.json',
           'import_english_ewt_exposure.py','public_sources/ud-ewt-2.18/source-lock.json',
           'public_corpus_preparation_v1.py','control_ledger.py','english_family_keys.py',
           'holdout_ledger.py','source_identities.py','conversation_split_checks.py','recover_legacy_families.py')
    bindings={name:sha(Path(__file__).parent/name) for name in names}
    if (bindings['ewt-surface-exclusions-v1.json']!=english_surfaces.FIXTURE_SHA or
            bindings['public_sources/ud-ewt-2.18/source-lock.json']!=english_surfaces.LOCK_SHA):
        raise ValueError('ACCEPTANCE_SURFACE_DRIFT')
    return bindings


def registry_bindings(lexical_bytes,control_bytes):
    result=registry_bindings_v1(lexical_bytes,control_bytes)
    result['schema']='rune-acceptance-registry-bindings-v2'
    result['englishSurfaceBindings']=english_surface_bindings()
    return result


def verify_registry_bindings(report,lexical_path,control_path):
    """Check current public ledgers against a report; does not approve its corpus."""
    expected=registry_bindings(Path(lexical_path).read_bytes(),Path(control_path).read_bytes())
    if (not isinstance(report,dict) or report.get('registryBindings')!=expected
            or not isinstance(report.get('inputBindings'),dict)
            or any(report['inputBindings'].get(name)!=binding['sha256']
                   for name,binding in expected['registries'].items())):
        raise ValueError('ACCEPTANCE_REGISTRY_DRIFT')
    return expected


def verify_historical_registry_bindings_v1(report,lexical_path,control_path):
    """Verify old ledger identities only; this does not check surface exclusions."""
    expected=registry_bindings_v1(Path(lexical_path).read_bytes(),Path(control_path).read_bytes())
    if (not isinstance(report,dict) or report.get('registryBindings')!=expected
            or not isinstance(report.get('inputBindings'),dict)
            or any(report['inputBindings'].get(name)!=binding['sha256']
                   for name,binding in expected['registries'].items())):
        raise ValueError('ACCEPTANCE_REGISTRY_DRIFT')
    return expected


def preflight(rows,task,lexical,controls,profile='new-sentences'):
    validate_ledger(lexical);control.validate(controls)
    if task not in TASKS or profile not in ('new-sentences','new-families'):raise ValueError('PREPARATION_SCOPE')
    if not isinstance(rows,list) or not rows:raise ValueError('PREPARATION_EMPTY_ROWS')
    lexical_overlap={k:0 for k in ('article','sentence','context','family')}
    control_overlap={k:0 for k in ('article','punctuation','protected','regression','surface')}
    errors=set();seen=set();lex_keys={k:set() for k in lexical_overlap};control_keys={k:set() for k in control_overlap};surface_keys=set()
    unsupported=set();english_surface_keys=set()
    for row in rows:
        if not isinstance(row,dict):errors.add('row-schema');continue
        if not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen:errors.add('row-id')
        else:seen.add(row['id'])
        language=row.get('language');target=row.get('currentWord') if task=='punctuation' else row.get('expectedSpelling',row.get('typed'))
        typed=row.get('typed',target)
        for token in (typed,target):
            surface=unsupported_surface_key(token,language)
            if surface is not None:surface_keys.add(surface)
            if language=='en' and profile=='new-families':
                try:
                    for variant in english_surface_variants(token):
                        english_surface=control.surface_key('en',variant)
                        english_surface_keys.add(english_surface)
                        surface_keys.add(english_surface)
                except ValueError:errors.add('english-surface-schema')
        if task=='spelling' and language!='ru':errors.add('unsupported-spelling-language')
        if task=='protected' and (row.get('noAuto') is not True or row.get('cohort')!='protected'
                or type(row.get('expectedCandidate')) is not int or row['expectedCandidate']!=0
                or not isinstance(row.get('candidates'),list) or not row['candidates'] or row['candidates'][0]!=' '+str(typed)):
            errors.add('protected-label-schema')
        if task=='punctuation' and (row.get('task')!='punctuation' or row.get('noAuto') is not True):errors.add('punctuation-label-schema')
        # Both control contexts are checked for every task, including relabeling.
        for token in (typed,target):
            try:
                variants=english_surface_variants(token) if language=='en' else (token,)
                control_keys['surface'].update(control.surface_key(language,variant) for variant in variants)
                control_keys['regression'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),typed=token),'regression'))
            except ValueError:errors.add('control-regression-schema')
            try:control_keys['protected'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),typed=token),'protected'))
            except ValueError:errors.add('control-token-schema')
        try:
            control_keys['punctuation'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),currentWord=target,
                expectedBoundary=row.get('expectedBoundary',' ')),'punctuation'))
        except ValueError:errors.add('control-punctuation-schema')
        wikisource = row.get('sourceRepository') == WIKISOURCE
        has_source = task != 'protected' or 'article' in row or wikisource
        page_key = None
        if has_source:
            try:
                page_key = wikisource_page_key(row) if wikisource else control.article_key(row)
                control_keys['article'].add(page_key)
            except ValueError:errors.add('source-article-schema')
        if language=='ru':
            mapped=row|dict(expectedSpelling=target)
            if has_source:
                segment_row = {'sourceSegmentHash': row.get('sourceSegmentHash')} if wikisource else row
                try:require_source_segment(segment_row)
                except ValueError:errors.add('source-segment-schema')
            axes=('article','sentence','context','family') if task!='protected' else ('article','sentence','context') if has_source else ('context',)
            for axis in axes:
                if wikisource and axis=='article':
                    if page_key is not None:lex_keys[axis].add(page_key)
                    continue
                # Source-neutral sentence keys still match disclosed text from other collections.
                key_row = mapped
                if wikisource and axis=='sentence':
                    key_row = {key: row[key] for key in ('contextHash', 'sourceSegmentHash') if key in row}
                try:lex_keys[axis].update(keys_for([key_row],axis))
                except ValueError:errors.add('lexical-'+axis+'-schema')
        elif language=='en':
            # The registry already quarantines these English source identities.
            # Detect overlap even though English lexical-family qualification is
            # not yet supported; this branch must never grant readiness by itself.
            if row.get('sourceRepository') in ('tatoeba','ud-english-ewt'):
                unsupported.add('en')
                for axis in ('article','sentence'):
                    try:lex_keys[axis].update(keys_for([row],axis))
                    except ValueError:errors.add('lexical-'+axis+'-schema')
            elif task!='protected' or 'article' in row or 'sourceRepository' in row:
                unsupported.add('en')
            if 'englishLemmas' in row:
                unsupported.add('en')
                try:lex_keys['family'].update(english_family_keys.keys_for(row['englishLemmas']))
                except ValueError:errors.add('lexical-en-family-schema')
        elif task!='protected' or 'article' in row or 'sourceRepository' in row:
            unsupported.add(str(language))
    for axis,proposed in lex_keys.items():
        blocked={k for e in lexical['entries'] if axis!='family' or profile=='new-families' or e['usage'] in ('supervised','prepared-training-quarantine')
                 for k in e['keys'].get(axis,[])}
        lexical_overlap[axis]=len(proposed&blocked)
    for kind in ('punctuation','protected','regression'):
        blocked={k for e in controls['entries'] if e['kind']==kind for k in e['keys']}
        control_overlap[kind]=len(control_keys[kind]&blocked)
    control_overlap['surface']=len(control_keys['surface']&{k for e in controls['entries'] for k in e.get('surfaceKeys',[])})
    articles={k for e in controls['entries'] for k in e.get('articleKeys',[])}
    control_overlap['article']=len(control_keys['article']&articles)
    punctuation=[e for e in controls['entries'] if e['kind']=='punctuation']
    article_coverage=bool(punctuation) and all(e.get('articleKeys') for e in punctuation)
    unsupported_targets=len(surface_keys & {k for entry in lexical['entries'] for k in entry.get('unsupportedSurfaceKeys',[])})
    english_surface_overlap=len(english_surface_keys & english_surfaces.load()) if english_surface_keys else 0
    overlap=any(lexical_overlap.values()) or any(control_overlap.values()) or bool(unsupported_targets) or bool(english_surface_overlap)
    complete=lexical['coverage']['complete'] and controls['coverageComplete'] and article_coverage and not unsupported
    status='BLOCKED_OVERLAP' if overlap else 'BLOCKED_IDENTITIES' if errors else 'BLOCKED_COVERAGE' if not complete else 'READY_TO_FREEZE'
    return dict(status=status,task=task,profile=profile,rows=len(rows),lexicalOverlaps=lexical_overlap,controlOverlaps=control_overlap,unsupportedTargetOverlaps=unsupported_targets,
        identityErrors=sorted(errors),unsupportedLexicalLanguages=sorted(unsupported),englishSourceSurfaceOverlaps=english_surface_overlap,
        lexicalCoverageComplete=lexical['coverage']['complete'],controlCoverageComplete=controls['coverageComplete'],
        controlArticleCoverage=article_coverage,modelQualityQualified=False,sourceLabelsQualified=False)


def prepare(rows_path,manifest_path,output,task,lexical_path,controls_path,profile='new-sentences'):
    output=Path(output)
    if output.exists():raise ValueError('PREPARATION_OUTPUT_EXISTS')
    rows_path=Path(rows_path);manifest_path=Path(manifest_path)
    # Read and bind immutable input bytes before any output directory is created.
    inputs={name:Path(path).read_bytes() for name,path in (
        ('rows.jsonl',rows_path),('source-manifest.json',manifest_path),('lexical-ledger.json',lexical_path),('control-ledger.json',controls_path))}
    manifest=json.loads(inputs['source-manifest.json'])
    digest=hashlib.sha256(inputs['rows.jsonl']).hexdigest()
    if (manifest.get('containsPersonalMessages') is not False or manifest.get('frozenBeforeScoring') is not True
            or manifest.get('files',{}).get(rows_path.name)!=digest):raise ValueError('PREPARATION_PROPOSAL_BINDING')
    rows=[json.loads(line) for line in inputs['rows.jsonl'].decode().splitlines()]
    extra={name:sha(Path(__file__).parent/name) for name in
           ('ewt_surface_exclusions_v1.py','ewt-surface-exclusions-v1.json',
            'import_english_ewt_exposure.py','public_sources/ud-ewt-2.18/source-lock.json')}
    report=preflight(rows,task,json.loads(inputs['lexical-ledger.json']),json.loads(inputs['control-ledger.json']),profile)
    report['inputBindings']={name:hashlib.sha256(value).hexdigest() for name,value in inputs.items()}
    report['registryBindings']=registry_bindings(inputs['lexical-ledger.json'],inputs['control-ledger.json'])
    report['builderSha256']=sha(Path(__file__))
    report['builderBindings']={name:sha(Path(__file__).with_name(name)) for name in (
        'public_corpus_preparation_v1.py','control_ledger.py','holdout_ledger.py',
        'conversation_split_checks.py','recover_legacy_families.py','source_identities.py','english_family_keys.py')}
    if extra!={name:sha(Path(__file__).parent/name) for name in extra}:raise ValueError('PREPARATION_SURFACE_INPUT_DRIFT')
    report['builderBindings'].update(extra)
    if report['status']!='READY_TO_FREEZE':return report
    # Exclusion success would still require independent source/label/cohort/model qualification.
    output.mkdir(parents=True,exist_ok=False)
    for name,value in inputs.items():(output/name).write_bytes(value)
    (output/'preparation.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    return report


def cli(task=None):
    parser=argparse.ArgumentParser(description=__doc__)
    if task is None:parser.add_argument('--kind',choices=('punctuation','protected'),required=True)
    parser.add_argument('--rows',type=Path,required=True);parser.add_argument('--source-manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lexical-ledger',type=Path,default=Path(__file__).with_name('holdout-ledger.json'))
    parser.add_argument('--control-ledger',type=Path,default=Path(__file__).with_name('control-ledger.json'))
    parser.add_argument('--profile',choices=('new-sentences','new-families'),default='new-sentences')
    args=parser.parse_args()
    try:report=prepare(args.rows,args.source_manifest,args.output,task or args.kind,args.lexical_ledger,args.control_ledger,args.profile)
    except (ValueError,OSError) as error:raise SystemExit(str(error)) from error
    print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['status']=='READY_TO_FREEZE' else 2)
