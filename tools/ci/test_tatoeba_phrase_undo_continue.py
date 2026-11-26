import copy
import unittest
import tatoeba_phrase_undo_continue as subject


def example():
    return {'id':'a#0','typed':'слово далее','status':'COMPLETE','phraseStages':[
        {'wordIndex':0,'typed':'слово','before':'слово','after':'Слово ','changed':True,'prefixChanged':False,
         'automaticEdit':True,'undoResult':'HANDLED','undoExact':True,'afterUndoBoundary':'слово '},
        {'wordIndex':1,'typed':'далее','before':'слово далее','after':'слово далее ','changed':False,'prefixChanged':False}]}


class ContinueTest(unittest.TestCase):
    def test_continuation_requires_reproduced_edit_exact_undo_and_following_word(self):
        target={'id':'a#0','phrase':'слово далее','index':0,'before':'слово','after':'Слово '}
        row=example();self.assertEqual((1,0),subject.verify(target,row))
        for key,value in (('undoExact',False),('afterUndoBoundary','Слово '),('after','Другое ')):
            altered=copy.deepcopy(row);altered['phraseStages'][0][key]=value
            with self.assertRaises(ValueError):subject.verify(target,altered)
        altered=copy.deepcopy(row);altered['phraseStages'][1]['before']='Слово далее'
        with self.assertRaisesRegex(ValueError,'CONTINUE_SESSION'):subject.verify(target,altered)

    def test_selection_excludes_final_word(self):
        row=example();row['id']='a';row['phraseStages'][1]['automaticEdit']=True
        self.assertEqual([0],[v['index'] for v in subject.select([('a','слово далее')],[row])])


if __name__=='__main__':unittest.main()
