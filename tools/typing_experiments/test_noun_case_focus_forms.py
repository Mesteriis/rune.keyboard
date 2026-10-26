from types import SimpleNamespace
import unittest

from noun_case_focus_forms import accusative_contrast


def tag(lemma, case, **changes):
    return SimpleNamespace(**(dict(lemma=lemma, pos='NOUN', case=case, number='sing') | changes))


class Dictionary:
    def __init__(self, word, rival):
        self.words = {word: [tag(word, 'accs')], rival: [tag(word, 'ablt')]}

    def analyses(self, word):
        return self.words.get(word, ())


class NounCaseFocusFormsTest(unittest.TestCase):
    def test_known_forms_supply_shared_equal_cost_unknown_corruption(self):
        for word, rival, typed in [('фотографию', 'фотографией', 'фотографие'),
                                   ('книгу', 'книгой', 'книго'),
                                   ('задачу', 'задачей', 'задаче'),
                                   ('песню', 'песней', 'песне')]:
            result = accusative_contrast(word, Dictionary(word, rival))
            self.assertEqual(dict(word=word, instrumental=rival, typed=typed, editCosts=[1., 1.]), result)

    def test_an_existing_dictionary_word_cannot_be_mislabeled_as_typo(self):
        dictionary = Dictionary('песню', 'песней')
        dictionary.words['песне'] = [tag('песню', 'datv')]
        self.assertIsNone(accusative_contrast('песню', dictionary))

    def test_ambiguous_or_wrong_case_number_pos_lemma_is_not_accepted(self):
        for side, extra in [('фотографию', tag('фотографию', 'datv')),
                            ('фотографию', tag('другое', 'accs')),
                            ('фотографией', tag('другое', 'ablt')),
                            ('фотографией', tag('фотографию', 'nomn')),
                            ('фотографию', tag('фотографию', 'accs', number='plur')),
                            ('фотографией', tag('фотографию', 'ablt', pos='ADJF'))]:
            dictionary = Dictionary('фотографию', 'фотографией')
            dictionary.words[side].append(extra)
            self.assertIsNone(accusative_contrast('фотографию', dictionary))
        dictionary = Dictionary('фотографию', 'фотографией')
        dictionary.words['фотографией'] = [tag('другой', 'ablt')]
        self.assertIsNone(accusative_contrast('фотографию', dictionary))

    def test_missing_and_unsupported_forms_have_no_guessed_result(self):
        dictionary = Dictionary('фотографию', 'фотографией')
        for word in [None, '', 'Фотографию', '@фотографию', 'фото', 'это-семью', 'я' * 17, 'луну']:
            self.assertIsNone(accusative_contrast(word, dictionary))

    def test_two_dictionary_instrumental_spellings_are_left_ambiguous(self):
        dictionary = Dictionary('семью', 'семьей')
        dictionary.words['семьёй'] = [tag('семью', 'ablt')]
        self.assertIsNone(accusative_contrast('семью', dictionary))


if __name__ == '__main__':
    unittest.main()
