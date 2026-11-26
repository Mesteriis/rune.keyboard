import copy
import json
import unittest

import control_ledger as control
import register_historical_qualification_controls as subject


class HistoricalQualificationControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = subject.inputs()
        cls.ledger = control.load(subject.CONTROL)
        cls.entries = subject.derive(cls.files, cls.ledger)

    def test_all_versions_languages_and_input_types_are_registered(self):
        self.assertEqual(12, len(self.entries))
        self.assertEqual(30600, sum(e['rowCount'] for e in self.entries if '-surfaces-' not in e['id']))
        self.assertEqual(12, len({e['id'] for e in self.entries}))
        self.assertEqual({'en', 'es', 'ru'}, {e['language'] for e in self.entries})
        self.assertEqual({'regression'}, {e['kind'] for e in self.entries})
        self.assertEqual(3, sum('-surfaces-' in e['id'] for e in self.entries))
        protected = copy.deepcopy(self.ledger)
        protected['entries'] = [e for e in protected['entries'] if not e['id'].startswith(subject.PREFIX)]
        protected['entries'].extend(copy.deepcopy(self.entries))
        self.assertEqual({'entries': 12, 'independentQualification': False}, subject.check(protected))

    def test_real_previously_unlisted_inputs_are_rejected(self):
        original = copy.deepcopy(self.ledger)
        original['entries'] = [e for e in original['entries'] if not e['id'].startswith(subject.PREFIX)]
        prior = {k for e in original['entries'] for k in e.get('surfaceKeys', [])}
        protected = copy.deepcopy(original); protected['entries'].extend(copy.deepcopy(self.entries))
        candidates = {'regression': None, 'punctuation': None, 'protected': None}
        for name, raw in self.files['v3'].items():
            if not name.endswith('.jsonl'): continue
            for line in raw.splitlines():
                record = json.loads(line)
                kind = 'punctuation' if record['task'] == 'punctuation' else 'protected' if record['cohort'] == 'protected' else 'regression'
                if candidates[kind] is not None: continue
                lang = record['language']; word = record.get('currentWord') if kind == 'punctuation' else record.get('typed')
                if control.surface_key(lang, word) in prior: continue
                row = {'language': lang, 'prefix': '' if kind == 'regression' else 'исторический контроль', 'typed': word} if kind != 'punctuation' else {
                    'language': lang, 'prefix': 'исторический контроль', 'currentWord': word,
                    'expectedBoundary': record['expectedBoundary']}
                candidates[kind] = row
        for kind, row in candidates.items():
            with self.subTest(kind=kind):
                self.assertIsNotNone(row)
                with self.assertRaisesRegex(ValueError, 'CONTROL_COVERAGE_INCOMPLETE'):
                    control.assert_disjoint([row], original, kind)
                with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
                    control.assert_disjoint([row], protected, kind)

    def test_modified_or_missing_registered_entry_is_rejected(self):
        protected = copy.deepcopy(self.ledger)
        protected['entries'] = [e for e in protected['entries'] if not e['id'].startswith(subject.PREFIX)]
        protected['entries'].extend(copy.deepcopy(self.entries))
        protected['entries'][-1]['surfaceKeys'].pop()
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_CONTROL_REGISTERED_DRIFT'):
            subject.check(protected)
        protected['entries'].pop()
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_CONTROL_REGISTERED_DRIFT'):
            subject.check(protected)

    def test_existing_punctuation_components_must_match_before_surface_registration(self):
        ledger = copy.deepcopy(self.ledger)
        entry = next(e for e in ledger['entries'] if e['id'] == 'compact-v3-punctuation-ru')
        entry['keys'].pop()
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_CONTROL_PRIOR_COMPONENT'):
            subject.derive(self.files, ledger)

    def test_bad_scope_is_rejected(self):
        files = dict(self.files); files.pop('v4')
        with self.assertRaisesRegex(ValueError, 'HISTORICAL_CONTROL_VERSIONS'):
            subject.derive(files, self.ledger)


if __name__ == '__main__':
    unittest.main()
