import unittest

import a3_taiga_propn_screen as screen
import control_ledger as controls
from test_control_ledger import registry


class TaigaPropnScreenTest(unittest.TestCase):
    def test_requires_title_propn_rare_and_unambiguous_alignment(self):
        def block(text, word, pos='PROPN'):
            return f'# text = {text}\n1\t{word}\t_\t{pos}\t_\t_\t0\troot\t_\t_\n'
        data = (block('Здравствуй Ира', 'Ира') + '\n' + block('Ира Ира', 'Ира') + '\n' +
                block('тут Ива', 'Ива') + '\n' + block('там Ира', 'Ира', 'NOUN')).encode()
        rows, counts = screen.select(data, {'ира', 'ива'}, {'ива'})
        self.assertEqual((2, 1, 1), (counts['eligibleTokens'], counts['unaligned'], len(rows)))
        self.assertEqual(('Здравствуй', 'ира'), (rows[0]['prefix'], rows[0]['typed']))
        self.assertNotIn('expectedSpelling', rows[0])
        result = screen.register(registry(), rows, {'fixture': 'a' * 64})
        with self.assertRaisesRegex(ValueError, 'CONTROL_SURFACE_OVERLAP'):
            controls.assert_disjoint([rows[0] | {'prefix': 'иной'}], result, 'regression')

    def test_rejects_malformed_token(self):
        with self.assertRaisesRegex(ValueError, 'TAIGA_TOKEN_SHAPE'):
            screen.select('# text = Ира\n1\tИра\n'.encode(), {'ира'}, set())
