import json
import unittest

import import_wiktionary_remaining_surfaces as subject
from public_corpus_preparation_v1 import preflight
from source_identities import unsupported_surface_key
from test_public_corpus_preparation_v1 import candidate, controls


class RemainingWiktionarySurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(subject.LEDGER.read_bytes())
        cls.fixture = json.loads(subject.FIXTURE.read_bytes())

    def test_bound_entry_and_new_surface_refusal(self):
        expected = subject.entry(self.base, self.fixture)
        self.assertEqual(expected, next(e for e in self.base['entries'] if e['id'] == subject.ENTRY))
        before = dict(self.base, entries=[e for e in self.base['entries'] if e['id'] != subject.ENTRY])
        added = set(expected['unsupportedSurfaceKeys'])
        form = next(f for _, f in self.fixture['pairs'] if unsupported_surface_key(f) in added)
        row = candidate(typed=form, expectedSpelling=form)
        self.assertEqual(0, preflight([row], 'spelling', before, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertEqual(1, preflight([row], 'spelling', self.base, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertFalse(self.base['coverage']['complete'])

    def test_parent_mutation_and_fixture_drift_are_rejected(self):
        changed = dict(self.base, entries=list(self.base['entries']))
        index = next(i for i, e in enumerate(changed['entries']) if e['id'] == self.fixture['parentIds'][0])
        changed['entries'][index] = dict(changed['entries'][index], notes='altered')
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_REMAINING_BASELINE'):
            subject.entry(changed, self.fixture)
        altered = dict(self.fixture, pairs=self.fixture['pairs'][:-1])
        with self.assertRaisesRegex(ValueError, 'WIKTIONARY_REMAINING_FIXTURE'):
            subject.entry(self.base, altered)


if __name__ == '__main__':
    unittest.main()
