"""Train/evaluate an aggregate English edit-channel prototype on disclosed EWT.

No source sentence, token pair, document ID or learned event table is emitted.
This is an offline experiment, not a product candidate or independent holdout.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import string

import english_family_keys as family
import import_english_ewt_exposure as ewt

ROOT=Path(__file__).resolve().parents[2]
VOCAB=ROOT/'tools/ci/product-replay-v1/sources/en_50k.txt'
VOCAB_SHA='5351ff405b1126ef555791dd4d9798a48e3e9a501a9fc481a9da957752cfb458'
LOCK_SHA='380668545aa5b37008eea1708bd9da9375fb1825d3f1b5ee76a6a469accc4709'
PARTS=('train','dev','test')
WORD=re.compile(r'[a-z]{2,32}\Z')
LETTERS=string.ascii_lowercase
WEIGHTS=(0.0,0.25,0.5,1.0,2.0)


def sha(data):return hashlib.sha256(data).hexdigest()


def one_edit(target,typed):
    """Unique deterministic single-character error; ambiguous repeats collapse."""
    if not WORD.fullmatch(target) or not WORD.fullmatch(typed) or target==typed:return None
    found=set()
    if len(target)==len(typed):
        diffs=[i for i,(a,b) in enumerate(zip(target,typed)) if a!=b]
        if len(diffs)==1:
            i=diffs[0];found.add(('substitute',target[i],typed[i]))
        elif len(diffs)==2:
            i,j=diffs
            if j==i+1 and target[i]==typed[j] and target[j]==typed[i]:
                found.add(('transpose',target[i],target[j]))
    elif len(target)==len(typed)+1:
        for i in range(len(target)):
            if target[:i]+target[i+1:]==typed:found.add(('delete',target[i]))
    elif len(typed)==len(target)+1:
        for i in range(len(typed)):
            if typed[:i]+typed[i+1:]==target:found.add(('insert',typed[i]))
    return next(iter(found)) if len(found)==1 else None


def candidates(typed,vocab):
    if not WORD.fullmatch(typed):raise ValueError('EWT_MODEL_TOKEN')
    raw=set()
    for i in range(len(typed)):
        raw.add(typed[:i]+typed[i+1:])
        for c in LETTERS:raw.add(typed[:i]+c+typed[i+1:])
    for i in range(len(typed)+1):
        for c in LETTERS:raw.add(typed[:i]+c+typed[i:])
    for i in range(len(typed)-1):raw.add(typed[:i]+typed[i+1]+typed[i]+typed[i+2:])
    raw.discard(typed)
    return {word:one_edit(word,typed) for word in raw if word in vocab and one_edit(word,typed) is not None}


def parse_vocab(data):
    result={}
    for line in data.decode('utf-8').splitlines():
        word,number=line.rsplit(' ',1)
        if not number.isdecimal() or int(number)<1:raise ValueError('EWT_MODEL_VOCAB')
        if WORD.fullmatch(word):
            if word in result:raise ValueError('EWT_MODEL_VOCAB_DUPLICATE')
            result[word]=int(number)
    if not result:raise ValueError('EWT_MODEL_VOCAB_EMPTY')
    return result


def annotations(data,hashes):
    # Verify all source identities and complete document/sentence metadata first.
    rows=ewt.rows_from_sources(data,hashes)
    if len(rows)!=16622:raise ValueError('EWT_MODEL_SOURCE_COUNT')
    groups={part:[] for part in PARTS};documents={part:set() for part in PARTS};counts=Counter()
    for name in sorted(data):
        part=name.removeprefix('en_ewt-ud-').removesuffix('.conllu')
        if part not in groups:raise ValueError('EWT_MODEL_PARTITION')
        document=None
        for line in data[name].decode('utf-8').splitlines():
            if line.startswith('# newdoc id = '):
                document=line.removeprefix('# newdoc id = ');documents[part].add(document)
            if not line or line.startswith('#'):continue
            fields=line.split('\t')
            if len(fields)!=10:raise ValueError('EWT_MODEL_ROW')
            if not fields[0].isdigit():continue
            values=[x.removeprefix('CorrectForm=') for x in fields[9].split('|') if x.startswith('CorrectForm=')]
            if len(values)>1:raise ValueError('EWT_MODEL_MULTIPLE_LABELS')
            if not values:continue
            counts[part+':annotated']+=1
            if document is None:raise ValueError('EWT_MODEL_DOCUMENT')
            typed=fields[1].casefold();target=values[0].casefold()
            if not WORD.fullmatch(typed) or not WORD.fullmatch(target) or typed==target:
                counts[part+':unsupportedShapeOrCase']+=1;continue
            event=one_edit(target,typed)
            if event is None:counts[part+':notSingleEdit']+=1;continue
            counts[part+':singleEdit']+=1
            groups[part].append((typed,target,event))
    if any(documents[a]&documents[b] for i,a in enumerate(PARTS) for b in PARTS[i+1:]):
        raise ValueError('EWT_MODEL_DOCUMENT_OVERLAP')
    return groups,counts


def evaluate(groups,vocab):
    # Exclude exact target overlap before training/calibration/test; this is not
    # a lemmatizer or evidence that inflected families are disjoint.
    train_targets={target for _,target,_ in groups['train']}
    dev_targets={target for _,target,_ in groups['dev']}
    filtered={'train':groups['train'],
        'dev':[r for r in groups['dev'] if r[1] not in train_targets],
        'test':[r for r in groups['test'] if r[1] not in train_targets|dev_targets]}
    channel=Counter(event for _,_,event in filtered['train'])
    if not channel:raise ValueError('EWT_MODEL_EMPTY_TRAIN')
    def score(rows,weight):
        result=Counter(); seen=set()
        for typed,target,_ in rows:
            result['rows']+=1;seen.add(target)
            if typed in vocab:result['protectedOriginal']+=1;continue
            pool=candidates(typed,vocab)
            if target not in pool:result['targetUnavailable']+=1;continue
            result['scored']+=1
            ranked=sorted(pool,key=lambda w:(-(math.log(channel[pool[w]]+1)+weight*math.log(vocab[w])),w))
            frequency=sorted(pool,key=lambda w:(-vocab[w],w))
            result['channelTop1']+=ranked[0]==target
            result['frequencyTop1']+=frequency[0]==target
            result['channelTop3']+=target in ranked[:3]
            result['frequencyTop3']+=target in frequency[:3]
            result['candidates']+=len(pool)
        result['distinctTargets']=len(seen)
        return dict(sorted(result.items()))
    # Select only on development, fixed candidate weights and deterministic ties.
    trials={str(w):score(filtered['dev'],w) for w in WEIGHTS}
    if not trials[str(WEIGHTS[0])].get('scored'):raise ValueError('EWT_MODEL_EMPTY_DEVELOPMENT')
    chosen=min(WEIGHTS,key=lambda w:(-trials[str(w)].get('channelTop1',0),w))
    test=score(filtered['test'],chosen)
    if not test.get('scored'):raise ValueError('EWT_MODEL_EMPTY_TEST')
    return dict(trainSingleEditRows=len(filtered['train']),trainDistinctTargets=len(train_targets),
        developmentExcludedTargetOverlap=len(groups['dev'])-len(filtered['dev']),
        testExcludedTargetOverlap=len(groups['test'])-len(filtered['test']),
        developmentTrials=trials,chosenFrequencyWeight=chosen,test=test,
        eligibility='not a protected vocabulary word; exact single-edit target in pinned vocabulary',
        sourceLabelsQualified=False,independentQualification=False)


def run(source):
    lock=ewt.LOCK.read_bytes();vocab=VOCAB.read_bytes()
    if sha(lock)!=LOCK_SHA or sha(vocab)!=VOCAB_SHA:raise ValueError('EWT_MODEL_INPUT_DRIFT')
    hashes=json.loads(lock)['files'];data={name:(source/name).read_bytes() for name in hashes}
    groups,counts=annotations(data,hashes)
    vocabulary=parse_vocab(vocab)
    result=evaluate(groups,vocabulary)
    # These exact public-vocabulary target forms have been observed during
    # development and evaluation. Hashes are reversible and are not anonymization.
    target_keys=sorted({family.key_for(target) for rows in groups.values() for _,target,_ in rows
                        if target in vocabulary})
    if (ewt.LOCK.read_bytes()!=lock or VOCAB.read_bytes()!=vocab or
            any(sha((source/name).read_bytes())!=digest for name,digest in hashes.items())):
        raise ValueError('EWT_MODEL_INPUT_DRIFT')
    return dict(schemaVersion=1,scope='disclosed-ewt-annotation-experiment-not-qualification',
        sourceLockSha256=sha(lock),vocabularySha256=sha(vocab),analyzerSha256=sha(Path(__file__).read_bytes()),
        extractorSha256=sha(Path(ewt.__file__).read_bytes()),familyKeySha256=sha(Path(family.__file__).read_bytes()),
        sourceCounts=dict(sorted(counts.items())),targetSurfaceKeys=target_keys,results=result)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('EWT_MODEL_OUTPUT')
    result=run(args.source_directory)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(result['results'],sort_keys=True))


if __name__=='__main__':main()
