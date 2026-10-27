"""Reproduce template-authored training; leave unproven example origin explicit."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='authored-right-context-template-history-'
GENERATOR='tools/typing_experiments/right_context_contrast_corpus.py'
SELECTOR='tools/typing_experiments/grammar_contrast_corpus.py'
SELECTOR_SHA='eeb289a4572eda11889a7180200d9b94894411bddd6ad97a92578b5bdb8f402f'
SPECS=(
 ('v1','build/right-context-evidence-20261027/corpus','d6cd17951bd19e11115f515c09eb4eed9442644132f870a43450137eb65a5456','361495f8260486f4feb56f6e8c256801828bd2039cc047647a4cacac0e1f9b55',{}),
 ('v2','build/right-context-training-v2-20261027/corpus','d2c269bbfaa1aa145f89bd3e4515171f09b4c17e29644dab47435d5c15d3810a','580581dca64b0cc08976b6318d69c175d9699fa97684fa35e142cfb207c8d059',{'copula_coverage':True}),
 ('v3','build/right-context-training-v3-20261027/corpus','3e0ccdc638a479889f2fe22f9bbcbde0a96729916ff890f97ad9a75b1a230b73','a7922139ecc2d610be4b63ba6964449f9783452775d5c0bee4a9758bc1a58af7',{'copula_coverage':True,'original_acquisition':True}),
)


def archived_generator(directory,digest):
    directory=Path(directory);entry=json.loads((directory/'manifest.json').read_text())['sources'].get(digest)
    if not entry or entry['originalPath']!=GENERATOR:raise ValueError('AUTHORED_GENERATOR_NOT_ARCHIVED')
    path=directory/entry['file']
    if path.parent!=directory or sha(path)!=digest:raise ValueError('AUTHORED_GENERATOR_IDENTITY')
    spec=importlib.util.spec_from_file_location('authored_'+digest,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module,path


def verify_payload(rows,manifest,digest):
    payload=''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode()
    if hashlib.sha256(payload).hexdigest()!=digest or manifest.get('corpusSha256')!=digest or len(rows)!=manifest.get('rows'):
        raise ValueError('AUTHORED_REPRODUCTION_MISMATCH')
    return payload


def exclusions(name,rows,lexicon,bindings):
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('AUTHORED_ROW_IDS')
    families=set();contexts=[]
    for row in rows:
        if row.get('purpose')!='AUTHORED_RIGHT_CONTEXT_TRAINING_ONLY' or row.get('split')!='train' or row.get('language')!='ru':raise ValueError('AUTHORED_ROW_SCOPE')
        forms=row['candidateForms'];analyses=[a for form in forms for a in lexicon.analyses(form)]
        if len(forms)!=2 or any(not lexicon.analyses(form) for form in forms) or row['family'] not in {a.lemma for a in analyses}:
            raise ValueError('AUTHORED_DICTIONARY_FAMILY')
        families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
        # Conservative left-context projection also blocks reuse with another suffix.
        for target in set(forms)|{row['applied'],row['expectedApplied']}:
            contexts.append(dict(prefix=row['leftContext'],typed=row['original'],expectedSpelling=target))
    keys=sorted(keys_for(contexts,'context'))
    entries=[dict(id=PREFIX+name+'-families',usage='prepared-training-quarantine',bindings=bindings,keys={'family':sorted(families)},missingAxes=[],
        notes='Reproduced prepared authored candidate forms; all dictionary-only analyses. Conservative exclusion does not certify model consumption. Unknown corruptions are not guessed lemmas.'),
        dict(id=PREFIX+name+'-contexts',usage='historical-context-exclusion',bindings=bindings,keys={'context':keys},missingAxes=[],
        notes='Reproduced authored training templates. Conservative left-context/target projection ignores right suffix; never fresh qualification.')]
    return entries,dict(rows=len(rows),dictionaryFamilies=len(families),contexts=len(keys))


def unproven_examples(directory):
    directory=Path(directory);manifest=json.loads((directory/'authored-manifest.json').read_text());path=directory/'authored.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    # Compare locally, never return the text, private corpus hash or row identities.
    return dict(declaredRows=manifest.get('rows'),observedRows=len(rows),
        manifestMatchesObservedRows=manifest.get('rows')==len(rows) and manifest.get('sha256')==sha(path),
        generatorBindingPresent=any(k in manifest for k in ('generatorSha256','sources','sourceRepository')),
        provenanceStatus='UNPROVEN_ORIGIN',imported=False,privateFingerprintsStored=False)


def training_chain(directory,corpus_sha):
    directory=Path(directory);selection_path=directory/'selection.json';plan_path=directory/'plan.json';groups_path=directory/'groups.jsonl'
    selection=json.loads(selection_path.read_text());plan=json.loads(plan_path.read_text());digest=sha(groups_path)
    count=sum(1 for line in groups_path.read_text().splitlines() if line)
    if (selection.get('corpusSha256')!=corpus_sha or selection.get('groupsSha256')!=digest
            or plan.get('groupsSha256')!=digest or selection.get('acceptedGroups')!=count or plan.get('groups')!=count):
        raise ValueError('AUTHORED_TRAINING_CHAIN')
    return dict(groups=count,consistent=True,modelExecutionEstablished=False),[selection_path,plan_path,groups_path]


def build(root,base,lexicon):
    root=Path(root);result=copy.deepcopy(validate_ledger(base));archive=root/'tools/typing_experiments/frozen_sources'
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('AUTHORED_HISTORY_ALREADY_IMPORTED')
    if sha(root/SELECTOR)!=SELECTOR_SHA:raise ValueError('AUTHORED_SELECTOR_IDENTITY')
    # Selector is imported by the verified archives; check it before execution.
    if SELECTOR.removesuffix('.py').split('/')[-1] in sys.modules:
        module=sys.modules['grammar_contrast_corpus']
        if Path(module.__file__).resolve()!=(root/SELECTOR).resolve():raise ValueError('AUTHORED_SELECTOR_MODULE')
    counts={};bindings={};source_bindings={p:sha(root/p) for p in ('tools/typing_experiments/audit_authored_training_history.py','tools/morphology/ranker.py')}
    for name,directory,generator_sha,corpus_sha,options in SPECS:
        path=directory+'/train.jsonl';metadata=directory+'/manifest.json';manifest=json.loads((root/metadata).read_text())
        if sha(root/path)!=corpus_sha or manifest.get('generatorSha256')!=generator_sha or manifest.get('corruptionSelectorSha256')!=SELECTOR_SHA:
            raise ValueError('AUTHORED_HISTORICAL_BINDING')
        generator,archived=archived_generator(archive,generator_sha);rows,skipped=generator.generate(lexicon,**options)
        verify_payload(rows,manifest,corpus_sha)
        if skipped!=manifest['skipped']:raise ValueError('AUTHORED_SKIPPED_MISMATCH')
        training=root/('build/right-context-training-20261027' if name=='v1' else 'build/right-context-training-'+name+'-20261027')
        chain,chain_paths=training_chain(training,corpus_sha)
        local={path:corpus_sha,metadata:sha(root/metadata),str(archived.relative_to(root)):generator_sha,SELECTOR:SELECTOR_SHA}|source_bindings
        local.update({str(p.relative_to(root)):sha(p) for p in chain_paths})
        entries,counts[name]=exclusions(name,rows,lexicon,local);counts[name]['trainingChain']=chain
        result['entries'].extend(entries);bindings.update(local)
    receipt=dict(purpose='REPRODUCED_AUTHORED_TRAINING_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,bindings=bindings,
        dictionary=lexicon.receipt(),modelCalls=0,allThreePayloadsReproduced=True,
        unprovenExamples=unproven_examples(root/'build/context-feature-ranker-20261026'))
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384))
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(counts=receipt['counts'],unprovenExamples=receipt['unprovenExamples'])))


if __name__=='__main__':main()
