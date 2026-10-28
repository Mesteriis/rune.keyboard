import unittest
from calibrate_joint_followup import final_word

class JointFollowupTest(unittest.TestCase):
    def record(self,**changes):
        return dict(dict(candidate='слово',baseline='слово',original='сдово',topScore=.8,margin=.5),**changes)
    def test_existing_correction_is_retained_or_original_but_never_a_third_word(self):
        self.assertEqual('слово',final_word(self.record(),.5,.2))
        self.assertEqual('сдово',final_word(self.record(candidate='снова'),.5,.2))
        self.assertEqual('сдово',final_word(self.record(),.9,.2))
    def test_new_acquisition_requires_its_own_threshold(self):
        r=self.record(baseline='сдово')
        self.assertEqual('слово',final_word(r,.5,.2))
        self.assertEqual('сдово',final_word(r,.9,.2))
