import re
import shutil
import tempfile
import unittest
from pathlib import Path

import check_guide_facts as gate


class GuideFactsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = set(gate.DOCS) | {gate.REGISTRY, gate.MODELS, gate.FROZEN, gate.ENCODING,
                                  'docs/acceptance/README.md'}
        names.update(gate.ASSETS + n for n in ['ru-ranker.bin', 'ru-ranking-context.bin', 'ru-context.bin'])
        for name in names:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(gate.ROOT / name, p)

    def change(self, name, old, new):
        p = self.root / name
        text = p.read_text()
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1))

    def test_current_facts(self):
        self.assertEqual([], gate.inspect(self.root))

    def test_old_feature_count_is_rejected(self):
        p = self.root / gate.DOCS[0]
        text, count = re.subn(r'(все\s+\*{0,2})18(\*{0,2}\s+дополнитель)',
                              r'\g<1>17\2', p.read_text(), count=1)
        self.assertEqual(1, count)
        p.write_text(text)
        self.assertIn('GUIDE_ADDITIONAL_FEATURE_COUNT', gate.inspect(self.root))

    def test_added_feature_requires_doc_count_update(self):
        self.change(gate.REGISTRY, 'val entries: List<AdditionalFeature> = listOf(',
                    'val entries: List<AdditionalFeature> = listOf(AdditionalFeature(SettingsCodec.KEY_NEW,')
        self.assertIn('GUIDE_ADDITIONAL_FEATURE_COUNT', gate.inspect(self.root))

    def test_new_writer_schema_cannot_use_old_doc_marker(self):
        self.change(gate.ENCODING, '\\"schema\\":9', '\\"schema\\":10')
        errors = gate.inspect(self.root)
        self.assertIn('CURRENT_DIAGNOSTICS_SCHEMA docs/USER_GUIDE.ru.md', errors)
        self.assertIn('CURRENT_DIAGNOSTICS_SCHEMA docs/DEBUG_DIAGNOSTICS.md', errors)

    def test_analyzer_compatibility_range_must_match_current_writer(self):
        self.change(gate.DOCS[0], 'schema 1–9', 'schema 1–8')
        self.assertIn('GUIDE_DIAGNOSTICS_COMPATIBILITY', gate.inspect(self.root))

    def test_ranking_and_tap_windows_cannot_be_swapped(self):
        self.change(gate.DOCS[0], '`ru-ranking-context.bin` | 320216 | 48',
                    '`ru-ranking-context.bin` | 320216 | 24')
        self.assertIn('GUIDE_EXPERIMENT_ASSET_FACT ru-ranking-context.bin', gate.inspect(self.root))

    def test_wrong_binary_size_is_rejected(self):
        self.change(gate.DOCS[0], '`ru-ranker.bin` | 22036', '`ru-ranker.bin` | 7756')
        self.assertIn('GUIDE_EXPERIMENT_ASSET_FACT ru-ranker.bin', gate.inspect(self.root))

    def test_source_declared_size_does_not_mask_changed_file(self):
        p = self.root / (gate.ASSETS + 'ru-ranker.bin')
        p.write_bytes(p.read_bytes() + b'x')
        self.assertIn('GUIDE_EXPERIMENT_ACTUAL_BYTES ru-ranker.bin', gate.inspect(self.root))

    def test_index_requires_current_review_navigation(self):
        self.change('docs/acceptance/README.md', '../plans/2026-10-27-review-completion.md',
                    'historical-only.md')
        self.assertIn('ACCEPTANCE_INDEX_CURRENT_REVIEW', gate.inspect(self.root))

    def test_missing_source_fails_closed(self):
        (self.root / gate.MODELS).unlink()
        self.assertIn('UNREADABLE_OR_UNREVIEWED_GUIDE_SOURCE', gate.inspect(self.root))


if __name__ == '__main__':
    unittest.main()
