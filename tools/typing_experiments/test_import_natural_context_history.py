import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from holdout_ledger import keys_for
from import_natural_context_history import verify_article,entries_for
from recover_legacy_holdout import load_generator
from recover_natural_context_history import FEATURE_NAMES, SEED, recover_pool
from right_context_sentence_audit import _source_hash


class Dictionary:
    def analyses(self,word):return [SimpleNamespace(lemma='готовый')] if word in ('готов','готовы') else []


def row(**changes):
    return dict(word='готовы',rival='готов',typed='готвоы',prefix='Они',rightContext=' были дома.',article='123',
        contextHash=_source_hash('Они','готовы',' были дома.'),selectionHash='a'*64)|changes


class NaturalHistoryTest(unittest.TestCase):
    def test_source_prefix_word_and_suffix_must_match_the_actual_article(self):
        generator=load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')
        verify_article('Они готовы были дома.',[row()],generator)
        with self.assertRaisesRegex(ValueError,'SOURCE_CAPTURE'):verify_article('Они готовы ушли.',[row()],generator)
        with self.assertRaisesRegex(ValueError,'WINDOW_IDENTITY'):verify_article('Они готовы были дома.',[row(contextHash='0'*64)],generator)

    def test_source_article_window_context_and_both_candidate_families_are_excluded(self):
        original=[row()];before=copy.deepcopy(original)
        entries,counts=entries_for('fixture',original,Dictionary(),{'file':'b'*64})
        self.assertEqual(before,original);self.assertEqual([],entries[0]['missingAxes'])
        self.assertEqual(keys_for([dict(families=['готовый'])],'family'),set(entries[0]['keys']['family']))
        self.assertEqual(1,counts['rows']);self.assertEqual([],counts['unresolvedCandidateAnalyses'])

    def test_unknown_rival_is_not_guessed_and_keeps_family_coverage_incomplete(self):
        entries,counts=entries_for('fixture',[row(rival='нераспознано')],Dictionary(),{'file':'b'*64})
        self.assertEqual(['family'],entries[0]['missingAxes']);self.assertEqual('historical-family-exclusion',entries[1]['usage'])
        self.assertEqual('rival',counts['unresolvedCandidateAnalyses'][0]['field'])

    def test_empty_and_duplicate_pool_identities_fail(self):
        for rows in ([],[row(),row()]):
            with self.assertRaises(ValueError):entries_for('fixture',rows,Dictionary(),{'file':'b'*64})

    def test_pool_recovery_requires_exact_historical_bytes_and_source(self):
        source = b'fixture source data'
        source_hash = hashlib.sha256(source).hexdigest()
        pair = dict(word='готовы', rival='готов', typed='готвоы', family='готовый', editCosts=[1, 1])
        split_byte = hashlib.sha256((SEED + ':family:готовый').encode()).digest()[0]
        expected = dict(pair, prefix='Они', rightContext=' были дома.', article='123',
                        source='ru-0012.parquet', contextHash=row()['contextHash'],
                        selectionHash=hashlib.sha256((SEED + ':wiki:123готовыОни').encode()).hexdigest(),
                        provisionalSplit='holdout' if split_byte % 2 else 'calibration')
        raw = (json.dumps(expected, ensure_ascii=False) + '\n').encode()
        row_path = 'build/fixture/contexts.unqualified.jsonl'
        source_path = 'build/fixture/ru-0012.parquet'
        bindings = {row_path: hashlib.sha256(raw).hexdigest(), source_path: source_hash}
        shard = dict(name='0012.parquet', bytes=len(source), sha256=source_hash)
        entries, facts = entries_for('fixture', [expected], Dictionary(), bindings.copy())
        generator = load_generator('2cbcb2508ef66b32a60b5c7665ad96c66dc1c6477c9da4ad6dde0ea969806e65')

        def features(_suffix, word):
            enabled = 'right_copula_number_supported' if word == 'готовы' else 'right_copula_number_conflict'
            return [int(name == enabled) for name in FEATURE_NAMES]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / shard['name']
            path.write_bytes(source)
            with (patch('recover_natural_context_history.find_forms', return_value=pair),
                  patch('recover_natural_context_history.RightContextGrammarFeatures') as grammar):
                grammar.return_value.extract.side_effect = features

                def recover(records):
                    return recover_pool(path, shard, entries[0], bindings, Dictionary(), generator,
                                        lambda _: records)

                records = [(['123'], ['Они готовы были дома.'])]
                self.assertEqual((raw, facts), recover(records))
                with self.assertRaisesRegex(ValueError, 'AMBIGUOUS_CAPTURE'):
                    recover(records + records)
                with self.assertRaisesRegex(ValueError, 'ORIGINAL_ROW_DIGEST'):
                    # The registries normalize case, but the original row bytes must match.
                    recover([(['123'], ['они готовы были дома.'])])
                path.write_bytes(b'changed source data')
                with self.assertRaisesRegex(ValueError, 'SHARD_IDENTITY'):
                    recover(records)


if __name__=='__main__':unittest.main()
