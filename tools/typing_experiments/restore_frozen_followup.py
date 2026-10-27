"""Restore the exact v1 follow-up bytes from a pinned v3, with both hashes checked."""
import argparse
import hashlib
from pathlib import Path

V3 = 'b9cc4859e08021f851711bcabff12d329d6219312d3d988157b9716a1af574b6'
V1 = '964b7c6505cf5b3a0d766563e29ff750b3db70638302267db9c0318ffa05aef8'


def restore(source):
    if hashlib.sha256(source).hexdigest() != V3:
        raise ValueError('RESTORE_SOURCE_IDENTITY')
    text = source.decode('utf-8')
    text = text.replace('def prepare(source_root, output, exclude_corpus=None):', 'def prepare(source_root, output):')
    text = text.replace('    excluded=set(); excluded_articles=set()', '    excluded=set()')
    text = text.replace("            value=json.loads(line);excluded.add(value['family']);excluded_articles.add(value['article'])",
                        "            excluded.add(json.loads(line)['family'])")
    start = text.index('    if exclude_corpus is not None:')
    end = text.index('    lock=', start)
    text = text[:start] + text[end:]
    text = text.replace('            if str(article) in excluded_articles:continue\n', '')
    text = text.replace('excludedFamilies=len(excluded),excludedArticles=len(excluded_articles),', 'excludedFamilies=len(excluded),')
    text = text.replace("    p.add_argument('--exclude-corpus',type=Path)\n", '')
    text = text.replace('prepare(a.source_root,a.output,a.exclude_corpus)', 'prepare(a.source_root,a.output)')
    result = text.encode('utf-8')
    if hashlib.sha256(result).hexdigest() != V1:
        raise ValueError('RESTORE_TARGET_IDENTITY')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('frozen_sources')/'prepare_joint_followup_b9cc4859e08021f8.py')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    restored = restore(args.source.read_bytes())
    with args.output.open('xb') as stream:
        stream.write(restored)
    print(V1)


if __name__ == '__main__':
    main()
