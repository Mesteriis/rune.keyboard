"""Preserve pinned public conversational history with explicit Tatoeba identities."""
import argparse
import bz2
import copy
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_families import sha

ROOT=Path(__file__).resolve().parents[2]
PREFIX='public-tatoeba-history-'
CC0_ROOT='build/context-feature-ranker-20261026'
CC0_SPLITS=CC0_ROOT+'/tatoeba-sentence-splits.jsonl'
CC0_SPLIT_SHA='5a2c1bf8301f48c689428d9f1bc34b89cbca6eb4e3e2f76ded2e596f508bb3e4'
CC0_LOCK_SHA='850a865909accd5680c0e7ddb522efb05b5dc6addc6e3f2e96d2d3be899cbeff'
DETAIL_ROOT='build/conversation-supervised-20261026'
DETAIL_SHA='3993a545d85db1e60a9423c0165a909c0d52beba85070883adf93cf5abe3db5f'
CORPORA={
 'context-feature':(CC0_ROOT+'/conversation-corpus','76a1d12473bcd31e3d093537eb8a52dfd88332b8043927b9f1a1986a6b7ee541','cc0'),
 'supervised-v2':(DETAIL_ROOT+'/corpus-v2','330ac710e7cb3053fae1b97d2841b327caf0e498b2a8148d84c1c9bae82c358c','cc0'),
 'promoted-followon':(DETAIL_ROOT+'/followon-corpus-v2','9509ec8aef83b0c3bc311b8a482ae2fdd5e673a618cd2fe335faf65c3df7507b','detail'),
 'supervised95':('build/conversation-supervised95-20261026/corpus','cd0ea49a51b04e70059291fac7208a054aafee33e7c11a8491df2dcd038ad91e','detail'),
 'grammar-context':('build/grammar-context-ranking-20261026/corpus','612498f019bcc052ef3ec51651d4a4d71a9ff2fcf6a9af197796d41a0e0e8a11','detail'),
}
DERIVED_CORPORA={
 'grammar-focused':('build/grammar-focused-eval-20261026/corpus','11efa3793df4ac550e9f6680af3e9b2e8fcb47394c80dd2b5dd86a8a6c8f853a','detail'),
 'grammar-contrast-eval':('build/grammar-contrast-training-20261026/corpus','dc360183a36b887fb1c763bf8d4d80660fe4e0845ddc18b2880f6cf5fd8572a2','detail'),
 'noun-case-v2':('build/noun-case-focus-v2-20261026/corpus','8b6ae6dbd877d10f074bc60c052b5e2c5525c79c54b768a305cfc7f20fa3e5e4','detail'),
 'noun-case-v3':('build/noun-case-focus-v3-20261026/corpus','0a25ccbaa8cde3a65ef5da985e1e751f59409122be9773f0260bd3199e88eaf1','detail'),
 'grammar-profile-eval':('build/grammar-profile-training-20261026/corpus','8a7807aee382a994cff8c975aa6035cb29fff51a4665924349ea6748b4a1c2cb','detail'),
 'grammar-revision-broad':('build/grammar-revision-broad-20261026/corpus','8a7807aee382a994cff8c975aa6035cb29fff51a4665924349ea6748b4a1c2cb','detail'),
 'grammar-conservative':('build/grammar-conservative-20261026/corpus','8a7807aee382a994cff8c975aa6035cb29fff51a4665924349ea6748b4a1c2cb','detail'),
}


def sentence_hash(text):
    return hashlib.sha256(' '.join(unicodedata.normalize('NFC',text).casefold().split()).encode()).hexdigest()


def verify_sources(path,wanted,columns,captures=None):
    remaining=set(wanted)
    with bz2.open(path,'rt',encoding='utf-8') as stream:
        for line in stream:
            fields=line.rstrip('\n').split('\t')
            if len(fields)!=columns or fields[1]!='rus':raise ValueError('TATOEBA_SOURCE_COLUMNS')
            if fields[0] not in remaining:continue
            if sentence_hash(fields[2])!=wanted[fields[0]]:raise ValueError('TATOEBA_SOURCE_SENTENCE_HASH')
            source_text=unicodedata.normalize('NFC',fields[2])
            for prefix in (captures or {}).get(fields[0],()):
                if not isinstance(prefix,str) or not prefix or unicodedata.normalize('NFC',prefix) not in source_text:
                    raise ValueError('TATOEBA_SOURCE_PREFIX_CAPTURE')
            remaining.remove(fields[0])
    if remaining:raise ValueError('TATOEBA_SOURCE_IDS_MISSING')


def partition_entries(name,part,rows,trained,lexicon,bindings):
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('TATOEBA_ROW_IDENTITY')
    mapped=[];families=set();unknown=[]
    for row in rows:
        if row.get('language')!='ru' or row.get('split')!=part:raise ValueError('TATOEBA_ROW_SCOPE')
        value=row|dict(sourceRepository='tatoeba');mapped.append(value)
        targets={row['word']}
        expected=row.get('expectedSpelling',row.get('typed'))
        if row.get('group')=='protected' or row.get('cohort')=='protected':
            if row.get('group')!='protected' or row.get('cohort') not in ('correct','protected') or row.get('noAuto') is not True or expected!='@'+row['word'] or row['typed']!=expected:
                raise ValueError('TATOEBA_PROTECTED_CONTROL')
        else:targets.add(expected)
        for target in sorted(targets):
            analyses=lexicon.analyses(target)
            if not analyses:unknown.append(row['id']);continue
            families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
    keys={axis:sorted(keys_for(mapped,axis)) for axis in ('article','sentence','context')}
    if not unknown:keys['family']=sorted(families)
    parent=PREFIX+name+'-'+part
    entries=[dict(id=parent,usage='historical-exclusion',keys=keys,missingAxes=['family'] if unknown else [],
        rowCount=len(rows),bindings=bindings,sourceRepository='tatoeba',
        notes='Public RU Tatoeba source sentence IDs/text hashes verified. Native numeric families are not used as lemmas.')]
    if trained or unknown:
        entries.append(dict(id=parent+'-families',usage='supervised' if trained else 'historical-family-exclusion',
            keys={'family':sorted(families)},missingAxes=[],bindings=bindings,parentEntries=[parent],
            notes='Dictionary-supported target families; includes explicitly promoted prior holdout when trained.'))
    return entries,dict(rows=len(rows),sourceSentences=len(keys['article']),fullSentenceHashes=len(keys['sentence']),
        contexts=len(keys['context']),dictionaryFamilies=len(families),unresolvedRows=sorted(set(unknown)),supervised=trained)


def build(root,base,lexicon,corpora=None):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    corpora=CORPORA if corpora is None else corpora
    if any(any(e['id'].startswith(PREFIX+name+'-') for name in corpora) for e in result['entries']):raise ValueError('TATOEBA_ALREADY_IMPORTED')
    lock_path=CC0_ROOT+'/tatoeba-source-lock.json'
    if sha(root/lock_path)!=CC0_LOCK_SHA or sha(root/CC0_SPLITS)!=CC0_SPLIT_SHA:raise ValueError('TATOEBA_CC0_LOCK')
    lock=json.loads((root/lock_path).read_text())
    cc0_path=CC0_ROOT+'/rus_sentences_CC0.tsv.bz2';detail_path=DETAIL_ROOT+'/rus_sentences_detailed.tsv.bz2'
    if (lock['url']!='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_CC0.tsv.bz2'
            or lock['license']!='CC0-1.0' or sha(root/cc0_path)!=lock['compressedSha256']
            or sha(root/detail_path)!=DETAIL_SHA):raise ValueError('TATOEBA_PUBLIC_SOURCES')
    splits=[json.loads(line) for line in (root/CC0_SPLITS).read_text().splitlines()]
    wanted_cc0={r['id']:r['normalizedSha256'] for r in splits};wanted_detail={};jobs=[];captures={'cc0':{},'detail':{}}
    common={lock_path:CC0_LOCK_SHA,CC0_SPLITS:CC0_SPLIT_SHA,cc0_path:sha(root/cc0_path),detail_path:DETAIL_SHA}
    source_bindings={p:sha(root/p) for p in ('tools/typing_experiments/import_tatoeba_history.py',
        'tools/typing_experiments/source_identities.py','tools/typing_experiments/holdout_ledger.py','tools/morphology/ranker.py')}
    common.update(source_bindings)
    promotion_path='build/conversation-supervised95-20261026/plan.json';promotion=json.loads((root/promotion_path).read_text())
    counts={};bindings=dict(common)
    for name,(directory,digest,source) in corpora.items():
        manifest_path=directory+'/manifest.json'
        if sha(root/manifest_path)!=digest:raise ValueError('TATOEBA_CORPUS_MANIFEST')
        manifest=json.loads((root/manifest_path).read_text())
        if manifest['sourceSha256']!=(CC0_SPLIT_SHA if source=='cc0' else DETAIL_SHA):raise ValueError('TATOEBA_CORPUS_SOURCE')
        if source=='detail' and (manifest['sourceUrl']!='https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_detailed.tsv.bz2' or manifest['sourceLicense']!='CC-BY-2.0-FR'):
            raise ValueError('TATOEBA_PUBLIC_LICENSE')
        files=manifest.get('files',{'holdout.jsonl':manifest.get('rowSha256')})
        for filename,digest_rows in files.items():
            if not filename.endswith('.jsonl') or Path(filename).name!=filename:raise ValueError('TATOEBA_CORPUS_FILES')
            path=directory+'/'+filename
            if sha(root/path)!=digest_rows:raise ValueError('TATOEBA_CORPUS_ROWS')
            rows=[json.loads(line) for line in (root/path).read_text().splitlines()];part=filename.removesuffix('.jsonl')
            if source=='cc0':
                expected_count=manifest['counts'][part]['rows']
            else:expected_count=manifest['rows'] if name=='promoted-followon' else manifest['counts'][part]['rows']
            if len(rows)!=expected_count:raise ValueError('TATOEBA_CORPUS_COUNT')
            for row in rows:
                article=row.get('article','')
                if not article.startswith('tatoeba:'):raise ValueError('TATOEBA_CORPUS_NAMESPACE')
                identity=article.removeprefix('tatoeba:');expected=row['sentenceHash']
                captures[source].setdefault(identity,set()).add(row['prefix'])
                if source=='cc0':
                    if wanted_cc0.get(identity)!=expected:raise ValueError('TATOEBA_CC0_SENTENCE_IDENTITY')
                else:
                    if identity in wanted_detail and wanted_detail[identity]!=expected:raise ValueError('TATOEBA_INCONSISTENT_SENTENCE')
                    wanted_detail[identity]=expected
            trained=part=='train' or name=='promoted-followon'
            local=common|{manifest_path:digest,path:digest_rows}
            if name=='promoted-followon':
                if promotion['trainPromotedSource']!=path or promotion['promotedRowsSha256']!=digest_rows:raise ValueError('TATOEBA_PROMOTION_BINDING')
                local[promotion_path]=sha(root/promotion_path)
            jobs.append((name,part,rows,trained,local));bindings.update(local)
    verify_sources(root/cc0_path,wanted_cc0,4,captures['cc0']);verify_sources(root/detail_path,wanted_detail,6,captures['detail'])
    for part in ('train','calibration','holdout'):
        rows=[dict(sourceRepository='tatoeba',language='ru',article='tatoeba:'+r['id'],sentenceHash=r['normalizedSha256']) for r in splits if r['split']==part]
        entry_id=PREFIX+'cc0-source-'+part;keys={axis:sorted(keys_for(rows,axis)) for axis in ('article','sentence')}
        existing=next((e for e in result['entries'] if e['id']==entry_id),None)
        if existing is not None:
            if existing['keys']!=keys or existing['rowCount']!=len(rows) or any(existing['bindings'].get(path)!=common[path] for path in (lock_path,CC0_SPLITS,cc0_path,detail_path)):
                raise ValueError('TATOEBA_SOURCE_REIMPORT_CHANGED')
        else:
            result['entries'].append(dict(id=entry_id,usage='historical-source-exclusion',rowCount=len(rows),bindings=common,
                keys=keys,missingAxes=[],notes='Full preprocessed public source split, not a labeled family corpus; target-training families tracked separately.'))
    for name,part,rows,trained,local in jobs:
        entries,counts[name+'/'+part]=partition_entries(name,part,rows,trained,lexicon,local);result['entries'].extend(entries)
    receipt=dict(purpose='PUBLIC_TATOEBA_HISTORY_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,bindings=bindings,
        dictionary=lexicon.receipt(),verifiedCc0Sentences=len(wanted_cc0),verifiedDetailedSentences=len(wanted_detail),
        modelCalls=0,publicSourceLicenses=['CC0-1.0','CC-BY-2.0-FR'],sourceSentenceHashesVerified=True,sourcePrefixesVerified=True,
        privateOrOwnerAuthoredCorporaImported=False,sourceBindings=source_bindings)
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scope',choices=('core','derived'),default='core');args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384),CORPORA if args.scope=='core' else DERIVED_CORPORA)
    receipt['scope']=args.scope
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):(args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(rows=sum(c['rows'] for c in receipt['counts'].values()),cc0Sentences=receipt['verifiedCc0Sentences'],detailedSentences=receipt['verifiedDetailedSentences'],unresolvedRows=sum(len(c['unresolvedRows']) for c in receipt['counts'].values()))))


if __name__=='__main__':main()
