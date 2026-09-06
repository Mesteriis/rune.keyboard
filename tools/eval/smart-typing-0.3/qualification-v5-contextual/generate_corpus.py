#!/usr/bin/env python3
"""Generate a source-observation corpus without scores, models or threshold fitting."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import unicodedata

import corpus_contract as c


def extract(text, language):
    text=unicodedata.normalize('NFC',text)
    result=[]
    for match in c.BOUNDARY_RE.finditer(text):
        marker,whitespace,observed=match.groups()
        if marker.isspace():
            if marker!=' ' or whitespace:continue
        elif marker in '.,:':
            if not whitespace:continue
        else:continue
        word=observed.casefold()
        if not 3<=len(word)<=20 or not all(char in c.ALPHABETS[language] for char in word):continue
        boundary=marker+' ' if marker in '.,:' else ' '
        if boundary=='. ':
            if observed[:1]!=observed[:1].upper():continue
        elif observed!=word:continue
        end=match.start(1);start=max(0,end-512)
        window=text[start:end]
        prefix=c.bounded_prefix(window).rstrip()
        if not prefix:continue
        result.append({'prefix':prefix,'word':word,'boundary':boundary,
            'selectionHash':c.selection_hash(language,boundary,prefix,word),
            'sourceSpan':{'windowStart':start,'boundaryStart':end,'wordStart':match.start(3),
                'wordEnd':match.end(3),'window':window,'separator':text[end:match.start(3)],'observedWord':observed}})
    return result


def materialize(article, language, ordinal, item):
    source,_=c.locks()
    split=c.article_split(language,article['id'])
    raw=article['text'] or ''
    return {'corpusVersion':5,'id':f"{language}-{split}-v5-{item['selectionHash']}",
        'language':language,'split':split,'task':'punctuation','prefix':item['prefix'],
        'currentWord':item['word'],'originalContinuation':' '+item['word'],'observedBoundary':item['boundary'],
        'labelSemantics':c.LABEL,'noAuto':True,'selectionHash':item['selectionHash'],
        'source':{'articleId':article['id'],'url':article['url'],'title':article['title'],
            'repositoryPath':source['files'][source['languageFiles'][language]]['repositoryPath'],
            'parquetRow':ordinal,'articleSha256':c.text_sha(raw),
            'normalizedArticleSha256':c.text_sha(unicodedata.normalize('NFC',raw)),
            'span':item['sourceSpan'],'transformations':dict(c.TRANSFORMATIONS)}}


class Selector:
    def __init__(self, language, exclusions):
        self.language=language
        self.exclusions=exclusions
        self.rows=[]
        self.counts=Counter()
        self.selected_observations=set()
        self.articles=set()
        self.stats=Counter({'articlesScanned':0,'residue3ArticlesInspected':0,
            'priorObservationCandidatesRejected':0,'selectedObservationCandidatesRejected':0})

    @property
    def complete(self):
        return len(self.rows)==400

    def consider(self, article, ordinal):
        self.stats['articlesScanned']+=1
        identity=article['id']
        c.require(isinstance(identity,str) and identity.isdecimal(), 'ARTICLE_ID')
        c.require(identity not in self.articles, 'DUPLICATE_ARTICLE_ID')
        self.articles.add(identity)
        if not c.admitted(self.language,identity):return
        self.stats['residue3ArticlesInspected']+=1
        split=c.article_split(self.language,identity)
        available={b:[] for b in c.BOUNDARIES}
        for item in extract(article['text'] or '',self.language):
            key=c.observation(item['prefix']+' '+item['word'])
            if self.exclusions.blocks(self.language,item['prefix'],item['word']):
                self.stats['priorObservationCandidatesRejected']+=1
                continue
            if key in self.selected_observations:
                self.stats['selectedObservationCandidatesRejected']+=1
                continue
            available[item['boundary']].append((item['selectionHash'],key,item))
        for boundary in c.BOUNDARIES:
            if self.counts[(split,boundary)]<50 and available[boundary]:
                _,key,item=min(available[boundary],key=lambda value:value[:2])
                row=materialize(article,self.language,ordinal,item)
                c.verify_article(row,article)
                self.rows.append(row)
                self.selected_observations.add(key)
                self.counts[(split,boundary)]+=1
                break


def write_artifacts(output, rows, identity, stats, toolchain):
    output=Path(output)
    c.require(not output.exists(), 'FRESH_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    ordered=[]
    for lang in c.LANGUAGES:
        selected=sorted([row for row in rows if row['language']==lang],key=lambda row:(row['split']!='calibration',row['id']))
        ordered.extend(selected)
        with (output/f'punctuation-{lang}.jsonl').open('xb') as stream:
            for row in selected:stream.write(c.canonical(row)+b'\n')
    with (output/'attribution.jsonl').open('xb') as stream:
        for row in ordered:stream.write(c.canonical({'id':row['id'],'language':row['language'],'source':row['source']})+b'\n')
    validation=c.validate_rows(ordered,c.Exclusions())
    manifest={'schemaVersion':1,'corpusVersion':5,'scope':c.SCOPE,'labelSemantics':c.LABEL,
        'modelScoringPerformed':False,'qualityQualified':False,'frozen':False,'identity':identity,
        'toolchain':toolchain,'generationCounts':stats,'validation':validation,
        'files':{name:c.sha(output/name) for name in c.FILES}}
    (output/'manifest.json').write_bytes(c.canonical(manifest)+b'\n')


def run(output):
    import pyarrow.parquet as parquet
    output=Path(output).resolve()
    permitted=c.REPO/'build/smart-typing-0.3/contextual-v5-20260906'
    c.require(output.parent==permitted and not output.exists(), 'FRESH_SCOPED_OUTPUT_REQUIRED')
    identity=c.current_identity()
    toolchain=c.toolchain_identity()
    exclusions=c.load_exclusions()
    source,_=c.locks()
    rows=[];counts={'exclusions':exclusions.counts(),'languages':{}}
    for lang in c.LANGUAGES:
        selector=Selector(lang,exclusions);ordinal=0
        for batch in parquet.ParquetFile(c.INPUTS/source['languageFiles'][lang]).iter_batches(batch_size=64,columns=['id','url','title','text']):
            for article in batch.to_pylist():
                selector.consider(article,ordinal);ordinal+=1
                if selector.complete:break
            if selector.complete:break
        c.require(selector.complete,'INSUFFICIENT_SOURCE_BOUNDARY_QUOTA')
        rows.extend(selector.rows)
        counts['languages'][lang]=dict(sorted(selector.stats.items()))
    c.validate_rows(rows,exclusions)
    c.validate_generation_counts(rows,counts,exclusions)
    c.require(identity==c.current_identity() and toolchain==c.toolchain_identity(), 'GENERATION_INPUT_DRIFT')
    write_artifacts(output,rows,identity,counts,toolchain)
    print(c.canonical({'rows':len(rows),'counts':counts,'manifestSha256':c.sha(output/'manifest.json'),
                      'modelScoringPerformed':False,'qualityQualified':False,'frozen':False}).decode())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
