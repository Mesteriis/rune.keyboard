import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluate import metrics, validate_rows, verify_observations, verify_export, final_proposal, sha
from types import SimpleNamespace


class EvaluationTest(unittest.TestCase):
    def test_counts_false_changes_and_abstentions(self):
        rows = [dict(id='1', typed='котт', expectedSpelling='кот', cohort='typo', noAuto=False),
                dict(id='2', typed='дом', cohort='correct', noAuto=False),
                dict(id='3', typed='URL', cohort='protected', noAuto=True),
                dict(id='4', typed='слишков', expectedSpelling='слишком', cohort='typo', noAuto=False)]
        r = metrics(rows, ['кот', 'том', None, None])
        self.assertEqual((r['changes'],r['correctChanges'],r['falseChanges'],r['abstentions']), (2,1,1,2))
        self.assertEqual(r['negativeFalseChangeRate'], 0.5)
        self.assertEqual(r['typoRecall'], 0.5)

    def test_empty_is_not_perfect_quality(self):
        self.assertIsNone(metrics([], [])['precision'])

    def test_metrics_rejects_truncated_predictions(self):
        with self.assertRaises(ValueError): metrics([{}], [])

    def test_rows_require_unique_id_and_valid_split(self):
        row = dict(id='1', typed='слово', prefix='', split='holdout', language='ru', cohort='correct', noAuto=False)
        validate_rows([row])
        with self.assertRaises(ValueError): validate_rows([row,row])
        with self.assertRaises(ValueError): validate_rows([dict(row,split='train')])

    def test_observations_cannot_reorder_or_change_original(self):
        rows=[dict(typed='кот')]
        ok=[dict(index=0,generation=dict(original='кот'),baseline=None)]
        verify_observations(rows,ok)
        with self.assertRaises(ValueError): verify_observations(rows,[dict(ok[0],index=1)])
        with self.assertRaises(ValueError): verify_observations(rows,[dict(ok[0],generation=dict(original='кит'))])

    def test_copied_export_cannot_validate_against_original_inputs(self):
        with TemporaryDirectory() as temp:
            original = Path(temp).resolve() / 'original'; copied = Path(temp).resolve() / 'copied'
            original.mkdir(); copied.mkdir()
            names = ('rows.jsonl','observations.jsonl','inputs.tsv','source-freeze.json')
            for name in names:
                (original / name).write_text('{}')
                (copied / name).write_text('{}')
            files = {str(original / name):sha(original / name) for name in names}
            receipt = dict(schemaVersion=1,scope='host-production-candidate-proposals',files=files,sources=files)
            verify_export(original, receipt)
            with self.assertRaisesRegex(ValueError,'CONSUMED_INPUT_NOT_BOUND'):
                verify_export(copied, receipt)

    def test_keep_original_is_not_replaced_by_baseline(self):
        self.assertEqual(final_proposal(SimpleNamespace(word=None,reason='insufficient_margin'),'кот'),(None,False))
        self.assertEqual(final_proposal(SimpleNamespace(word=None,reason='no_context'),'кот'),('кот',True))
        self.assertEqual(final_proposal(SimpleNamespace(word=None,reason='invalid_candidate'),'кот'),(None,False))

    def test_harness_uses_production_width(self):
        source = Path(__file__).with_name('ProductionCandidates.kt').read_text()
        self.assertIn('CandidateGenerator(PackedCandidateLexicon(handles), CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES,',source)


if __name__ == '__main__': unittest.main()
