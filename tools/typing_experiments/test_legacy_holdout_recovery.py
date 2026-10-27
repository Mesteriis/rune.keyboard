from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import recover_legacy_holdout as recovery_module
from recover_legacy_holdout import LegacySelections, MIXED_GUARD_SHA, load_generator
from right_context_sentence_audit import _source_hash

OLD = '2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65'


def selected(generator, text, word='целевое'):
    item = generator.spelling_candidates(text, 'ru', {word}, set(), 7)[0]
    return dict(id='public-case', template='holdout-wikipedia-' + item['selectionHash'],
                prefix=item['prefix'], family=item['family'], expectedSpelling=item['word'],
                cohort='typo', typed='ошибка')


class LegacyRecoveryTest(unittest.TestCase):
    def test_both_original_generator_versions_load_with_exact_hashes(self):
        for digest in (OLD, MIXED_GUARD_SHA):
            generator = load_generator(digest)
            text = 'Один два три четыре целевое слово.'
            row = selected(generator, text)
            records = LegacySelections([row], generator, 7, digest).recover_article('123', text)
            self.assertEqual(1, len(records))
            self.assertEqual(('public-case', '123'), (records[0]['id'], records[0]['article']))
            self.assertEqual(_source_hash(row['prefix'], 'целевое', ' слово.'), records[0]['contextHash'])

    def test_all_matching_articles_and_occurrences_are_retained(self):
        generator = load_generator(OLD)
        text = 'Один два три четыре целевое слово.'
        recovery = LegacySelections([selected(generator, text)], generator, 7, OLD)
        records = recovery.recover_article('1', text) + recovery.recover_article('2', text)
        self.assertEqual({'1', '2'}, {r['article'] for r in records})
        doubled = recovery.recover_article('3', text + ' ' + text)
        self.assertEqual(2, len(doubled))
        # Short occurrences can project to the same whole-article window;
        # their source occurrences must still not be silently dropped.
        self.assertTrue(all(r['article'] == '3' for r in doubled))

    def test_original_mixed_script_eligibility_is_not_rewritten(self):
        old, new = load_generator(OLD), load_generator(MIXED_GUARD_SHA)
        text = 'Один два три четыре Cцелевое слово.'
        row = selected(old, text)
        self.assertEqual(1, len(LegacySelections([row], old, 7, OLD).recover_article('1', text)))
        self.assertEqual([], LegacySelections([row], new, 7, MIXED_GUARD_SHA).recover_article('1', text))

    def test_nfc_and_long_utf8_prefixes_preserve_reference_selection(self):
        generator = load_generator(OLD)
        text = ('Подготовка ' * 70) + 'е\u0308лка появилась.'
        row = selected(generator, text, 'ёлка')
        records = LegacySelections([row], generator, 7, OLD).recover_article('4', text)
        self.assertEqual(1, len(records))
        self.assertLessEqual(len(row['prefix'].encode()), 256)

    def test_changed_selection_or_unknown_source_cannot_be_loaded(self):
        generator = load_generator(OLD)
        row = selected(generator, 'Один два три четыре целевое слово.')
        for changed in (row | dict(template='wrong'), row | dict(prefix='другое'),
                        row | dict(family='другая')):
            with self.assertRaisesRegex(ValueError, 'RECOVERY_SELECTION_IDENTITY'):
                LegacySelections([changed], generator, 7, OLD)
        with self.assertRaisesRegex(ValueError, 'NOT_ARCHIVED'):
            load_generator('f' * 64)

    def test_correct_control_target_is_recovered_without_a_new_label(self):
        generator = load_generator(OLD)
        text = 'Один два три четыре целевое слово.'
        row = selected(generator, text)
        row.pop('expectedSpelling'); row.update(cohort='correct', typed='целевое')
        self.assertEqual(1, len(LegacySelections([row], generator, 7, OLD).recover_article('5', text)))

    def test_changed_archived_byte_is_rejected_before_loading(self):
        original = Path(recovery_module.__file__).with_name('frozen_sources')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(original, root / 'frozen_sources')
            path = next((root / 'frozen_sources').glob('qualification_v2_2cb*.py'))
            path.write_bytes(path.read_bytes() + b'\n')
            with patch.object(recovery_module, '__file__', str(root / 'recover.py')):
                with self.assertRaisesRegex(ValueError, 'GENERATOR_IDENTITY'):
                    load_generator(OLD)


if __name__ == '__main__':
    unittest.main()
