import shutil
import tempfile
import unittest
from pathlib import Path

import check_learning_disclosures as gate


class LearningDisclosureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = {'docs/USER_GUIDE.ru.md', 'PRIVACY.md'}
        paths.update(gate.BASE + path for path, _ in gate.CONTRACTS.values())
        paths.update(gate.BASE + path for path, _ in gate.LIMITS)
        paths.update('app/src/main/res/' + locale + '/' + file
                     for locale, resources in gate.CONSENT.items() for file, _ in resources)
        for name in paths:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(gate.ROOT / name, destination)

    def change(self, name, old, new):
        p = self.root / name
        text = p.read_text()
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1))

    def test_current_contract(self):
        self.assertEqual([], gate.inspect(self.root))

    def test_computed_serialized_value_cannot_bypass_record_inventory(self):
        self.change(gate.BASE + 'personalization/PersonalTypingCodec.kt',
                    'out.writeInt(MAGIC)', 'out.writeInt(MAGIC); out.writeLong(0L)')
        self.assertIn('UNREVIEWED_SERIALIZED_WRITER personalization/PersonalTypingCodec.kt/encode',
                      gate.inspect(self.root))

    def test_added_record_field_needs_review_and_disclosure(self):
        self.change(gate.BASE + 'learning/LearningModel.kt',
                    'data class LearningEvidence(', 'data class LearningEvidence(val extra: String,')
        errors = gate.inspect(self.root)
        self.assertIn('UNREVIEWED_PERSISTED_FIELDS LearningEvidence', errors)
        self.assertIn('GUIDE_PERSISTED_FIELDS LearningEvidence', errors)

    def test_field_mentioned_in_another_row_cannot_cover_missing_disclosure(self):
        p = self.root / 'docs/USER_GUIDE.ru.md'
        rows = p.read_text().splitlines()
        p.write_text('\n'.join(line.replace('`language`', 'язык') if line.startswith('| `PersonalWord`')
                               else line for line in rows) + '\n')
        self.assertIn('GUIDE_PERSISTED_FIELDS PersonalWord', gate.inspect(self.root))

    def test_increased_storage_limit_cannot_use_stale_copy(self):
        self.change(gate.BASE + 'learning/LearningCodec.kt', 'MAX_BYTES = 512 * 1024', 'MAX_BYTES = 1024 * 1024')
        self.assertIn('UNDISCLOSED_STORAGE_LIMIT MAX_BYTES', gate.inspect(self.root))

    def test_numeric_prefix_cannot_hide_larger_underscored_limit(self):
        self.change(gate.BASE + 'learning/LearningModel.kt', 'MAX_EVIDENCE = 512', 'MAX_EVIDENCE = 512_000')
        self.assertIn('UNDISCLOSED_STORAGE_LIMIT MAX_EVIDENCE', gate.inspect(self.root))

    def test_phrase_disclosure_must_exist_in_each_consent_locale(self):
        for locale, word in [('values', 'phrase prefixes/continuations'), ('values-ru', 'начала и продолжения фраз')]:
            with self.subTest(locale=locale):
                p = self.root / 'app/src/main/res' / locale / 'strings.xml'
                original = p.read_text()
                p.write_text(original.replace(word, 'other data'))
                self.assertIn('CONSENT_DISCLOSURE ' + locale + '/settings_personal_learning_summary', gate.inspect(self.root))
                p.write_text(original)

    def test_hash_only_recording_disclosure_cannot_disappear(self):
        self.change('app/src/main/res/values/typing_controls_strings.xml',
                    'also turn off typo-pattern learning', 'turn off example collection')
        self.assertIn('CONSENT_DISCLOSURE values/settings_collect_examples_summary', gate.inspect(self.root))

    def test_pattern_only_switch_needs_its_own_hash_disclosure(self):
        self.change('app/src/main/res/values/typing_controls_strings.xml',
                    'raw-example collection off', 'raw-example collection on')
        self.assertIn('CONSENT_DISCLOSURE values/settings_typo_patterns_summary', gate.inspect(self.root))

    def test_ordinary_typing_phrase_collection_is_explicit(self):
        self.change('app/src/main/res/values/strings.xml',
                    'including words you did not correct', 'after corrections')
        self.assertIn('CONSENT_DISCLOSURE values/settings_personal_learning_summary', gate.inspect(self.root))

    def test_separate_reset_is_required(self):
        self.change('PRIVACY.md', 'Learning lab → Reset examples and patterns', 'Reset everything')
        self.assertIn('SEPARATE_RESET_DISCLOSURE', gate.inspect(self.root))

    def test_invalid_source_fails_closed(self):
        (self.root / 'app/src/main/res/values/strings.xml').write_text('<invalid')
        self.assertIn('UNREADABLE_OR_UNREVIEWED_DISCLOSURE_SOURCE', gate.inspect(self.root))


if __name__ == '__main__':
    unittest.main()
