import copy
import unittest

import phrase_replay_review_screen as screen
import register_review_phrase as disclosure


class ReviewedPhraseScreenTest(unittest.TestCase):
    def test_source_and_contexts_are_bound_to_real_registries(self):
        cases=screen.inputs()
        self.assertEqual(11,len(cases))
        self.assertEqual(8,sum(c['label']=='preserve' for c,_ in cases))
        self.assertEqual(56,disclosure.check())
        row=disclosure.rows()[0]
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
            disclosure.control.assert_disjoint([row],disclosure.control.load(disclosure.CONTROL),'regression')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            disclosure.lexical.assert_disjoint([row],disclosure.lexical.load_ledger(disclosure.LEXICAL),kinds=('context',),require_complete=False)

    def test_reports_real_changes_and_refuses_invalid_observations(self):
        cases=[({'id':'case','typed':'бадлон','label':'preserve'},'это бадлон')]
        stages=[dict(wordIndex=0,typed='это',before='это',after='это ',changed=False,prefixChanged=False,caseOnly=False,automaticEdit=False),
                dict(wordIndex=1,typed='бадлон',before='это бадлон',after='это баллон ',changed=True,prefixChanged=False,caseOnly=False,automaticEdit=True,undoResult='HANDLED',undoExact=True)]
        rows=[dict(id='case',typed='это бадлон',status='COMPLETE',phraseStages=stages)]
        result=screen.evaluate(cases,rows)
        self.assertEqual((1,0,1,0),(result['preserveRows'],result['preserved'],result['undoChecked'],result['undoFailures']))
        registered=[dict(language='ru',prefix=prefix,typed=word,expectedSpelling=word)
                    for prefix,word in (('', 'это'), ('это', 'бадлон'), ('это', 'баллон'))]
        screen.ensure_disclosed(rows,registered)
        with self.assertRaisesRegex(ValueError,'PHRASE_REVIEW_UNDISCLOSED_CONTEXT'):
            screen.ensure_disclosed(rows,registered[:-1])
        changed=copy.deepcopy(rows);changed[0]['phraseStages'][1]['undoExact']=False
        with self.assertRaisesRegex(ValueError,'PHRASE_REVIEW_UNDO'):screen.evaluate(cases,changed)
        changed=copy.deepcopy(rows);changed[0]['phraseStages'][1]['prefixChanged']=True
        with self.assertRaisesRegex(ValueError,'PHRASE_REVIEW_FLAGS'):screen.evaluate(cases,changed)
        changed=copy.deepcopy(rows);changed[0]['phraseStages'][1]['before']='чужой бадлон'
        with self.assertRaisesRegex(ValueError,'PHRASE_REVIEW_SESSION'):screen.evaluate(cases,changed)


if __name__=='__main__':unittest.main()
