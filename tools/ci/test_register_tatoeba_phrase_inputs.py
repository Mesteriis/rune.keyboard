import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_tatoeba_phrase_inputs as subject
import control_ledger as control
import holdout_ledger as lexical


class TatoebaPhraseInputsTest(unittest.TestCase):
    def test_source_bound_entries_match_and_reject_reuse(self):
        a = control.load(subject.CONTROL)
        b = lexical.load_ledger(subject.LEXICAL)
        first, second = subject.entries(b)
        self.assertEqual([first], [e for e in a['entries'] if e['id'] == subject.ENTRY])
        self.assertEqual([second], [e for e in b['entries'] if e['id'] == subject.ENTRY + '-contexts'])
        self.assertEqual(42153, first['rowCount'])
        name, phrase = subject.cases(b)[0]
        words = phrase.split(' ')
        row = dict(language='ru', prefix=' '.join(words[:-1]), typed=words[-1], expectedSpelling=words[-1])
        self.assertIn(control.key_for(row, 'regression'), first['keys'])
        self.assertTrue(lexical.keys_for([row], 'context') <= set(second['keys']['context']))
        with self.assertRaisesRegex(ValueError, 'CONTROL_OVERLAP'):
            control.assert_disjoint([row], a, 'regression')
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            lexical.assert_disjoint([row], b, kinds=('context',), require_complete=False)
        self.assertTrue(name.startswith('chat-regression-'))

    def test_mutated_or_duplicate_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ids.json'
            original = json.loads(subject.IDS.read_bytes())
            for changed in (original | {'purpose': 'qualification'}, original | {'ids': original['ids'][:-1] + [original['ids'][0]]}):
                path.write_text(json.dumps(changed))
                with mock.patch.object(subject, 'IDS', path), self.assertRaisesRegex(ValueError, 'TATOEBA_PHRASE_IDS'):
                    subject.cases({})

    def test_source_or_lock_mutation_fails_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lock.json'; path.write_bytes(subject.LOCK.read_bytes() + b' ')
            with mock.patch.object(subject, 'LOCK', path), self.assertRaisesRegex(ValueError, 'TATOEBA_PHRASE_LOCK'):
                subject.cases({})
            path.write_bytes(b'not the source')
            with mock.patch.object(subject, 'SOURCE', path), self.assertRaisesRegex(ValueError, 'TATOEBA_PHRASE_SOURCE'):
                subject.cases({})


if __name__ == '__main__':
    unittest.main()
