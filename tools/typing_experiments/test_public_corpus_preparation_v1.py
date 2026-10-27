import copy
import unittest
from control_ledger import SCHEMA,key_for,article_key
from holdout_ledger import keys_for
from public_corpus_preparation_v1 import preflight
from test_holdout_ledger import ledger


def candidate(**changes):
    return dict(id='new',language='ru',article='999999999',families=['пробный'],contextHash='0'*64,
                prefix='Новый контекст проверки',typed='пробный',expectedSpelling='пробный')|changes


def controls():
    return dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['pending'],entries=[
        dict(id='punct',kind='punctuation',language='ru',rowCount=1,bindings={'file':'a'*64},
             keys=[key_for(dict(language='ru',prefix='Пунктуация',currentWord='слово',expectedBoundary=', '),'punctuation')],
             articleKeys=sorted([article_key(dict(language='ru',article='777')),article_key(dict(language='en',article='123'))])),
        dict(id='protected',kind='protected',language='ru',rowCount=1,bindings={'file':'b'*64},
             keys=[key_for(dict(language='ru',prefix='Сохранить',typed='API36'),'protected')])])


class PreparationGateTest(unittest.TestCase):
    def report(self,row=None,task='spelling',**changes):
        args=dict(rows=[row or candidate()],task=task,lexical=ledger(False),controls=controls())|changes
        return preflight(**args)

    def test_unknown_rows_are_blocked_by_both_incomplete_registries(self):
        result=self.report()
        self.assertEqual('BLOCKED_COVERAGE',result['status']);self.assertFalse(result['lexicalCoverageComplete'])
        self.assertFalse(result['controlCoverageComplete']);self.assertEqual([],result['identityErrors'])

    def test_lexical_and_control_articles_each_block_spelling_preparation(self):
        word=self.report(candidate(article='123'));control=self.report(candidate(article='777'))
        self.assertEqual(1,word['lexicalOverlaps']['article']);self.assertEqual('BLOCKED_OVERLAP',word['status'])
        self.assertEqual(1,control['controlOverlaps']['article']);self.assertEqual(0,control['lexicalOverlaps']['article'])
        self.assertEqual('BLOCKED_OVERLAP',control['status'])

    def test_protected_controls_are_checked_even_when_task_is_spelling(self):
        result=self.report(candidate(prefix='Сохранить',typed='API36',expectedSpelling='API36'))
        self.assertEqual(1,result['controlOverlaps']['protected']);self.assertEqual('BLOCKED_OVERLAP',result['status'])

    def test_changed_punctuation_label_still_blocks_preparation(self):
        row=candidate(prefix='Пунктуация',currentWord='слово',expectedBoundary='. ',task='punctuation',noAuto=True)
        result=self.report(row,task='punctuation')
        self.assertEqual(1,result['controlOverlaps']['punctuation']);self.assertEqual('BLOCKED_OVERLAP',result['status'])

    def test_family_profiles_preserve_supervised_versus_historical_semantics(self):
        row=candidate(families=['готовый'])
        self.assertEqual(0,self.report(row)['lexicalOverlaps']['family'])
        self.assertEqual(1,self.report(row,profile='new-families')['lexicalOverlaps']['family'])
        lex=ledger(False);lex['entries'].append(dict(id='train',usage='supervised',bindings={'file':'c'*64},
            keys={'family':sorted(keys_for([row],'family'))},missingAxes=[]))
        self.assertEqual(1,self.report(row,lexical=lex)['lexicalOverlaps']['family'])

    def test_identity_errors_do_not_skip_control_checks_and_languages_do_not_alias(self):
        result=self.report(candidate(article=1,prefix='Сохранить',typed='API36',expectedSpelling='API36'))
        self.assertTrue(result['identityErrors']);self.assertEqual(1,result['controlOverlaps']['protected'])
        result=self.report(candidate(article='123'))
        self.assertEqual(0,result['controlOverlaps']['article']) # EN 123 is distinct from RU 123.

    def test_empty_duplicate_and_unsupported_language_inputs_fail_closed(self):
        with self.assertRaises(ValueError):self.report(rows=[])
        self.assertEqual('BLOCKED_IDENTITIES',self.report(rows=[candidate(),candidate()])['status'])
        self.assertIn('unsupported-spelling-language',self.report(candidate(language='en'))['identityErrors'])

    def test_invalid_second_registry_cannot_be_ignored_on_a_known_lexical_overlap(self):
        invalid=controls();invalid['coverageComplete']=True
        with self.assertRaisesRegex(ValueError,'CONTROL_LEDGER_SCHEMA'):self.report(candidate(article='123'),controls=invalid)

    def test_tatoeba_source_namespace_and_source_backed_protected_rows_are_checked(self):
        row=candidate(sourceRepository='tatoeba',article='tatoeba:123',sentenceHash='b'*64)
        result=self.report(row)
        self.assertEqual(0,result['lexicalOverlaps']['article']);self.assertEqual([],result['identityErrors'])
        lex=ledger(False);lex['entries'].append(dict(id='tt',usage='historical-source-exclusion',bindings={'source':'a'*64},
            keys={axis:sorted(keys_for([row],axis)) for axis in ('article','sentence')},missingAxes=[]))
        row.update(cohort='protected',noAuto=True,expectedCandidate=0,candidates=[' '+row['typed']])
        result=self.report(row,task='protected',lexical=lex)
        self.assertEqual(1,result['lexicalOverlaps']['article']);self.assertEqual(1,result['lexicalOverlaps']['sentence'])


if __name__=='__main__':unittest.main()
