import json
from pathlib import Path
import tempfile
from unittest import mock
import unittest
import screen_rlc_learner as subject


class LearnerScreenTest(unittest.TestCase):
    def setUp(self):
        self.docs = [{'id': 'd1'}, {'id': 'd2'}]
        self.sentences = [
            {'id': 's1', 'document_id': 'd1', 'status': '', 'text': 'это дом', 'corrected': 'это дом'},
            {'id': 's2', 'document_id': 'd1', 'status': '', 'text': 'нет', 'corrected': 'нет'},
            {'id': 's3', 'document_id': 'd2', 'status': 'needs correction', 'text': 'дом', 'corrected': 'дом'},
            {'id': 's4', 'document_id': 'd2', 'status': '', 'text': 'ошбка', 'corrected': 'ошибка'},
        ]
        self.annotations = [{'sentence_id': 's2', 'annotation_source': 'manual'}]

    def test_aggregate_does_not_export_words_or_treat_it_as_qualification(self):
        result = subject.analyze(self.docs, self.sentences, self.annotations)
        self.assertEqual(1, result['counts']['unchangedWithoutAnnotations'])
        self.assertEqual(1, result['counts']['unchangedWithAnnotations'])
        self.assertEqual(2, result['counts']['shortLowercaseTokens'])
        self.assertEqual(1, result['candidateDocuments'])
        self.assertFalse(result['qualified'])
        self.assertEqual(0, result['modelCalls'])
        self.assertNotIn('это', json.dumps(result, ensure_ascii=False))

    def test_orphan_annotations_are_reported_without_certification(self):
        result = subject.analyze(self.docs, self.sentences, self.annotations +
                                 [{'sentence_id': 'missing', 'annotation_source': 'rlc-errant'}])
        self.assertEqual(1, result['orphanAnnotations'])
        self.assertEqual(1, result['orphanSentenceReferences'])
        self.assertEqual({'rlc-errant': 1}, result['orphanAnnotationSources'])
        self.assertFalse(result['qualified'])

    def test_unknown_source_bytes_are_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / 'source'
            source.mkdir()
            for name in subject.PINS:
                (source / name).write_text('unexpected')
            output = root / 'build' / 'report'
            with mock.patch.object(subject, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'RLC_SOURCE_IDENTITY'):
                    subject.run(source, output)
            self.assertFalse(output.exists())

    def test_ambiguous_and_broken_references_fail_closed(self):
        for docs, sentences, annotations in [
            (self.docs + [self.docs[0]], self.sentences, self.annotations),
            (self.docs, self.sentences + [self.sentences[0]], self.annotations),
            (self.docs[:1], self.sentences, self.annotations),
        ]:
            with self.subTest(docs=len(docs), sentences=len(sentences)), self.assertRaises(ValueError):
                subject.analyze(docs, sentences, annotations)


if __name__ == '__main__':
    unittest.main()
