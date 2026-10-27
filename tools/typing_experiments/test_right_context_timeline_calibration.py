import unittest
from right_context_timeline_calibration import completed_prefixes,path_metrics,select_path_policy


def step(words,word,score):return dict(completedWords=words,proposed=word,score=score,margin=.2,sourceCertified=True)
def row(key='one',steps=None,**changes):
    r=dict(id=key,original='опечтка',previous='опечтка',expected='верно',control=False,steps=steps or [])
    r.update(changes);return r


class TimelineCalibrationTest(unittest.TestCase):
    def test_prefixes_use_actual_completed_boundaries(self):
        self.assertEqual([(1,' будет '),(2,' будет она,')],list(completed_prefixes(' будет она, потом ')))
        self.assertEqual([(1,' будет ')],list(completed_prefixes(' будет он')))
        self.assertEqual([],list(completed_prefixes(' будет')))
        self.assertEqual([],list(completed_prefixes('x будет ')))
        self.assertEqual([],list(completed_prefixes(' '*125+'она ')))

    def test_later_correct_answer_never_hides_an_already_accepted_wrong_word(self):
        paths=[row(steps=[step(1,'неверно',.6),step(2,'верно',.8)])]
        self.assertEqual(1,path_metrics(paths,dict(minimumScore=.5,minimumMargin=.1))['newWrong'])
        m=path_metrics(paths,dict(minimumScore=.7,minimumMargin=.1))
        self.assertEqual(1,m['newCorrect']);self.assertEqual({'2':1},m['firstBoundaryActions'])

    def test_later_high_score_does_not_overwrite_the_first_correct_accepted_action(self):
        paths=[row(steps=[step(1,'верно',.6),step(2,'неверно',.8)])]
        self.assertEqual(1,path_metrics(paths,dict(minimumScore=.5,minimumMargin=.1))['newCorrect'])
        self.assertEqual(1,path_metrics(paths,dict(minimumScore=.7,minimumMargin=.1))['newWrong'])

    def test_minimum_gain_is_per_source_word_not_per_prefix_step(self):
        paths=[row(str(i),steps=[step(1,'верно',.6),step(2,'верно',.8)]) for i in range(60)]
        self.assertIsNone(select_path_policy(paths,required_precision=1.0))
        paths += [row(str(i),steps=[step(1,'верно',.6)]) for i in range(60,100)]
        self.assertIsNotNone(select_path_policy(paths,required_precision=1.0))

    def test_certificate_boundary_order_and_preservation_constraints_remain_required(self):
        for steps in [[step(2,'верно',.6),step(1,'верно',.8)],[step(1,'верно',.6)|{'sourceCertified':False}]]:
            with self.assertRaises(ValueError):path_metrics([row(steps=steps)],dict(minimumScore=.5,minimumMargin=.1))
        good=[row(str(i),steps=[step(1,'верно',.6)]) for i in range(200)]
        bad=row('bad',steps=[step(1,'неверно',.6)],previous='верно')
        self.assertIsNone(select_path_policy(good+[bad],required_precision=.95))
        self.assertEqual(0,path_metrics([row()],dict(minimumScore=.5,minimumMargin=.1))['newCorrect'])


if __name__ == '__main__':unittest.main()
