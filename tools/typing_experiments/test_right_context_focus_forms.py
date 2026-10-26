from types import SimpleNamespace
import unittest
from right_context_focus_forms import predicate_contrast


def tag(number,gender=None,lemma='пример',pos='ADJS'):
    return SimpleNamespace(number=number,gender=gender,lemma=lemma,pos=pos)


class Dictionary:
    def __init__(self):
        self.words={'готов':[tag('sing','masc')],'готова':[tag('sing','femn')],
                    'готовы':[tag('plur')],'другой':[tag('plur',lemma='другой')]}
    def analyses(self,word):return self.words.get(word,())


class FocusFormsTest(unittest.TestCase):
    def test_paradigm_is_rechecked_and_corruptions_are_unknown_shared_one_edit(self):
        dictionary=Dictionary()
        for source in ['готов','готова','готовы']:
            result=predicate_contrast(source,dictionary,dictionary.words)
            self.assertIsNotNone(result);self.assertEqual(source,result['word'])
            self.assertFalse(dictionary.analyses(result['typed']))
            self.assertEqual('пример',result['family'])
            self.assertEqual(2,len(result['editCosts']))
        self.assertEqual('готов',predicate_contrast('готовы',dictionary,dictionary.words)['rival'])

    def test_all_analyses_need_the_same_family_number_and_short_predicate_part(self):
        for extra in [tag('plur'),tag('sing',lemma='другой'),tag('sing',pos='NOUN')]:
            dictionary=Dictionary();dictionary.words['готов'].append(extra)
            self.assertIsNone(predicate_contrast('готов',dictionary,dictionary.words))
        dictionary=Dictionary();dictionary.words['готовы']=[tag('plur',lemma='другой')]
        self.assertIsNone(predicate_contrast('готов',dictionary,['готовы']))

    def test_empty_unknown_or_identifier_sources_do_not_create_targets(self):
        dictionary=Dictionary()
        for word in ['', 'готов_имя','Ready','неизвестный']:
            self.assertIsNone(predicate_contrast(word,dictionary,dictionary.words))
        self.assertIsNone(predicate_contrast('готов',dictionary,[]))

    def test_known_corruption_is_not_silently_reused(self):
        dictionary=Dictionary();before=predicate_contrast('готов',dictionary,dictionary.words)
        dictionary.words[before['typed']]=[tag('sing')]
        after=predicate_contrast('готов',dictionary,dictionary.words)
        self.assertTrue(after is None or before['typed']!=after['typed'])


if __name__ == '__main__':unittest.main()
