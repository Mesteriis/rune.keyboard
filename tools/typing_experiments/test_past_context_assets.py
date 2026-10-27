from types import SimpleNamespace
import unittest
from past_context_assets import past_query_keys


class Dictionary:
    @property
    def words(self):return self
    def iteritems(self):return iter([('были',(0,0)),('были',(1,0)),('иди',(2,0)),('пришёл',(3,0)),('тест_имя',(4,0))])
    def build_tag_info(self,paradigm,index):
        return [SimpleNamespace(POS='NOUN',tense=None),SimpleNamespace(POS='VERB',tense='past'),
                SimpleNamespace(POS='VERB',tense=None),SimpleNamespace(POS='VERB',tense='past'),
                SimpleNamespace(POS='VERB',tense='past')][paradigm]


class PastAssetsTest(unittest.TestCase):
    def test_all_dictionary_readings_are_checked_and_imperatives_are_not_past(self):
        keys=past_query_keys(Dictionary())
        self.assertIn('были',keys);self.assertNotIn('иди',keys)
        self.assertNotIn('тест_имя',keys)

    def test_e_yo_query_aliases_follow_dictionary_analyzer_semantics(self):
        self.assertEqual({'были','пришел','пришёл'},past_query_keys(Dictionary()))


if __name__=='__main__':unittest.main()
