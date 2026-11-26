import hashlib
import unittest

import import_word_epoch_segments as subject


class SelectorSegmentsTest(unittest.TestCase):
    def test_matches_original_selector_and_preserves_whole_segment(self):
        sentence = 'раз два три длинное окончание.'
        prefix, word, article = 'раз два три ', 'длинное', '123'
        context = hashlib.sha256((prefix + '\0' + word).encode()).hexdigest()
        identity = 'wordrank-' + hashlib.sha256(
            f"{subject.HISTORICAL_SEEDS['wordrank']}:{article}:{context}".encode()).hexdigest()[:24]
        row = {'id': identity, 'articleId': article, 'prefix': prefix, 'expectedSpelling': word}
        result = subject.capture(article, sentence + ' Следующее.', [row])
        digest = hashlib.sha256(sentence.encode()).hexdigest()
        expected = subject._digest('sentence', ['tatoeba-full-sentence-normalized-v1', digest])
        self.assertEqual({expected}, result[identity])
        tatoeba = {'sourceRepository': 'tatoeba', 'article': 'tatoeba:1', 'language': 'ru', 'sentenceHash': digest}
        self.assertEqual(result[identity], subject.windows.keys_for([tatoeba], 'sentence'))
        with self.assertRaisesRegex(ValueError, 'SEGMENT_CAPTURE_DIVERGENCE'):
            subject.capture(article, sentence, [row | {'expectedSpelling': 'ошибка'}])
        with self.assertRaisesRegex(ValueError, 'SEGMENT_CAPTURE_MISSING'):
            subject.capture(article, 'совсем другая фраза', [row])
