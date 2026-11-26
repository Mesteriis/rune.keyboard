import copy
import unittest
from unittest.mock import patch

import phrase_replay_smoke as subject
import register_phrase_replay as disclosure


def row(name, typed, after, undo=False):
    words=typed.split(' '); stages=[]; prior=''
    for i, word in enumerate(words):
        current=prior+word; output=after if i==len(words)-1 else current+' '
        changed=output!=current+' '; prefix=not output.startswith(current[:-len(word)])
        stage=dict(wordIndex=i,typed=word,before=current,after=output,changed=changed,prefixChanged=prefix,
                   caseOnly=changed and output.casefold()==(current+' ').casefold(),automaticEdit=changed)
        if i==len(words)-1 and undo:stage.update(undoResult='HANDLED',undoExact=True)
        stages.append(stage);prior=output
    return dict(id=name,typed=typed,status='COMPLETE',phraseStages=stages)


class PhraseReplayTest(unittest.TestCase):
    def test_refuses_changed_prefix_bad_undo_and_corrupt_stages(self):
        cases=(('first','один ошибко','один ошибка ',True),('second','два слова','два слова ',False),
               ('third','три ошибко','три ошибка ',True))
        values=[row(name,typed,expected,undo) for name,typed,expected,undo in cases]
        with patch.object(subject,'CASES',cases):
            result=subject.validate(values)
            self.assertEqual((0,2,0),(result['prefixChanges'],result['undoChecked'],result['undoFailures']))
            changed=copy.deepcopy(values);changed[0]['phraseStages'][-1]['undoExact']=False
            with self.assertRaisesRegex(ValueError,'PHRASE_INVARIANT_FAILURE'):subject.validate(changed)
            changed=copy.deepcopy(values);changed[1]['phraseStages'][-1]['prefixChanged']=True
            with self.assertRaisesRegex(ValueError,'PHRASE_OBSERVATION_MISMATCH'):subject.validate(changed)
            changed=copy.deepcopy(values);changed[1]['phraseStages'][-1]['before']='чужой слова'
            with self.assertRaisesRegex(ValueError,'PHRASE_SESSION_DIVERGENCE'):subject.validate(changed)
            changed=copy.deepcopy(values);changed[0]['phraseStages'][-1]['after']='один другая '
            with self.assertRaisesRegex(ValueError,'PHRASE_OUTPUT_MISMATCH'):subject.validate(changed)

    def test_requires_declared_revision_paths(self):
        cases=(('infinitive-case','один слово','один слово ',False),
               ('one','два ошибко','два ошибка ',True),('two','три ошибко','три ошибка ',True))
        values=[row(name,typed,expected,undo) for name,typed,expected,undo in cases]
        with patch.object(subject,'CASES',cases):
            with self.assertRaisesRegex(ValueError,'PHRASE_GRAMMAR_NOT_EXERCISED'):subject.validate(values)
            values[0]['phraseStages'][-1]['grammarRevisionAttempted']=True
            subject.validate(values)

    def test_disclosed_stages_are_blocked_by_both_real_registries(self):
        self.assertEqual(20,disclosure.check())
        first=disclosure.rows()[0]
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
            disclosure.controls.assert_disjoint([first],disclosure.controls.load(disclosure.CONTROL),'regression')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            disclosure.lexical.assert_disjoint([first],disclosure.lexical.load_ledger(disclosure.LEXICAL),
                                                kinds=('context',),require_complete=False)
        with patch.object(disclosure,'CASES',disclosure.CASES[:-1]), \
             self.assertRaisesRegex(ValueError,'PHRASE_DISCLOSURE_DRIFT'):
            disclosure.check()


if __name__=='__main__': unittest.main()
