import copy
import unittest
from control_ledger import SCHEMA,key_for,article_key,assert_disjoint,validate


def punctuation(**changes):return dict(language='ru',prefix='Текст',currentWord='слово',expectedBoundary=', ')|changes

def registry(kind='punctuation',row=None):
    row=row or punctuation()
    return dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['integration'],
        entries=[dict(id='test',kind=kind,language=row['language'],rowCount=1,bindings={'file':'a'*64},keys=[key_for(row,kind)])])


class ControlLedgerTest(unittest.TestCase):
    def test_empty_context_is_valid_only_for_standalone_regressions(self):
        row=dict(language='ru',prefix='',typed='зочу')
        self.assertEqual(key_for(row,'regression'),key_for(dict(row),'regression'))
        self.assertNotEqual(key_for(row,'regression'),key_for(row|dict(prefix='Текст'),'regression'))
        for kind in ('protected','punctuation'):
            with self.assertRaisesRegex(ValueError,'CONTROL_TEXT'):
                key_for(row|dict(currentWord='слово',expectedBoundary=' '),kind)
        with self.assertRaisesRegex(ValueError,'CONTROL_TEXT'):
            key_for(row|dict(prefix=None),'regression')

    def test_disclosed_named_rows_are_durably_blocked_without_freshness_claim(self):
        import register_named_regressions as named
        original=registry()
        added=named.register(original)
        self.assertEqual(1,len(original['entries']))
        self.assertEqual(original['entries'],added['entries'][:1])
        self.assertFalse(added['coverageComplete'])
        named.check(added)
        self.assertEqual([12,36,8],[e['rowCount'] for e in named.entries()])
        for row in named.runner.named_rows():
            with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
                assert_disjoint([row],added,'regression')
            with self.assertRaisesRegex(ValueError,'CONTROL_SURFACE_OVERLAP'):
                assert_disjoint([row|dict(prefix='new context')],added,'regression')
        with self.assertRaisesRegex(ValueError,'NAMED_ALREADY_REGISTERED'):named.register(added)
        changed=copy.deepcopy(added);changed['entries'][-1]['bindings']['changed']='a'*64
        with self.assertRaisesRegex(ValueError,'NAMED_REGISTRY_DRIFT'):named.check(changed)
        with self.assertRaisesRegex(ValueError,'CONTROL_COVERAGE_INCOMPLETE'):
            assert_disjoint([dict(language='ru',prefix='',typed='unseen-example')],added,'regression')

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
        self.assertNotEqual(key_for(row|dict(typed='съемка'),'protected'),key_for(row|dict(typed='съёмка'),'protected'))
        with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:protected'):
            assert_disjoint([row],registry('protected',row),'protected')

    def test_disclosed_article_is_rejected_with_new_surface_and_context(self):
        disclosed = registry()
        disclosed['entries'][0]['articleKeys'] = [article_key(dict(language='ru', article='42'))]
        with self.assertRaisesRegex(ValueError, 'CONTROL_ARTICLE_OVERLAP'):
            assert_disjoint([punctuation(prefix='Новый контекст', currentWord='иное', article='42')],
                            disclosed, 'punctuation')
        with self.assertRaisesRegex(ValueError, 'CONTROL_COVERAGE_INCOMPLETE'):
            assert_disjoint([punctuation(prefix='Новый контекст', currentWord='иное', article='43')],
                            disclosed, 'punctuation')
        with self.assertRaisesRegex(ValueError, 'CONTROL_ARTICLE_ID'):
            assert_disjoint([punctuation(prefix='Новый контекст', currentWord='иное', article='?')],
                            disclosed, 'punctuation')

    def test_disclosed_tatoeba_sentence_is_rejected(self):
        disclosed = registry()
        source = dict(language='ru', sourceRepository='tatoeba', article='tatoeba:42')
        disclosed['entries'][0]['articleKeys'] = [article_key(source)]
        with self.assertRaisesRegex(ValueError, 'CONTROL_ARTICLE_OVERLAP'):
            assert_disjoint([punctuation(prefix='Другой текст', currentWord='иное') | source],
                            disclosed, 'punctuation')

    def test_source_only_entry_blocks_english_ewt_document(self):
        from holdout_ledger import keys_for
        row=dict(language='en',sourceRepository='ud-english-ewt',article='ewt:example-doc',
                 prefix='A new context ',typed='example')
        article=article_key(row)
        self.assertEqual({article},keys_for([row],'article'))
        disclosed=registry()
        disclosed['entries'].append(dict(id='ewt-source',kind='source',language='en',rowCount=1,
            bindings={'source':'a'*64},keys=[],articleKeys=[article]))
        validate(disclosed)
        with self.assertRaisesRegex(ValueError,'CONTROL_ARTICLE_OVERLAP'):
            assert_disjoint([row],disclosed,'regression')
        for changed in (dict(keys=['a'*64]),dict(articleKeys=[]),
                        dict(articleKeys=sorted([article,'f'*64]))):
            invalid=copy.deepcopy(disclosed);invalid['entries'][-1].update(changed)
            with self.assertRaises(ValueError):validate(invalid)

    def test_unseen_controls_do_not_certify_complete_freshness(self):
        with self.assertRaisesRegex(ValueError,'COVERAGE_INCOMPLETE'):
            assert_disjoint([punctuation(prefix='Другой')],registry(),'punctuation')
        with self.assertRaisesRegex(ValueError,'EMPTY_ROWS'):assert_disjoint([],registry(),'punctuation')

    def test_invalid_scope_schema_hashes_duplicates_and_false_coverage_fail(self):
        for row in (punctuation(language='fr'),punctuation(expectedBoundary='! '),punctuation(prefix=None)):
            with self.assertRaises(ValueError):key_for(row,'punctuation')
        with self.assertRaises(ValueError):key_for([],'punctuation')
        cases=[[],{},registry()|dict(coverageComplete=True)]
        x=registry();x['entries']*=2;cases.append(x)
        x=registry();x['entries'][0]['keys']=['bad'];cases.append(x)
        x=registry();x['entries'][0]['rowCount']=True;cases.append(x)
        x=registry();x['entries'][0]=None;cases.append(x)
        for value in cases:
            with self.assertRaises(ValueError):validate(value)


if __name__=='__main__':unittest.main()
