"""Compare complete disclosed phrase observations without inferring labels."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def compare(old, new):
    if len(old) != len(new): raise ValueError('CHAT_COMPARE_COUNT')
    counts = Counter(); removed = []
    for a, b in zip(old, new, strict=True):
        if (a.get('id'), a.get('typed'), a.get('status')) != (b.get('id'), b.get('typed'), b.get('status')) or a.get('status') != 'COMPLETE':
            raise ValueError('CHAT_COMPARE_IDENTITY')
        before = a.get('phraseStages'); after = b.get('phraseStages')
        if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
            raise ValueError('CHAT_COMPARE_STAGES')
        for x, y in zip(before, after, strict=True):
            if (x.get('wordIndex'), x.get('typed')) != (y.get('wordIndex'), y.get('typed')):
                raise ValueError('CHAT_COMPARE_WORD')
            if not isinstance(x.get('changed'), bool) or not isinstance(y.get('changed'), bool):
                raise ValueError('CHAT_COMPARE_FLAG')
            if x['after'] == y['after']: continue
            if x['changed'] and not y['changed']:
                counts['removedEdits'] += 1; removed.append(x['typed'])
            elif not x['changed'] and y['changed']: counts['newEdits'] += 1
            elif x['changed'] and y['changed']: counts['bothChanged'] += 1
            else: counts['contextOnly'] += 1
    return dict(rows=len(old), removedEdits=counts['removedEdits'], newEdits=counts['newEdits'],
                bothChanged=counts['bothChanged'], contextOnly=counts['contextOnly'], removedWords=sorted(removed))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True)
    args=p.parse_args();raw_a=args.before.read_bytes();raw_b=args.after.read_bytes()
    result=compare([json.loads(line) for line in raw_a.splitlines()], [json.loads(line) for line in raw_b.splitlines()])
    result.update(beforeSha256=hashlib.sha256(raw_a).hexdigest(), afterSha256=hashlib.sha256(raw_b).hexdigest())
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__ == '__main__': main()
