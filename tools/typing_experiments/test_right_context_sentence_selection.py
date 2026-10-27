import copy
import hashlib
import re
import unittest
from right_context_sentence_selection import adjacent_russian_pairs,choose_article_contexts


def row(group,part='calibration',order=1):
    h=lambda s:hashlib.sha256(s.encode()).hexdigest()
    return dict(article='123',sideGroup=group,part=part,selectionHash=f'{order:064x}',contextHash=h(group+part+str(order)))


class SentenceSelectionTest(unittest.TestCase):
    def test_every_adjacent_pair_is_seen_with_exact_source_offsets(self):
        text='теперь готов был он'
        pairs=list(adjacent_russian_pairs(text))
        self.assertEqual([('теперь','готов'),('готов','был'),('был','он')],[(m['word'],m['right']) for m in pairs])
        self.assertTrue(all(text[m.start('word'):m.end('word')]==m['word'] for m in pairs))
        old=list(re.finditer(r'(?<![\w-])(?P<word>[а-яё]{3,20})[ \t]+(?P<right>[а-яё]{1,32})(?![\w-])',text))
        self.assertNotIn(('готов','был'),[(m['word'],m['right']) for m in old])

    def test_identifiers_hyphens_and_line_breaks_cannot_be_laundered_into_pairs(self):
        for text in ['prefix_готов был ','prefix-готов был ','готов был_имя ','готов был-то ','готов\nбыл ']:
            self.assertFalse(list(adjacent_russian_pairs(text)))
        self.assertEqual([('готов','был')],[(m['word'],m['right']) for m in adjacent_russian_pairs('готов\tбыл,')])

    def test_negative_priority_does_not_discard_another_group_in_the_same_article(self):
        choices=[row('hard_other_part_negative'),row('matched_copula_positive'),row('direct_subject_positive')];before=copy.deepcopy(choices)
        chosen=choose_article_contexts(choices,article='123',seed='fixed')
        self.assertEqual({r['sideGroup'] for r in choices},{r['sideGroup'] for r in chosen})
        self.assertEqual(before,choices)

    def test_article_never_crosses_parts_and_selection_is_order_and_score_independent(self):
        choices=[row(g,p,i) for g in ['positive','negative'] for p in ['calibration','holdout'] for i in [2,1]]
        chosen=choose_article_contexts(choices,article='123',seed='fixed')
        self.assertEqual(1,len({r['part'] for r in chosen}));self.assertEqual(2,len(chosen))
        self.assertEqual(chosen,choose_article_contexts(list(reversed(choices)),article='123',seed='fixed'))
        scored=[r|dict(score=int(r['selectionHash'],16),expectedSpelling='ignored') for r in choices]
        self.assertEqual([r['contextHash'] for r in chosen],[r['contextHash'] for r in choose_article_contexts(scored,article='123',seed='fixed')])
        self.assertTrue(all(r['selectionHash']==f'{1:064x}' for r in chosen))

    def test_missing_part_article_or_hash_evidence_fails_closed(self):
        for invalid in [row('positive')|dict(article='999'),row('positive')|dict(part='train'),row('positive')|dict(selectionHash='')]:
            with self.assertRaises(ValueError):choose_article_contexts([invalid],article='123',seed='fixed')


if __name__=='__main__':unittest.main()
