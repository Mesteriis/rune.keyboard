import hashlib
import shutil
import unittest
from pathlib import Path
import tempfile
from control_ledger import SCHEMA,key_for
from import_control_components import validate_rows,build,read_components,ROOT,CORPORA
from control_ledger import load


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


    def test_archived_components_recreate_current_control_keys(self):
        existing = {e['id']: e for e in load(ROOT / 'tools/typing_experiments/control-ledger.json')['entries']}
        for kind, expected_rows in (('punctuation', 1200), ('protected', 1800)):
            with self.subTest(kind=kind):
                ledger, receipt = build(ROOT, kind)
                self.assertEqual({'qualification-v2': 'historical-files', 'compact-v3': 'verified-archive',
                                  'compact-v4': 'verified-archive'}, receipt['corpusStorage'])
                self.assertEqual([expected_rows] * 3, [x['rows'] for x in receipt['counts'].values()])
                self.assertEqual(9, len(ledger['entries']))
                for entry in ledger['entries']:
                    prior = existing[entry['id']]
                    self.assertEqual(prior['rowCount'], entry['rowCount'])
                    self.assertEqual(prior['keys'], entry['keys'])

    def test_partial_original_set_does_not_fall_back(self):
        directory, expected, _ = CORPORA['compact-v3']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root / directory / 'manifest.json'
            path.parent.mkdir(parents=True); path.write_bytes(b'partial')
            with self.assertRaisesRegex(ValueError, 'CONTROL_PARTIAL_CORPUS'):
                read_components(root, 'compact-v3', directory, expected, ['punctuation-ru.jsonl'])
            with self.assertRaisesRegex(ValueError, 'CONTROL_COMPONENT_NAMES'):
                read_components(root, 'compact-v3', directory, expected, ['../other'])

    def test_corrupt_archive_is_rejected_when_original_files_are_absent(self):
        directory, expected, _ = CORPORA['compact-v3']
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); dest = root / 'tools/typing_experiments'; dest.mkdir(parents=True)
            shutil.copy2(source / 'check_historical_qualification_archives.py', dest)
            shutil.copytree(source / 'historical-qualification-v3-v4', dest / 'historical-qualification-v3-v4')
            archive = dest / 'historical-qualification-v3-v4/qualification-v3.tar.bz2'
            archive.write_bytes(archive.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ARCHIVE_IDENTITY'):
                read_components(root, 'compact-v3', directory, expected, ['punctuation-ru.jsonl'])

    def test_changed_original_component_is_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); directory = 'legacy'; dest = root / directory; dest.mkdir()
            data = b'original'
            manifest = json.dumps({'files': {'punctuation-ru.jsonl': hashlib.sha256(data).hexdigest()}}).encode()
            (dest / 'manifest.json').write_bytes(manifest)
            (dest / 'punctuation-ru.jsonl').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'CONTROL_COMPONENT_IDENTITY'):
                read_components(root, 'fixture', directory, hashlib.sha256(manifest).hexdigest(), ['punctuation-ru.jsonl'])


if __name__=='__main__':unittest.main()
