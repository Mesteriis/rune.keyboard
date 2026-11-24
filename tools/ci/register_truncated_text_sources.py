"""Register source-bound completions of disclosed truncated public fragments."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/typing_experiments'), str(ROOT/'tools/ci')]
import control_ledger as control
import holdout_ledger as lexical
import historical_data_fixtures as data
import historical_model_fixtures as model
from audit_selector_text_exposure import WORD
from audit_wordrank_source_boundaries import TOKEN
from audit_truncated_text_sources import HELPERS, PARTS, CORPORA
from source_identities import unsupported_surface_key

ENTRY='historical-truncated-text-source-completions-v1'
FIXTURE=ROOT/'tools/typing_experiments/truncated-text-source-v1'
CONTROL=ROOT/'tools/typing_experiments/control-ledger.json'
LEXICAL=ROOT/'tools/typing_experiments/holdout-ledger.json'
SOURCE=ROOT/'tools/model/rune-text-0.2/source-lock.json'
AUDIT=ROOT/'tools/typing_experiments/audit_truncated_text_sources.py'
SNAPSHOTS={'tools/typing_experiments/control_ledger.py':'0dc79fb6fa98cf5cd4ed28c5aa7379da6a4d16eecf736e77655f0e5e59eed045',
           'tools/typing_experiments/independent_corpus_guard.py':'f8bf944977321d8f2864308a8b822a39c11e47f23b87793e28bf298f42de4ce6'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def helper(name):return FIXTURE/'sources'/(SNAPSHOTS[name]+'.txt') if name in SNAPSHOTS else ROOT/name


def inputs():
    raw=(FIXTURE/'contexts.jsonl').read_bytes();receipt=json.loads((FIXTURE/'receipt.json').read_bytes())
    lock=SOURCE.read_bytes();_,model_archive=model.verify();data_archive=data.verify()
    archives={'word':model_archive,'refinement':data_archive,'epoch':data_archive}
    names={name:{p:f'{folder}/{p}-text.jsonl' for p in PARTS} for name,folder in CORPORA.items()}
    archived={name:{p:[json.loads(line) for line in archives[name][names[name][p]].splitlines()] for p in PARTS} for name in CORPORA}
    by_article={name:{p:{r['articleId']:r for r in archived[name][p]} for p in PARTS} for name in CORPORA}
    if any(len(by_article[name][p])!=len(archived[name][p]) for name in CORPORA for p in PARTS):
        raise ValueError('TRUNCATED_REG_ARCHIVE_DUPLICATE')
    rows=[json.loads(line) for line in raw.splitlines()];counts=receipt.get('counts',{})
    if (receipt.get('scope')!='disclosed-historical-truncated-source-boundary' or
        receipt.get('independentQualification') is not False or receipt.get('contextsSha256')!=sha(raw) or
        receipt.get('sourceLockSha256')!=sha(lock) or receipt.get('sourceSha256')!=
            json.loads(lock)['wikipediaContext']['files']['ru-0007.parquet']['sha256'] or
        receipt.get('archiveTextSha256')!={name:{p:sha(archives[name][names[name][p]]) for p in PARTS} for name in CORPORA} or
        receipt.get('analyzerSha256')!=sha(AUDIT.read_bytes()) or
        receipt.get('helperSha256')!={name:sha(helper(name).read_bytes()) for name in HELPERS} or
        counts!={'rows':24,'forms':24,'newForms':19,'families':24,'newFamilies':1,'unknownRows':4,
                 'corpusRows':{'word':4,'refinement':17,'epoch':3}} or len(rows)!=24):
        raise ValueError('TRUNCATED_REG_BINDING')
    seen=set()
    for row in rows:
        fields={'id','corpus','partition','language','article','prefix','typed','expectedSpelling','head','partial',
                'wordOrdinal','sourceStart','sourceEnd','families'}
        if not isinstance(row,dict) or set(row)!=fields:
            raise ValueError('TRUNCATED_REG_ROW')
        name,part,article=row['corpus'],row['partition'],row['article']
        token,head,partial=row['typed'],row['head'],row['partial']
        if (name not in CORPORA or part not in PARTS or row['language']!='ru' or
            not isinstance(article,str) or article not in by_article[name][part] or
            not isinstance(token,str) or not TOKEN.fullmatch(token) or not isinstance(head,str) or not head or
            not isinstance(partial,str) or not partial or not isinstance(row['prefix'],str) or
            row['expectedSpelling']!=token or type(row['wordOrdinal']) is not int or
            type(row['sourceStart']) is not int or type(row['sourceEnd']) is not int or
            row['sourceStart']<0 or row['sourceEnd']-row['sourceStart']!=len(token) or
            not isinstance(row['families'],list) or row['families']!=sorted(set(row['families']))):
            raise ValueError('TRUNCATED_REG_ROW')
        identity=f"{name}:{part}:{article}:{row['sourceStart']}:{row['sourceEnd']}:{row['wordOrdinal']}"
        if row['id']!=sha(identity.encode()) or row['id'] in seen:
            raise ValueError('TRUNCATED_REG_ID')
        seen.add(row['id'])
        fragment=by_article[name][part][article]['text'];matches=list(WORD.finditer(fragment));i=row['wordOrdinal']
        if (i!=len(matches)-1 or i<0 or matches[i].end()!=len(fragment) or matches[i].group()!=partial or
            not head.startswith(partial) or len(head)<=len(partial) or
            head not in {m.group().casefold() for m in WORD.finditer(token)}):
            raise ValueError('TRUNCATED_REG_RELATION')
        if row['families']:
            lexical.keys_for([row],'family')
        elif unsupported_surface_key(head) is None:
            raise ValueError('TRUNCATED_REG_UNSUPPORTED')
    paths=[Path(__file__).resolve(),FIXTURE/'NOTICE.md',FIXTURE/'contexts.jsonl',FIXTURE/'receipt.json',SOURCE,AUDIT,
           *(helper(name) for name in HELPERS)]
    for directory in ('historical-data-v1','historical-model-fixtures-v1'):
        paths.extend(ROOT/'tools/ci'/directory/name for name in ('manifest.json','files.tar.gz','articles.jsonl','NOTICE.md'))
    return rows,{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths},receipt


def entries():
    rows,bindings,receipt=inputs()
    first=dict(id=ENTRY,kind='regression',language='ru',rowCount=len(rows),bindings=bindings,
        keys=sorted({control.key_for(r,'regression') for r in rows}),
        surfaceKeys=sorted({control.surface_key('ru',r['typed']) for r in rows}),
        articleKeys=sorted({control.article_key(r) for r in rows}),
        semantics='Conservative full source completions of disclosed truncated fragments; not independent data.')
    known=[r for r in rows if r['families']]
    second=dict(id=ENTRY+'-contexts',usage='historical-context-exclusion',rowCount=len(rows),bindings=bindings,
        keys={'context':sorted(lexical.keys_for(rows,'context'))},missingAxes=[],
        notes='Full source completions of disclosed truncated fragments; not independent data.')
    third=dict(id=ENTRY+'-families',usage='prepared-training-quarantine',rowCount=len(rows),bindings=bindings,
        keys={'family':sorted(lexical.keys_for(known,'family'))},missingAxes=[],
        unsupportedSurfaceKeys=sorted({unsupported_surface_key(r['head']) for r in rows if not r['families']}),
        notes='Dictionary-only head analyses; unknown heads remain exact exclusions.')
    if len(first['surfaceKeys'])!=receipt['counts']['forms'] or len(third['keys']['family'])!=receipt['counts']['families']:
        raise ValueError('TRUNCATED_REG_COUNT')
    return first,second,third


def check():
    first,second,third=entries();a=control.load(CONTROL);b=lexical.load_ledger(LEXICAL)
    if ([e for e in a['entries'] if e['id']==ENTRY]!=[first] or
        [e for e in b['entries'] if e['id']==ENTRY+'-contexts']!=[second] or
        [e for e in b['entries'] if e['id']==ENTRY+'-families']!=[third]):
        raise ValueError('TRUNCATED_REG_DRIFT')
    return first['rowCount']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.check:
        if args.output:raise ValueError('TRUNCATED_REG_SCOPE')
        print(json.dumps({'rows':check(),'independentQualification':False}));return
    if args.output is None:raise ValueError('TRUNCATED_REG_SCOPE')
    output=args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('TRUNCATED_REG_OUTPUT')
    old_a,old_b=CONTROL.read_bytes(),LEXICAL.read_bytes();first,second,third=entries()
    receipt=json.loads((FIXTURE/'receipt.json').read_bytes())
    if receipt.get('controlLedgerSha256')!=sha(old_a) or receipt.get('lexicalLedgerSha256')!=sha(old_b):
        raise ValueError('TRUNCATED_REG_LEDGER_DRIFT')
    controls,stored=json.loads(old_a),json.loads(old_b);control.validate(controls);logical=lexical.validate_ledger(copy.deepcopy(stored))
    if any(e['id']==ENTRY for e in controls['entries']) or any(e['id'] in (ENTRY+'-contexts',ENTRY+'-families') for e in logical['entries']):
        raise ValueError('TRUNCATED_REG_EXISTS')
    controls['entries'].append(first);stored['entries'].extend((second,third))
    control.validate(controls);lexical.validate_ledger(copy.deepcopy(stored))
    if CONTROL.read_bytes()!=old_a or LEXICAL.read_bytes()!=old_b or entries()!=(first,second,third):
        raise ValueError('TRUNCATED_REG_INPUT_DRIFT')
    output.mkdir(parents=True,mode=0o700)
    for name,value in (('control-ledger.json',controls),('holdout-ledger.json',stored)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'rows':first['rowCount'],'independentQualification':False}))


if __name__=='__main__':main()
