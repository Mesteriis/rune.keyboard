"""Import exact public punctuation/protected components into a separate registry."""
import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

from control_ledger import SCHEMA,LANGUAGES,key_for,load,validate
import check_historical_qualification_archives as archives
from import_early_ru_history import CORPORA,ROOT
from recover_early_ru_sources import archived_source
from recover_legacy_families import sha


def load_original(root,manifest):
    original=next(p for p in manifest['sources'] if p.endswith('/generate_corpus.py'))
    digest=manifest['sources'][original];path=archived_source(root,original,digest)
    spec=importlib.util.spec_from_file_location('frozen_controls_'+digest,path)
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    return generator,path


def validate_rows(rows,kind,seed=None):
    ids=set()
    if not rows:raise ValueError('CONTROL_COMPONENT_EMPTY')
    for row in rows:
        if not isinstance(row.get('id'),str) or row['id'] in ids:raise ValueError('CONTROL_ROW_ID')
        ids.add(row['id']);key_for(row,kind)
        split=row.get('split')
        if split not in ('calibration','holdout') or row.get('noAuto') is not True:raise ValueError('CONTROL_ROW_FLAGS')
        if kind=='punctuation':
            if (row.get('task')!='punctuation' or row.get('cohort')!='punctuation'
                    or row.get('boundaries')!=[' ', ', ', ': ', '. ']
                    or type(row.get('expectedCandidate')) is not int
                    or row['expectedCandidate']!=row['boundaries'].index(row['expectedBoundary'])):
                raise ValueError('CONTROL_PUNCTUATION_LABEL')
            identity=hashlib.sha256(f"{seed}:punctuation:{row['language']}:{row['expectedBoundary']}:{row['prefix']}:{row['currentWord']}".encode()).hexdigest()
            if row.get('template')!=split+'-punctuation-'+identity or row.get('family')!='punctuation:'+identity:
                raise ValueError('CONTROL_PUNCTUATION_IDENTITY')
        elif (row.get('task')!='spelling' or row.get('cohort')!='protected'
                or type(row.get('expectedCandidate')) is not int or row.get('expectedCandidate')!=0 or not isinstance(row.get('candidates'),list)
                or not row['candidates'] or row['candidates'][0]!=' '+row['typed']):
            raise ValueError('CONTROL_PROTECTED_LABEL')


def read_components(root,name,directory,expected_manifest,filenames):
    """Use checked legacy files, or verified archives when the legacy set is absent."""
    root=Path(root); names=['manifest.json',*filenames]
    allowed={'manifest.json','protected-tokens.jsonl',*(f'punctuation-{lang}.jsonl' for lang in LANGUAGES)}
    if len(set(names))!=len(names) or not set(names)<=allowed:raise ValueError('CONTROL_COMPONENT_NAMES')
    paths={item:root/directory/item for item in names}
    present=any(p.exists() or p.is_symlink() for p in paths.values())
    if present:
        if any(p.is_symlink() or not p.is_file() for p in paths.values()):raise ValueError('CONTROL_PARTIAL_CORPUS')
        data={item:path.read_bytes() for item,path in paths.items()}
        local={str(path.relative_to(root)):hashlib.sha256(data[item]).hexdigest() for item,path in paths.items()}
        storage='historical-files'
    elif name in ('compact-v3','compact-v4'):
        base=root/'tools/typing_experiments/historical-qualification-v3-v4'
        checker=root/'tools/typing_experiments/check_historical_qualification_archives.py'
        if sha(checker)!=sha(Path(archives.__file__)):raise ValueError('CONTROL_ARCHIVE_CHECKER_DRIFT')
        label='v3' if name=='compact-v3' else 'v4'
        data=archives.load(base)[label]
        bound=[base/f'qualification-{label}.tar.bz2',base/'catalog.json',checker]
        local={str(path.relative_to(root)):sha(path) for path in bound}
        catalog=json.loads(bound[1].read_bytes())
        if local[str(bound[0].relative_to(root))]!=catalog['archives'][label]['archiveSha256']:
            raise ValueError('CONTROL_ARCHIVE_DRIFT')
        storage='verified-archive'
    else:raise ValueError('CONTROL_MISSING_CORPUS')
    if hashlib.sha256(data['manifest.json']).hexdigest()!=expected_manifest:raise ValueError('CONTROL_MANIFEST_IDENTITY')
    manifest=json.loads(data['manifest.json'])
    for filename in filenames:
        if hashlib.sha256(data[filename]).hexdigest()!=manifest['files'][filename]:raise ValueError('CONTROL_COMPONENT_IDENTITY')
    return manifest,{filename:data[filename] for filename in filenames},local,storage


def build(root,kind,base=None):
    root=Path(root)
    result=copy.deepcopy(validate(base)) if base is not None else dict(schema=SCHEMA,publicDataOnly=True,
        coverageComplete=False,pending=['Other historical controls and versioned preparation integration; lexical registry also required.'],entries=[])
    if any(entry['kind']==kind for entry in result['entries']):raise ValueError('CONTROL_ALREADY_IMPORTED')
    counts={};bindings={};storage={}
    for name,(directory,digest,_) in CORPORA.items():
        files=[f'punctuation-{lang}.jsonl' for lang in LANGUAGES] if kind=='punctuation' else ['protected-tokens.jsonl']
        manifest,components,local,storage[name]=read_components(root,name,directory,digest,files)
        if manifest['containsPersonalMessages'] is not False or manifest['frozenBeforeScoring'] is not True:
            raise ValueError('CONTROL_PUBLIC_PROVENANCE')
        generator,generator_path=load_original(root,manifest)
        lock_original=next(p for p in manifest['sources'] if p.endswith('/source-lock.json'))
        lock_path=archived_source(root,lock_original,manifest['sources'][lock_original]);lock=json.loads(lock_path.read_text())
        seed=3042026 if name=='qualification-v2' else lock['corpusSeed']
        component=[];local.update({str(generator_path.relative_to(root)):sha(generator_path),str(lock_path.relative_to(root)):sha(lock_path)})
        for filename in files:
            component.extend(json.loads(line) for line in components[filename].splitlines())
        validate_rows(component,kind,seed)
        for lang in LANGUAGES:
            rows=[r for r in component if r['language']==lang]
            if kind=='protected' and rows!=generator.protected_rows(lang):raise ValueError('CONTROL_PROTECTED_GENERATOR_PARITY')
            entry_id=name+'-'+kind+'-'+lang
            if any(e['id']==entry_id for e in result['entries']):raise ValueError('CONTROL_ALREADY_IMPORTED')
            result['entries'].append(dict(id=entry_id,kind=kind,language=lang,rowCount=len(rows),
                keys=sorted({key_for(r,kind) for r in rows}),bindings=local))
        counts[name]=dict(rows=len(component),languages=dict(Counter(r['language'] for r in component)))
        bindings.update(local)
    receipt=dict(purpose='PUBLIC_CONTROL_COMPONENT_EXCLUSIONS_NOT_QUALIFICATION',kind=kind,counts=counts,bindings=bindings,corpusStorage=storage,
        sourceBindings={p:sha(root/p) for p in ('tools/typing_experiments/control_ledger.py','tools/typing_experiments/import_control_components.py')},
        modelCalls=0,lexicalFamiliesChanged=False,lexicalLedgerChanged=False)
    return validate(result),receipt



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=('punctuation','protected'),required=True)
    parser.add_argument('--base',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    ledger,receipt=build(ROOT,args.kind,load(args.base) if args.base else None)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__=='__main__':main()
