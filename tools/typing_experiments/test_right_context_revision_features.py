import unittest
from right_context_revision_features import FEATURES, revision_features


class Right:
    def __init__(self, values=(0.0,)*16):self.values=values;self.arguments=[]
    def extract(self,context,candidate):self.arguments.append((context,candidate));return self.values


class RevisionFeaturesTest(unittest.TestCase):
    def test_applied_word_identity_disambiguates_retention_without_using_a_label(self):
        right=Right();a=revision_features([0.5]*146,right,' будут ','готов','готов')
        b=revision_features([0.5]*146,right,' будут ','готовы','готов')
        self.assertEqual(FEATURES,len(a));self.assertEqual(a[:-1],b[:-1])
        self.assertEqual((1.0,0.0),(a[-1],b[-1]))
        self.assertEqual([(' будут ','готов')]*2,right.arguments)
        self.assertEqual(1.0,revision_features([0.0]*146,right,' ','ЁЛКИ','е\u0308лки')[-1])

    def test_base_and_right_values_are_preserved_in_order_and_finite(self):
        base=[i/146 for i in range(146)];right=tuple(i/16 for i in range(16))
        values=revision_features(base,Right(right),' буду ','готов','готовы')
        self.assertEqual(tuple(base),values[:146]);self.assertEqual(right,values[146:162])
        for base,right in [([0.0]*145,Right()),([0.0]*146,Right((0.0,)*15)),([float('nan')]*146,Right()),([0.0]*146,Right((float('inf'),)*16))]:
            with self.assertRaises(ValueError):revision_features(base,right,' ','готов','готов')


if __name__ == '__main__':unittest.main()
