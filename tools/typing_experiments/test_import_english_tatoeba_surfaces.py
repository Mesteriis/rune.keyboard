import bz2
import copy
import hashlib
import json
import unittest
from unittest import mock

import control_ledger as control
import import_english_tatoeba_surfaces as subject
from public_corpus_preparation_v1 import preflight
from test_public_corpus_preparation_v1 import candidate, controls


class TatoebaSurfaceExclusionsTest(unittest.TestCase):
    def test_source_parser_preserves_words_and_rejects_partial_tokens(self):
        raw=bz2.compress("1\teng\tmyopia can't foo-bar café dog2 ab_cd\tpublic\n".encode())
        lock=json.dumps({'compressedSha256':hashlib.sha256(raw).hexdigest(),'license':'CC0-1.0'}).encode()
        with mock.patch.object(subject.source,'DIGEST',hashlib.sha256(raw).hexdigest()), \
                mock.patch.object(subject,'LOCK_SHA',hashlib.sha256(lock).hexdigest()):
            keys,rows,context,verified=subject.extract(raw,lock)
        self.assertEqual({control.surface_key('en','myopia'),control.surface_key('en',"can't")},keys)
        self.assertEqual(2,rows)
        self.assertEqual(1,len(verified))
        self.assertEqual(64,len(context))

    def test_altered_source_and_missing_parent_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_IDENTITY'):
            subject.extract(b'changed',subject.LOCK.read_bytes())
        value=json.loads(subject.LEDGER.read_bytes())
        value['entries']=[e for e in value['entries'] if e['id']!=subject.source.ENTRY]
        with self.assertRaisesRegex(ValueError,'PARENT'):
            subject.entry(value,b'',b'')

    def test_disclosed_surface_reaches_real_family_gate(self):
        value=json.loads(subject.LEDGER.read_bytes())
        old=copy.deepcopy(value);old['entries']=[e for e in old['entries'] if e['id']!=subject.ENTRY]
        row=candidate(language='en',sourceRepository='tatoeba',article='tatoeba:999999999',
                      sentenceHash='f'*64,prefix='a ',typed='myopia',expectedSpelling='myopia')
        before=preflight([row],'spelling',old,controls(),'new-families')
        self.assertEqual(0,before['unsupportedTargetOverlaps'])
        after=preflight([row],'spelling',value,controls(),'new-families')
        self.assertEqual(1,after['unsupportedTargetOverlaps'])
        self.assertEqual('BLOCKED_OVERLAP',after['status'])
        self.assertIn('en',after['unsupportedLexicalLanguages'])
        self.assertEqual(0,preflight([row],'spelling',value,controls(),'new-sentences')['unsupportedTargetOverlaps'])


if __name__ == '__main__':
    unittest.main()
