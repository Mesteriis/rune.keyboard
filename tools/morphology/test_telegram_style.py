from contextlib import contextmanager
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import telegram_style as style


@contextmanager
def private_repo():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory).resolve()
        subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
        (root / '.gitignore').write_text('**/build/\n')
        yield str(root)


def message(text, **extra):
    return {'id': 1, 'type': 'message', 'from_id': 'user123', 'text': text, **extra}


def chat(chat_id, messages, **extra):
    return {'id': chat_id, 'type': 'personal_chat', 'messages': messages, **extra}


class TelegramStyleTest(unittest.TestCase):
    def test_only_authored_personal_text(self):
        payload = {'chats': {'list': [
            chat(1, [message('Моя фраза!'), message('Чужая', from_id='user456'),
                     message('Переслано', forwarded_from='someone'),
                     message('Событие', type='service'), message('Бот', via_bot='bot')]),
            chat(2, [message('В группе')], type='private_group')]}}
        self.assertEqual([text for _, text in style.parse_export(payload, '123')], ['Моя фраза!'])

    def test_rich_text_preserves_punctuation(self):
        payload = chat(1, [message(['Привет, ', {'type': 'bold', 'text': 'мир'}, '!'])])
        self.assertEqual(style.parse_export(payload, 'user123')[0][1], 'Привет, мир!')

    def test_contact_code_and_unknown_entities_are_excluded(self):
        unsafe = ['https://example.test', 'user@example.test', '@somebody',
                  '+7 (999) 123-45-67', 'call_me_now', 'someFunction()', '`код`',
                  'ftp://host', 'example.xyz', '/Users/private/file', 'user123', 'мой_код']
        rows = [message(text) for text in unsafe]
        rows += [message([{'type': kind, 'text': 'скрыто'}])
                 for kind in ('link', 'text_link', 'code', 'pre', 'phone', 'mention', 'unknown')]
        rows.append(message('видимо безопасно', text_entities=[{'type': 'text_link', 'text': 'ссылка'}]))
        self.assertEqual(style.parse_export(chat(1, rows), '123'), [])

    def test_malformed_envelopes_and_identity_fail_closed(self):
        for payload in ([], {}, {'chats': []}, chat(1, 'text'), chat(None, [])):
            with self.subTest(payload=payload), self.assertRaises(style.ImportFailure):
                style.parse_export(payload, '123')
        for identity in ('', 'name', '-1', True):
            with self.subTest(identity=identity), self.assertRaises(style.ImportFailure):
                style.parse_export(chat(1, []), identity)

    def test_empty_and_unsupported_text_is_not_imported(self):
        rows = [message(''), message({'text': 'bad'}), message([{'type': 'bold'}]),
                message('text', from_id=None), message('text\x00'),
                message([{'type': [], 'text': 'invalid'}]),
                message('text', text_entities=[{'type': {}, 'text': 'invalid'}])]
        self.assertEqual(style.parse_export(chat(1, rows), '123'), [])

    def test_model_context_is_bounded_and_has_no_message_transitions(self):
        model = style.build_model(['я люблю кофе', 'завтра будет тепло'])
        scorer = style.StyleModel(model)
        self.assertEqual(scorer.bonus('', 'кофе'), 0)
        self.assertEqual(scorer.bonus('несуществующий', 'кофе'), 0)
        self.assertEqual(scorer.bonus('кофе', 'завтра'), 0)
        self.assertGreater(scorer.bonus('Я ЛЮБЛЮ', 'КОФЕ'), 0)
        self.assertLessEqual(scorer.bonus('я люблю', 'кофе'), 1)
        self.assertNotIn('кофе завтра', model['bigrams'])
        self.assertEqual(style.build_model(['а б', 'а б']), style.build_model(['а б']))
        self.assertEqual(style.build_model(['а б', 'в г']), style.build_model(['в г', 'а б']))

    def test_model_rejects_nonfinite_or_invalid_counts(self):
        for count in (float('nan'), float('inf'), -1, True, 1.5, 10**30):
            payload = style.build_model(['я люблю кофе'])
            payload['bigrams']['я люблю'] = count
            with self.subTest(count=count), self.assertRaises(style.ImportFailure):
                style.StyleModel(payload)

    def test_model_does_not_cross_punctuation_or_newlines(self):
        for boundary in ('. ', '! ', '? ', ', ', '\n', ': ', ' — '):
            model = style.build_model(['кот' + boundary + 'дом'])
            self.assertNotIn('кот дом', model['bigrams'])
            scorer = style.StyleModel(style.build_model(['кот дом']))
            self.assertEqual(scorer.bonus('кот' + boundary, 'дом'), 0)
            self.assertGreater(scorer.bonus('здесь. кот', 'дом'), 0)
        self.assertIn('straße', style.build_model(['Straße'])['unigrams'])

    def test_model_size_and_total_entries_are_bounded(self):
        model = style.build_model(['первый второй третий'])
        with patch.object(style, 'MAX_NGRAM_ENTRIES', 2):
            with self.assertRaises(style.ImportFailure):
                style.build_model(['первый второй третий'])
            with self.assertRaises(style.ImportFailure):
                style.StyleModel(model)
        with patch.object(style, 'MAX_FILE_BYTES', 10):
            with self.assertRaises(style.ImportFailure):
                style.build_model(['фраза'])
            with self.assertRaises(style.ImportFailure):
                style.StyleModel(model)

    def test_model_rejects_bad_schema_hashes_and_keys(self):
        for key, value in (('schemaVersion', True), ('trainingSha256', 'invalid'),
                           ('messageHashes', [None]), ('bigrams', {'wrong': 1}),
                           ('trigrams', {'A b c': 1}), ('unigrams', {'foo_bar': 1})):
            payload = style.build_model(['я люблю кофе'])
            payload[key] = value
            with self.subTest(key=key), self.assertRaises(style.ImportFailure):
                style.StyleModel(payload)

    def test_identity_is_explicit_even_with_a_majority_sender(self):
        payload = chat(1, [message('incoming', from_id='user456') for _ in range(5)])
        self.assertEqual(style.parse_export(payload, '123'), [])

    def test_import_deduplicates_before_disjoint_split_and_keeps_outputs_private(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            payload = {'chats': {'list': [chat(1, [message('Общее'), message('Первый чат')]),
                                        chat(2, [message('Общее'), message('Второй чат')])]}}
            source.write_text(json.dumps(payload), encoding='utf-8')
            duplicate = root / 'duplicate.json'
            duplicate.write_bytes(source.read_bytes())
            output = root / 'build' / 'private' / 'run'
            report = style.import_exports([source, duplicate], '123', output)
            train = [json.loads(line)['text'] for line in (output / 'train.jsonl').read_text().splitlines()]
            validation = [json.loads(line)['text'] for line in (output / 'validation.jsonl').read_text().splitlines()]
            self.assertEqual(len(train) + len(validation), 3)
            self.assertFalse(set(train) & set(validation))
            self.assertTrue(report['validationEligible'])
            self.assertEqual(report['uniqueExports'], 1)
            receipt = json.loads((output / 'receipt.json').read_text())
            self.assertFalse(set(receipt['trainChatHashes']) & set(receipt['validationChatHashes']))
            self.assertEqual(style.build_model(train), json.loads((output / 'model.json').read_text()))
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o700)
            for file in output.iterdir():
                self.assertEqual(os.stat(file).st_mode & 0o777, 0o600)
            self.assertNotIn('Общее', json.dumps(receipt, ensure_ascii=False))
            self.assertNotIn('user123', json.dumps(receipt))
            second = root / 'build' / 'private' / 'other'
            style.import_exports([duplicate, source], 'user123', second)
            for name in ('train.jsonl', 'validation.jsonl', 'model.json', 'receipt.json'):
                self.assertEqual((output / name).read_bytes(), (second / name).read_bytes())

    def test_dedup_normalizes_case_and_whitespace_across_chats(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps({'chats': {'list': [
                chat(1, [message('ОДНА  ФРАЗА')]),
                chat(2, [message('одна фраза')])
            ]}}))
            report = style.import_exports([source], 123, root / 'build' / 'run')
            self.assertEqual(report['uniqueMessages'], 1)
            self.assertFalse(report['validationEligible'])

    def test_one_chat_is_training_only_and_not_validation_eligible(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(chat(1, [message('Моя фраза')])))
            output = root / 'build' / 'run'
            report = style.import_exports([source], '123', output)
            self.assertFalse(report['validationEligible'])
            self.assertEqual((output / 'validation.jsonl').read_text(), '')

    def test_split_preserves_majority_training_coverage(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps({'chats': {'list': [
                chat(1, [message('Большой чат ' + word) for word in ('один', 'два', 'три', 'четыре')]),
                chat(2, [message('Маленький чат')])
            ]}}))
            report = style.import_exports([source], 123, root / 'build' / 'run')
            self.assertEqual(report['trainMessages'], 4)
            self.assertEqual(report['validationMessages'], 1)

    def test_output_must_be_fresh_under_build_and_not_a_symlink(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(chat(1, [message('Моя фраза')])))
            for output in (root / 'unsafe', root / 'build'):
                with self.assertRaises(style.ImportFailure):
                    style.import_exports([source], '123', output)
            existing = root / 'build' / 'existing'
            existing.mkdir(parents=True)
            with self.assertRaises(style.ImportFailure):
                style.import_exports([source], '123', existing)
            linked = root / 'build' / 'link'
            linked.symlink_to(root, target_is_directory=True)
            with self.assertRaises(style.ImportFailure):
                style.import_exports([source], '123', linked / 'new')

    def test_build_must_actually_be_ignored(self):
        with private_repo() as directory:
            root = Path(directory)
            (root / '.gitignore').write_text('')
            with self.assertRaises(style.ImportFailure):
                style.import_exports([], '123', root / 'build' / 'run')

    def test_bounded_input_and_nonregular_input(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(chat(1, [message('Моя фраза')])))
            with patch.object(style, 'MAX_FILE_BYTES', 3), self.assertRaises(style.ImportFailure):
                style.import_exports([source], '123', root / 'build' / 'large')
            link = root / 'link.json'
            link.symlink_to(source)
            for path in (link, root):
                with self.subTest(path=path.name), self.assertRaises(style.ImportFailure):
                    style.import_exports([path], '123', root / 'build' / 'bad')

    def test_empty_selection_and_invalid_split_create_no_output(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'input.json'
            source.write_text(json.dumps(chat(1, [message('Чужое', from_id='user456')])))
            for fraction in (0, 0.75, float('nan'), float('inf'), True):
                with self.subTest(fraction=fraction), self.assertRaises(style.ImportFailure):
                    style.import_exports([source], '123', root / 'build' / 'bad', fraction)
            with self.assertRaises(style.ImportFailure):
                style.import_exports([source], '123', root / 'build' / 'empty')
            self.assertFalse((root / 'build').exists())

    def test_errors_never_include_message_text(self):
        with private_repo() as directory:
            root = Path(directory)
            source = root / 'secret_filename.json'
            source.write_text('{"secret text": broken')
            with self.assertRaises(style.ImportFailure) as caught:
                style.import_exports([source], '123', root / 'build' / 'run')
            self.assertNotIn('secret', str(caught.exception))
            self.assertFalse((root / 'build' / 'run').exists())

    def test_cli_argument_errors_do_not_echo_private_values(self):
        error = io.StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as caught:
            style.main(['--input', 'secret_filename', '--self-id', 'secret_identity',
                        '--output', 'secret_directory', '--validation-fraction', 'secret_value'])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(error.getvalue(), 'INVALID_ARGUMENTS\n')


if __name__ == '__main__':
    unittest.main()
