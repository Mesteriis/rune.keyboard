"""Recover public historical retrieval rows and source exclusions, never qualify them."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/morphology')]
import control_ledger as control
import holdout_ledger as lexical
import independent_corpus_guard as guard
from joint_exclusion_inputs import source_context_hash
from ranker import PymorphyLexicon
from source_identities import unsupported_surface_key

ROWS_SHA='cdc09d6b5885e0d6a01757c05b814d7efe97f7aaefb8932287dbaa673811098c'
SOURCE_LOCK=ROOT/'tools/model/rune-text-0.2/source-lock.json'
WORD=re.compile('[а-яё]+',re.IGNORECASE)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def derive(rows, articles, lexicon, generator):
    ids=set();counts=Counter();article_keys=set();sentence_keys=set();context_keys=set();families=set();unknown=set();controls=set();surfaces=set();control_articles=set()
    for row in rows:
        rid=row.get('id');article=row.get('articleId');target=row.get('expectedSpelling');typed=row.get('typed');prefix=row.get('prefix');cohort=row.get('cohort')
        if (not isinstance(rid,str) or not rid or rid in ids or row.get('language')!='ru' or row.get('partition')!='test' or row.get('split')!='holdout' or
            not isinstance(article,str) or not article.isascii() or not article.isdecimal() or
            not isinstance(target,str) or not WORD.fullmatch(target) or not isinstance(typed,str) or not WORD.fullmatch(typed) or
            not isinstance(prefix,str) or not prefix or cohort not in ('correct','typo') or
            type(row.get('noAuto')) is not bool or row['noAuto']!=(cohort=='correct') or (cohort=='correct' and typed!=target)):
            raise ValueError('RETRIEVAL_HISTORY_ROW')
        ids.add(rid);text=articles.get(article)
        if not isinstance(text,str):raise ValueError('RETRIEVAL_HISTORY_ARTICLE')
        positions=[m.start()+len(prefix) for m in re.finditer(re.escape(prefix+target),text)]
        if not positions:raise ValueError('RETRIEVAL_HISTORY_SOURCE')
        counts['rows']+=1;counts['multipleSourceMatches']+=len(positions)>1
        proposal=dict(language='ru',article=article,prefix=prefix,typed=typed,expectedSpelling=target)
        article_keys.update(lexical.keys_for([proposal],'article'));context_keys.update(lexical.keys_for([proposal],'context'))
        control_articles.add(control.article_key(proposal))
        for token in (typed,target):
            controls.add(control.key_for(proposal|{'typed':token},'regression'));surfaces.add(control.surface_key('ru',token))
        for start in positions:
            match=WORD.match(text,start)
            if match is None or match.group()!=target:raise ValueError('RETRIEVAL_HISTORY_TOKEN')
            window=source_context_hash(text,match,generator)
            sentence_keys.update(lexical.keys_for([{'contextHash':window}],'sentence'))
        analyses=sorted({a.lemma for a in lexicon.analyses(target)})
        if analyses:
            families.update(lexical.keys_for([{'families':analyses}],'family'));counts['resolvedRows']+=1
        else:
            key=unsupported_surface_key(target)
            if key is None:raise ValueError('RETRIEVAL_HISTORY_UNKNOWN')
            unknown.add(key);counts['unresolvedRows']+=1
    for text in articles.values():
        for segment,_ in guard.selector_segments(text):
            if segment.strip():
                value=lexical.source_segment_hash(segment)
                sentence_keys.add(lexical._digest('sentence',['tatoeba-full-sentence-normalized-v1',value]))
    return dict(articleKeys=sorted(article_keys),sentenceKeys=sorted(sentence_keys),contextKeys=sorted(context_keys),
                familyKeys=sorted(families),unsupportedSurfaceKeys=sorted(unknown),controlKeys=sorted(controls),
                surfaceKeys=sorted(surfaces),controlArticleKeys=sorted(control_articles)),dict(sorted(counts.items()))


def run(rows_path,parquet,output):
    import pyarrow.parquet as pq
    rows_path=Path(rows_path).resolve(strict=True);parquet=Path(parquet).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('RETRIEVAL_HISTORY_OUTPUT')
    helpers=[Path(__file__).resolve(),ROOT/'tools/typing_experiments/holdout_ledger.py',
             ROOT/'tools/typing_experiments/control_ledger.py',ROOT/'tools/typing_experiments/source_identities.py',
             ROOT/'tools/typing_experiments/independent_corpus_guard.py',ROOT/'tools/typing_experiments/joint_exclusion_inputs.py',
             ROOT/'tools/typing_experiments/right_context_sentence_audit.py',ROOT/'tools/typing_experiments/prepare_external_spelling_holdout.py',
             ROOT/'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py',ROOT/'tools/morphology/ranker.py']
    helper_hashes={str(p.relative_to(ROOT)):file_sha(p) for p in helpers}
    raw=rows_path.read_bytes();lock=SOURCE_LOCK.read_bytes();source=json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']
    if sha(raw)!=ROWS_SHA or parquet.stat().st_size!=source['bytes'] or file_sha(parquet)!=source['sha256']:
        raise ValueError('RETRIEVAL_HISTORY_INPUT')
    rows=[json.loads(x) for x in raw.splitlines()];wanted={r['articleId'] for r in rows};articles={};metadata={}
    if len(rows)!=1800 or len(wanted)!=341:raise ValueError('RETRIEVAL_HISTORY_SCOPE')
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128,columns=['id','title','text']):
        for i,title,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),batch.column(2).to_pylist(),strict=True):
            i=str(i)
            if i in wanted:
                if i in articles or not isinstance(title,str) or not title:raise ValueError('RETRIEVAL_HISTORY_DUPLICATE')
                articles[i]=unicodedata.normalize('NFC',text or '')
                metadata[i]=dict(articleId=i,title=title,historyUrl='https://ru.wikipedia.org/w/index.php?curid='+i+'&action=history')
    if set(articles)!=wanted:raise ValueError('RETRIEVAL_HISTORY_ARTICLE')
    dictionary=PymorphyLexicon(cache_size=16384);dictionary_receipt=dictionary.receipt();generator=guard._context_generator()
    keys,counts=derive(rows,articles,dictionary,generator)
    if (rows_path.read_bytes()!=raw or SOURCE_LOCK.read_bytes()!=lock or file_sha(parquet)!=source['sha256'] or dictionary.receipt()!=dictionary_receipt or
        helper_hashes!={str(p.relative_to(ROOT)):file_sha(p) for p in helpers}):
        raise ValueError('RETRIEVAL_HISTORY_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    article_raw=''.join(json.dumps(metadata[i],ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for i in sorted(metadata,key=int)).encode()
    key_raw=(json.dumps(keys,sort_keys=True,separators=(',',':'))+'\n').encode()
    (output/'rows.jsonl').write_bytes(raw);(output/'articles.jsonl').write_bytes(article_raw);(output/'source-keys.json').write_bytes(key_raw)
    receipt=dict(scope='disclosed-historical-retrieval-not-qualification',independentQualification=False,counts=counts,sourceArticles=len(wanted),
        rowsSha256=sha(raw),articlesSha256=sha(article_raw),keysSha256=sha(key_raw),sourceSha256=source['sha256'],
        sourceLockSha256=sha(lock),dictionary=dictionary_receipt,helperSha256=helper_hashes,captureSha256=file_sha(Path(__file__)))
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'counts':counts,'articles':len(wanted),'keyCounts':{k:len(v) for k,v in keys.items()}},sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rows','parquet','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();run(a.rows,a.parquet,a.output)
