"""Source-bound format-character diagnostic; never authorizes publication.

The previous reader and diagnostics remain available for historical receipts.
The caller must independently trust the source lock and decoder supply chain.
"""
import argparse
import json
from pathlib import Path
import sys

import control_ledger
import holdout_ledger
import selector_text_preflight_files_v1 as files
import selector_text_preflight_files_v2 as parquet
import selector_text_preflight_v3 as text

ROOT = Path(__file__).resolve().parents[2]


def assess_files(data, source, lock_path, lexical_path, controls_path, lexicon):
    data, source = Path(data), Path(source)
    paths = {'source-lock.json': Path(lock_path), 'lexical-ledger.json': Path(lexical_path),
             'control-ledger.json': Path(controls_path), 'manifest.json': data / 'manifest.json'}
    for part in files.PARTS:
        for kind in ('text', 'rows'):
            name = f'{part}-{kind}.jsonl'
            paths[name] = data / name
    captured = {name: path.read_bytes() for name, path in paths.items()}
    texts = {part: [json.loads(line) for line in captured[f'{part}-text.jsonl'].splitlines()]
             for part in files.PARTS}
    rows = {part: [json.loads(line) for line in captured[f'{part}-rows.jsonl'].splitlines()]
            for part in files.PARTS}
    wanted = {row['articleId'] for part in files.PARTS for row in texts[part]}
    wanted.update(row['articleId'] for part in files.PARTS for row in rows[part]
                  if isinstance(row, dict) and isinstance(row.get('articleId'), str)
                  and row['articleId'].isascii() and row['articleId'].isdecimal())
    decoder = parquet.decoder_identity()
    helper_paths = {'formatDiagnostic': Path(text.__file__), 'formatBoundary': Path(text.text_format.__file__),
                    'fileDiagnostic': Path(__file__),
                    'previousFormatDiagnostic': Path(text.previous.__file__)}
    helper_hashes = {name: files.file_sha(path) for name, path in helper_paths.items()}
    dictionary = json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':'), allow_nan=False)
    selected = {}

    def batches(path):
        for ids, values in parquet.read_source_batches(path):
            for article, value in zip(ids, values, strict=True):
                if article in wanted:
                    if article in selected:
                        raise ValueError('TEXT_PREFLIGHT_DUPLICATE_SOURCE')
                    selected[article] = value
            yield ids, values

    report = files.assess_files(data, source, lock_path, lexical_path, controls_path, lexicon, batches)
    if report['bindings']['inputs'] != {name: files.sha(raw) for name, raw in captured.items()}:
        raise ValueError('TEXT_PREFLIGHT_INPUT_DRIFT')
    previous_helpers = {name: Path(files.__file__).with_name(name) for name in files.HELPERS}
    previous_helpers['ranker.py'] = files.ROOT / 'tools/morphology/ranker.py'
    previous_helpers['qualification-v2/generate_corpus.py'] = files.selector.GENERATOR
    for name in ('ewt_surface_exclusions_v1.py', 'ewt-surface-exclusions-v1.json',
                 'import_english_ewt_exposure.py', 'public_sources/ud-ewt-2.18/source-lock.json'):
        previous_helpers[name] = Path(files.__file__).parent / name
    extra = text.assess(texts, rows, selected, lexicon,
                        holdout_ledger.validate_ledger(json.loads(captured['lexical-ledger.json'])),
                        control_ledger.validate(json.loads(captured['control-ledger.json'])))
    count = extra['textIdentityBlockers']['sourceFormatFragments']
    dashes = extra['textIdentityBlockers']['sourceDashFragments']
    report['textIdentityBlockers']['sourceFormatFragments'] = count
    report['textIdentityBlockers']['sourceDashFragments'] = dashes
    if (count or dashes) and report['status'] == 'BLOCKED_COVERAGE':
        report['status'] = 'BLOCKED_TEXT_IDENTITIES'
    if (any(path.read_bytes() != captured[name] for name, path in paths.items()) or
            files.file_sha(source) != report['bindings']['sourceSha256'] or
            parquet.decoder_identity() != decoder or
            any(files.file_sha(path) != helper_hashes[name] for name, path in helper_paths.items()) or
            any(files.file_sha(path) != report['bindings']['helpers'][name]
                for name, path in previous_helpers.items()) or
            json.dumps(lexicon.receipt(), sort_keys=True, separators=(',', ':'), allow_nan=False) != dictionary):
        raise ValueError('TEXT_PREFLIGHT_INPUT_DRIFT')
    report['schema'] = 3
    report['bindings']['decoder'] = decoder
    report['bindings']['formatHelpers'] = helper_hashes
    report['scope'] = 'bound-parquet-dash-diagnostic-not-admission'
    report['sourceDecoderAttested'] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'tools/morphology'))
    from ranker import PymorphyLexicon
    report = assess_files(args.data, args.source, files.SOURCE_LOCK,
                          files.LEXICAL, files.CONTROLS, PymorphyLexicon(cache_size=16384))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
