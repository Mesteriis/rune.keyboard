import json
import unittest

import import_spanish_unimorph_control_surfaces as subject
from public_corpus_preparation_v1 import preflight
from test_holdout_ledger import ledger
from test_public_corpus_preparation_v1 import candidate


class SpanishUnimorphControlSurfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(subject.LEDGER.read_bytes())
        cls.fixture = json.loads(subject.FIXTURE.read_bytes())

    def test_projection_keeps_ambiguous_heads_and_accented_forms(self):
        targets = {subject.control.surface_key('es', 'casas')}
        raw = ('casa\tcasas\tN;PL\ncasar\tcasas\tV;PRS\n'
               'casar\tcasó\tV;PST\notro\totros\tN;PL\n').encode()
        rows, pairs, titles = subject.project(raw, targets)
        self.assertEqual(4, rows)
        self.assertEqual([('casa', 'casas'), ('casar', 'casas'), ('casar', 'casó')], pairs)
        self.assertEqual([('casa', 'casa'), ('casar', 'casar')], titles)
        with self.assertRaisesRegex(ValueError, 'ES_UNIMORPH_SOURCE_ROW'):
            subject.project(b'invalid\n', targets)

    def test_new_form_blocks_real_preflight_without_clearing_coverage(self):
        expected = subject.entry(self.base, self.fixture)
        self.assertEqual(expected, next(e for e in self.base['entries'] if e['id'] == subject.ENTRY))
        before = dict(self.base, entries=[e for e in self.base['entries'] if e['id'] != subject.ENTRY])
        added = set(expected['surfaceKeys'])
        form = next(form for _, form in self.fixture['pairs']
                    if subject.control.surface_key('es', form) in added)
        row = candidate(language='es', prefix='contexto ', typed=form, expectedSpelling=form)
        for profile in ('new-sentences', 'new-families'):
            old = preflight([row], 'spelling', ledger(False), before, profile)
            new = preflight([row], 'spelling', ledger(False), self.base, profile)
            self.assertEqual(0, old['controlOverlaps']['surface'])
            self.assertGreater(new['controlOverlaps']['surface'], 0)
            self.assertEqual('BLOCKED_OVERLAP', new['status'])
        self.assertFalse(self.base['coverageComplete'])

    def test_changed_parent_fixture_and_source_fail_closed(self):
        altered = dict(self.base, entries=list(self.base['entries']))
        index = next(i for i, e in enumerate(altered['entries']) if e['id'] == subject.PARENTS[0])
        altered['entries'][index] = dict(altered['entries'][index], notes='changed')
        with self.assertRaisesRegex(ValueError, 'ES_UNIMORPH_BASELINE'):
            subject.entry(altered, self.fixture)
        with self.assertRaisesRegex(ValueError, 'ES_UNIMORPH_FIXTURE'):
            subject.entry(self.base, dict(self.fixture, pairs=self.fixture['pairs'][:-1]))
        with self.assertRaisesRegex(ValueError, 'ES_UNIMORPH_SOURCE_IDENTITY'):
            subject.capture(b'bad source', self.base, self.fixture)


if __name__ == '__main__':
    unittest.main()
