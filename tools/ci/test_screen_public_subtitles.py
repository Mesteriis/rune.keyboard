import copy
import json
import unittest
import screen_public_subtitles as subject


class SubtitleScreenTest(unittest.TestCase):
    def test_counts_filters_and_cross_split_without_text(self):
        def row(source,correction):return {'source':source,'correction':correction,'domain':'subtitles'}
        parts={'train':[row('это хорошо','это хорошо'),row('это ошбка','это ошибка'),row('Он здесь','Он здесь')],
               'test':[row('это хорошо','это хорошо'),row('да нет','да нет')]}
        result=subject.analyze(parts)
        self.assertEqual(1,result['exactCorrectedSentenceOverlap'])
        self.assertEqual(2,result['splits']['train']['eligibleCorrectedPhrases'])
        self.assertEqual(1,result['splits']['train']['eligibleUnchangedPhrases'])
        self.assertEqual(2,result['splits']['train']['eligibleUnchangedTokens'])
        self.assertFalse(result['qualified']);self.assertEqual(0,result['modelCalls'])
        self.assertNotIn('это хорошо',json.dumps(result,ensure_ascii=False))

    def test_invalid_split_domain_and_nonstring_refused(self):
        good={'train':[{'source':'да нет','correction':'да нет','domain':'subtitles'}],
              'test':[{'source':'да нет','correction':'да нет','domain':'subtitles'}]}
        for field,value in [('domain','reviews'),('source',None),('correction','')]:
            bad=copy.deepcopy(good);bad['train'][0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'SUBTITLE_ROW'):subject.analyze(bad)
        with self.assertRaisesRegex(ValueError,'SUBTITLE_SPLITS'):subject.analyze({'test':good['test']})


if __name__=='__main__':unittest.main()
