from copy import deepcopy
import unittest
from right_context_prior_evidence import previous_word_evidence


def units(text):return len(text.encode('utf-16-le'))//2

def observation(prefix,original='готв',previous='готов',leading=' '):
    rendered=prefix+' ' if prefix else '';before=rendered+original;after=rendered+previous+' '
    assert rendered.endswith(leading)
    old=leading+original;new=leading+previous+' '
    return dict(inputChangedByTyping=False,beforeBoundary=dict(text=before,caret=units(before)),
       afterBoundary=dict(text=after,caret=units(after)),
       stateBeforeBoundary=dict(enabled=True,sessionId=1,typedWord=original,contextText=before),
       stateAfterBoundary=dict(enabled=True,sessionId=1,typedWord='',contextText=after),
       autoEdit=dict(committedStart=units(before)-units(old),original=old,applied=new,
          hasCorrectionCandidates=True,correctionGeneration=dict(original=original)))


class PriorEvidenceTest(unittest.TestCase):
    def test_raw_word_can_be_proven_without_a_fabricated_correction_root(self):
        o=observation('я',previous='готв');o['autoEdit']=None
        self.assertTrue(previous_word_evidence('я','готв',o)['owned'])

    def test_leading_comma_is_not_mistaken_for_part_of_the_original_spelling(self):
        o=observation('сказал,',leading=', ');before=deepcopy(o)
        self.assertTrue(previous_word_evidence('сказал,','готв',o)['owned'])
        self.assertEqual(before,o)
        o['autoEdit']['applied']=' готов '
        self.assertEqual('LEADING_BOUNDARY_CHANGED',previous_word_evidence('сказал,','готв',o)['reason'])

    def test_emoji_offsets_are_utf16_units_and_not_python_string_indices(self):
        o=observation('🙂 я')
        self.assertTrue(previous_word_evidence('🙂 я','готв',o)['owned'])
        o['afterBoundary']['caret']=len(o['afterBoundary']['text'])
        self.assertEqual('CARET_DIVERGENCE',previous_word_evidence('🙂 я','готв',o)['reason'])

    def test_stale_roots_first_character_loss_and_external_state_changes_refuse(self):
        o=observation('я');o['autoEdit']['committedStart']=0
        self.assertEqual('STALE_PREVIOUS_EDIT',previous_word_evidence('я','готв',o)['reason'])
        o=observation('я');o['beforeBoundary']['text']='я отв'
        self.assertEqual('INPUT_OR_PREFIX_CHANGED',previous_word_evidence('я','готв',o)['reason'])
        o=observation('я');o['stateAfterBoundary']['sessionId']=2
        self.assertEqual('PRIVATE_STATE_DIVERGENCE',previous_word_evidence('я','готв',o)['reason'])
        o=observation('я');o['stateAfterBoundary']['contextText']='чужое слово '
        self.assertEqual('PRIVATE_CONTEXT_DIVERGENCE',previous_word_evidence('я','готв',o)['reason'])


if __name__ == '__main__':unittest.main()
