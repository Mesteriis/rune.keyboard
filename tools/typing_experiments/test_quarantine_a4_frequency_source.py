import unittest
import quarantine_a4_frequency_source as subject


class A4SourceQuarantineTest(unittest.TestCase):
    def test_keys_are_unique_order_independent_and_namespaced(self):
        left,right=subject.article_keys(['9','1','42'])
        self.assertEqual((left,right),subject.article_keys(['42','9','1']))
        self.assertEqual(3,len(left));self.assertEqual(3,len(right));self.assertNotEqual(left,right)
        self.assertEqual(64,len(subject.digest(left)))

    def test_malformed_and_aliased_identifiers_fail_closed(self):
        for rows in ([],['0'],['-1'],['１'],['1','01'],['1',None]):
            with self.assertRaises(ValueError):subject.article_keys(rows)


if __name__ == '__main__': unittest.main()
