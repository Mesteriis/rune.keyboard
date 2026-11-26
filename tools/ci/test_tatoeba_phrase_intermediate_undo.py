import unittest
import tatoeba_phrase_intermediate_undo as subject


class UndoReplayTest(unittest.TestCase):
    def test_targets_keep_precise_stage_and_truncate_later_words(self):
        stage=lambda i,w,auto:{'wordIndex':i,'typed':w,'automaticEdit':auto,'before':'до', 'after':'после'}
        rows=[{'id':'a','typed':'один два три','status':'COMPLETE','phraseStages':[stage(0,'один',False),stage(1,'два',True),stage(2,'три',False)]}]
        self.assertEqual([{'id':'a#1','typed':'один два','before':'до','after':'после','index':1}],subject.targets([('a','один два три')],rows))
        rows[0]['phraseStages'][1]['wordIndex']=0
        with self.assertRaisesRegex(ValueError,'UNDO_TARGET_WORD'):subject.targets([('a','один два три')],rows)

    def test_single_and_multiword_require_same_decision_and_exact_undo(self):
        target={'id':'a#1','index':1,'before':'до','after':'после'}
        good={'id':'a#1','status':'COMPLETE','phraseStages':[{}, {'before':'до','after':'после','automaticEdit':True,'undoResult':'HANDLED','undoExact':True}]}
        subject.verify(target,good,True)
        good['phraseStages'][-1]['undoExact']=False
        with self.assertRaisesRegex(ValueError,'UNDO_REPLAY_FAILED'):subject.verify(target,good,True)
        single={'id':'a#1','status':'COMPLETE','beforeBoundary':{'text':'до'},'afterBoundary':{'text':'после'},'backspaceResult':'HANDLED','restoredBeforeBoundaryExactly':True}
        subject.verify(target,single,False);single['afterBoundary']['text']='другое'
        with self.assertRaisesRegex(ValueError,'UNDO_REPLAY_DECISION'):subject.verify(target,single,False)


if __name__=='__main__':unittest.main()
