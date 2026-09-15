"""Frozen public article split for model refinement; accepts only hash-pinned source files."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
SEED = 'rune-refinement-20260915-v1'
CAPS = {'train': (2_000_000, 5000), 'dev': (250_000, 1000), 'test': (250_000, 1500)}
WORD = re.compile('[а-яё]+', re.IGNORECASE)
ALPHABET = 'йцукенгшщзхъфывапролджэячсмитьбюё'
KEY_ROWS = ('йцукенгшщзхъ', 'фывапролджэ', 'ячсмитьбю')

def digest(value):
    return hashlib.sha256(value).hexdigest()

def file_hash(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def partition(article_id):
    bucket = int(digest((SEED + ':' + str(article_id)).encode())[:8], 16) % 10
    return 'train' if bucket < 8 else 'dev' if bucket == 8 else 'test'

def perturb(word, identity, vocabulary):
    variants = []
    for i in range(len(word)):
        variants.append((word[:i] + word[i+1:], 'deletion'))
        variants.append((word[:i] + word[i] + word[i:], 'repetition'))
        if i+1 < len(word) and word[i] != word[i+1]:
            variants.append((word[:i] + word[i+1] + word[i] + word[i+2:], 'transposition'))
        for row in KEY_ROWS:
            if word[i] in row:
                j = row.index(word[i])
                for neighbour in (j-1,j+1):
                    if 0 <= neighbour < len(row):
                        variants.append((word[:i] + row[neighbour] + word[i+1:], 'neighbour'))
    variants = sorted(set((v,c) for v,c in variants if v not in vocabulary and v != word and len(v) >= 4),
                      key=lambda pair: digest((identity+':'+pair[0]+':'+pair[1]).encode()))
    return variants[0] if variants else None

def run(parquet_path, frequency_path, output):
    import pyarrow.parquet as pq
    lock = json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())
    expected = lock['wikipediaContext']['files']['ru-0007.parquet']
    if parquet_path.stat().st_size != expected['bytes'] or file_hash(parquet_path) != expected['sha256']:
        raise ValueError('PUBLIC_PARQUET_IDENTITY')
    if file_hash(frequency_path) != lock['frequencyWords']['files']['ru_50k.txt']:
        raise ValueError('PUBLIC_VOCABULARY_IDENTITY')
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'): raise ValueError('FRESH_BUILD_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    vocabulary = {unicodedata.normalize('NFC', line.rsplit(' ',1)[0]).lower()
                  for line in frequency_path.read_text().splitlines()}
    texts = {p: [] for p in CAPS}; rows = {p: [] for p in CAPS}
    chars = dict.fromkeys(CAPS,0); word_counts = {p:{} for p in CAPS}; seen_articles=set(); seen_contexts=set()
    articles = {p:[] for p in CAPS}; scanned=0
    for batch in pq.ParquetFile(parquet_path).iter_batches(batch_size=128,columns=['id','text']):
        for article_id, text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist()):
            scanned += 1
            p = partition(article_id)
            if chars[p]>=CAPS[p][0] and len(rows[p])>=CAPS[p][1]: continue
            normalized = unicodedata.normalize('NFC',text or '')
            identity = digest(normalized.encode())
            if identity in seen_articles: continue
            seen_articles.add(identity); articles[p].append(str(article_id))
            # Keep sentence boundaries as spaces, preserving original preceding-context spelling/case in rows.
            clean = ' '.join(WORD.findall(normalized.lower()))
            if chars[p] < CAPS[p][0] and len(clean) >= 80:
                fragment = clean[:min(12000,CAPS[p][0]-chars[p])]
                texts[p].append({'articleId':str(article_id),'text':fragment}); chars[p]+=len(fragment)
            selected = set(); count=0
            for sentence in re.split(r'(?<=[.!?])\s+|\n+',normalized):
                matches=list(WORD.finditer(sentence))
                for ordinal, match in enumerate(matches):
                    word=match.group()
                    if ordinal<3 or word!=word.lower() or not 5<=len(word)<=12 or word not in vocabulary: continue
                    if word in selected or word_counts[p].get(word,0)>=4: continue
                    prefix=sentence[:match.start()][-128:].lstrip()
                    if not prefix or not prefix[-1].isspace():continue
                    context_identity=digest((prefix.lower()+'\0'+word).encode())
                    if context_identity in seen_contexts:continue
                    rid=digest((SEED+':'+str(article_id)+':'+str(match.start())+':'+context_identity).encode())
                    mutation=perturb(word,rid,vocabulary)
                    if mutation is None:continue
                    if len(rows[p])>=CAPS[p][1] or count>=12:break
                    typo, category=mutation
                    seen_contexts.add(context_identity);selected.add(word);count+=1
                    word_counts[p][word]=word_counts[p].get(word,0)+1
                    rows[p].append({'id':'refine-'+rid[:24],'articleId':str(article_id),'language':'ru',
                        'split':{'train':'calibration','dev':'diagnostic','test':'holdout'}[p], 'partition':p,
                        'family':word,'template':'article-'+str(article_id),'typed':typo,'prefix':prefix,
                        'cohort':'typo','noAuto':False,'expectedSpelling':word,'category':category})
                if len(rows[p])>=CAPS[p][1] or count>=12:break
        if all(chars[p]>=CAPS[p][0] and len(rows[p])>=CAPS[p][1] for p in CAPS):break
        if scanned>=20000:break
    if not all(chars[p]>=CAPS[p][0]//2 and len(rows[p])>=CAPS[p][1] for p in CAPS):raise ValueError('INSUFFICIENT_CORPUS')
    def write_rows(path, values):
        path.write_text(''.join(json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n' for v in values))
    for p in CAPS:
        write_rows(output/f'{p}-text.jsonl',texts[p]);write_rows(output/f'{p}-rows.jsonl',rows[p])
    manifest={'schema':1,'seed':SEED,'sourceSha256':expected['sha256'],'frequencySha256':file_hash(frequency_path),
              'sourceRepository':lock['wikipediaContext']['repository'],'sourceRevision':lock['wikipediaContext']['parquetRevision'],
              'sourcePath':expected['repositoryPath'],'license':lock['wikipediaContext']['licenses'],
              'preparationScriptSha256':file_hash(Path(__file__)),'containsPersonalMessages':False,'scannedArticles':scanned,
              'partitions':{p:{'characters':chars[p],'rows':len(rows[p]),'articles':articles[p]} for p in CAPS},
              'files':{p.name:file_hash(p) for p in output.glob('*.jsonl')}}
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps({p:{'characters':chars[p],'rows':len(rows[p]),'articles':len(articles[p])} for p in CAPS}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet',type=Path,required=True);parser.add_argument('--frequency',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run(args.parquet,args.frequency,args.output)
