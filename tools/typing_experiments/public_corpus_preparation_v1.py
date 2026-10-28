"""Versioned finalization of source-extracted proposals behind BOTH exclusion registries.

This gate establishes exclusion checks only, never label/source/model quality.
Current incomplete registries deliberately prevent final corpus publication.
"""
import argparse
import hashlib
import json
from pathlib import Path

import control_ledger as control
from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_families import sha
from source_identities import unsupported_surface_key

TASKS=('spelling','punctuation','protected')


def preflight(rows,task,lexical,controls,profile='new-sentences'):
    validate_ledger(lexical);control.validate(controls)
    if task not in TASKS or profile not in ('new-sentences','new-families'):raise ValueError('PREPARATION_SCOPE')
    if not isinstance(rows,list) or not rows:raise ValueError('PREPARATION_EMPTY_ROWS')
    lexical_overlap={k:0 for k in ('article','sentence','context','family')}
    control_overlap={k:0 for k in ('article','punctuation','protected','regression','surface')}
    errors=set();seen=set();lex_keys={k:set() for k in lexical_overlap};control_keys={k:set() for k in control_overlap};surface_keys=set()
    unsupported=set()
    for row in rows:
        if not isinstance(row,dict):errors.add('row-schema');continue
        if not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen:errors.add('row-id')
        else:seen.add(row['id'])
        language=row.get('language');target=row.get('currentWord') if task=='punctuation' else row.get('expectedSpelling',row.get('typed'))
        typed=row.get('typed',target)
        for token in (typed,target):
            surface=unsupported_surface_key(token,language)
            if surface is not None:surface_keys.add(surface)
        if task=='spelling' and language!='ru':errors.add('unsupported-spelling-language')
        if task=='protected' and (row.get('noAuto') is not True or row.get('cohort')!='protected'
                or type(row.get('expectedCandidate')) is not int or row['expectedCandidate']!=0
                or not isinstance(row.get('candidates'),list) or not row['candidates'] or row['candidates'][0]!=' '+str(typed)):
            errors.add('protected-label-schema')
        if task=='punctuation' and (row.get('task')!='punctuation' or row.get('noAuto') is not True):errors.add('punctuation-label-schema')
        # Both control contexts are checked for every task, including relabeling.
        for token in (typed,target):
            try:
                control_keys['surface'].add(control.surface_key(language,token))
                control_keys['regression'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),typed=token),'regression'))
            except ValueError:errors.add('control-regression-schema')
            try:control_keys['protected'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),typed=token),'protected'))
            except ValueError:errors.add('control-token-schema')
        try:
            control_keys['punctuation'].add(control.key_for(dict(language=language,prefix=row.get('prefix'),currentWord=target,
                expectedBoundary=row.get('expectedBoundary',' ')),'punctuation'))
        except ValueError:errors.add('control-punctuation-schema')
        if task!='protected' or 'article' in row:
            try:control_keys['article'].add(control.article_key(row))
            except ValueError:errors.add('source-article-schema')
        if language=='ru':
            mapped=row|dict(expectedSpelling=target)
            axes=('article','sentence','context','family') if task!='protected' else ('article','sentence','context') if 'article' in row else ('context',)
            for axis in axes:
                try:lex_keys[axis].update(keys_for([mapped],axis))
                except ValueError:errors.add('lexical-'+axis+'-schema')
        elif task!='protected':unsupported.add(str(language))
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
    overlap=any(lexical_overlap.values()) or any(control_overlap.values()) or bool(unsupported_targets)
    complete=lexical['coverage']['complete'] and controls['coverageComplete'] and article_coverage and not unsupported
    status='BLOCKED_OVERLAP' if overlap else 'BLOCKED_IDENTITIES' if errors else 'BLOCKED_COVERAGE' if not complete else 'READY_TO_FREEZE'
    return dict(status=status,task=task,profile=profile,rows=len(rows),lexicalOverlaps=lexical_overlap,controlOverlaps=control_overlap,unsupportedTargetOverlaps=unsupported_targets,
        identityErrors=sorted(errors),unsupportedLexicalLanguages=sorted(unsupported),
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
    report=preflight(rows,task,json.loads(inputs['lexical-ledger.json']),json.loads(inputs['control-ledger.json']),profile)
    report['inputBindings']={name:hashlib.sha256(value).hexdigest() for name,value in inputs.items()}
    report['builderSha256']=sha(Path(__file__))
    report['builderBindings']={name:sha(Path(__file__).with_name(name)) for name in (
        'public_corpus_preparation_v1.py','control_ledger.py','holdout_ledger.py',
        'conversation_split_checks.py','recover_legacy_families.py','source_identities.py')}
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
