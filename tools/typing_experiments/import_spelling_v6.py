"""Recover the pinned public spelling-v6 exposure with its original selector."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for, load_ledger, validate_ledger
from recover_legacy_families import recover_rows, sha
from recover_legacy_holdout import LegacySelections, load_generator, ORIGINAL

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY='build/typing-ranker-v2/external-holdout-v6-ru0011'
MANIFEST_SHA='cde8f78c6ada31a25bdc835295014232d64df6de61c199d4e9467cb9a58d4d4d'
SOURCE='build/typing-ranker-v2/ru-0011.parquet'
ENTRY='public-legacy-spelling-v6'


def assemble(base, rows, records, manifest, bindings, lexicon):
    result=copy.deepcopy(validate_ledger(base))
    if any(e['id']==ENTRY for e in result['entries']):
        raise ValueError('SPELLING_V6_ALREADY_IMPORTED')
    selections={r['id']:r['template'].removeprefix('holdout-wikipedia-') for r in rows}
    if (len(rows)!=manifest['counts']['total'] or len(selections)!=len(rows)
            or {r['id'] for r in records}!=set(selections)):
        raise ValueError('SPELLING_V6_COVERAGE')
    if any(r['selectionHash']!=selections[r['id']] for r in records):
        raise ValueError('SPELLING_V6_SELECTION')
    # Correct controls have no explicit expectedSpelling in the legacy format.
    contexts=[]
    for row in rows:
        value=dict(row)
        if 'expectedSpelling' not in value and value.get('cohort')=='correct':
            value['expectedSpelling']=value['typed']
        contexts.append(value)
    families,counts=recover_rows(rows,lexicon)
    keys={axis:sorted(keys_for(records,axis)) for axis in ('article','sentence')}
    keys['context']=sorted(keys_for(contexts,'context'))
    result['entries'].append(dict(id=ENTRY,usage='historical-exclusion',rowCount=len(rows),bindings=bindings,
        keys=keys,missingAxes=['family'],publicSource=manifest['source'],generatorBindings=manifest['sources'],
        notes='All original-selector matches retained. Source-window projection is not a full-sentence hash. Family addendum is partial.'))
    if families:
        result['entries'].append(dict(id=ENTRY+'-families',usage='historical-family-exclusion',bindings=bindings,
            keys={'family':families},missingAxes=[],parentEntries=[ENTRY],
            notes='Dictionary-only union of target analyses; unknown targets remain pending.'))
    historical=[e for e in result['entries'] if e['id'].startswith('public-spelling-v') or e['id']==ENTRY]
    articles={key for e in historical for key in e['keys']['article']}
    result['historicalArticleOverlap']=dict(
        status='NOT_INDEPENDENT_OF_HISTORICAL_SPELLING',historicalArticles=len(articles),
        scopeEntries=sorted(e['id'] for e in historical),
        entries={e['id']:len(articles & set(e['keys'].get('article',[]))) for e in base['entries']
                 if e['id'].startswith('public-right-context-available-')},
        note='Expanded to spelling v6-v12. Existing corpora and scores are unchanged; article-disjoint freshness is not certified.')
    receipt=dict(purpose='PUBLIC_SPELLING_V6_EXCLUSIONS_NOT_QUALIFICATION',counts=counts,
        source=manifest['source'],bindings=bindings,dictionary=lexicon.receipt(),modelCalls=0,
        matchedOccurrences=len(records),articles=len(keys['article']),contexts=len(keys['context']),
        sourceWindows=len(keys['sentence']),rowsInMultipleOccurrences=sum(v>1 for v in Counter(r['id'] for r in records).values()),
        currentCorpusArticleOverlap={e['id']:len(set(keys['article'])&set(e['keys'].get('article',[])))
            for e in base['entries'] if e['id'].startswith('public-right-context-available-')})
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    base=load_ledger(args.base)
    if any(e['id']==ENTRY for e in base['entries']):raise ValueError('SPELLING_V6_ALREADY_IMPORTED')
    manifest_path=ROOT/DIRECTORY/'manifest.json';rows_path=ROOT/DIRECTORY/'rows.jsonl'
    if sha(manifest_path)!=MANIFEST_SHA:raise ValueError('SPELLING_V6_MANIFEST')
    manifest=json.loads(manifest_path.read_text())
    if (manifest['containsPersonalMessages'] is not False or manifest['frozenBeforeScoring'] is not True
            or manifest['source']['repository']!='https://huggingface.co/datasets/wikimedia/wikipedia'
            or manifest['source']['revision']!='a634f78b1c435397c07001e175fa74cc4ad5e775'
            or manifest['source']['path']!='20231101.ru/train/0011.parquet'
            or sha(ROOT/SOURCE)!=manifest['source']['sha256']
            or (ROOT/SOURCE).stat().st_size!=manifest['source']['bytes']
            or sha(rows_path)!=manifest['files']['rows.jsonl']):
        raise ValueError('SPELLING_V6_PUBLIC_INPUT')
    rows=[json.loads(line) for line in rows_path.read_text().splitlines()]
    archive=ROOT/'tools/typing_experiments/frozen_sources'
    archive_manifest=json.loads((archive/'manifest.json').read_text())
    prepare_path='tools/typing_experiments/prepare_external_spelling_holdout.py'
    prepare_sha=manifest['sources'][prepare_path]
    prepared=archive_manifest['sources'][prepare_sha]
    if prepared['originalPath']!=prepare_path or sha(archive/prepared['file'])!=prepare_sha:
        raise ValueError('SPELLING_V6_BUILDER_ARCHIVE')
    generator_sha=manifest['sources'][ORIGINAL];generator=load_generator(generator_sha)
    selection=LegacySelections(rows,generator,manifest['selection']['seed'],generator_sha)
    import pyarrow.parquet as parquet
    records=[];scanned=0
    for batch in parquet.ParquetFile(ROOT/SOURCE).iter_batches(batch_size=128,columns=['id','text']):
        for article,text in zip(batch.column(0).to_pylist(),batch.column(1).to_pylist(),strict=True):
            records.extend(selection.recover_article(str(article),text));scanned+=1
        if scanned%8192==0:print(json.dumps(dict(scanned=scanned,occurrences=len(records))),flush=True)
    args.output.mkdir(parents=True,exist_ok=False)
    identities=args.output/'identities.jsonl'
    identities.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(records,key=lambda r:(r['id'],r['article'],r['contextHash']))))
    bindings={str(p.relative_to(ROOT)):sha(p) for p in (manifest_path,rows_path,ROOT/SOURCE,identities.resolve(),
        ROOT/'tools/typing_experiments/import_spelling_v6.py',ROOT/'tools/typing_experiments/recover_legacy_holdout.py',
        ROOT/'tools/typing_experiments/recover_legacy_families.py',ROOT/'tools/typing_experiments/right_context_sentence_audit.py',
        ROOT/'tools/morphology/ranker.py',archive/prepared['file'],archive/'manifest.json')}
    sys.path.insert(0,str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    ledger,receipt=assemble(base,rows,records,manifest,bindings,PymorphyLexicon(cache_size=16384))
    receipt['sourceArticlesScanned']=scanned
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('articles','matchedOccurrences','currentCorpusArticleOverlap','sourceArticlesScanned')}),flush=True)


if __name__=='__main__':main()
