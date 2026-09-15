import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace

from personal_holdout import synthetic_rows, verify_dataset
from telegram_style import build_model, _json_bytes, _sha


class Lexicon:
    def analyses(self, word):
        if word in {'шкафов','домами','лампой'}:
            return (SimpleNamespace(grammemes=frozenset()),)
        if word == 'москвы':
            return (SimpleNamespace(grammemes=frozenset({'Geox'})),)
        return ()


class PersonalHoldoutTest(unittest.TestCase):
    def test_pairs_are_distinct_targets_and_context_never_crosses_sentence(self):
        rows=synthetic_rows(['старая. несколько шкафов', 'несколько шкафов', 'с лампой'],Lexicon(),10)
        self.assertEqual(len(rows),4)
        typo=[r for r in rows if r['cohort']=='typo']
        self.assertEqual(len({r['expectedSpelling'] for r in typo}),2)
        self.assertTrue(all(r['prefix'] in ('несколько','с') for r in rows))
        self.assertTrue(all(r['typed'] != r['expectedSpelling'] for r in typo))
        self.assertEqual(rows,synthetic_rows(['с лампой','несколько шкафов','старая. несколько шкафов'],Lexicon(),10))

    def test_unknown_and_proper_names_are_excluded(self):
        self.assertEqual(synthetic_rows(['из москвы абракадабра'],Lexicon(),10),[])

    def test_known_corruption_is_never_a_typo(self):
        class AllKnown:
            def analyses(self,word): return (SimpleNamespace(grammemes=frozenset()),)
        self.assertEqual(synthetic_rows(['со шкафами'],AllKnown(),10),[])

    def dataset(self,path):
        train=['с лампой']; val=['несколько шкафов']
        data={'train.jsonl':b''.join(_json_bytes({'text':s}) for s in train),
              'validation.jsonl':b''.join(_json_bytes({'text':s}) for s in val),
              'model.json':_json_bytes(build_model(train))}
        for n,b in data.items():(path/n).write_bytes(b)
        receipt=dict(schemaVersion=1,validationEligible=True,trainChatHashes=['a'],validationChatHashes=['b'],
            artifactSha256={n:_sha(b) for n,b in data.items()},trainingSha256=build_model(train)['trainingSha256'])
        (path/'receipt.json').write_text(json.dumps(receipt))
        return receipt

    def test_dataset_verifies_consumed_bytes(self):
        with TemporaryDirectory() as temp:
            p=Path(temp);self.dataset(p)
            self.assertEqual(verify_dataset(p)[0],['несколько шкафов'])
            (p/'validation.jsonl').write_text('{"text":"changed"}\n')
            with self.assertRaises(ValueError):verify_dataset(p)

    def test_chat_overlap_is_rejected(self):
        with TemporaryDirectory() as temp:
            p=Path(temp);r=self.dataset(p);r['validationChatHashes']=['a']
            (p/'receipt.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):verify_dataset(p)

    def test_message_overlap_is_rejected_even_with_updated_receipt(self):
        with TemporaryDirectory() as temp:
            p=Path(temp);r=self.dataset(p);data=(p/'train.jsonl').read_bytes()
            (p/'validation.jsonl').write_bytes(data);r['artifactSha256']['validation.jsonl']=_sha(data)
            (p/'receipt.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):verify_dataset(p)


if __name__=='__main__':unittest.main()
