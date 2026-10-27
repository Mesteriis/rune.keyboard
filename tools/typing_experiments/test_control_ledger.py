import copy
import unittest
from control_ledger import SCHEMA,key_for,assert_disjoint,validate


def punctuation(**changes):return dict(language='ru',prefix='Текст',currentWord='слово',expectedBoundary=', ')|changes

def registry(kind='punctuation',row=None):
    row=row or punctuation()
    return dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['integration'],
        entries=[dict(id='test',kind=kind,language=row['language'],rowCount=1,bindings={'file':'a'*64},keys=[key_for(row,kind)])])


class ControlLedgerTest(unittest.TestCase):
    def test_boundary_label_changes_do_not_hide_a_disclosed_punctuation_context(self):
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:punctuation'):
            assert_disjoint([punctuation(expectedBoundary='. ')],registry(),'punctuation')

    def test_language_and_task_namespaces_are_separate(self):
        self.assertNotEqual(key_for(punctuation(),'punctuation'),key_for(punctuation(language='en'),'punctuation'))
        self.assertNotEqual(key_for(punctuation(),'punctuation'),key_for(dict(language='ru',prefix='Текст',typed='слово'),'protected'))

    def test_protected_case_punctuation_and_nfc_are_preserved(self):
        row=dict(language='ru',prefix='Сохранить',typed='API36')
        self.assertNotEqual(key_for(row,'protected'),key_for(row|dict(typed='api36'),'protected'))
        self.assertNotEqual(key_for(row,'protected'),key_for(row|dict(typed='API-36'),'protected'))
        self.assertEqual(key_for(row|dict(typed='е\u0308лка'),'protected'),key_for(row|dict(typed='ёлка'),'protected'))
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:protected'):
            assert_disjoint([row],registry('protected',row),'protected')

    def test_unseen_controls_do_not_certify_complete_freshness(self):
        with self.assertRaisesRegex(ValueError,'COVERAGE_INCOMPLETE'):
            assert_disjoint([punctuation(prefix='Другой')],registry(),'punctuation')
        with self.assertRaisesRegex(ValueError,'EMPTY_ROWS'):assert_disjoint([],registry(),'punctuation')

    def test_invalid_scope_schema_hashes_duplicates_and_false_coverage_fail(self):
        for row in (punctuation(language='fr'),punctuation(expectedBoundary='! '),punctuation(prefix=None)):
            with self.assertRaises(ValueError):key_for(row,'punctuation')
        cases=[[],{},registry()|dict(coverageComplete=True)]
        x=registry();x['entries']*=2;cases.append(x)
        x=registry();x['entries'][0]['keys']=['bad'];cases.append(x)
        x=registry();x['entries'][0]['rowCount']=True;cases.append(x)
        x=registry();x['entries'][0]=None;cases.append(x)
        for value in cases:
            with self.assertRaises(ValueError):validate(value)


if __name__=='__main__':unittest.main()
