"""Preserve RU spelling identities from pinned early multi-language corpora."""
import argparse
import copy
import json
from pathlib import Path
import sys

from holdout_ledger import keys_for,load_ledger,validate_ledger
from recover_legacy_families import recover_rows,sha

ROOT=Path(__file__).resolve().parents[2]
CORPORA={
 'qualification-v2':('tools/eval/smart-typing-0.3/qualification-v2/corpus',
  '8bb3d0a0db1c11306ab809a4a1ede7c1a2b613529c7305e51523d668afd5a452',
  'build/smart-typing-0.3/qualification-v2/wikipedia-20231101/ru-0009.parquet'),
 'compact-v3':('build/smart-typing-0.3/compact-v3-external-20260919/source',
  '56a5b994bc2048c4cf434a123ebbe2e2f7a746102b936a83d535fc582ceecee3',
  'build/smart-typing-0.3/qualification-v3/wikipedia-20231101/ru-0010.parquet'),
 'compact-v4':('build/smart-typing-0.3/compact-v4-external-20260919/source',
  'a1579d3596ba733dbf5fff49adb6c9dad5d7a54902fe5d98776329578328c9cc',
  'build/smart-typing-0.3/qualification-v4/wikipedia-20231101/ru-0008.parquet'),
}
PREFIX='public-early-ru-'


def corpus_entries(name,rows,bindings,lexicon):
    if not rows or any(r.get('language')!='ru' or r.get('task')!='spelling' for r in rows):
        raise ValueError('EARLY_RU_SPELLING_SCOPE')
    contexts=[]
    for row in rows:
        value=dict(row)
        if 'expectedSpelling' not in value and value.get('cohort')=='correct':value['expectedSpelling']=value['typed']
        contexts.append(value)
    families,counts=recover_rows(rows,lexicon)
    parent=PREFIX+name
    entries=[dict(id=parent,usage='historical-exclusion',rowCount=len(rows),bindings=bindings,
        keys={'context':sorted(keys_for(contexts,'context'))},missingAxes=['article','family','sentence'],
        notes='RU spelling component only. Exact target-context keys; article/window recovery and other languages/tasks remain pending.')]
    if families:
        entries.append(dict(id=parent+'-families',usage='historical-family-exclusion',bindings=bindings,
            keys={'family':families},missingAxes=[],parentEntries=[parent],
            notes='Dictionary-only union of target analyses. Parent family coverage remains partial.'))
    return entries,counts


def build(root,base,lexicon):
    root=Path(root);result=copy.deepcopy(validate_ledger(base))
    if any(e['id'].startswith(PREFIX) for e in result['entries']):raise ValueError('EARLY_RU_ALREADY_IMPORTED')
    counts={};sources={};builder_hashes={};bindings={}
    for name,(directory,digest,source) in CORPORA.items():
        manifest_path=directory+'/manifest.json'
        if sha(root/manifest_path)!=digest:raise ValueError('EARLY_RU_MANIFEST_IDENTITY')
        manifest=json.loads((root/manifest_path).read_text());public=manifest['source']
        if (manifest['containsPersonalMessages'] is not False or manifest['frozenBeforeScoring'] is not True
                or public['repository']!='wikimedia/wikipedia' or public['parquetRevision']!='a634f78b1c435397c07001e175fa74cc4ad5e775'
                or sha(root/source)!=public['files'][Path(source).name]):
            raise ValueError('EARLY_RU_PUBLIC_SOURCE')
        row_path=directory+'/spelling-ru.jsonl'
        if sha(root/row_path)!=manifest['files']['spelling-ru.jsonl']:raise ValueError('EARLY_RU_ROWS_IDENTITY')
        corpus_bindings={manifest_path:digest,row_path:sha(root/row_path),source:sha(root/source)}
        corpus_bindings.update({p:sha(root/p) for p in ('tools/typing_experiments/import_early_ru_history.py',
            'tools/typing_experiments/recover_legacy_families.py','tools/morphology/ranker.py')})
        archive=root/'tools/typing_experiments/frozen_sources'
        archived=json.loads((archive/'manifest.json').read_text())['sources']
        for original,expected in manifest['sources'].items():
            if not original.endswith('/generate_corpus.py'):continue
            entry=archived[expected]
            path=archive/entry['file']
            if entry['originalPath']!=original or sha(path)!=expected:
                raise ValueError('EARLY_RU_GENERATOR_ARCHIVE')
            corpus_bindings[str(path.relative_to(root))]=expected
        rows=[json.loads(line) for line in (root/row_path).read_text().splitlines()]
        entries,counts[name]=corpus_entries(name,rows,corpus_bindings,lexicon)
        result['entries'].extend(entries);bindings.update(corpus_bindings);sources[name]=public
        builder_hashes[name]=manifest['sources']
    receipt=dict(purpose='EARLY_RU_SPELLING_HISTORY_NOT_COMPLETE_MULTILINGUAL_IMPORT',
        counts=counts,bindings=bindings,publicSources=sources,originalSourceBindings=builder_hashes,
        dictionary=lexicon.receipt(),modelCalls=0,
        pending=['Source article and window identity recovery','Unresolved dictionary target families',
                 'Punctuation and protected-token components','EN/ES require language-qualified namespaces',
                 'Remaining evaluation/source-lock/runtime dependencies'])
    return validate_ledger(result),receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists')
    sys.path.insert(0,str(ROOT/'tools/morphology'))
    from ranker import PymorphyLexicon
    ledger,receipt=build(ROOT,load_ledger(args.base),PymorphyLexicon(cache_size=16384))
    args.output.mkdir(parents=True,exist_ok=False)
    for name,value in (('ledger.json',ledger),('receipt.json',receipt)):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({name:dict(rows=v['rows'],unresolvedRows=len(v['unresolvedRows'])) for name,v in receipt['counts'].items()}))


if __name__=='__main__':main()
