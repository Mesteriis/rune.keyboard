import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from holdout_ledger import assert_disjoint
from recover_legacy_holdout import load_generator
from recover_ranker_sources import SEED,recover_article,verify_reproduction,window_entry
from test_holdout_ledger import ledger


def row(prefix='Мы уже давно ',word='готовы',start=None):
    if start is None:start=len(prefix)
    context=hashlib.sha256((prefix.lower()+'\0'+word).encode()).hexdigest()
    identity='refine-'+hashlib.sha256((SEED+':123:'+str(start)+':'+context).encode()).hexdigest()[:24]
    return dict(id=identity,articleId='123',prefix=prefix,expectedSpelling=word,typed='готвы')


class RankerSourceTest(unittest.TestCase):
    def setUp(self):
        self.generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')

    def test_every_matching_occurrence_is_retained(self):
        value=row();text='Мы уже давно готовы'+(' идти домой'*30)+'. Мы уже давно готовы остаться тут.'
        windows=recover_article('123',text,[value],self.generator)
        self.assertEqual(2,len(windows[value['id']]))

    def test_historical_cyrillic_regex_keeps_mixed_script_boundary(self):
        value=row()
        windows=recover_article('123','Мы уже давно готовыx идти.',[value],self.generator)
        self.assertEqual(1,len(windows[value['id']]))

    def test_missing_or_changed_source_identity_fails_closed(self):
        value=row();text='Мы уже давно готовы идти.'
        for changed in (value|dict(id='refine-'+'0'*24),value|dict(expectedSpelling='готово'),value|dict(prefix='Чужой контекст '),value|dict(articleId='124')):
            with self.assertRaises(ValueError):recover_article('123',text,[changed],self.generator)
        with self.assertRaises(ValueError):recover_article('123',text,[value,value],self.generator)

    def test_recovered_context_is_independent_of_typo_and_article(self):
        value=row();windows=recover_article('123','Мы уже давно готовы идти.',[value],self.generator)
        entry,counts=window_entry('train',[value],windows,{'source':'a'*64})
        base=ledger(False);prior=copy.deepcopy(base['entries']);base['entries'].append(entry)
        self.assertEqual(1,counts['rows']);self.assertEqual(['family'],entry['missingAxes'])
        self.assertEqual(prior,base['entries'][:-1])
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([value|dict(article='456',typed='готовв')],base,kinds=('context',))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:sentence'):
            assert_disjoint([dict(contextHash=next(iter(windows[value['id']])))],base,kinds=('sentence',))

    def test_reproduction_requires_manifest_and_all_six_original_file_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            original=Path(folder)/'original';reproduced=Path(folder)/'reproduced';original.mkdir();reproduced.mkdir()
            files={part+'-'+kind+'.jsonl':hashlib.sha256(b'public\n').hexdigest() for part in ('train','dev','test') for kind in ('rows','text')}
            manifest=json.dumps(dict(files=files)).encode();digest=hashlib.sha256(manifest).hexdigest()
            for directory in (original,reproduced):
                (directory/'manifest.json').write_bytes(manifest)
                for name in files:(directory/name).write_bytes(b'public\n')
            with patch('recover_ranker_sources.MANIFEST_SHA',digest):
                verify_reproduction(original,reproduced)
                (reproduced/'test-text.jsonl').write_bytes(b'changed\n')
                with self.assertRaisesRegex(ValueError,'REPRODUCTION_FILE'):verify_reproduction(original,reproduced)
                (reproduced/'manifest.json').write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError,'REPRODUCTION_MANIFEST'):verify_reproduction(original,reproduced)


if __name__=='__main__':unittest.main()
