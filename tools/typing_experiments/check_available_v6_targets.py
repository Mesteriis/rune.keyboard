"""Check retained v6 target-key candidates without downloading source text."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

import recover_available_v6_targets as recovery

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'tools/typing_experiments/available-v6-article-origin-v1/target-recovery'
MATCHES_SHA256 = '2be072e1019f844f5455626a9443a9f3481b2e633c015c9e3f4519ec4d1537d4'
NOUN_CASE_ADDITIONS = {
    'authored-noun-case-training-v1-families': '965c4ca528380d74c549d524985dcbcdc6e7d172264ed96cca1a786d1fef1ac1',
    'authored-noun-case-training-v1-contexts': 'a6f348082dcfaab54a5289dd937df95ffa187a17463b61d166da1bbc8a043828',
}
GRAMMAR_CONTRAST_ADDITIONS = {
    'authored-grammar-contrasts-20261026-families': '4084b69862ed0a2d1c3d80080b5f4d3875bd84c093917eb177a5d32fc312bfb8',
    'authored-grammar-contrasts-20261026-contexts': '15bbff1d0061650ed333c20619b885922c7c534754fe6d0b281a1d489fe87895',
}
RECOVERED_V6_ADDITIONS = {
    'public-recovered-v6-fresh-matched-v5': 'f8c4f1d056808f37a16346ad3eb83600ae6dee386cda908973af6587a8c217a1',
    'public-recovered-v6-reliable-side-v5': 'bec929760003795ad9d4eadfcffae3faba7beb609254b571e7620b5ce82b68ec',
    'public-recovered-v6-sentence-corpus-v6': '08a4fe1bccef9af85e615103b2af09693f8919230b2707c12f26f6bc62e28418',
    'public-recovered-v6-sentence-pairs-v2-v6': '1c55b3765ccb6ebd70c1006785dee1e0e4745bd990daff2d0fcb6da743855bc1',
    'public-recovered-v6-diagnostic-rare-ranking-calibration': '813148c18c8a8ef5c9e45825c89307fa011762c90e5b76a653bc0672f9f8b02a',
    'public-recovered-v6-diagnostic-rare-ranking-holdout': '2d8a8b6b80e03d501bc160764c99218a3634505a964651f61cf2e174bf780214',
}
RARE_RANKING_ADDITIONS = {
    'public-recovered-v6-diagnostic-rare-ranking-calibration-windows': 'a94cbd631506e6c0e767a6424c3b07846945aeaf094b995ead87f5592af18813',
    'public-recovered-v6-diagnostic-rare-ranking-calibration-dictionary-families': '26bcde1edd913352cb0164b540f2160c8236445bb8b0ef22fbcd52a823646472',
    'public-recovered-v6-diagnostic-rare-ranking-holdout-windows': '78af0cebbdb59145048143b99897853dd488875c35e933e94bc4f4162b0ba16b',
    'public-recovered-v6-diagnostic-rare-ranking-holdout-dictionary-families': '2568faf738c608051b3f48fee4ce6b0e74cc3b4f17a557a47c202402e85dc3fd',
}
PUBLIC_SOURCE_ADDITIONS = (
    {'public-ru-wikisource-page-exposure-v1': 'b6b1d46aaa526bc18a61142ce27369a8df1002fe3234752ac01e0e5e21a11ed4'},
    {
        'public-ud-ancora-test-exposure-v1-ca': 'e2b407460b09d2a5ea8fc25237eed6264e26b5a30e24109447a816fd220ec91a',
        'public-ud-ancora-test-exposure-v1-es': '2e7b87b330848ff148c2bad3e315115fe001c46c41e2281f57e73c2431222c11',
    },
    {'public-a4-brockhaus-efron-quantities-v1': '76050a4b8d2dca46b67a36c852c9bcc6ae08170e43124e295110d9120be149c6'},
    {'public-a4-ytsaurus-ru-markdown-v1': 'f2043bf94b4e125a627c9f569e6b09a403436a2788c770893804c58cfc82780c'},
)


def verify_ledger_binding(path, expected):
    """Recover the exact historical ledger after verifying known later additions."""
    path = Path(path)
    if recovery.articles.sha_file(path) == expected:
        return
    import import_a4_review_exposure as reviewed
    import import_a4_frequency_source as frequency

    stored = json.loads(path.read_bytes())
    logical = recovery.holdout_ledger.validate_ledger(copy.deepcopy(stored))
    controls = reviewed.control.load(reviewed.CONTROL)
    by_id = {entry['id']: entry for entry in logical['entries']}
    c_by_id = {entry['id']: entry for entry in controls['entries']}
    try:
        review_control, review_lexical = reviewed.entries()
        source_lexical = by_id[frequency.ENTRY]
        source_control = c_by_id[frequency.ENTRY]
        expected_control, expected_lexical = frequency.entries(
            source_lexical['keys']['article'], source_control['articleKeys'])
        if (by_id.get(reviewed.ENTRY) != review_lexical or c_by_id.get(reviewed.ENTRY) != review_control or
                source_lexical != expected_lexical or source_control != expected_control):
            raise ValueError('V6_TARGET_LEDGER_BINDING')
        removed = {reviewed.ENTRY, frequency.ENTRY}
        for additions in (NOUN_CASE_ADDITIONS, GRAMMAR_CONTRAST_ADDITIONS,
                          RECOVERED_V6_ADDITIONS, RARE_RANKING_ADDITIONS, *PUBLIC_SOURCE_ADDITIONS):
            present = additions.keys() & by_id.keys()
            if not present:
                continue
            if present != additions.keys():
                raise ValueError('V6_TARGET_LEDGER_BINDING')
            for entry_id, digest in additions.items():
                raw = json.dumps(by_id[entry_id], ensure_ascii=False, sort_keys=True,
                                 separators=(',', ':')).encode()
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError('V6_TARGET_LEDGER_BINDING')
            removed.update(present)
        stored['entries'] = [entry for entry in stored['entries'] if entry['id'] not in removed]
        reconstructed = (json.dumps(stored, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        if hashlib.sha256(reconstructed).hexdigest() != expected:
            raise ValueError('V6_TARGET_LEDGER_BINDING')
    except (KeyError, TypeError, ValueError):
        raise ValueError('V6_TARGET_LEDGER_BINDING') from None


def check(directory=DIRECTORY):
    directory = Path(directory)
    raw = (directory / 'matches.jsonl').read_bytes()
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    recovery.context_check.check()
    lock, lock_raw = recovery.articles.read_lock()
    mapping_raw = recovery.contexts.MAPPING.read_bytes()
    mapping = [json.loads(line) for line in mapping_raw.splitlines()]
    anchor_raw = recovery.ANCHORS.read_bytes()
    anchors = [json.loads(line) for line in anchor_raw.splitlines()]
    targets = recovery.target_index(recovery.holdout_ledger.load_ledger(recovery.LEDGER))
    if (receipt.get('schema') != 1 or
            receipt.get('scope') != 'source-and-protected-target-candidate-diagnostic-not-corpus-reproduction' or
            receipt.get('independentQualification') is not False or
            receipt.get('corpusRowsRecovered') is not False or
            receipt.get('originalLabelsRecovered') is not False or
            receipt.get('sourceDecoderAttested') is not False or
            receipt.get('sourceLockSha256') != hashlib.sha256(lock_raw).hexdigest() or
            receipt.get('articleMappingSha256') != hashlib.sha256(mapping_raw).hexdigest() or
            receipt.get('anchorSha256') != hashlib.sha256(anchor_raw).hexdigest() or
            receipt.get('matchesSha256') != MATCHES_SHA256 or
            hashlib.sha256(raw).hexdigest() != MATCHES_SHA256):
        raise ValueError('V6_TARGET_RECEIPT')
    expected_helpers = {'tools/typing_experiments/recover_available_v6_targets.py',
        'tools/typing_experiments/recover_available_v6_contexts.py',
        'tools/typing_experiments/check_available_v6_contexts.py',
        'tools/typing_experiments/recover_available_v6_articles.py',
        'tools/typing_experiments/check_available_v6_articles.py',
        'tools/typing_experiments/holdout_ledger.py',
        'tools/typing_experiments/prepare_external_spelling_holdout.py',
        'tools/typing_experiments/right_context_sentence_selection.py',
        'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py',
        'tools/typing_experiments/source_identities.py',
        'tools/typing_experiments/conversation_split_checks.py',
        'tools/typing_experiments/frozen_sources/prepare_60f079e28a18fd98.py'}
    helpers = receipt.get('helperSha256')
    if not isinstance(helpers, dict) or set(helpers) != expected_helpers or any(
            recovery.articles.sha_file(ROOT / name) != digest for name, digest in helpers.items()):
        raise ValueError('V6_TARGET_HELPER_BINDING')
    verify_ledger_binding(recovery.LEDGER, receipt.get('ledgerSha256'))
    def anchor_id(a):
        return (a['source'], a['article'], a['wordStart'], a['wordEnd'],
                a['contextHash'], a['sentenceKey'], a['sentencePartition'])
    eligible = {anchor_id(a) for a in anchors if a['articlePartition'] == a['sentencePartition']}
    if len(eligible) != sum(a['articlePartition'] == a['sentencePartition'] for a in anchors):
        raise ValueError('V6_TARGET_DUPLICATE_ANCHOR')
    matches = [json.loads(line) for line in raw.splitlines()]
    seen, per_shard = set(), Counter()
    for row in matches:
        if (not isinstance(row, dict) or set(row) != {'article', 'source', 'wordStart', 'wordEnd',
                'contextHash', 'sentenceKey', 'sourcePartition', 'targetKey', 'targetPartition', 'variant'} or
                row['variant'] not in ('source-word', 'protected-source-word')):
            raise ValueError('V6_TARGET_MATCH')
        identity = (row['source'], row['article'], row['wordStart'], row['wordEnd'], row['contextHash'],
                    row['sentenceKey'], row['sourcePartition'])
        item = (identity, row['variant'])
        if identity not in eligible or item in seen or targets.get(row['targetKey']) != row['targetPartition']:
            raise ValueError('V6_TARGET_MATCH_IDENTITY')
        seen.add(item)
        per_shard[row['source']] += 1
    if matches != sorted(matches, key=lambda m: (m['targetPartition'], m['targetKey'],
            int(m['article']), m['wordStart'], m['variant'])):
        raise ValueError('V6_TARGET_ORDER')
    article_counts = Counter(row['shard'] for row in mapping)
    anchor_counts = Counter(a['source'] for a in anchors if a['articlePartition'] == a['sentencePartition'])
    shards = {s['name'] for s in lock['shards']}
    source_counts = receipt.get('sourceCounts')
    if not isinstance(source_counts, dict) or set(source_counts) != shards or any(
            source_counts[name] != {'sourceRows': 92622, 'articles': article_counts[name],
                'checkedAnchors': anchor_counts[name],
                'candidates': {'source-word': anchor_counts[name], 'protected-source-word': anchor_counts[name]},
                'matched': per_shard[name]} for name in shards):
        raise ValueError('V6_TARGET_SOURCE_COUNTS')
    summary = recovery.summarize(targets, matches)
    if (receipt.get('targetCounts') != dict(Counter(targets.values())) or
            receipt.get('totalTargets') != len(targets) or
            any(receipt.get(k) != v for k, v in summary.items())):
        raise ValueError('V6_TARGET_COUNTS')
    return dict(targets=len(targets), matches=len(matches), **summary, independentQualification=False)


if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
