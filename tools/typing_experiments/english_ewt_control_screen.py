"""Screen an offline edit-channel prototype on uncorrected EWT test tokens.

Output contains aggregates only. This is not product behavior, a validated
false-change rate, or an independent evaluation dataset.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import english_ewt_error_model as model
import import_english_ewt_exposure as ewt
import holdout_ledger as lexical
import register_ewt_error_targets as targets

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import register_ewt_control_source as source_control
RECEIPT=ROOT/'tools/typing_experiments/english-ewt-error-model-v1.json'
RECEIPT_SHA='42dbf472f8a9109413b8cf8ba3a21459436ffcfa8739bf7accc2f17d611482c7'
MARGINS=(0.5,1.0,2.0,3.0)


def test_controls(data):
    """Return raw words in memory only; missing CorrectForm is not a gold label."""
    rows=[];counts=Counter()
    for line in data.decode('utf-8').splitlines():
        if not line or line.startswith('#'):continue
        fields=line.split('\t')
        if len(fields)!=10:raise ValueError('EWT_CONTROL_ROW')
        if not fields[0].isdigit():continue
        if any(item.startswith('CorrectForm=') for item in fields[9].split('|')):
            counts['annotatedCorrectionExcluded']+=1;continue
        typed=fields[1].casefold()
        if not model.WORD.fullmatch(typed):
            counts['unsupportedShapeExcluded']+=1;continue
        counts['asciiRows']+=1
        if fields[3] not in ('ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART',
                             'PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X'):
            raise ValueError('EWT_CONTROL_POS')
        rows.append((typed,fields[3]))
    return rows,counts


def screen(rows,vocab,train,excluded,weight):
    if not train or not math.isfinite(weight):raise ValueError('EWT_CONTROL_MODEL')
    counts=Counter();by_pos={};distinct=set()
    for typed,pos in rows:
        if not model.WORD.fullmatch(typed):raise ValueError('EWT_CONTROL_TOKEN')
        counts['inputRows']+=1
        if typed in vocab:counts['vocabularyOriginalProtected']+=1;continue
        if typed in excluded:counts['priorAnnotatedWordExcluded']+=1;continue
        counts['unseenUnknownRows']+=1;distinct.add(typed)
        pos_count=by_pos.setdefault(pos,Counter());pos_count['rows']+=1
        pool=model.candidates(typed,vocab)
        if not pool:counts['noCandidate']+=1;pos_count['noCandidate']+=1;continue
        scores=sorted((math.log(train[event]+1)+weight*math.log(vocab[word]),word)
                      for word,event in pool.items())
        counts['candidateAvailable']+=1;pos_count['candidateAvailable']+=1
        if len(scores)==1:
            counts['singleCandidate']+=1;pos_count['singleCandidate']+=1
            for cutoff in MARGINS:counts['marginAtLeast:'+str(cutoff)]+=1
        else:
            counts['multipleCandidates']+=1;pos_count['multipleCandidates']+=1
            gap=scores[-1][0]-scores[-2][0]
            for cutoff in MARGINS:counts['marginAtLeast:'+str(cutoff)]+=gap>=cutoff
    counts['distinctUnknownForms']=len(distinct)
    return dict(counts=dict(sorted(counts.items())),byPos={p:dict(sorted(v.items())) for p,v in sorted(by_pos.items())})


def run(source):
    frozen=RECEIPT.read_bytes()
    if model.sha(frozen)!=RECEIPT_SHA:raise ValueError('EWT_CONTROL_RECEIPT_DRIFT')
    raw_ledger=targets.LEDGER.read_bytes();raw_control=source_control.CONTROL.read_bytes();stored=json.loads(raw_ledger)
    expected=targets.entry(stored,targets.FIXTURE.read_bytes())
    if [e for e in lexical.validate_ledger(stored)['entries'] if e['id']==targets.ENTRY]!=[expected]:
        raise ValueError('EWT_CONTROL_TARGET_EXCLUSIONS')
    if source_control.check()!=1174:raise ValueError('EWT_CONTROL_SOURCE_EXCLUSIONS')
    # Recompute the exact earlier experiment before using its training or weight.
    prior=model.run(source)
    if (json.dumps(prior,sort_keys=True,indent=2)+'\n').encode()!=frozen:
        raise ValueError('EWT_CONTROL_MODEL_DRIFT')
    hashes=json.loads(ewt.LOCK.read_bytes())['files']
    data={name:(source/name).read_bytes() for name in hashes}
    groups,_=model.annotations(data,hashes)
    channel=Counter(event for _,_,event in groups['train'])
    excluded={word for part in ('train','dev') for typed,target,_ in groups[part] for word in (typed,target)}
    rows,counts=test_controls(data['en_ewt-ud-test.conllu'])
    result=screen(rows,model.parse_vocab(model.VOCAB.read_bytes()),channel,excluded,
                  prior['results']['chosenFrequencyWeight'])
    if (RECEIPT.read_bytes()!=frozen or targets.LEDGER.read_bytes()!=raw_ledger or source_control.CONTROL.read_bytes()!=raw_control or
            any(model.sha((source/name).read_bytes())!=digest
                                              for name,digest in hashes.items())):
        raise ValueError('EWT_CONTROL_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-unannotated-controls-not-qualification',
        experimentReceiptSha256=model.sha(frozen),sourceLockSha256=model.LOCK_SHA,
        registrySha256={'lexical':model.sha(raw_ledger),'control':model.sha(raw_control)},
        analyzerSha256=model.sha(Path(__file__).read_bytes()),modelSha256=model.sha(Path(model.__file__).read_bytes()),
        sourceCounts=dict(sorted(counts.items())),screen=result,
        labelsQualified=False,independentQualification=False,productBehaviorMeasured=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_CONTROL_OUTPUT')
    result=run(args.source_directory)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result['screen'],sort_keys=True))


if __name__=='__main__':main()
