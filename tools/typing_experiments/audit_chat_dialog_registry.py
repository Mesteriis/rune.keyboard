"""Screen exact token contexts of a pinned public dialogue source against the ledger."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from audit_chat_dialog_source import SOURCE_SHA,README_SHA,REVISION,normalized
from holdout_ledger import keys_for,load_ledger


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def scan(stream,ledger):
    blocked={key for entry in ledger['entries'] for key in entry['keys'].get('context',[])}
    reader=csv.DictReader(stream,strict=True)
    if reader.fieldnames!=['q','a']:raise ValueError('DIALOG_SCHEMA')
    phrases=set();total=0
    for row in reader:
        if None in row or any(not isinstance(row.get(k),str) or not row[k] for k in ('q','a')):raise ValueError('DIALOG_ROW')
        total+=1
        for field in ('q','a'):
            phrase=normalized(row[field])
            if phrase is not None:phrases.add(phrase)
    if not total:raise ValueError('DIALOG_EMPTY')
    contexts=set();overlapping=set();first_overlapping=set();later_overlapping=set();last_overlapping=set()
    for phrase in phrases:
        words=phrase.split()
        for i,word in enumerate(words):
            row=dict(prefix=' '.join(words[:i]),typed=word,expectedSpelling=word)
            key=next(iter(keys_for([row],'context')));contexts.add(key)
            if key in blocked:
                overlapping.add(phrase)
                (first_overlapping if i==0 else later_overlapping).add(phrase)
                if i==len(words)-1:last_overlapping.add(phrase)
    return dict(dialogues=total,uniquePhrases=len(phrases),uniqueTokenContexts=len(contexts),
                phrasesWithAnyContextOverlap=len(overlapping),phrasesWithFirstContextOverlap=len(first_overlapping),
                phrasesWithLaterContextOverlap=len(later_overlapping),phrasesWithLastContextOverlap=len(last_overlapping),
                distinctTokenContextOverlaps=len(contexts & blocked),ledgerComplete=ledger['coverage']['complete'])


def run(source,readme,ledger_path):
    paths=[Path(source),Path(readme),Path(ledger_path),Path(__file__),Path(__file__).with_name('audit_chat_dialog_source.py'),Path(__file__).with_name('holdout_ledger.py'),Path(__file__).with_name('conversation_split_checks.py')]
    before=[digest(p) for p in paths]
    if before[:2]!=[SOURCE_SHA,README_SHA]:raise ValueError('DIALOG_SOURCE_IDENTITY')
    ledger=load_ledger(paths[2])
    with paths[0].open(encoding='utf-8',newline='') as f:counts=scan(f,ledger)
    if before!=[digest(p) for p in paths]:raise ValueError('DIALOG_INPUT_DRIFT')
    return dict(schema=1,purpose='PUBLIC_SYNTHETIC_CONTEXT_SCREEN_NOT_QUALIFICATION',revision=REVISION,
        bindings={p.name:h for p,h in zip(paths,before,strict=True)},counts=counts,qualification=False,
        limitations=['Only exact prefix-target keys are screened; source, article, family, right context and semantic overlap remain unverified.',
                     'Ledger coverage is incomplete; no independent freshness claim.',
                     'Synthetic source spelling and intent are not verified.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','readme','ledger','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('DIALOG_OUTPUT_EXISTS')
    result=run(args.source,args.readme,args.ledger)
    args.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result['counts']))


if __name__=='__main__':main()
