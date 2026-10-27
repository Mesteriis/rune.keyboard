"""Verify applied-word template preparation and prior group reuse, without fitting."""
import argparse
import copy
import json
from pathlib import Path
import sys

from audit_authored_training_history import exclusions,verify_payload
from audit_late_authored_history import BASE,DEPENDENCIES,archive_path,load_generator
from holdout_ledger import load_ledger,validate_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='authored-right-context-applied-history-'
PARENT='build/right-context-training-v7-20261027'
PRODUCER='build/right-context-applied-v10-20261027/prepare.py'
PRODUCER_SHA='cf6502fd69c52de3ab4b0a2b25bcd45f5053857c4a1978e30f23d54d5744ec6c'
GENERATOR=BASE+'right_context_applied_corpus.py'
SPECS=(
 ('v1','build/right-context-applied-v10-20261027','7e9b8780a969645aa97309f3096a594fc509e24cd32da82fd153c4cda3363d7c','31ecbd6855cad818fae652f75828422a64036d1afbad2a326b7b916352152370'),
 ('v2','build/right-context-applied-v10-v2-20261027','602890657811a39c17ce01e1557a01b6aa124bb0c1f6a1886131f6a79fa835d9','fdfb4d2858580562f1bb13c77335661f0bd044e48fccbf4145f23896b02d35fa'),
)


def verify_selection(folder,manifest_path,rows):
    folder=Path(folder);selection=folder/'selection.json';groups=folder/'groups.jsonl';s=json.loads(selection.read_text())
    records=[json.loads(line) for line in groups.read_text().splitlines()];expected={r['id']:r for r in rows}
    if (s.get('corpusManifestSha256')!=sha(manifest_path) or s.get('groupsSha256')!=sha(groups) or s.get('groups')!=len(records)):
        raise ValueError('APPLIED_SELECTION_BINDING')
    selected=[g.get('row') for g in records]
    if (any(not isinstance(r,dict) or r.get('id') not in expected or r!=expected[r['id']] for r in selected)
            or len({r['id'] for r in selected})!=len(selected)):raise ValueError('APPLIED_SELECTED_ROW')
    return dict(groups=len(records),allGroupRowsMatchCorpus=True,modelExecutionEstablished=False),[selection,groups]


def verify_reuse(folder,parent_folder,rows):
    folder=Path(folder);parent_folder=Path(parent_folder)
    if sha(folder/'groups.jsonl')!=sha(parent_folder/'groups.jsonl'):raise ValueError('APPLIED_GROUP_REUSE')
    facts,paths=verify_selection(folder,parent_folder/'corpus/manifest.json',rows)
    plan=folder/'plan.json';metadata=json.loads(plan.read_text())
    if metadata.get('groupsSha256')!=sha(folder/'groups.jsonl') or metadata.get('groups')!=facts['groups']:raise ValueError('APPLIED_REUSE_PLAN')
    return facts|dict(exactParentGroupBytes=True),paths+[plan]


def verify_parent(rows,manifest,parent,parent_sha):
    if (manifest.get('oldCorpusSha256')!=parent_sha or manifest.get('oldRows')!=len(parent)
            or rows[:len(parent)]!=parent or manifest.get('appliedRoleRows')!=len(rows)-len(parent)):
        raise ValueError('APPLIED_PARENT_DERIVATION')


def build(root,base,lexicon):
    root=Path(root);result=copy.deepcopy(validate_ledger(base));archive=root/(BASE+'frozen_sources')
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('APPLIED_HISTORY_ALREADY_IMPORTED')
    parent=next(e for e in base['entries'] if e['id']=='authored-right-context-late-history-v7-contexts');bindings={}
    for path in (PARENT+'/corpus/manifest.json',PARENT+'/corpus/train.jsonl',PARENT+'/groups.jsonl'):
        if parent['bindings'].get(path)!=sha(root/path):raise ValueError('APPLIED_PARENT_BINDING')
        bindings[path]=sha(root/path)
    old=[json.loads(line) for line in (root/PARENT/'corpus/train.jsonl').read_text().splitlines()];parent_sha=bindings[PARENT+'/corpus/train.jsonl']
    # These modules are the only live imports made by the archived generators.
    for name in ('grammar_contrast_corpus','right_context_contrast_corpus'):
        path=BASE+name+'.py'
        if sha(root/path)!=DEPENDENCIES[name]:raise ValueError('APPLIED_DEPENDENCY_IDENTITY')
        if name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(root/path).resolve():raise ValueError('APPLIED_DEPENDENCY_MODULE')
        bindings[path]=sha(root/path)
    from right_context_contrast_corpus import PAIRS
    lexicon._load();paradigms={}
    for singular,_ in PAIRS:
        lemmas={a.lemma for a in lexicon.analyses(singular) if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc'}
        paradigms[singular]=sorted({p.word for parsed in lexicon._analyzer.parse(singular) if parsed.normal_form in lemmas for p in parsed.lexeme})
    aliases={}
    for name in ('right-context-training-v8-20261027','right-context-residual-v9-20261027'):
        aliases[name],paths=verify_reuse(root/'build'/name,root/PARENT,old)
        bindings.update({str(p.relative_to(root)):sha(p) for p in paths})
    counts={};producer=archive_path(archive,PRODUCER,PRODUCER_SHA);bindings[str(producer.relative_to(root))]=PRODUCER_SHA
    source_bindings={p:sha(root/p) for p in (BASE+'audit_applied_authored_history.py',BASE+'audit_authored_training_history.py',BASE+'audit_late_authored_history.py','tools/morphology/ranker.py')}
    for name,directory,generator_sha,corpus_sha in SPECS:
        path=directory+'/corpus/train.jsonl';metadata=directory+'/corpus/manifest.json';manifest=json.loads((root/metadata).read_text())
        if sha(root/path)!=corpus_sha or manifest['sourceHashes'].get(GENERATOR)!=generator_sha:raise ValueError('APPLIED_CORPUS_IDENTITY')
        generator=archive_path(archive,GENERATOR,generator_sha);extra,skipped=load_generator(generator).generate(lexicon,paradigms);rows=old+extra
        verify_payload(rows,manifest,corpus_sha);verify_parent(rows,manifest,old,parent_sha)
        if skipped!=manifest['skipped']:raise ValueError('APPLIED_SKIPPED_MISMATCH')
        for source,digest in manifest['sourceHashes'].items():
            if source==GENERATOR:
                if digest!=generator_sha:raise ValueError('APPLIED_GENERATOR_BINDING')
                continue
            if Path(source).is_absolute():
                if tuple(Path(source).parts[-3:])!=tuple(Path(directory+'/prepare.py').parts):raise ValueError('APPLIED_SOURCE_PATH')
                source=directory+'/prepare.py'
            allowed={directory+'/prepare.py',BASE+'right_context_applied_features.py',BASE+'grammar_contrast_corpus.py',BASE+'right_context_training_groups.py'}
            if source not in allowed or sha(root/source)!=digest:raise ValueError('APPLIED_SOURCE_BINDING')
            if source.endswith('/prepare.py') and digest!=PRODUCER_SHA:raise ValueError('APPLIED_PRODUCER_IDENTITY')
            bindings[source]=digest
        local=bindings|source_bindings|{path:corpus_sha,metadata:sha(root/metadata),str(generator.relative_to(root)):generator_sha}
        chain,paths=verify_selection(root/directory,root/metadata,rows);local.update({str(p.relative_to(root)):sha(p) for p in paths})
        entries,counts[name]=exclusions(name,rows,lexicon,dict(local));counts[name].update(selection=chain,addedRows=len(extra))
        for entry in entries:entry['id']=entry['id'].replace('authored-right-context-template-history-',PREFIX)
        result['entries'].extend(entries);bindings.update(local)
    receipt=dict(purpose='APPLIED_TEMPLATE_PREPARATION_AND_GROUP_REUSE_NOT_QUALIFICATION',counts=counts,aliases=aliases,
        bindings=bindings,sourceBindings=source_bindings,dictionary=lexicon.receipt(),modelCalls=0,archivedPreparationScriptsExecuted=False,
        versionsAreIndependentSamples=False)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384));args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(counts=receipt['counts'],aliases=receipt['aliases'])))


if __name__=='__main__':main()
