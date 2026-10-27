"""Append verified early RU article/window exclusions, preserving all prior keys."""
import argparse
import copy
import json
from pathlib import Path

from holdout_ledger import keys_for,load_ledger,validate_ledger
from import_early_ru_history import CORPORA,PREFIX,ROOT
from recover_legacy_families import sha


def enrich(parent,rows,records,receipt,bindings):
    if (receipt.get('allRowsRecovered') is not True or receipt.get('missingRows')!=[] or receipt.get('modelCalls')!=0
            or receipt.get('sourceRows')!=parent['rowCount'] or len(rows)!=parent['rowCount']
            or receipt.get('matchedOccurrences')!=len(records)):
        raise ValueError('EARLY_MERGE_RECEIPT')
    selected={r['id']:r['template'].removeprefix(r['split']+'-wikipedia-') for r in rows}
    recovered={r['id'] for r in records}
    if len(selected)!=len(rows) or set(selected)!=recovered or receipt.get('recoveredRows')!=len(recovered):
        raise ValueError('EARLY_MERGE_COVERAGE')
    if any(r['selectionHash']!=selected[r['id']] for r in records):raise ValueError('EARLY_MERGE_SELECTION')
    if any(path in parent['bindings'] and digest!=parent['bindings'][path] for path,digest in bindings.items()):
        raise ValueError('EARLY_MERGE_BINDING_CHANGE')
    result=copy.deepcopy(parent)
    for axis in ('article','sentence'):
        result['keys'][axis]=sorted(set(result['keys'].get(axis,[]))|keys_for(records,axis))
    result['missingAxes']=[axis for axis in result['missingAxes'] if axis not in ('article','sentence')]
    result['bindings'].update(bindings)
    result['recoveryCounts']=dict(rows=len(rows),occurrences=len(records),articles=len(result['keys']['article']))
    result['notes']='RU spelling only. All eligible original-selector matches retained. Window hashes are not full-sentence IDs. Canonical family and other components remain partial.'
    return result


def build(root,base,recovery_root):
    root=Path(root).resolve();recovery_root=Path(recovery_root).resolve()
    result=copy.deepcopy(validate_ledger(base))
    for corpus,(directory,manifest_sha,source) in CORPORA.items():
        parent=next(e for e in result['entries'] if e['id']==PREFIX+corpus)
        receipt_path=recovery_root/corpus/'receipt.json';identities=recovery_root/corpus/'identities.jsonl'
        receipt=json.loads(receipt_path.read_text())
        if receipt['corpus']!=corpus:raise ValueError('EARLY_MERGE_CORPUS')
        # Every scanner dependency/source binding must still match this receipt.
        for path,digest in receipt['bindings'].items():
            if sha(root/path)!=digest:raise ValueError('EARLY_MERGE_INPUT_IDENTITY')
        if receipt['bindings'].get(str(identities.relative_to(root)))!=sha(identities):
            raise ValueError('EARLY_MERGE_IDENTITIES')
        rows_path=directory+'/spelling-ru.jsonl';manifest_path=directory+'/manifest.json'
        if (sha(root/manifest_path)!=manifest_sha or receipt['bindings'].get(manifest_path)!=manifest_sha
                or sha(root/rows_path)!=parent['bindings'][rows_path]
                or receipt['bindings'].get(rows_path)!=parent['bindings'][rows_path]
                or receipt['bindings'].get(source)!=parent['bindings'][source]):
            raise ValueError('EARLY_MERGE_FROZEN_INPUT')
        rows=[json.loads(line) for line in (root/rows_path).read_text().splitlines()]
        records=[json.loads(line) for line in identities.read_text().splitlines()]
        bindings=receipt['bindings']|{str(receipt_path.relative_to(root)):sha(receipt_path)}
        updated=enrich(parent,rows,records,receipt,bindings);parent.clear();parent.update(updated)
    scope=set(result['historicalArticleOverlap']['scopeEntries'])|{PREFIX+name for name in CORPORA}
    articles={key for e in result['entries'] if e['id'] in scope for key in e['keys']['article']}
    result['historicalArticleOverlap']=dict(status='NOT_INDEPENDENT_OF_HISTORICAL_SPELLING',
        historicalArticles=len(articles),scopeEntries=sorted(scope),
        entries={e['id']:len(articles & set(e['keys'].get('article',[]))) for e in result['entries']
                 if e['id'].startswith('public-right-context-available-')},
        note='Expanded to early RU spelling components and spelling v6-v12. Existing rows/scores unchanged; freshness coverage remains incomplete.')
    return validate_ledger(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True);parser.add_argument('--recovery-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    ledger=build(ROOT,load_ledger(args.base),args.recovery_root)
    with args.output.open('x') as stream:stream.write(json.dumps(ledger,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(ledger['historicalArticleOverlap']))


if __name__=='__main__':main()
