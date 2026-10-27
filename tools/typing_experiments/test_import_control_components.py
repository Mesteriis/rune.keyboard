import hashlib
import unittest
from pathlib import Path
import tempfile
from control_ledger import SCHEMA,key_for
from import_control_components import validate_rows,build


def row():
    value=dict(id='p',language='ru',task='punctuation',cohort='punctuation',split='calibration',noAuto=True,
        prefix='Текст',currentWord='слово',expectedBoundary=', ',boundaries=[' ', ', ', ': ', '. '],expectedCandidate=1)
    identity=hashlib.sha256('7:punctuation:ru:, :Текст:слово'.encode()).hexdigest()
    return value|dict(template='calibration-punctuation-'+identity,family='punctuation:'+identity)


class ImportControlTest(unittest.TestCase):
    def test_original_punctuation_selection_hash_and_boundary_label_are_verified(self):
        validate_rows([row()],'punctuation',7)
        for change in (dict(template='other'),dict(prefix='Иной'),dict(currentWord='другое'),dict(expectedCandidate=0),dict(noAuto=False),dict(language='fr')):
            with self.assertRaises(ValueError):validate_rows([row()|change],'punctuation',7)

    def test_protected_tokens_require_original_unchanged_candidate(self):
        value=dict(id='a',language='en',task='spelling',cohort='protected',split='holdout',noAuto=True,
                   prefix='Keep',typed='API36',expectedCandidate=0,candidates=[' API36',' API3'])
        validate_rows([value],'protected')
        for change in (dict(expectedCandidate=True),dict(expectedCandidate=1),dict(candidates=[' api36']),dict(noAuto=False)):
            with self.assertRaises(ValueError):validate_rows([value|change],'protected')

    def test_empty_and_duplicate_source_ids_fail(self):
        for rows in ([],[row(),row()]):
            with self.assertRaises(ValueError):validate_rows(rows,'punctuation',7)

    def test_duplicate_component_import_fails_before_accessing_original_files(self):
        value=dict(language='ru',prefix='Сохранить',typed='API36')
        base=dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['pending'],entries=[
            dict(id='existing',kind='protected',language='ru',rowCount=1,bindings={'file':'a'*64},keys=[key_for(value,'protected')])])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'ALREADY_IMPORTED'):build(Path(folder),'protected',base)


if __name__=='__main__':unittest.main()
