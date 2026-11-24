import unittest
import hashlib
import json
from pathlib import Path
from audit_english_ewt_i_context import audit
import control_ledger


def sentence(text, word, tag):
    return f'# sent_id = x\n# text = {text}\n1\t{word}\t{word}\t{tag}\t_\t_\t0\troot\t_\t_\n'


class AuditEnglishContextTest(unittest.TestCase):
    def test_initial_replay_contexts_are_registered(self):
        root = Path(__file__).resolve().parents[2]
        path = root / 'tools/typing_experiments/a1_controls/initial-replay-v1.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        entries = {e['id']: e for e in control_ledger.load(root / 'tools/typing_experiments/control-ledger.json')['entries']}
        for language in ('en', 'es'):
            selected = [row for row in rows if row['language'] == language]
            entry = entries[f'a1-initial-disclosed-replay-{language}']
            self.assertEqual(len(selected), entry['rowCount'])
            self.assertEqual(sorted({control_ledger.key_for(row, 'regression') for row in selected}), entry['keys'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             entry['bindings'][str(path.relative_to(root))])

    def test_aligned_context_collision_without_exporting_source(self):
        data = (sentence('chapter I went', 'I', 'PRON') + '\n' +
                sentence('chapter i ended', 'i', 'NUM') + '\n').encode()
        result = audit(data)
        self.assertEqual(1, result['counts']['previous_word_collision_types'])
        self.assertEqual(1, result['counts']['lower_other_pos_space_word'])
        self.assertNotIn('chapter', str(result))

    def test_unaligned_occurrences_fail_closed_instead_of_fabricating_labels(self):
        result = audit((sentence('Baha\'i is here', 'here', 'ADV') + '\n').encode())
        self.assertEqual(1, result['counts']['sentences_unaligned'])
        self.assertEqual(1, result['counts']['occurrences_unaligned'])
        with self.assertRaises(ValueError): audit(b'# sent_id = x\n1\tbad\n')

    def test_end_of_sentence_is_not_classified_as_punctuation(self):
        result = audit((sentence('it is I', 'I', 'PRON') + '\n').encode())
        self.assertEqual(1, result['counts']['upper_pronoun_end_word'])


if __name__ == '__main__': unittest.main()
