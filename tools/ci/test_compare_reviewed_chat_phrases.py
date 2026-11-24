import unittest
import compare_reviewed_chat_phrases as subject


def row(after, changed):
    return {'id':'sample','typed':'слово','status':'COMPLETE','phraseStages':[
        {'wordIndex':0,'typed':'слово','after':after,'changed':changed}]}


class CompareTest(unittest.TestCase):
    def test_removed_and_new_are_distinguished(self):
        self.assertEqual(1,subject.compare([row('другое ',True)],[row('слово ',False)])['removedEdits'])
        self.assertEqual(1,subject.compare([row('слово ',False)],[row('другое ',True)])['newEdits'])

    def test_wrong_identity_and_incomplete_observation_fail(self):
        for other in (row('слово ',False)|{'id':'other'},row('слово ',False)|{'status':'FAILED'},
                      row('слово ',False)|{'phraseStages':[]}):
            with self.assertRaises(ValueError):subject.compare([row('слово ',False)],[other])


if __name__ == '__main__': unittest.main()
