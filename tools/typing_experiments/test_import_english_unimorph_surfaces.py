import json
import unittest

import import_english_unimorph_surfaces as subject
from public_corpus_preparation_v1 import preflight
from test_public_corpus_preparation_v1 import candidate, controls


class EnglishUnimorphSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(subject.LEDGER.read_bytes())
        cls.fixture = json.loads(subject.FIXTURE.read_bytes())

    def test_projection_keeps_ambiguous_heads_and_never_guesses(self):
        targets = {subject.control.surface_key('en', 'running')}
        lines = ['run\trunning\tV;PTCP', 'run\truns\tV;PRS',
                 'running\trunning\tN;SG', 'running\trunnings\tN;PL',
                 'other\tother\tN;SG', 'bad-form\trunning\tN;SG']
        self.assertEqual([('run', 'running'), ('run', 'runs'),
                          ('running', 'running'), ('running', 'runnings')], subject.project(lines, targets))
        with self.assertRaisesRegex(ValueError, 'EN_UNIMORPH_SOURCE_ROW'):
            subject.project(['invalid'], targets)

    def test_new_form_is_blocked_without_clearing_coverage(self):
        expected = subject.entry(self.base, self.fixture)
        self.assertEqual(expected, next(e for e in self.base['entries'] if e['id'] == subject.ENTRY))
        before = dict(self.base, entries=[e for e in self.base['entries'] if e['id'] != subject.ENTRY])
        added = set(expected['unsupportedSurfaceKeys'])
        real_controls = subject.control.load(subject.ROOT / 'tools/typing_experiments/control-ledger.json')
        control_surfaces = {key for entry in real_controls['entries'] for key in entry.get('surfaceKeys', [])}
        form = next(form for _, form in self.fixture['pairs']
                    if subject.control.surface_key('en', form) in added - control_surfaces)
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                        sentenceHash='f'*64, prefix='a ', typed=form, expectedSpelling=form)
        self.assertEqual(0, preflight([row], 'spelling', before, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertEqual(1, preflight([row], 'spelling', self.base, controls(), 'new-families')['unsupportedTargetOverlaps'])
        self.assertEqual(0, preflight([row], 'spelling', before, real_controls, 'new-families')['controlOverlaps']['surface'])
        self.assertFalse(self.base['coverage']['complete'])

    def test_parent_fixture_and_source_drift_fail_closed(self):
        altered = dict(self.base, entries=list(self.base['entries']))
        index = next(i for i, e in enumerate(altered['entries']) if e['id'] == subject.PARENT)
        altered['entries'][index] = dict(altered['entries'][index], notes='changed')
        with self.assertRaisesRegex(ValueError, 'EN_UNIMORPH_BASELINE'):
            subject.entry(altered, self.fixture)
        with self.assertRaisesRegex(ValueError, 'EN_UNIMORPH_FIXTURE'):
            subject.entry(self.base, dict(self.fixture, pairs=self.fixture['pairs'][:-1]))
        with self.assertRaisesRegex(ValueError, 'EN_UNIMORPH_SOURCE_IDENTITY'):
            subject.capture(b'bad source', self.base, self.fixture)


if __name__ == '__main__':
    unittest.main()
