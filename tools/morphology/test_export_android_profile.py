import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from export_android_profile import MAX_PHRASES, PROFILE_HEADER, export_profile, main
from export_dictionary import write_index
from telegram_style import ImportFailure, build_model


class AndroidProfileExportTest(unittest.TestCase):
    def test_dictionary_and_repeated_support_are_required(self):
        payload = build_model(['see you soon', 'see you soon today', 'please see you soon',
                               'see yuo soon', 'please see yuo soon', 'see yuo soon today'])
        words = {'see', 'you', 'soon', 'today', 'please'}
        profile = export_profile(payload, 'en', words.__contains__).decode()
        self.assertTrue(profile.startswith(PROFILE_HEADER + '\n'))
        self.assertIn('ENGLISH\tsee you\tsoon\t3\n', profile)
        self.assertIn('ENGLISH\tsee\tyou soon\t3\n', profile)
        self.assertNotIn('yuo', profile)
        self.assertNotIn('today', profile)
        self.assertNotIn('trainingSha256', profile)
        self.assertNotIn('messageHashes', profile)

    def test_raw_unigram_frequency_cannot_export_spelling(self):
        payload = build_model(['misspelled', 'misspelled!'])
        payload['unigrams']['misspelled'] = 255
        self.assertEqual((PROFILE_HEADER + '\n').encode(), export_profile(payload, 'en', lambda _: True))

    def test_output_is_bounded_deterministic_and_support_saturates(self):
        payload = build_model([])
        def word(index):
            return 'word' + chr(97 + index // 26) + chr(97 + index % 26)
        payload['bigrams'] = {f'{word(index)} next': 1000 for index in range(600)}
        payload['trigrams'] = {f'{word(index)} next word': 1000 for index in range(600)}
        result = export_profile(payload, 'en', lambda _: True)
        self.assertEqual(MAX_PHRASES + 1, result.count(b'\n'))
        self.assertEqual(result, export_profile(payload, 'en', lambda _: True))
        self.assertTrue(all(line.endswith(b'\t255') for line in result.splitlines()[1:]))

    def test_invalid_options_or_model_rejected(self):
        for language, minimum in [('de', 3), ('en', 2), ('en', True)]:
            with self.assertRaises(ImportFailure):
                export_profile(build_model([]), language, lambda _: True, min_support=minimum)
        with self.assertRaises(ImportFailure):
            export_profile({'schemaVersion': 99}, 'en', lambda _: True)

    def test_cli_writes_private_profile_from_synthetic_model_and_public_format(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dictionary = root / 'test.morph'
            words = sorted(['добрый', 'день', 'вам'], key=lambda word: word.encode('utf-8'))
            write_index([(word, index) for index, word in enumerate(words)], dictionary)
            model = root / 'model.json'
            payload = build_model(['добрый день', 'вам добрый день', 'добрый день вам'])
            model.write_text(json.dumps(payload), encoding='utf-8')
            output = root / 'profile.runephrases'
            arguments = ['--model', str(model), '--dictionary', str(dictionary), '--language', 'ru', '--output', str(output)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, main(arguments))
                self.assertEqual(1, main(arguments))  # Existing output is never overwritten.
            self.assertEqual(0o600, output.stat().st_mode & 0o777)
            self.assertIn('RUSSIAN\tдобрый\tдень\t3', output.read_text())

    def test_boundaries_from_host_model_remain_boundaries(self):
        model = build_model(['see. you soon', 'see! you soon', 'see\nyou soon'])
        profile = export_profile(model, 'en', lambda _: True).decode()
        self.assertNotIn('\tsee\tyou', profile)
        self.assertNotIn('\tsee you\tsoon', profile)


if __name__ == '__main__':
    unittest.main()
