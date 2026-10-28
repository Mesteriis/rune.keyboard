import unittest
from conversation_acceptance import candidate_gate


def metrics(correct=190, wrong=10):
    return dict(newCorrect=correct, newWrong=wrong, controlChanges=0,
                priorCorrectLosses=0, netCorrect=correct)


class ConversationAcceptanceTest(unittest.TestCase):
    def test_95_percent_boundary_and_previous_audit(self):
        self.assertTrue(candidate_gate(metrics(), required_precision=.95))
        self.assertFalse(candidate_gate(metrics(189, 11), required_precision=.95))
        self.assertTrue(candidate_gate(metrics(466, 5), required_precision=.95))
        self.assertFalse(candidate_gate(metrics(466, 5), required_precision=.99))

    def test_precision_does_not_remove_control_volume_or_loss_guards(self):
        for name in ('controlChanges', 'priorCorrectLosses'):
            value = metrics(); value[name] = 1
            self.assertFalse(candidate_gate(value, required_precision=.95))
        self.assertFalse(candidate_gate(metrics(99, 0), required_precision=.95))
        value = metrics(); value['netCorrect'] = 0
        self.assertFalse(candidate_gate(value, required_precision=.95))

    def test_invalid_policy_and_counts_fail(self):
        for precision in (0, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                candidate_gate(metrics(), required_precision=precision)
        value = metrics(); value['newWrong'] = -1
        with self.assertRaises(ValueError): candidate_gate(value, required_precision=.95)
        value = metrics(); value['netCorrect'] = float('nan')
        with self.assertRaises(ValueError): candidate_gate(value, required_precision=.95)


if __name__ == '__main__':
    unittest.main()
