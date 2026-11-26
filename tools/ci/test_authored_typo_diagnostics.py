import copy
import unittest
import authored_typo_diagnostics as subject


class TypoDiagnosticsTest(unittest.TestCase):
    def test_refusals_and_applied_sources_are_checked(self):
        cases=[('a','это молоо','молоко'),('b','ты проед','проезд')]
        rows=[dict(id='a',typed='это молоо',phraseStages=[dict(automaticEdit=False,after='это молоо ',
              boundaryDiagnostics=[dict(reason='TOO_SHORT',source='NONE')])]),
              dict(id='b',typed='ты проед',phraseStages=[dict(automaticEdit=True,after='ты проезд ',
              boundaryDiagnostics=[dict(reason='AUTO_REPLACE',source='LOCAL_POLICY')])])]
        self.assertEqual({'refusals':{'TOO_SHORT':1},'appliedSources':{'LOCAL_POLICY':1}},subject.summarize(cases,rows))
        bad=copy.deepcopy(rows);bad[1]['phraseStages'][-1]['boundaryDiagnostics'][0]['reason']='TOO_SHORT'
        with self.assertRaisesRegex(ValueError,'TYPO_DIAGNOSTIC_APPLICATION'):subject.summarize(cases,bad)
        bad=copy.deepcopy(rows);bad[0]['phraseStages'][-1]['boundaryDiagnostics']=[]
        with self.assertRaisesRegex(ValueError,'TYPO_DIAGNOSTIC_EVENT'):subject.summarize(cases,bad)
        bad=copy.deepcopy(rows);bad[1]['phraseStages'][-1]['after']='ты проход '
        with self.assertRaisesRegex(ValueError,'TYPO_DIAGNOSTIC_TARGET'):subject.summarize(cases,bad)


if __name__=='__main__': unittest.main()
