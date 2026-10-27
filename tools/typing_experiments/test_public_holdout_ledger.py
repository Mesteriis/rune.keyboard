from pathlib import Path
import unittest

from holdout_ledger import assert_disjoint, load_ledger


class PublicLedgerSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.ledger = load_ledger(Path(__file__).with_name('holdout-ledger.json'))

    def test_historical_entries_cannot_disappear_from_the_bootstrap_snapshot(self):
        expected = {f'public-spelling-v{v}' for v in range(7, 13)} | {
            'public-right-context-available-v6-calibration',
            'public-right-context-available-v6-holdout',
            'authored-right-context-supervised-families-v12',
        }
        self.assertTrue(expected <= {e['id'] for e in self.ledger['entries']})

    def test_known_public_article_is_blocked_without_any_build_directory(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='8825104')], self.ledger, kinds=('article',))

    def test_recovered_historical_article_is_blocked_without_build(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='5156102')], self.ledger, kinds=('article',))

    def test_recovered_dictionary_family_is_blocked_without_morphology(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['жара'])], self.ledger, kinds=('family',))

    def test_ranker_text_article_and_training_family_are_persisted(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='3069606')], self.ledger, kinds=('article',))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['ранний'])], self.ledger, kinds=('family',), usages=('supervised',))

    def test_joint_history_article_is_blocked_without_the_original_corpus(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='5045254')], self.ledger, kinds=('article',))

    def test_spelling_v6_article_is_blocked_without_original_inputs(self):
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='5011218')], self.ledger, kinds=('article',))

    def test_early_qualification_context_is_blocked_without_original_inputs(self):
        row=dict(prefix='В ходе работы над направлением могут быть созданы: биопротезы с прямым нервным',
                 expectedSpelling='управлением',typed='инаяопечатка')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([row],self.ledger,kinds=('context',))

    def test_recovered_early_article_is_blocked_without_original_inputs(self):
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='4027525')],self.ledger,kinds=('article',))

    def test_all_verified_natural_context_pools_survive_without_original_files(self):
        entries=[e for e in self.ledger['entries'] if e['id'].startswith('public-natural-context-pool-')]
        self.assertEqual(7,len(entries));self.assertEqual(1204,sum(e['rowCount'] for e in entries))
        self.assertTrue(all(not e['missingAxes'] and set(e['keys'])=={'article','sentence','context','family'} for e in entries))

    def test_tatoeba_source_sentence_and_promoted_training_families_are_persisted(self):
        row=dict(sourceRepository='tatoeba',language='ru',article='tatoeba:11122358',sentenceHash='26454da27d2d82877e728be5c9611a8342d63a3e6f302f116d749cb1c28a2542')
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:article'):assert_disjoint([row],self.ledger,kinds=('article',))
        entries={e['id']:e for e in self.ledger['entries'] if e['id'].startswith('public-tatoeba-history-')}
        self.assertEqual(29,len(entries));self.assertEqual('supervised',entries['public-tatoeba-history-promoted-followon-holdout-families']['usage'])

    def test_derived_tatoeba_aliases_do_not_pretend_to_be_independent_data(self):
        entries={e['id']:e for e in self.ledger['entries']}
        for part in ('calibration','holdout'):
            baseline=entries['public-tatoeba-history-grammar-profile-eval-'+part]['keys']
            self.assertEqual(baseline,entries['public-tatoeba-history-grammar-revision-broad-'+part]['keys'])
            self.assertEqual(baseline,entries['public-tatoeba-history-grammar-conservative-'+part]['keys'])

    def test_unsupported_surface_exclusions_do_not_clear_unproven_families(self):
        entries=[e for e in self.ledger['entries'] if 'unsupportedSurfaceKeys' in e]
        self.assertEqual(11,len(entries));self.assertEqual(1357,len({k for e in entries for k in e['unsupportedSurfaceKeys']}))
        self.assertTrue(all('family' in e['missingAxes'] for e in entries));self.assertFalse(self.ledger['coverage']['complete'])

    def test_legacy_context_partitions_are_durable_and_fully_source_verified(self):
        entries=[e for e in self.ledger['entries'] if e['id'].startswith('public-legacy-context-')]
        self.assertEqual(6,len(entries));self.assertEqual(23977,sum(e['rowCount'] for e in entries))
        self.assertTrue(all(not e['missingAxes'] for e in entries))

    def test_rejected_prepared_training_families_are_separately_quarantined(self):
        entry=next(e for e in self.ledger['entries'] if e['id']=='public-prepared-conversation-v1-family-quarantine')
        self.assertEqual('prepared-training-quarantine',entry['usage']);self.assertEqual(25,len(entry['keys']['family']))

    def test_rejected_conversation_contexts_survive_without_build_data(self):
        entry=next(e for e in self.ledger['entries'] if e['id']=='public-rejected-conversation-v1-context-exclusions')
        self.assertEqual('historical-context-exclusion',entry['usage'])
        self.assertEqual({'context'},set(entry['keys']));self.assertEqual(740,len(entry['keys']['context']))

    def test_reproduced_ranker_source_windows_survive_without_build_data(self):
        entries=[e for e in self.ledger['entries'] if e['id'].startswith('public-ranker-source-windows-')]
        self.assertEqual(3,len(entries));self.assertEqual(7500,sum(e['rowCount'] for e in entries))
        self.assertTrue(all(e['missingAxes']==['family'] for e in entries))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([dict(prefix='Дху́лия, Дхуле, ',expectedSpelling='раннее',typed='другаяопечатка')],self.ledger,kinds=('context',))

    def test_template_authored_history_keeps_ambiguous_family_exclusions(self):
        entries=[e for e in self.ledger['entries'] if e['id'].startswith('authored-right-context-template-history-')]
        self.assertEqual(6,len(entries))
        family_entries=[e for e in entries if e['usage']=='prepared-training-quarantine']
        self.assertEqual(3,len(family_entries));self.assertTrue(all(len(e['keys']['family'])==29 for e in family_entries))
        for word in ('весло','красить'):
            with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
                assert_disjoint([dict(families=[word])],self.ledger,kinds=('family',),usages=('supervised','prepared-training-quarantine'))

    def test_historical_overlap_disclosure_matches_recorded_keys(self):
        scope={f'public-spelling-v{v}' for v in range(7,13)}|{'public-legacy-spelling-v6'}|{
            'public-early-ru-'+name for name in ('qualification-v2','compact-v3','compact-v4')}
        historical = {key for e in self.ledger['entries'] if e['id'] in scope
                      for key in e['keys']['article']}
        disclosure = self.ledger['historicalArticleOverlap']
        self.assertEqual('NOT_INDEPENDENT_OF_HISTORICAL_SPELLING', disclosure['status'])
        self.assertEqual(sorted(scope),disclosure['scopeEntries'])
        self.assertEqual(len(historical), disclosure['historicalArticles'])
        for e in self.ledger['entries']:
            if e['id'] in disclosure['entries']:
                self.assertEqual(len(historical & set(e['keys']['article'])), disclosure['entries'][e['id']])
        self.assertEqual(122, disclosure['entries']['public-right-context-available-v6-calibration'])
        self.assertEqual(131, disclosure['entries']['public-right-context-available-v6-holdout'])


if __name__ == '__main__':
    unittest.main()
