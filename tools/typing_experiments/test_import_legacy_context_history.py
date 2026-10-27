from types import SimpleNamespace
import unittest
from holdout_ledger import keys_for
from import_legacy_context_history import captures,entries_for
from recover_legacy_holdout import load_generator


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')] if word=='готовы' else []


def row(**changes):return dict(id='a',language='ru',split='calibration',source='0019.parquet',article='123',word='готовы',
    prefix='Они',typed='готвоы',expectedSpelling='готовы',cohort='typo',group='typo',family='form:готовы')|changes


class LegacyContextTest(unittest.TestCase):
    def test_actual_source_capture_preserves_historical_hyphen_boundaries(self):
        generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
        result=captures('Они готовы-то были дома.',{('готовы','Они')},generator)
        self.assertEqual(1,len(result[('готовы','Они')]))
        with self.assertRaisesRegex(ValueError,'SOURCE_CAPTURE'):captures('Они подготовились.',{('готовы','Они')},generator)

    def test_all_matching_windows_and_dictionary_families_replace_no_surface_labels(self):
        windows={('0019.parquet','123','готовы','Они'):{'a'*64,'b'*64}}
        entries,counts=entries_for('fixture','calibration',[row()],windows,Dictionary(),{'file':'c'*64})
        self.assertEqual(2,counts['sourceWindows']);self.assertEqual([],entries[0]['missingAxes'])
        self.assertEqual(keys_for([dict(families=['готовый'])],'family'),set(entries[0]['keys']['family']))

    def test_protected_mentions_do_not_become_dictionary_family_guesses(self):
        windows={('0019.parquet','123','готовы','Они'):{'a'*64}}
        value=row(typed='@готовы',expectedSpelling='@готовы',cohort='correct',group='protected',noAuto=True)
        _,counts=entries_for('fixture','calibration',[value],windows,Dictionary(),{'file':'c'*64})
        self.assertEqual([],counts['unresolvedRows'])
        with self.assertRaises(ValueError):entries_for('fixture','calibration',[value|dict(noAuto=False)],windows,Dictionary(),{'file':'c'*64})

    def test_duplicate_and_wrong_scope_rows_fail(self):
        windows={('0019.parquet','123','готовы','Они'):{'a'*64}}
        for rows in ([row(),row()],[row(language='en')],[row(split='holdout')]):
            with self.assertRaises(ValueError):entries_for('fixture','calibration',rows,windows,Dictionary(),{'file':'c'*64})


if __name__=='__main__':unittest.main()
