import copy
import unittest
import a4_controls_gate as gate


def fixtures(boundary):
    rows, observations = [], []
    char = gate.BOUNDARIES[boundary]
    for family, count in gate.COUNTS.items():
        for _ in range(count):
            index = len(rows); word = f'word{index}'; identity = f'id{index}'
            row = dict(id=identity, language='ru', prefix='', split='holdout', typed=word,
                       cohort='correct', noAuto=True, expectedSpelling=word, family=family)
            obs = dict(id=identity, language='ru', prefix='', split='holdout', typed=word,
                       status='COMPLETE', boundaryResult='HANDLED', backspaceResult='HANDLED',
                       beforeBoundary={'text': word}, inputChangedByTyping=False,
                       afterBoundary={'text': word + char}, afterBackspace={'text': word},
                       restoredBeforeBoundaryExactly=True)
            if boundary == 'space': obs['boundaryChangedBeyondInsertedSpace'] = False
            else: obs.update(boundary=char, boundaryChangedBeyondInsertion=False)
            rows.append(row); observations.append(obs)
    return rows, observations


class ControlsGateTest(unittest.TestCase):
    def test_each_boundary_passes_and_case_change_fails(self):
        for boundary in gate.BOUNDARIES:
            rows, obs = fixtures(boundary)
            self.assertTrue(gate.evaluate(rows, obs, boundary)['passed'])
            changed = copy.deepcopy(obs)
            changed[0]['afterBoundary']['text'] = rows[0]['typed'].upper() + gate.BOUNDARIES[boundary]
            key = 'boundaryChangedBeyondInsertedSpace' if boundary == 'space' else 'boundaryChangedBeyondInsertion'
            changed[0][key] = True
            result = gate.evaluate(rows, changed, boundary)
            self.assertFalse(result['passed'])
            self.assertEqual(1, result['categories']['abbreviation']['changes'])
            self.assertEqual(rows[0]['id'], result['failures'][0]['id'])

    def test_refuses_missing_rows_and_inconsistent_flags(self):
        rows, obs = fixtures('period')
        with self.assertRaisesRegex(ValueError, 'A4_ROW_COUNT'): gate.evaluate(rows, obs[:-1], 'period')
        for changes in ({'boundary': ':'}, {'boundaryChangedBeyondInsertion': True},
                        {'afterBackspace': {'text': 'wrong'}}, {'typed': 'wrong'}, {'boundaryResult': 'UNHANDLED'}):
            broken = copy.deepcopy(obs); broken[0].update(changes)
            with self.assertRaises(ValueError): gate.evaluate(rows, broken, 'period')
        broken = copy.deepcopy(obs); broken[0].update(afterBackspace={'text': 'wrong'}, restoredBeforeBoundaryExactly=False)
        self.assertFalse(gate.evaluate(rows, broken, 'period')['passed'])

    def test_requires_exact_category_counts_and_labels(self):
        rows, obs = fixtures('space')
        rows[0]['family'] = 'domain_label'
        with self.assertRaisesRegex(ValueError, 'A4_CATEGORIES'): gate.evaluate(rows, obs, 'space')
        rows, obs = fixtures('space'); rows[0]['noAuto'] = False
        with self.assertRaisesRegex(ValueError, 'A4_ROW_SHAPE'): gate.evaluate(rows, obs, 'space')


if __name__ == '__main__': unittest.main()
