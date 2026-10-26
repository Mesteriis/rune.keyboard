import unittest

from grammar_focus_forms import infinitive_contrast
from test_grammar_revision_scope import Dictionary, tag


class GrammarFocusFormsTest(unittest.TestCase):
    def setUp(self):
        self.lexicon = Dictionary()
        self.lexicon.words['ходить'] = [tag('ходить', 'INFN')]
        self.lexicon.words['ходишь'] = [tag('ходить', 'VERB', person='2per', number='sing')]

    def test_reflexive_and_plain_source_forms_have_verified_asymmetric_costs(self):
        self.assertEqual(infinitive_contrast('учиться', self.lexicon),
                         dict(word='учиться', finite='учишься', typed='учищься', editCosts=[1., .75]))
        self.assertEqual(infinitive_contrast('ходить', self.lexicon),
                         dict(word='ходить', finite='ходишь', typed='ходищь', editCosts=[1., .75]))

    def test_unknown_or_ambiguous_forms_and_unrelated_lemmas_are_excluded(self):
        self.assertIsNone(infinitive_contrast('говорить', self.lexicon))
        self.lexicon.words['ходишь'] = [tag('другое', 'VERB', person='2per', number='sing')]
        self.assertIsNone(infinitive_contrast('ходить', self.lexicon))
        self.lexicon.words['учиться'].append(tag('другое', 'NOUN'))
        self.assertIsNone(infinitive_contrast('учиться', self.lexicon))

    def test_known_corruption_and_invalid_text_never_become_typo_rows(self):
        self.lexicon.words['учищься'] = [tag('слово', 'NOUN')]
        self.assertIsNone(infinitive_contrast('учиться', self.lexicon))
        for word in ('Учиться', 'учиться!', 'xучиться', None, 'делать', 'пить'):
            self.assertIsNone(infinitive_contrast(word, self.lexicon))


if __name__ == '__main__':
    unittest.main()
