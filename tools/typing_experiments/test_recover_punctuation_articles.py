import copy
import unittest
from control_ledger import SCHEMA,article_key,key_for,validate
from import_early_ru_history import CORPORA
from recover_punctuation_articles import selected_rows,matches,merge
from test_import_control_components import row


class Generator:
    def __init__(self,item):self.item=item
    def punctuation_candidates(self,*_):return [dict(self.item),dict(self.item)]


class PunctuationArticleTest(unittest.TestCase):
    def test_every_matching_occurrence_is_retained_without_inferring_labels(self):
        value=row();selected=selected_rows([value],7);identity=next(iter(selected))
        generator=Generator(dict(prefix=value['prefix'],word=value['currentWord'],boundary=value['expectedBoundary'],selectionHash=identity))
        records=matches('1','unused',selected,generator,'ru',7)
        self.assertEqual(2,len(records));self.assertEqual('1',records[0]['article'])
        generator.item['boundary']='. '
        with self.assertRaisesRegex(ValueError,'DIVERGENCE'):matches('1','unused',selected,generator,'ru',7)
        with self.assertRaises(ValueError):selected_rows([value,value|dict(id='other')],7)

    def test_article_keys_include_language_and_normalize_decimal_ids_only(self):
        ru=article_key(dict(language='ru',article='123'))
        self.assertEqual(ru,article_key(dict(language='ru',article='00123')))
        self.assertNotEqual(ru,article_key(dict(language='en',article='123')))
        for value in (dict(language='fr',article='1'),dict(language='ru',article='ru:1'),dict(language='ru',article=1)):
            with self.assertRaises(ValueError):article_key(value)

    def fixture(self):
        entries=[];groups=[]
        for corpus in CORPORA:
            for lang in ('en','ru','es'):
                entries.append(dict(id=corpus+'-punctuation-'+lang,kind='punctuation',language=lang,rowCount=1,
                                    bindings={'file':'a'*64},keys=[key_for(row()|dict(language=lang),'punctuation')]))
                groups.append((dict(corpus=corpus,language=lang,allRowsRecovered=True,missingRows=[],modelCalls=0,
                    sourceRows=1,recoveredRows=1,occurrences=2),[dict(id='p',language=lang,article='1'),dict(id='p',language=lang,article='2')]))
        base=dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['pending'],entries=entries)
        return base,groups

    def test_merge_adds_all_articles_preserving_original_entries_keys_and_bindings(self):
        base,groups=self.fixture();before=copy.deepcopy(base);result=merge(base,groups)
        self.assertEqual(before,base)
        for old,new in zip(base['entries'],result['entries'],strict=True):
            for field in old:self.assertEqual(old[field],new[field])
            self.assertEqual(2,len(new['articleKeys']))

    def test_missing_groups_rows_model_calls_and_bad_article_hashes_fail(self):
        base,groups=self.fixture()
        with self.assertRaises(ValueError):merge(base,groups[:-1])
        for change in (dict(modelCalls=1),dict(allRowsRecovered=False),dict(missingRows=['p']),dict(recoveredRows=0)):
            bad=copy.deepcopy(groups);bad[0][0].update(change)
            with self.assertRaises(ValueError):merge(base,bad)
        base['entries'][0]['articleKeys']=['bad']
        with self.assertRaisesRegex(ValueError,'ARTICLE_KEYS'):validate(base)


if __name__=='__main__':unittest.main()
