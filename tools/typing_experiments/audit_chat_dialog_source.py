"""Inspect a pinned synthetic public dialogue source, without creating evaluation rows."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata

REVISION='4f85463dc22850a2f6e961c9c21b13510d362d3a'
SOURCE_SHA='15aea2ae3ceb98c23082731fda3e389e7bcd09c5fbcc9c50b728b4b7b20fce36'
README_SHA='20a3d72074da322b063b82e2ddecbb2f9adc3cb003316749f3c58eb6e563e1f5'
PRIOR_SHA='c25d9afed4b75f78490f2e360c3eb0a0e06aaf97e3291d79f0bdd29aec0ee62f'
TOKEN=re.compile('[а-яё]+\\Z')


def normalized(value):
    value=unicodedata.normalize('NFC',value).casefold().strip().rstrip('.!?').strip()
    words=value.split()
    return ' '.join(words) if 2<=len(words)<=6 and all(TOKEN.fullmatch(w) for w in words) else None


def analyze(stream,prior):
    reader=csv.DictReader(stream,strict=True)
    if reader.fieldnames!=['q','a']:raise ValueError('DIALOG_SCHEMA')
    count=Counter();seen=set();prior_seen=set()
    for row in reader:
        if None in row or any(not isinstance(row.get(k),str) or not row[k] for k in ('q','a')):
            raise ValueError('DIALOG_ROW')
        count['dialogues']+=1
        for key in ('q','a'):
            text=normalized(row[key])
            if text is not None:
                count[key+'Eligible']+=1;seen.add(text)
                if text in prior:prior_seen.add(text)
    if not count['dialogues']:raise ValueError('DIALOG_EMPTY')
    return dict(dialogues=count['dialogues'],questionEligible=count['qEligible'],answerEligible=count['aEligible'],
                uniqueEligible=len(seen),uniqueExactPriorControls=len(prior_seen))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(source,readme,prior):
    source,readme,prior=map(Path,(source,readme,prior))
    before=[digest(p) for p in (source,readme,prior,Path(__file__))]
    if before[:3]!=[SOURCE_SHA,README_SHA,PRIOR_SHA]:raise ValueError('DIALOG_SOURCE_IDENTITY')
    prior_text=set()
    with prior.open(encoding='utf-8') as f:
        for line in f:
            row=json.loads(line)
            if row['cohort']=='correct':
                text=normalized(row['prefix']+' '+row['expectedSpelling'])
                if text is None:raise ValueError('DIALOG_PRIOR_CONTROL')
                prior_text.add(text)
    with source.open(encoding='utf-8',newline='') as f:counts=analyze(f,prior_text)
    if before!=[digest(p) for p in (source,readme,prior,Path(__file__))]:raise ValueError('DIALOG_INPUT_DRIFT')
    return dict(schema=1,purpose='PUBLIC_SYNTHETIC_SOURCE_SCREENING_NOT_QUALIFICATION',
        repository='https://huggingface.co/datasets/GlayAI/Tiny-Russian-Dialogs',revision=REVISION,
        sourceSha256=before[0],readmeSha256=before[1],priorRowsSha256=before[2],auditSha256=before[3],counts=counts,
        caveats=['Synthetic paired questions and assistant answers, not natural chat.',
                 'Exact prior control overlap is not a full training or holdout provenance audit.',
                 'Source text and labels have not been proofread.'],qualification=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','readme','prior','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('DIALOG_OUTPUT_EXISTS')
    report=audit(args.source,args.readme,args.prior)
    args.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report['counts']))


if __name__=='__main__':main()
