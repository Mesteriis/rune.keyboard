"""Reproduce auxiliary authored corpora and verify combined/reused group inputs."""
import argparse
import copy
import json
from pathlib import Path
import sys

from audit_applied_authored_history import PARENT,verify_selection
from audit_authored_training_history import exclusions,verify_payload
from audit_late_authored_history import BASE,DEPENDENCIES,archive_path,load_generator
from holdout_ledger import load_ledger,validate_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='authored-right-context-auxiliary-history-'
# name, generator, generator hash, preparation hash, corpus hash, paradigm kind
SPECS=(
 ('instrumental-v1','right_context_instrumental_corpus.py','ae3087a5c5e6da22bcaac282885a5ab7a63a991aac5dfc9545fa40233f087794','d998fe824368a3b50c1493a73f5bd4497a4b595c738e0b3f631776da2734a6a2','00e8aefd8494d152fc6008c0f883a2888f35d580f8b4aa3bf7c551f27a3b318d','noun'),
 ('instrumental-v2','right_context_instrumental_corpus.py','d760e08e2fd222ab26f4b36debec0f9b845a89c1b4a60eef28a5d4647d99ab32','6c8302be34d57de689e6430f997a002c2cbbdd5dc1a55628778d699ac1fa3b2e','82ef4b3f0eb594c0031ddf2e349fb2bafdda245e3d369ae97b711a74dee81636','noun'),
 ('left-sequence-v1','right_context_left_sequence_corpus.py','99aeb5d9e2118e54aec84c3575d07a30866eba38354cf598204f762237c608ff','ec0a6349a5c99805e3274b01c631bd0aa7009000f37a914a958f79535cbfa14c','daed1a7b5e9d0d61c59bae3a63b052cc02feb8de059305fbf7bf2e699fcf94aa','adjective'),
 ('left-sequence-v1-v2','right_context_left_sequence_corpus.py','99aeb5d9e2118e54aec84c3575d07a30866eba38354cf598204f762237c608ff','ec0a6349a5c99805e3274b01c631bd0aa7009000f37a914a958f79535cbfa14c','daed1a7b5e9d0d61c59bae3a63b052cc02feb8de059305fbf7bf2e699fcf94aa','adjective'),
 ('oblique-v1','right_context_oblique_corpus.py','b8a011560a662b77322d7eba0e5ae1263e82b091b6eea758c159e8ab7c176077','9ce00a00fe49583bca8ed2218f3dae9158fcef88d234bdb31e223755309e7875','e5474d7282f793bfdfcb13e028e4b4b42d1941e3ac1105d862ae6a32bb5b0700','oblique'),
)
LIVE={name:DEPENDENCIES[name] for name in ('grammar_contrast_corpus','right_context_contrast_corpus')}
LIVE.update(right_context_applied_corpus='602890657811a39c17ce01e1557a01b6aa124bb0c1f6a1886131f6a79fa835d9',
    prepare_word_ranking='e213566e8f22f619a372f09c2c91866f93d8029d5db8666f783318285df74240',
    prepare_refinement='d2d84c3f328771fd0b9908a9216ee428eb2877079c8dacb481c42a0dafe11bab')
MISSING_FEATURE_SHA='82aeb37a82f7ac32aafd2f5f08eab36469ad2605b169943359db9a069726788e'
COMBINATIONS=(
 ('left-role-v11-inputs',('applied-v10-v2','left-sequence-v1-v2','instrumental-v2')),
 ('oblique-v12-inputs',('left-role-v11-inputs','oblique-v1')),
)
REUSES=(('applied-residual-v10','applied-v10-v2'),('left-role-residual-v11','left-role-v11-inputs'),('oblique-residual-v12','oblique-v12-inputs'),
        ('symmetric-residual-v13','oblique-v12-inputs'),('signature-residual-v14','oblique-v12-inputs'))


def folder(name):return 'build/right-context-'+name+'-20261027'


def read_groups(path):return [json.loads(line) for line in Path(path).read_text().splitlines()]


def verify_combination(root,name,parents):
    root=Path(root);directory=root/folder(name);selection=directory/'selection.json';groups=directory/'groups.jsonl';metadata=json.loads(selection.read_text())
    expected_bindings={folder(p)+'/selection.json':sha(root/folder(p)/'selection.json') for p in parents}
    actual=read_groups(groups);expected=[g for p in parents for g in read_groups(root/folder(p)/'groups.jsonl')]
    if (metadata.get('purpose')!='COMBINED_AUTHORED_NATIVE_GROUPS' or metadata.get('parentSelections')!=expected_bindings
            or metadata.get('groupsSha256')!=sha(groups) or metadata.get('groups')!=len(actual) or actual!=expected
            or len({g['row']['id'] for g in actual})!=len(actual)):
        raise ValueError('AUXILIARY_COMBINATION_LINEAGE')
    return dict(groups=len(actual),exactOrderedParentGroups=True),[selection,groups]


def verify_residual_reuse(root,name,parent):
    root=Path(root);directory=root/folder(name);groups=directory/'groups.jsonl';plan=directory/'plan.json';metadata=json.loads(plan.read_text())
    if (sha(groups)!=sha(root/folder(parent)/'groups.jsonl') or metadata.get('groupsSha256')!=sha(groups)
            or metadata.get('groups')!=len(groups.read_text().splitlines())):raise ValueError('AUXILIARY_RESIDUAL_REUSE')
    return dict(groups=metadata['groups'],exactParentGroupBytes=True,modelExecutionEstablished=False),[groups,plan]


def source_path(raw,expected_directory,allowed):
    if Path(raw).is_absolute():
        if tuple(Path(raw).parts[-3:])!=tuple(Path(expected_directory+'/prepare.py').parts):raise ValueError('AUXILIARY_SOURCE_PATH')
        raw=expected_directory+'/prepare.py'
    if raw not in allowed:raise ValueError('AUXILIARY_SOURCE_PATH')
    return raw


def build(root,base,lexicon):
    root=Path(root);result=copy.deepcopy(validate_ledger(base));archive=root/(BASE+'frozen_sources');bindings={};jobs=[];counts={};unavailable=[]
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('AUXILIARY_HISTORY_ALREADY_IMPORTED')
    parent=next(e for e in base['entries'] if e['id']=='authored-right-context-late-history-v7-contexts')
    parent_path=PARENT+'/corpus/train.jsonl'
    if parent['bindings'].get(parent_path)!=sha(root/parent_path):raise ValueError('AUXILIARY_PARENT_IDENTITY')
    bindings[parent_path]=sha(root/parent_path)
    for name,digest in LIVE.items():
        path=BASE+name+'.py'
        if sha(root/path)!=digest or name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(root/path).resolve():raise ValueError('AUXILIARY_DEPENDENCY_IDENTITY')
        bindings[path]=digest
    lexicon._load()
    for name,module,digest,producer_sha,corpus_sha,kind in SPECS:
        directory=folder(name);path=directory+'/corpus/train.jsonl';metadata_path=directory+'/corpus/manifest.json';metadata=json.loads((root/metadata_path).read_text())
        if sha(root/path)!=corpus_sha or metadata.get('oldRowsIncluded')!=0 or metadata.get('oldCorpusSha256')!=bindings[parent_path]:raise ValueError('AUXILIARY_CORPUS_IDENTITY')
        producer_directory=folder('left-sequence-v1') if name=='left-sequence-v1-v2' else directory
        generator_path=archive_path(archive,BASE+module,digest);producer=archive_path(archive,producer_directory+'/prepare.py',producer_sha)
        generator=load_generator(generator_path);paradigms={}
        words=[p[1] for p in generator.PAIRS] if kind=='noun' else list(generator.PREDICATES) if kind=='oblique' else [p[0] for p in generator.PAIRS]
        for word in words:
            if kind=='noun':lemmas={a.lemma for a in lexicon.analyses(word) if a.pos=='NOUN' and a.case=='nomn'}
            else:lemmas={a.lemma for a in lexicon.analyses(word) if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc'}
            paradigms[word]=sorted({p.word for parsed in lexicon._analyzer.parse(word) if parsed.normal_form in lemmas for p in parsed.lexeme})
        rows,skipped=generator.generate(lexicon,paradigms);verify_payload(rows,metadata,corpus_sha)
        if skipped!=metadata['skipped']:raise ValueError('AUXILIARY_SKIPPED_MISMATCH')
        allowed={BASE+m+'.py' for m in LIVE}|{BASE+module,BASE+'right_context_left_sequence_features.py',BASE+'right_context_applied_features.py',BASE+'right_context_training_groups.py',directory+'/prepare.py'}
        if metadata['sourceHashes'].get(BASE+module)!=digest:raise ValueError('AUXILIARY_GENERATOR_BINDING')
        for raw,expected in metadata['sourceHashes'].items():
            source=source_path(raw,directory,allowed)
            if source==BASE+module:continue
            if name=='left-sequence-v1' and source==BASE+'right_context_left_sequence_features.py' and expected==MISSING_FEATURE_SHA:
                unavailable.append(dict(corpus=name,path=source,sha256=expected,usedForPayloadGeneration=False));continue
            if sha(root/source)!=expected:raise ValueError('AUXILIARY_SOURCE_BINDING')
            if source.endswith('/prepare.py') and expected!=producer_sha:raise ValueError('AUXILIARY_PRODUCER_IDENTITY')
            bindings[source]=expected
        bindings.update({path:corpus_sha,metadata_path:sha(root/metadata_path),str(generator_path.relative_to(root)):digest,str(producer.relative_to(root)):producer_sha})
        selection,paths=verify_selection(root/directory,root/metadata_path,rows);bindings.update({str(p.relative_to(root)):sha(p) for p in paths})
        jobs.append((name,rows));counts[name]=dict(rows=len(rows),selection=selection)
    # The applied parent is already public and bound by the previous import.
    applied=next(e for e in base['entries'] if e['id']=='authored-right-context-applied-history-v2-contexts')
    for suffix in ('selection.json','groups.jsonl'):
        path=folder('applied-v10-v2')+'/'+suffix
        if applied['bindings'].get(path)!=sha(root/path):raise ValueError('AUXILIARY_APPLIED_PARENT')
        bindings[path]=sha(root/path)
    combinations={};reuses={}
    for name,parents in COMBINATIONS:
        combinations[name],paths=verify_combination(root,name,parents);bindings.update({str(p.relative_to(root)):sha(p) for p in paths})
    for name,parent_name in REUSES:
        reuses[name],paths=verify_residual_reuse(root,name,parent_name);bindings.update({str(p.relative_to(root)):sha(p) for p in paths})
    source_bindings={p:sha(root/p) for p in (BASE+'audit_auxiliary_authored_history.py',BASE+'audit_applied_authored_history.py',BASE+'audit_authored_training_history.py',BASE+'audit_late_authored_history.py','tools/morphology/ranker.py')}
    for name,rows in jobs:
        entries,facts=exclusions(name,rows,lexicon,bindings|source_bindings);counts[name].update(facts)
        for entry in entries:entry['id']=entry['id'].replace('authored-right-context-template-history-',PREFIX)
        result['entries'].extend(entries)
    receipt=dict(purpose='AUXILIARY_AUTHORED_CORPUS_AND_COMBINED_GROUP_LINEAGE_NOT_QUALIFICATION',counts=counts,bindings=bindings,sourceBindings=source_bindings,
        combinations=combinations,residualReuses=reuses,dictionary=lexicon.receipt(),modelCalls=0,archivedPreparationScriptsExecuted=False,
        unavailableHistoricalSources=unavailable,fullHistoricalSourceCoverageComplete=not unavailable,
        corpusAliases={'left-sequence-v1-v2':'left-sequence-v1'},exposureRows=sum(len(r) for _,r in jobs),uniqueRowIds=len({r['id'] for _,rows in jobs for r in rows}))
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384));args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(counts=receipt['counts'],combinations=receipt['combinations'],reuses=receipt['residualReuses'],unavailable=receipt['unavailableHistoricalSources'])))


if __name__=='__main__':main()
