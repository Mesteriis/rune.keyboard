import copy
import json
import unittest

import control_ledger as control
import holdout_ledger as lexical
import register_early_unknown_control_surfaces as subject
from source_identities import unsupported_surface_key


class EarlyUnknownControlSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = lexical.load_ledger(subject.LEXICAL)
        cls.ctl = control.load(subject.CONTROL)
        cls.entry = subject.make_entry(cls.lex, cls.ctl)

    def test_project_fails_for_missing_unknown_or_invalid_row(self):
        word = 'дарси'; key = unsupported_surface_key(word)
        row = {'language': 'ru', 'task': 'spelling', 'cohort': 'correct', 'typed': word}
        keys, occurrences = subject.project([row], {key})
        self.assertEqual({control.surface_key('ru', word)}, keys)
        self.assertEqual(1, occurrences)
        with self.assertRaisesRegex(ValueError, 'EARLY_CONTROL_UNKNOWN_COVERAGE'):
            subject.project([row], {key, '0' * 64})
        with self.assertRaisesRegex(ValueError, 'EARLY_CONTROL_ROW_SCOPE'):
            subject.project([row | {'language': 'en'}], {key})

    def test_real_unresolved_target_is_rejected_by_control_guard(self):
        original = copy.deepcopy(self.ctl)
        original['entries'] = [e for e in original['entries'] if e['id'] != subject.ENTRY and
                               not e['id'].startswith('historical-qualification-inputs-')]
        prior = {k for e in original['entries'] for k in e.get('surfaceKeys', [])}
        prior_contexts = {k for e in original['entries'] if e['kind'] == 'regression' for k in e['keys']}
        parents = {e['id']: e for e in self.lex['entries']}
        unknown = set(parents['public-early-ru-qualification-v2']['unsupportedSurfaceKeys'])
        selected = None
        for line in (subject.V2 / 'spelling-ru.jsonl').read_bytes().splitlines():
            record = json.loads(line)
            target = record.get('expectedSpelling') or (record.get('typed') if record.get('cohort') == 'correct' else None)
            if unsupported_surface_key(target) not in unknown or control.surface_key('ru', target) in prior:
                continue
            row = {'language': 'ru', 'prefix': '', 'typed': target}
            if control.key_for(row, 'regression') not in prior_contexts:
                selected = row; break
        self.assertIsNotNone(selected)
        with self.assertRaisesRegex(ValueError, 'CONTROL_COVERAGE_INCOMPLETE'):
            control.assert_disjoint([selected], original, 'regression')
        protected = copy.deepcopy(original); protected['entries'].append(copy.deepcopy(self.entry))
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            control.assert_disjoint([selected], protected, 'regression')
        self.assertEqual(654, len(self.entry['surfaceKeys']))
        self.assertFalse(subject.check(self.lex, protected)['independentQualification'])

    def test_missing_lexical_parent_surface_is_rejected(self):
        parent = next(e for e in self.lex['entries'] if e['id'] == 'public-early-ru-compact-v3')
        saved = parent['unsupportedSurfaceKeys']
        try:
            parent['unsupportedSurfaceKeys'] = saved[:-1]
            with self.assertRaisesRegex(ValueError, 'EARLY_CONTROL_PARENT_SURFACES'):
                subject.make_entry(self.lex, self.ctl)
        finally:
            parent['unsupportedSurfaceKeys'] = saved


if __name__ == '__main__':
    unittest.main()
