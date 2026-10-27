"""Reproduce late authored transformations without claiming model execution."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

from audit_authored_training_history import exclusions,verify_payload
from holdout_ledger import load_ledger,validate_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='authored-right-context-late-history-'
BASE='tools/typing_experiments/'
SPECS={
 4:('033c8720708bcdd62aaf92900ee8ccd15477ac9a6234fb45d26b62c211df1853','right_context_role_corpus.py','6c98af64d142d216c4eaf4ee36e00ed418cb22d04863b2f596322cbfb36b82e5','014565007f55eb0e0063b0e1a51bafcd392c07cbb8dad76e4eebf9c9e363f2cb'),
 5:('b822b4e5d6f29dc6b9b9a86d65fa6fdec709caf2cf387c1c26880a2b8c153850','right_context_other_part_corpus.py','dfdf3e0f0275be62032f26e3714f21acd52685e3aa9cbded332b08094775da24','174499d4873263d8ae4b8b9d95b59df9302eb849841fac4d44af7e3ac4699f92'),
 7:('e504fefab24003c7650aff8118859bad10cba1d76bb36b86cf546e0d290bd78f','right_context_continuation_corpus.py','b63ee2e7ac879cde13cec65c957bd6edcbe0b2dab66de346778738d85a49a968','557b57f7362d04d7dd6c8fd0e4cdbebee210bf41705bd85eb7933d26bbb6d17b'),
}
DEPENDENCIES={
 'right_context_contrast_corpus':'3e0ccdc638a479889f2fe22f9bbcbde0a96729916ff890f97ad9a75b1a230b73',
 'grammar_contrast_corpus':'eeb289a4572eda11889a7180200d9b94894411bddd6ad97a92578b5bdb8f402f',
 'right_context_timeline_calibration':'599a6a01f45980eda4b31a960f9f25785dc0195a467b109c5f17872043b00678',
 'right_context_grammar_features':'5195bb9507623a8ebb796a8dded0da9f33c54242c7256f172ca861fa7369b363',
 'contextual_policy_calibration':'27a1c146a2e8ba36468baa2597eed2cb1e8f8e60d22fdacff13d2e4d7fa54f77',
 'right_context_continuation_features':'80c7799ecc81aa9894aac63117383a53a0595f76194b0fb6ad3edad52afb8ee8',
 'right_context_role_features':'181fff1a36ee769db22269d54de9a00efb58155520d5fa3d793ef217dfcdfadc',
 'right_context_revision_features':'3169a63758cca4aa0ddd2dc8274f46945e2db3cdb15254f7b0f0b802359cc4cd',
 'right_context_subject_evidence':'353d2f7b9451923045bd7c97cb8c905198c30683539914e82f603b70352e1a4d',
}
MISSING_FEATURE_SHA='2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0'


def directory(version):return f'build/right-context-training-v{version}-20261027'


def archive_path(archive,original,digest):
    archive=Path(archive);entry=json.loads((archive/'manifest.json').read_text())['sources'].get(digest)
    if not entry or entry['originalPath']!=original:raise ValueError('LATE_ARCHIVE_MISSING')
    path=archive/entry['file']
    if path.parent!=archive or sha(path)!=digest:raise ValueError('LATE_ARCHIVE_IDENTITY')
    return path


def load_generator(path):
    spec=importlib.util.spec_from_file_location('late_'+Path(path).stem,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_derivation(version,rows,manifest,parent_rows=None,parent_sha=None):
    if version in (5,6):
        if (manifest.get('oldCorpusSha256')!=parent_sha or manifest.get('oldRows')!=len(parent_rows)
                or rows[:len(parent_rows)]!=parent_rows or manifest.get('otherPartRows')!=len(rows)-len(parent_rows)):
            raise ValueError('LATE_PARENT_DERIVATION')
    elif version==7:
        parents={p['id']:p for p in parent_rows}
        if (manifest.get('parentCorpusSha256')!=parent_sha or manifest.get('parentRows')!=len(parent_rows)
                or any(r['parentTrainingId'] not in parents if 'parentTrainingId' in r else r!=parents.get(r['id']) for r in rows)):
            raise ValueError('LATE_PARENT_DERIVATION')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('LATE_DUPLICATE_ROWS')


def training_chain(root,version,manifest_path,rows):
    folder=Path(root)/directory(version);selection=folder/'selection.json';plan=folder/'plan.json';groups=folder/'groups.jsonl'
    s=json.loads(selection.read_text());p=json.loads(plan.read_text());digest=sha(groups)
    records=[json.loads(line) for line in groups.read_text().splitlines()];count=len(records);parents={r['id']:r for r in rows}
    if (s.get('corpusManifestSha256')!=sha(manifest_path) or s.get('groupsSha256')!=digest
            or p.get('groupsSha256')!=digest or s.get('groups')!=count or p.get('groups')!=count):
        raise ValueError('LATE_TRAINING_CHAIN')
    selected=[record.get('row') for record in records]
    if (any(not isinstance(row,dict) or row.get('id') not in parents or row!=parents[row['id']] for row in selected)
            or len({row['id'] for row in selected})!=count):raise ValueError('LATE_TRAINING_GROUP_ROW')
    return dict(groups=count,consistent=True,allGroupRowsMatchCorpus=True,modelExecutionEstablished=False),[selection,plan,groups]


def build(root,base,lexicon):
    root=Path(root);result=copy.deepcopy(validate_ledger(base));archive=root/(BASE+'frozen_sources')
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('LATE_ALREADY_IMPORTED')
    bindings={};counts={};unavailable=[];all_rows={};manifests={}
    # Verify live import dependencies before archived generator imports execute.
    for name,digest in DEPENDENCIES.items():
        path=BASE+name+'.py'
        if sha(root/path)!=digest or name in sys.modules and Path(sys.modules[name].__file__).resolve()!=(root/path).resolve():raise ValueError('LATE_DEPENDENCY_IDENTITY')
        bindings[path]=digest
    allowed=set(bindings)|{BASE+s[1] for s in SPECS.values()}|{directory(v)+'/prepare.py' for v in SPECS}|{BASE+'right_context_training_groups.py'}
    for version in (4,5,6,7):
        spec_version=5 if version==6 else version;corpus_sha,filename,generator_sha,prepare_sha=SPECS[spec_version]
        folder=directory(version);metadata=folder+'/corpus/manifest.json';path=folder+'/corpus/train.jsonl';manifest=json.loads((root/metadata).read_text())
        if sha(root/path)!=corpus_sha:raise ValueError('LATE_CORPUS_IDENTITY')
        for original,digest in manifest['sourceHashes'].items():
            if Path(original).is_absolute():
                candidate='/'.join(Path(original).parts[-3:])
                if candidate not in allowed:raise ValueError('LATE_SOURCE_PATH')
                original=candidate
            if original not in allowed:raise ValueError('LATE_SOURCE_PATH')
            if version==4 and original==BASE+'right_context_role_features.py' and digest==MISSING_FEATURE_SHA:
                unavailable.append(dict(version=version,path=original,sha256=digest,usedForPayloadGeneration=False));continue
            if sha(root/original)!=digest:raise ValueError('LATE_SOURCE_BINDING')
            bindings[original]=digest
        gen_path=archive_path(archive,BASE+filename,generator_sha)
        producer=archive_path(archive,directory(spec_version)+'/prepare.py',prepare_sha)
        bindings[str(gen_path.relative_to(root))]=generator_sha;bindings[str(producer.relative_to(root))]=prepare_sha
        if version==4:
            from right_context_contrast_corpus import PAIRS
            lexicon._load();paradigms={}
            for singular,_ in PAIRS:
                lemmas={a.lemma for a in lexicon.analyses(singular) if a.pos=='ADJS' and a.number=='sing' and a.gender=='masc'}
                paradigms[singular]=sorted({p.word for parsed in lexicon._analyzer.parse(singular) if parsed.normal_form in lemmas for p in parsed.lexeme})
            rows,skipped=load_generator(gen_path).generate(lexicon,paradigms)
        elif version==5:
            extra,skipped=load_generator(gen_path).generate(lexicon);rows=all_rows[4]+extra
        elif version==6:
            rows=copy.deepcopy(all_rows[5]);skipped=manifests[5]['skipped']
        else:
            rows=load_generator(gen_path).generate(all_rows[6],lexicon);skipped=None
        verify_payload(rows,manifest,corpus_sha)
        if skipped is not None and skipped!=manifest['skipped']:raise ValueError('LATE_SKIPPED_MISMATCH')
        if version!=4:verify_derivation(version,rows,manifest,all_rows[4 if version in (5,6) else 6],SPECS[4 if version in (5,6) else 5][0])
        all_rows[version]=rows;manifests[version]=manifest;bindings.update({metadata:sha(root/metadata),path:corpus_sha})
        chain,chain_paths=training_chain(root,version,root/metadata,rows);bindings.update({str(p.relative_to(root)):sha(p) for p in chain_paths})
        local=bindings|{BASE+'audit_late_authored_history.py':sha(root/(BASE+'audit_late_authored_history.py')),BASE+'audit_authored_training_history.py':sha(root/(BASE+'audit_authored_training_history.py')),'tools/morphology/ranker.py':sha(root/'tools/morphology/ranker.py')}
        entries,counts[str(version)]=exclusions('v'+str(version),rows,lexicon,dict(local))
        for entry in entries:entry['id']=entry['id'].replace('authored-right-context-template-history-',PREFIX)
        if version==6:
            for entry in entries:entry['notes']+=' Exact v5 corpus reuse, not independent data.'
        result['entries'].extend(entries);counts[str(version)]['trainingChain']=chain
    source_bindings={p:sha(root/p) for p in (BASE+'audit_late_authored_history.py',BASE+'audit_authored_training_history.py','tools/morphology/ranker.py')}
    receipt=dict(purpose='LATE_AUTHORED_EXCLUSION_HISTORY_NOT_QUALIFICATION',counts=counts,bindings=bindings,sourceBindings=source_bindings,dictionary=lexicon.receipt(),
        unavailableHistoricalSources=unavailable,fullHistoricalSourceCoverageComplete=not unavailable,modelCalls=0,
        corpusAliases={'v6':'v5'},exposureRows=sum(len(r) for r in all_rows.values()),uniqueRowIds=len({r['id'] for rows in all_rows.values() for r in rows}),
        archivedPreparationScriptsExecuted=False)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384));args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(counts=receipt['counts'],uniqueRowIds=receipt['uniqueRowIds'],missingSources=receipt['unavailableHistoricalSources'])))


if __name__=='__main__':main()
