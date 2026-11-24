import unittest

import english_family_keys as subject
from holdout_ledger import keys_for as lexical_keys


class EnglishFamilyKeysTest(unittest.TestCase):
    def test_exact_lemma_namespace_and_apostrophe_normalization(self):
        self.assertEqual(subject.key_for('CAN’T'),subject.key_for("can't"))
        self.assertNotEqual(subject.key_for('go'),subject.key_for('went'))
        self.assertNotEqual(subject.key_for('go'),next(iter(lexical_keys([{'families':['go']}],'family'))))
        self.assertEqual({subject.key_for('go')},subject.keys_for(['Go','go']))

    def test_unresolved_or_non_lemma_shapes_are_rejected(self):
        for value in (None,'','_','two words','hyphen-word','école','a'*33,'a1',"'word", "word'"):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'EN_LEMMA_SCHEMA'):
                subject.key_for(value)
        for values in ([],None,'word'):
            with self.subTest(values=values),self.assertRaisesRegex(ValueError,'EN_LEMMA_SCHEMA'):
                subject.keys_for(values)


if __name__ == '__main__':unittest.main()
