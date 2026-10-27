from pathlib import Path
from types import SimpleNamespace
import hashlib
import tempfile
import unittest
from contextual_assets import write_index,grammar_payload,GRAMMAR_MAGIC
from right_context_side_forms import grammar_word_sets,non_predicate_contrast


def tag(pos,lemma,number='sing',case=None):
    return SimpleNamespace(pos=pos,lemma=lemma,number=number,gender=None,case=case,person=None)


class Dictionary:
    def analyses(self,word):
        return {'видел':[tag('VERB','видеть')],'виден':[tag('ADJS','видный')],
                'видны':[tag('ADJS','видный','plur')]}.get(word,())


class SideFormsTest(unittest.TestCase):
    def test_locked_grammar_projection_preserves_predicate_and_nominative_sets(self):
        values={'видел':[tag('VERB','видеть')],'виден':[tag('ADJS','видный')],
                'они':[tag('NPRO','они','plur','nomn')],'им':[tag('NPRO','они','plur','datv')]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'grammar.bin';write_index([(w,grammar_payload(values[w])) for w in sorted(values)],path,GRAMMAR_MAGIC);blob=path.read_bytes()
        predicates,nominatives=grammar_word_sets(blob,hashlib.sha256(blob).hexdigest())
        self.assertEqual({'виден'},predicates);self.assertEqual({'они'},nominatives)
        for data,digest in [(blob,'0'*64),(blob[:-1],hashlib.sha256(blob[:-1]).hexdigest()),(b'',hashlib.sha256(b'').hexdigest())]:
            with self.assertRaises(ValueError):grammar_word_sets(data,digest)

    def test_a_nonpredicate_source_and_actual_adjective_share_an_unknown_corruption(self):
        lexicon=Dictionary();result=non_predicate_contrast('видел',lexicon,{'виден','видны'})
        self.assertEqual(('видеть','видный'),(result['family'],result['rivalFamily']))
        self.assertFalse(lexicon.analyses(result['typed']));self.assertEqual(2,len(result['editCosts']))
        self.assertIsNone(non_predicate_contrast('виден',lexicon,{'виден','видны'}))
        self.assertIsNone(non_predicate_contrast('неизвестный',lexicon,{'виден'}))


if __name__ == '__main__':unittest.main()
