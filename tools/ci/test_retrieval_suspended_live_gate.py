"""Ensure the current admission path consumes the historic source exclusion."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/typing_experiments'))
import control_ledger
import holdout_ledger
from public_corpus_preparation_v1 import preflight


class SuspendedSourceLiveGateTest(unittest.TestCase):
    def test_live_preflight_blocks_disclosed_word_in_new_context(self):
        base = ROOT / 'tools/typing_experiments'
        lexical = holdout_ledger.load_ledger(base / 'holdout-ledger.json')
        controls = control_ledger.load(base / 'control-ledger.json')
        row = dict(id='fresh', language='ru', article='999999999', families=['редчайший'],
                   contextHash='0'*64, sourceSegmentHash='f'*64, prefix='другой контекст',
                   typed='видеофайлов', expectedSpelling='видеофайлов')
        result = preflight([row], 'spelling', lexical, controls, 'new-families')
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['unsupportedTargetOverlaps'])
        self.assertEqual(1, result['controlOverlaps']['surface'])
        lexical['entries'] = [e for e in lexical['entries'] if e['id'] != 'historical-retrieval-suspended-source-v1-contexts']
        controls['entries'] = [e for e in controls['entries'] if e['id'] != 'historical-retrieval-suspended-source-v1']
        previous = preflight([row], 'spelling', lexical, controls, 'new-families')
        self.assertEqual(0, previous['unsupportedTargetOverlaps'])
        self.assertEqual(0, previous['controlOverlaps']['surface'])


if __name__ == '__main__':
    unittest.main()
