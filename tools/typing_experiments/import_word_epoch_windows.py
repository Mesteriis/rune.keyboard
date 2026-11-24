"""Recover public historical target windows into durable exclusion addenda."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ci'))
import historical_data_fixtures as data
import historical_model_fixtures as model
from frozen_source_identity import read_frozen_source
from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_holdout import load_generator
from recover_ranker_sources import HISTORICAL_SEEDS,recover_word_epoch_article

SOURCE='build/smart-typing-0.3/model-v02/wikipedia-20231101/ru-0007.parquet'
SOURCE_SHA='39b59952cd92a148b301f4d2b3ae1fb71e4caab987c6abe278f0dbdf0b01bb88'
GENERATOR='tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py'
GENERATOR_SHA='2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'
PRODUCERS={'extra':('tools/typing_experiments/prepare_epoch_test.py','9b1ac2491feb961c6e45192e5a01f1c59e14448cedf87cd48bd00b68e354c241'),
           'wordrank':('tools/typing_experiments/prepare_word_ranking.py','e213566e8f22f619a372f09c2c91866f93d8029d5db8666f783318285df74240')}
PREFIX='public-word-epoch-source-windows-'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def make_entry(name,rows,windows,bindings,parent):
    records=[{'article':r['articleId'],'contextHash':w} for r in rows for w in windows[r['id']]]
    keys={axis:sorted(keys_for(records,axis)) for axis in ('article','sentence')}
    return dict(id=PREFIX+name,usage='historical-source-exclusion',rowCount=len(rows),
        bindings=bindings,keys=keys,missingAxes=[],parentEntries=[parent],
        notes='Public historical target windows; all matching occurrences retained. Window hashes do not establish full-sentence coverage.')


def verify_parents(base,data_payload):
    expected=(data.epoch_entry(data_payload),model.sources.word_entry())
    for parent in expected:
        if [entry for entry in base['entries'] if entry['id']==parent['id']] != [parent]:
            raise ValueError('WORD_EPOCH_PARENT_IDENTITY')


def build(base,read_batches):
    original=validate_ledger(base); result=copy.deepcopy(original)
    if any(e['id'].startswith(PREFIX) for e in original['entries']):raise ValueError('WORD_EPOCH_ALREADY_IMPORTED')
    inputs=[ROOT/SOURCE,ROOT/'tools/model/rune-text-0.2/source-lock.json',ROOT/'tools/typing_experiments/frozen_sources/manifest.json',
        ROOT/'tools/typing_experiments/frozen_sources/qualification_v2_2cbcb2508ef66b32.py',
        ROOT/'tools/typing_experiments/frozen_sources/prepare_epoch_test_9b1ac2491feb961c.py',
        ROOT/'tools/typing_experiments/frozen_sources/prepare_word_ranking_e213566e8f22f619.py',
        ROOT/'tools/typing_experiments/recover_ranker_sources.py',ROOT/'tools/typing_experiments/right_context_sentence_audit.py',Path(__file__)]
    for folder in (data.DATA,model.DATA):inputs.extend(folder/n for n in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md'))
    before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    if before[SOURCE]!=SOURCE_SHA:raise ValueError('WORD_EPOCH_SOURCE_IDENTITY')
    data_payload=data.verify(); _,model_payload=model.verify()
    verify_parents(original,data_payload)
    read_frozen_source(ROOT,GENERATOR,GENERATOR_SHA)
    for name,digest in PRODUCERS.values():read_frozen_source(ROOT,name,digest)
    jobs={}; needed={}; seen_ids=set()
    specs=[('extra','test',data_payload,'typing-extra-epochs/data/',data.ENTRY),
           *[('wordrank',p,model_payload,'build/typing-word-ranking/data/',model.sources.ENTRY) for p in ('train','dev','test')]]
    for kind,part,payload,directory,parent in specs:
        manifest=json.loads(payload[directory+'manifest.json'])
        if (manifest['sourceSha256']!=SOURCE_SHA or manifest['seed']!=HISTORICAL_SEEDS[kind]
                or manifest['preparationScriptSha256']!=PRODUCERS[kind][1]):raise ValueError('WORD_EPOCH_MANIFEST')
        rows=[json.loads(line) for line in payload[directory+part+'-rows.jsonl'].splitlines()]
        if len(rows)!=manifest['partitions'][part]['rows']:raise ValueError('WORD_EPOCH_COUNT')
        parent_entry=next(e for e in original['entries'] if e['id']==parent)
        if not keys_for([{'article':r['articleId']} for r in rows],'article') <= set(parent_entry['keys']['article']):
            raise ValueError('WORD_EPOCH_PARENT_ARTICLES')
        for row in rows:
            if (row['id'] in seen_ids or not row['id'].startswith(kind+'-') or row['partition']!=part
                    or row['language']!='ru' or row['split']!={'train':'calibration','dev':'diagnostic','test':'holdout'}[part]):
                raise ValueError('WORD_EPOCH_ROW')
            seen_ids.add(row['id']);needed.setdefault(row['articleId'],[]).append(row)
        jobs[kind+'-'+part]=(rows,parent)
    generator=load_generator(GENERATOR_SHA);seen=set();windows={}
    for articles,texts in read_batches(ROOT/SOURCE):
        for article,text in zip(articles,texts,strict=True):
            article=str(article)
            if article in needed:
                if article in seen:raise ValueError('WORD_EPOCH_DUPLICATE_ARTICLE')
                windows.update(recover_word_epoch_article(article,text,needed[article],generator));seen.add(article)
    if seen!=set(needed) or set(windows)!=seen_ids:raise ValueError('WORD_EPOCH_MISSING_CAPTURE')
    if before!={str(p.relative_to(ROOT)):sha(p) for p in inputs}:raise ValueError('WORD_EPOCH_INPUT_CHANGED')
    bindings=before|{GENERATOR:GENERATOR_SHA,**{p:h for p,h in PRODUCERS.values()}}
    old_sentences={v for e in original['entries'] for v in e['keys'].get('sentence',[])}
    counts={}
    for name,(rows,parent) in jobs.items():
        entry=make_entry(name,rows,windows,bindings,parent); result['entries'].append(entry)
        counts[name]=dict(rows=len(rows),articles=len(entry['keys']['article']),windows=len(entry['keys']['sentence']),
                          newWindows=len(set(entry['keys']['sentence'])-old_sentences))
    receipt=dict(purpose='PUBLIC_HISTORICAL_TARGET_WINDOWS_NOT_QUALIFICATION',counts=counts,bindings=bindings,
                 allRowsCaptured=True,globalCoverageComplete=False,modelCalls=0)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    import pyarrow.parquet as parquet
    def batches(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=128,columns=['id','text']):
            yield batch.column(0).to_pylist(),batch.column(1).to_pylist()
    ledger,receipt=build(load_ledger(args.base),batches)
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__=='__main__':main()
