import unittest
import audit_wordrank_source_boundaries as subject


def row(identity,target='слово',prefix='текст '):
    return dict(id=identity,language='ru',articleId=identity,prefix=prefix,expectedSpelling=target)


class SourceBoundariesTest(unittest.TestCase):
    def test_standalone_compound_mixed_and_ambiguous(self):
        rows=[row('1'),row('2'),row('3'),row('4')]
        articles={'1':'текст слово здесь','2':'текст слово-форма здесь',
                  '3':'текст словоі здесь','4':'текст слово здесь и текст слово-форма'}
        found,counts=subject.inspect(rows,articles)
        self.assertEqual((1,1,1,1),tuple(counts[k] for k in ('standaloneRows','hyphenRows','alphanumericRows','ambiguousBoundary')))
        self.assertEqual({'слово-форма','словоі'},{v['typed'] for v in found})
        self.assertEqual(1,counts['multipleSourceMatches'])

    def test_missing_duplicate_and_unsafe_left_boundary_fail(self):
        r=row('1')
        with self.assertRaises(ValueError):subject.inspect([r],{})
        with self.assertRaises(ValueError):subject.inspect([r,r],{'1':'текст слово'})
        with self.assertRaises(ValueError):subject.inspect([r],{'1':'текст иной'})
        with self.assertRaises(ValueError):subject.inspect([row('1',prefix='текст')],{'1':'текстслово'})


if __name__=='__main__':unittest.main()
