"""Count suitability of a pinned public subtitle corpus without retaining text or scoring."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[2]
REVISION='3395aa540689e4393c3e18d063e73a5b99d7f047'
PINS={'train':('807af43d48e195049a769eb943ade6f199e58a9b','dd79c5a01ba53939d2b95ab4fd207c036ea801b998891568148ec73979e1a461',932937),
      'test':('1e10dbdced4764854b40a423438c304a960aa8cf','d159981fd5a92322dbca6781bc89c03a0c42babdd58a8232bf856e562e3f5138',911691)}
PHRASE=re.compile(r'\s*[а-яё]+(?:\s+[а-яё]+){1,5}\s*[.!?…]?\s*')
WORD=re.compile('[а-яё]+',re.IGNORECASE)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def normalized(text):return ' '.join(unicodedata.normalize('NFC',text).casefold().split())


def analyze(parts):
    if set(parts)!=set(PINS):raise ValueError('SUBTITLE_SPLITS')
    metrics={};unique={}
    for name,rows in parts.items():
        if not isinstance(rows,list) or not rows:raise ValueError('SUBTITLE_EMPTY')
        unchanged=eligible=eligible_unchanged=tokens=0;values=set()
        for row in rows:
            if (not isinstance(row,dict) or set(row)!={'source','correction','domain'} or row['domain']!='subtitles' or
                not isinstance(row['source'],str) or not row['source'].strip() or
                not isinstance(row['correction'],str) or not row['correction'].strip()):raise ValueError('SUBTITLE_ROW')
            same=row['source']==row['correction']; accepted=PHRASE.fullmatch(row['correction']) is not None
            unchanged+=same;eligible+=accepted;eligible_unchanged+=same and accepted
            if same and accepted:tokens+=len(WORD.findall(row['correction']))
            values.add(normalized(row['correction']))
        metrics[name]=dict(rows=len(rows),unchangedPairs=unchanged,eligibleCorrectedPhrases=eligible,
                           eligibleUnchangedPhrases=eligible_unchanged,eligibleUnchangedTokens=tokens,
                           distinctCorrectedSentences=len(values));unique[name]=values
    return dict(splits=metrics,exactCorrectedSentenceOverlap=len(unique['train']&unique['test']),
                qualified=False,modelCalls=0,reportContainsRawText=False)


def run(source,output):
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('SUBTITLE_OUTPUT')
    raw={name:(source/(name+'.json')).read_bytes() for name in PINS}
    for name,(blob,digest,size) in PINS.items():
        value=raw[name];git=hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()
        if len(value)!=size or sha(value)!=digest or git!=blob:raise ValueError('SUBTITLE_SOURCE_IDENTITY')
    parts={name:[json.loads(line) for line in raw[name].splitlines()] for name in PINS}
    if any(len(parts[name])!=1810 for name in PINS):raise ValueError('SUBTITLE_SOURCE_SCOPE')
    result=analyze(parts)
    if any((source/(name+'.json')).read_bytes()!=value for name,value in raw.items()):raise ValueError('SUBTITLE_SOURCE_DRIFT')
    result.update(revision=REVISION,sourceSha256={name:sha(value) for name,value in raw.items()},
                  auditorSha256=sha(Path(__file__).read_bytes()),scope='metadata-only-public-corpus-screen')
    output.mkdir(parents=True,mode=0o700);(output/'report.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.source,args.output)
