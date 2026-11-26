import unittest
import authored_phrase_replay as subject


class AuthoredPhraseReplayTest(unittest.TestCase):
    def test_session_counts_corrections_and_exact_undo(self):
        cases=[('one','это книга')]
        rows=[dict(id='one', typed='это книга', status='COMPLETE', phraseStages=[
            dict(wordIndex=0, typed='это', before='это', after='это ', changed=False,
                 prefixChanged=False, caseOnly=False, automaticEdit=False),
            dict(wordIndex=1, typed='книга', before='это книга', after='это Книга ', changed=True,
                 prefixChanged=False, caseOnly=True, automaticEdit=True, undoResult='HANDLED', undoExact=True)])]
        result=subject.evaluate(cases,rows)
        self.assertEqual((1,2,1,1,1,1,1,0), tuple(result[k] for k in
            ('phrases','words','changedPhrases','boundaryChanges','caseOnlyChanges','automaticEdits','undoChecked','undoFailures')))
        rows[0]['phraseStages'][1]['undoExact']=False
        with self.assertRaisesRegex(ValueError, 'AUTHORED_REPLAY_UNDO'):
            subject.evaluate(cases,rows)
        rows[0]['phraseStages'][1]['undoExact']=True
        rows[0]['phraseStages'][1]['prefixChanged']=True
        with self.assertRaisesRegex(ValueError, 'AUTHORED_REPLAY_FLAGS'):
            subject.evaluate(cases,rows)


if __name__ == '__main__': unittest.main()
