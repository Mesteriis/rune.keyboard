"""Prepare private, label-free current-product replay of disclosed EWT tokens.

Only aggregate results should be shared. Source labels are not adjudicated and
this data cannot qualify a new model. No model is run by the replay itself.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/typing_experiments'))
import english_ewt_error_model as model
import import_english_ewt_exposure as ewt
import register_ewt_error_targets as targets
import holdout_ledger as lexical
import register_ewt_control_source as controls

PREFIX=re.compile(r'[A-Za-z]+(?: [A-Za-z]+)+\Z')
PARTS=('train','dev','test')


def extract(data,vocab,prior):
    """Conservatively align whole CoNLL-U sentences; return private rows/labels."""
    rows=[];labels=[];stats=Counter()
    for name in sorted(data):
        part=name.removeprefix('en_ewt-ud-').removesuffix('.conllu')
        if part not in PARTS:raise ValueError('EWT_REPLAY_PARTITION')
        for block in data[name].decode('utf-8').strip().split('\n\n'):
            lines=block.splitlines();texts=[x.removeprefix('# text = ') for x in lines if x.startswith('# text = ')]
            if len(texts)!=1:raise ValueError('EWT_REPLAY_TEXT')
            fields=[x.split('\t') for x in lines if x and not x.startswith('#')]
            if any(len(x)!=10 for x in fields):raise ValueError('EWT_REPLAY_ROW')
            if any(not x[0].isdigit() for x in fields):stats['nonIntegerSentenceExcluded']+=1;continue
            positions=[];reconstructed=''
            for i,f in enumerate(fields):
                positions.append(len(reconstructed));reconstructed+=f[1]
                if i+1<len(fields) and 'SpaceAfter=No' not in f[9].split('|'):reconstructed+=' '
            if reconstructed!=texts[0]:stats['unalignedSentenceExcluded']+=1;continue
            for f,pos in zip(fields,positions,strict=True):
                typed=f[1];lower=typed.casefold();before=texts[0][:pos]
                if not model.WORD.fullmatch(lower) or not before.endswith(' '):continue
                prefix=before.rstrip(' ')
                if len(prefix)>128 or not PREFIX.fullmatch(prefix):continue
                values=[x.removeprefix('CorrectForm=') for x in f[9].split('|') if x.startswith('CorrectForm=')]
                if len(values)>1:raise ValueError('EWT_REPLAY_LABEL')
                if values:
                    target=values[0].casefold()
                    if typed!=lower or not model.WORD.fullmatch(target) or model.one_edit(target,lower) is None:continue
                    kind='annotated'
                elif part=='test' and lower not in vocab and lower not in prior:
                    target=typed;kind='unannotated-unknown'
                else:continue
                identity=f'ewt-replay-{len(rows):06d}'
                rows.append(dict(id=identity,split={'train':'train','dev':'calibration','test':'holdout'}[part],
                                 language='en',prefix=prefix,typed=typed))
                labels.append(dict(id=identity,kind=kind,expected=target,part=part))
                stats[part+':'+kind]+=1
    if not rows:raise ValueError('EWT_REPLAY_EMPTY')
    return rows,labels,dict(sorted(stats.items()))


def prepare(source,output):
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_REPLAY_OUTPUT')
    lock=ewt.LOCK.read_bytes();vocab=model.VOCAB.read_bytes();ledger=targets.LEDGER.read_bytes();control=controls.CONTROL.read_bytes()
    if model.sha(lock)!=model.LOCK_SHA or model.sha(vocab)!=model.VOCAB_SHA:raise ValueError('EWT_REPLAY_SOURCE')
    stored=json.loads(ledger);expected=targets.entry(stored,targets.FIXTURE.read_bytes())
    if [x for x in lexical.validate_ledger(stored)['entries'] if x['id']==targets.ENTRY]!=[expected] or controls.check()!=1174:
        raise ValueError('EWT_REPLAY_EXCLUSIONS')
    hashes=json.loads(lock)['files'];data={n:(source/n).read_bytes() for n in hashes}
    groups,_=model.annotations(data,hashes)
    prior={word for part in ('train','dev') for typed,target,_ in groups[part] for word in (typed,target)}
    rows,labels,counts=extract(data,model.parse_vocab(vocab),prior)
    if (ewt.LOCK.read_bytes()!=lock or model.VOCAB.read_bytes()!=vocab or targets.LEDGER.read_bytes()!=ledger or
        controls.CONTROL.read_bytes()!=control or any(model.sha((source/n).read_bytes())!=h for n,h in hashes.items())):
        raise ValueError('EWT_REPLAY_INPUT_DRIFT')
    output.mkdir(mode=0o700)
    for name,values in (('inputs.jsonl',rows),('labels.jsonl',labels)):
        with (output/name).open('x',encoding='utf-8') as f:
            for value in values:f.write(json.dumps(value,ensure_ascii=False,sort_keys=True)+'\n')
    manifest=dict(schemaVersion=1,scope='disclosed-ewt-replay-not-qualification',rows=len(rows),counts=counts,
        sourceLockSha256=model.sha(lock),lexicalLedgerSha256=model.sha(ledger),controlLedgerSha256=model.sha(control),
        inputSha256=model.sha((output/'inputs.jsonl').read_bytes()),labelSha256=model.sha((output/'labels.jsonl').read_bytes()),
        analyzerSha256=model.sha(Path(__file__).read_bytes()),independentQualification=False)
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'counts':counts},sort_keys=True))


def summarize(data,replay):
    paths=[data/'inputs.jsonl',data/'labels.jsonl',data/'manifest.json',replay/'receipt.json',replay/'projection.jsonl']
    before={p:model.sha(p.read_bytes()) for p in paths}
    inputs=[json.loads(x) for x in paths[0].read_bytes().splitlines()];labels=[json.loads(x) for x in paths[1].read_bytes().splitlines()]
    meta=json.loads(paths[2].read_bytes());receipt=json.loads(paths[3].read_bytes());observed=[json.loads(x) for x in paths[4].read_bytes().splitlines()]
    if (meta.get('scope')!='disclosed-ewt-replay-not-qualification' or meta.get('independentQualification') is not False or
        meta.get('inputSha256')!=before[paths[0]] or meta.get('labelSha256')!=before[paths[1]] or
        meta.get('analyzerSha256')!=model.sha(Path(__file__).read_bytes()) or
        receipt.get('status')!='COMPLETE' or receipt.get('deterministic') is not True or receipt.get('modelCalls')!=0 or
        receipt.get('files',{}).get(str(paths[0].resolve().relative_to(ROOT)))!=before[paths[0]] or
        receipt.get('inputFieldsSent')!=['id','split','language','prefix','typed'] or
        receipt.get('projectionSha256')!=before[paths[4]] or len(inputs)!=len(labels) or len(inputs)!=len(observed) or
        receipt.get('rows')!=len(inputs)):
        raise ValueError('EWT_REPLAY_BINDING')
    stats={};
    for i,(row,label,obs) in enumerate(zip(inputs,labels,observed,strict=True)):
        if (label.get('id')!=row.get('id') or label.get('part') not in PARTS or
            row['split']!={'train':'train','dev':'calibration','test':'holdout'}[label['part']] or
            any(obs.get(k)!=row[k] for k in ('split','language','prefix','typed'))):
            raise ValueError('EWT_REPLAY_ALIGNMENT')
        if label.get('kind') not in ('annotated','unannotated-unknown') or not isinstance(label.get('expected'),str):
            raise ValueError('EWT_REPLAY_LABEL')
        kind=label['part']+':'+label['kind'];c=stats.setdefault(kind,Counter());c['rows']+=1
        expected=label['expected'];typed=row['typed'];prior=row['prefix']+' '+typed
        if obs['beforeBoundary']['text']!=prior:raise ValueError('EWT_REPLAY_EDITOR_ALIGNMENT')
        after=obs['afterBoundary']['text']; c['originalPreserved']+=after==prior+' '
        c['targetApplied']+=after==row['prefix']+' '+expected+' ' and expected!=typed
        c['otherBoundary']+=after not in (prior+' ',row['prefix']+' '+expected+' ')
        c['undoExact']+=obs['afterBackspace']['text']==prior
        gen=obs.get('fullTokenGeneration')
        if not isinstance(gen,dict) or not isinstance(gen.get('alternatives'),list):raise ValueError('EWT_REPLAY_GENERATION')
        c['completion:'+str(gen.get('completion'))]+=1
        c['targetInAlternatives']+=any(v.get('text','').casefold()==expected.casefold() and v.get('language')=='en' for v in gen['alternatives'])
        c['autoAllowed']+=obs.get('automaticAdmissionAllowed') is True
    if any(model.sha(p.read_bytes())!=digest for p,digest in before.items()):raise ValueError('EWT_REPLAY_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-current-product-diagnostic-not-qualification',
        rows=len(inputs),counts={k:dict(sorted(v.items())) for k,v in sorted(stats.items())},
        preparationManifestSha256=before[paths[2]],replayReceiptSha256=before[paths[3]],projectionSha256=before[paths[4]],
        analyzerSha256=model.sha(Path(__file__).read_bytes()),sourceLabelsQualified=False,
        independentQualification=False,modelCalls=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--source-directory',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    b=sub.add_parser('summarize');b.add_argument('--data',type=Path,required=True);b.add_argument('--replay',type=Path,required=True);b.add_argument('--output',type=Path,required=True)
    args=p.parse_args();os.umask(0o077)
    if args.command=='prepare':return prepare(args.source_directory,args.output)
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_REPLAY_OUTPUT')
    result=summarize(args.data,args.replay)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result['counts'],sort_keys=True))


if __name__=='__main__':main()
