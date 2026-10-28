import unittest
import neighbor_recovery as recovery

class NeighborRecoveryTest(unittest.TestCase):
    def test_neighbors_and_mixed_distance(self):
        self.assertEqual(2,recovery.distance('рооверка','проверка'))
        self.assertEqual(3,recovery.distance('ролверка','проверка'))
        self.assertGreater(recovery.distance('zzzzzzz','проверка'),3)
        for group in recovery.GROUPS:
            value=recovery.typo('проверка',group,'test',{'проверка'})
            self.assertIsNotNone(value)
            self.assertEqual(int(group[-1]),recovery.distance(value,'проверка'))
    def test_zero_error_threshold_excludes_wrong_and_tied_winners(self):
        records=[dict(topScore=.9,margin=.8,correct=True,control=False),
                 dict(topScore=.8,margin=.7,correct=False,control=False),
                 dict(topScore=.7,margin=.9,correct=False,control=True)]
        policy=recovery.calibrate(records)
        self.assertIsNotNone(policy)
        selected=[r for r in records if r['topScore']>=policy['minimumScore'] and r['margin']>=policy['minimumMargin']]
        self.assertEqual([records[0]],selected)
        self.assertIsNone(recovery.calibrate(records[1:]))
        self.assertIsNone(recovery.calibrate([dict(topScore=.9,margin=0.,correct=True,control=False)]))
    def test_mutations_are_repeatable_and_not_known_words(self):
        known={'клавиатура','проверка','работает'}
        for word in known:
            for group in recovery.GROUPS:
                a=recovery.typo(word,group,'fixed',known)
                self.assertEqual(a,recovery.typo(word,group,'fixed',known))
                if a is not None:self.assertNotIn(a,known)

if __name__=='__main__':unittest.main()
