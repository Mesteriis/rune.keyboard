"""Audit rejected unmanifested proposals without retrospectively qualifying them."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

from holdout_ledger import keys_for,load_ledger,validate_ledger
from import_tatoeba_history import CC0_ROOT,CC0_SPLITS,CC0_SPLIT_SHA,CC0_LOCK_SHA,DETAIL_ROOT,verify_sources
from recover_legacy_families import sha
from recover_legacy_holdout import load_generator

ROOT=Path(__file__).resolve().parents[2]
SEED='rune-supervised-conversation-20261026-v1'
QUARANTINE='public-prepared-conversation-v1-family-quarantine'
CONTEXT_EXCLUSIONS='public-rejected-conversation-v1-context-exclusions'


def typo_is_derived(word,typed,group):
    if not isinstance(typed,str) or not re.fullmatch('[а-яё]+',typed) or typed==word:return False
    if group=='missing_letter':return any(typed==word[:i]+word[i+1:] for i in range(len(word)))
    if group=='repeated_letter':return any(typed==word[:i]+word[i]+word[i:] for i in range(len(word)))
    if group=='transposition':return any(typed==word[:i]+word[i+1]+word[i]+word[i+2:] for i in range(len(word)-1))
    if group in ('substitution','adjacent1'):return len(word)==len(typed) and sum(a!=b for a,b in zip(word,typed))==1
    return False


def verify_row(row,part,sentences,generator):
    fields={'word','family','prefix','article','sentenceHash','selectionHash','id','language','split','typed','expectedSpelling','cohort','noAuto','group'}
    if set(row)!=fields or not isinstance(row.get('family'),str) or not row['family'].isascii() or not row['family'].isdecimal():raise ValueError('UNMANIFESTED_ROW_SCHEMA')
    if row.get('language')!='ru' or row.get('split')!=part or not isinstance(row.get('id'),str):raise ValueError('UNMANIFESTED_ROW_SCOPE')
    if not re.fullmatch('convo-supervised-'+part+'-[0-9]{5}',row['id']):raise ValueError('UNMANIFESTED_ROW_ID')
    article=row.get('article','')
    if not article.startswith('tatoeba:'):raise ValueError('UNMANIFESTED_SOURCE_NAMESPACE')
    identity=article.removeprefix('tatoeba:');source=sentences.get(identity)
    if source is None or source['normalizedSha256']!=row.get('sentenceHash'):raise ValueError('UNMANIFESTED_SOURCE_SENTENCE')
    word=row.get('word');prefix=row.get('prefix')
    if not isinstance(word,str) or not re.fullmatch('[а-яё]{3,12}',word) or not isinstance(prefix,str) or not prefix:raise ValueError('UNMANIFESTED_WORD_SCHEMA')
    text=unicodedata.normalize('NFC',source['text']);found=False
    for match in re.finditer(r'(?<!\w)'+re.escape(word)+r'(?!\w)',text,re.IGNORECASE):
        if match.group().islower() and generator.bounded_prefix(text[:match.start()]).rstrip()==prefix:found=True;break
    if not found:raise ValueError('UNMANIFESTED_SOURCE_CAPTURE')
    expected=hashlib.sha256((SEED+identity+word+prefix).encode()).hexdigest()
    if expected!=row.get('selectionHash'):raise ValueError('UNMANIFESTED_SELECTION_HASH')
    group=row.get('group');typed=row.get('typed');target=row.get('expectedSpelling')
    if group in ('correct','protected'):
        value=word if group=='correct' else '@'+word
        if row.get('cohort')!='correct' or row.get('noAuto') is not True or typed!=value or target!=value:raise ValueError('UNMANIFESTED_CONTROL')
    elif row.get('cohort')!='typo' or row.get('noAuto') is not False or target!=word or not typo_is_derived(word,typed,group):
        raise ValueError('UNMANIFESTED_TYPO')
    return row|dict(sourceRepository='tatoeba')


def audit_rows(rows,part,sentences,generator,lexicon,ledger):
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('UNMANIFESTED_ROW_IDS')
    mapped=[verify_row(row,part,sentences,generator) for row in rows]
    facts={};missing_contexts=[]
    for axis in ('article','sentence','context'):
        proposed=keys_for(mapped,axis);blocked={k for e in ledger['entries'] for k in e['keys'].get(axis,[])}
        facts[axis]=dict(keys=len(proposed),notAlreadyExcluded=len(proposed-blocked))
        if axis=='context':missing_contexts=sorted(proposed-blocked)
    families=set();unknown=[]
    for row in rows:
        analyses=lexicon.analyses(row['word'])
        if not analyses:unknown.append(row['id'])
        else:families.update(keys_for([dict(families=sorted({a.lemma for a in analyses}))],'family'))
    supervised={k for e in ledger['entries'] if e['usage'] in ('supervised','prepared-training-quarantine') for k in e['keys']['family']}
    all_families={k for e in ledger['entries'] for k in e['keys'].get('family',[])}
    missing_train=len(families-supervised) if part=='train' else 0
    missing_families=sorted(families-all_families)
    covered=not any(value['notAlreadyExcluded'] for value in facts.values()) and not missing_train and not missing_families and not unknown
    return dict(rows=len(rows),sourceKeys=facts,dictionaryFamilies=len(families),unresolvedRows=unknown,
        preparedTrainFamiliesNotAlreadySupervised=missing_train,
        preparedTrainFamilyKeysToQuarantine=sorted(families-supervised) if part=='train' else [],
        contextKeysToExclude=missing_contexts,historicalFamilyKeysToExclude=missing_families,
        status='EXCLUSIONS_COMPLETE_FOR_THIS_ARTIFACT' if covered else 'ADDITIONAL_EXCLUSIONS_REQUIRED',
        retrospectiveQualification=False,modelConsumptionEstablished=False)


def quarantine(ledger,receipt,report_binding):
    result=copy.deepcopy(validate_ledger(ledger));keys=receipt['counts']['train']['preparedTrainFamilyKeysToQuarantine']
    bindings=receipt['bindings']|receipt['sourceBindings']|report_binding
    additions=[]
    if keys:additions.append(dict(id=QUARANTINE,usage='prepared-training-quarantine',keys={'family':keys},missingAxes=[],bindings=bindings,
        notes='Source-verified prepared training targets in a rejected unmanifested artifact. Model consumption unproven; conservative exclusion only.'))
    contexts=sorted({k for facts in receipt['counts'].values() for k in facts['contextKeysToExclude']})
    if contexts:additions.append(dict(id=CONTEXT_EXCLUSIONS,usage='historical-context-exclusion',keys={'context':contexts},missingAxes=[],bindings=bindings,
        notes='Source-verified rejected preparation contexts. Source IDs/text covered by existing CC0 entries; no retrospective qualification.'))
    historical=sorted({k for facts in receipt['counts'].values() for k in facts['historicalFamilyKeysToExclude']}-set(keys))
    if historical:additions.append(dict(id=QUARANTINE+'-historical',usage='historical-family-exclusion',keys={'family':historical},missingAxes=[],bindings=bindings))
    if any(e['id'] in {a['id'] for a in additions} for e in result['entries']):raise ValueError('UNMANIFESTED_QUARANTINE_ALREADY_PRESENT')
    result['entries'].extend(additions)
    return validate_ledger(result)


def build(root,ledger,lexicon):
    root=Path(root);directory=root/DETAIL_ROOT/'corpus'
    if (directory/'manifest.json').exists():raise ValueError('UNMANIFESTED_CORPUS_NOW_HAS_MANIFEST')
    lock_path=CC0_ROOT+'/tatoeba-source-lock.json';source=CC0_ROOT+'/rus_sentences_CC0.tsv.bz2'
    if sha(root/lock_path)!=CC0_LOCK_SHA or sha(root/CC0_SPLITS)!=CC0_SPLIT_SHA:raise ValueError('UNMANIFESTED_SOURCE_LOCK')
    lock=json.loads((root/lock_path).read_text())
    if sha(root/source)!=lock['compressedSha256']:raise ValueError('UNMANIFESTED_PUBLIC_SOURCE')
    sentences={r['id']:r for r in (json.loads(line) for line in (root/CC0_SPLITS).read_text().splitlines())}
    verify_sources(root/source,{identity:r['normalizedSha256'] for identity,r in sentences.items()},4)
    generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
    counts={};bindings={lock_path:CC0_LOCK_SHA,CC0_SPLITS:CC0_SPLIT_SHA,source:sha(root/source)}
    for part in ('train','calibration','holdout'):
        path=DETAIL_ROOT+'/corpus/'+part+'.jsonl';rows=[json.loads(line) for line in (root/path).read_text().splitlines()]
        counts[part]=audit_rows(rows,part,sentences,generator,lexicon,ledger);bindings[path]=sha(root/path)
    rejected_log=DETAIL_ROOT+'/prepare-first-rejected.log';aborted=DETAIL_ROOT+'/prepare-followon-aborted-result.json'
    rejection_observed='CONTEXT_SPLIT_OVERLAP' in (root/rejected_log).read_text();stop=json.loads((root/aborted).read_text())
    # Owner-authored metadata has no public-source proof; do not retain its private corpus fingerprints.
    authored=json.loads((root/CC0_ROOT/'authored-manifest.json').read_text())
    return dict(purpose='UNMANIFESTED_PROVENANCE_AUDIT_NOT_RETROSPECTIVE_QUALIFICATION',counts=counts,bindings=bindings,
        dictionary=lexicon.receipt(),modelCalls=0,ledgerChanged=False,
        manifestAbsenceObserved=True,historicalTimingEstablished=False,rejectedSplitGuardObserved=rejection_observed,
        preparationFailureLogSha256=sha(root/rejected_log),
        abortedFollowon=dict(observedRowFiles=len(list((root/DETAIL_ROOT/'followon-corpus').glob('*.jsonl'))),stopBeforeFreezeFlag=stop.get('intentionalStopBeforeDataFreezeOrScoring') is True,receiptSha256=sha(root/aborted)),
        ownerAuthored=dict(declaredRows=authored.get('rows'),publicOriginEstablished=False,imported=False,privateFingerprintsStored=False),
        sourceBindings={p:sha(root/p) for p in ('tools/typing_experiments/audit_unmanifested_conversation.py','tools/morphology/ranker.py')})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ledger',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--quarantine-ledger',type=Path);args=parser.parse_args()
    if args.output.exists() or args.quarantine_ledger and args.quarantine_ledger.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'));from ranker import PymorphyLexicon
    receipt=build(ROOT,load_ledger(args.ledger),PymorphyLexicon(cache_size=16384));receipt['ledgerSha256']=sha(args.ledger)
    with args.output.open('x') as stream:stream.write(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    if args.quarantine_ledger:
        updated=quarantine(load_ledger(args.ledger),receipt,{str(args.output.resolve().relative_to(ROOT)):sha(args.output)})
        with args.quarantine_ledger.open('x') as stream:stream.write(json.dumps(updated,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({part:dict(rows=c['rows'],status=c['status'],missingTrainFamilies=c['preparedTrainFamiliesNotAlreadySupervised']) for part,c in receipt['counts'].items()}))


if __name__=='__main__':main()
