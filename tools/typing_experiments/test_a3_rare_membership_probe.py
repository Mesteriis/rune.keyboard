import unittest
from a3_rare_membership_probe import inputs


class RareMembershipInputsTest(unittest.TestCase):
    def test_selects_short_cyrillic_rare_keys_without_lowercase_evidence(self):
        self.assertEqual(['мир'], inputs({'мир': 1, 'кот': 2, 'длинно': 3, 'abc': 4}, {'кот'}))
