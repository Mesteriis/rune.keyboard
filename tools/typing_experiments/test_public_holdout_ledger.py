from pathlib import Path
import hashlib
import json
import unittest

from holdout_ledger import assert_disjoint, load_ledger
from import_recovered_v6_history import PARENT_ENTRY
from source_identities import unsupported_surface_key


class PublicLedgerSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.ledger = load_ledger(Path(__file__).with_name('holdout-ledger.json'))

    def test_disclosed_case_collision_is_bound_and_blocked(self):
        root = Path(__file__).resolve().parents[2]
        relative = 'tools/typing_experiments/chat_regression/case-context-collision-v1/rows.jsonl'
        raw = (root / relative).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line]
        entry = next(e for e in self.ledger['entries'] if e['id'] == 'public-case-context-collision-v1')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['bindings'][relative])
        self.assertEqual(2, len(rows))
        self.assertEqual(1, len({(r['prefix'], r['typed']) for r in rows}))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:context'):
            assert_disjoint(rows, self.ledger, kinds=('context',), require_complete=False)

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
        english=next(e for e in entries if e['id']=='public-tatoeba-english-a1-exact-surface-exclusions-v1')
        self.assertEqual(26735,len(english['unsupportedSurfaceKeys']))
        self.assertEqual('historical-context-exclusion',english['usage'])
        entries=[e for e in entries if e is not english]
        english_forms=next(e for e in entries if e['id']=='public-english-unimorph-historical-surfaces-v1')
        self.assertEqual(22647,len(english_forms['unsupportedSurfaceKeys']))
        self.assertEqual('historical-context-exclusion',english_forms['usage'])
        entries=[e for e in entries if e is not english_forms]
        suspended=next(e for e in entries if e['id']=='historical-retrieval-suspended-source-v1-contexts')
        self.assertEqual('historical-context-exclusion', suspended['usage'])
        self.assertEqual([unsupported_surface_key('видеофайлов')], suspended['unsupportedSurfaceKeys'])
        entries=[e for e in entries if e is not suspended]
        new=next(e for e in entries if e['id']=='public-word-ranking-family-quarantine-v1')
        self.assertEqual('prepared-training-quarantine',new['usage']);self.assertEqual(3,len(new['unsupportedSurfaceKeys']))
        parent=next(e for e in self.ledger['entries'] if e['id']=='public-word-ranking-data-articles-v1')
        self.assertIn('family',parent['missingAxes'])
        q7=[e for e in entries if e['id'].startswith('public-q7-regression-dictionary-families-')]
        self.assertEqual({'public-q7-regression-dictionary-families-product-v1',
                          'public-q7-regression-dictionary-families-original-v2'}, {e['id'] for e in q7})
        self.assertTrue(all(e['usage']=='historical-family-exclusion' and not e['missingAxes'] for e in q7))
        text_families=[e for e in entries if e['id'].startswith('public-word-epoch-text-families-')]
        self.assertEqual(4,len(text_families))
        self.assertTrue(all(e['usage']=='historical-family-exclusion' and not e['missingAxes'] for e in text_families))
        refinement_families=[e for e in entries if e['id'].startswith('public-refinement-text-families-')]
        self.assertEqual(3,len(refinement_families))
        self.assertTrue(all(e['usage']=='historical-family-exclusion' and not e['missingAxes'] for e in refinement_families))
        neighbor=next(e for e in entries if e['id']=='historical-neighbor-recovery-prefix-families-v1')
        self.assertEqual('historical-family-exclusion',neighbor['usage'])
        self.assertEqual(1163,len(neighbor['unsupportedSurfaceKeys']))
        self.assertFalse(neighbor['missingAxes'])
        truncated=next(e for e in entries if e['id']=='historical-truncated-text-source-completions-v1-families')
        self.assertEqual('prepared-training-quarantine',truncated['usage'])
        self.assertEqual(4,len(truncated['unsupportedSurfaceKeys']))
        self.assertEqual(24,len(truncated['keys']['family']))
        self.assertFalse(truncated['missingAxes'])
        taiga=next(e for e in entries if e['id']=='public-taiga-dev-dictionary-families-v1')
        self.assertEqual('historical-family-exclusion',taiga['usage'])
        self.assertEqual(6185,len(taiga['unsupportedSurfaceKeys']))
        self.assertEqual(4528,len(taiga['keys']['family']))
        self.assertFalse(taiga['missingAxes'])
        taiga_lemmas=next(e for e in entries if e['id']=='public-taiga-dev-annotated-lemmas-v1')
        self.assertEqual('historical-family-exclusion',taiga_lemmas['usage'])
        self.assertEqual(4080,len(taiga_lemmas['unsupportedSurfaceKeys']))
        self.assertEqual(4216,len(taiga_lemmas['keys']['family']))
        self.assertFalse(taiga_lemmas['missingAxes'])
        unimorph=next(e for e in entries if e['id']=='public-early-ru-unimorph-exclusions-v1')
        self.assertEqual('historical-context-exclusion',unimorph['usage'])
        self.assertEqual({'context'},set(unimorph['keys']))
        self.assertEqual(644,len(unimorph['unsupportedSurfaceKeys']))
        wiktionary=next(e for e in entries if e['id']=='public-historical-wiktionary-surfaces-v1')
        self.assertEqual('historical-context-exclusion',wiktionary['usage'])
        self.assertEqual({'context'},set(wiktionary['keys']))
        self.assertEqual(15833,len(wiktionary['unsupportedSurfaceKeys']))
        remaining=next(e for e in entries if e['id']=='public-historical-wiktionary-remaining-surfaces-v1')
        self.assertEqual('historical-context-exclusion',remaining['usage'])
        self.assertEqual({'context'},set(remaining['keys']))
        self.assertEqual(54808,len(remaining['unsupportedSurfaceKeys']))
        entries=[e for e in entries if e is not new and e is not neighbor and e is not truncated and e is not taiga and e is not taiga_lemmas and e is not unimorph and e is not wiktionary and e is not remaining and e not in q7 and e not in text_families and e not in refinement_families]
        self.assertEqual(13,len(entries))
        historical=[e for e in entries if e['id'] not in ('ci-product-replay-v1-ru-contexts','ci-original-spelling-v2-ru-contexts')]
        self.assertEqual(11,len(historical));self.assertEqual(1357,len({k for e in historical for k in e['unsupportedSurfaceKeys']}))
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

    def test_late_template_homographs_and_v6_reuse_survive_without_build_data(self):
        entries={e['id']:e for e in self.ledger['entries'] if e['id'].startswith('authored-right-context-late-history-')}
        self.assertEqual(8,len(entries))
        for suffix in ('families','contexts'):
            self.assertEqual(entries['authored-right-context-late-history-v5-'+suffix]['keys'],entries['authored-right-context-late-history-v6-'+suffix]['keys'])
        self.assertEqual(59,len(entries['authored-right-context-late-history-v7-families']['keys']['family']))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['полезно'])],self.ledger,kinds=('family',),usages=('supervised','prepared-training-quarantine'))

    def test_applied_role_template_history_keeps_alternative_full_adjective_lemma(self):
        entries={e['id']:e for e in self.ledger['entries'] if e['id'].startswith('authored-right-context-applied-history-')}
        self.assertEqual(4,len(entries));self.assertEqual(60,len(entries['authored-right-context-applied-history-v2-families']['keys']['family']))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['честной'])],self.ledger,kinds=('family',),usages=('supervised','prepared-training-quarantine'))

    def test_auxiliary_template_exclusions_and_sequence_reuse_are_durable(self):
        entries={e['id']:e for e in self.ledger['entries'] if e['id'].startswith('authored-right-context-auxiliary-history-')}
        self.assertEqual(10,len(entries))
        for suffix in ('families','contexts'):
            self.assertEqual(entries['authored-right-context-auxiliary-history-left-sequence-v1-'+suffix]['keys'],entries['authored-right-context-auxiliary-history-left-sequence-v1-v2-'+suffix]['keys'])
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:context'):
            assert_disjoint([dict(prefix='раньше он был ',typed='другаяопечатка',expectedSpelling='болью')],self.ledger,kinds=('context',))

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

    def test_neighbor_history_adds_to_v6_spelling_article_overlap(self):
        entries={entry['id']:entry for entry in self.ledger['entries']}
        spelling=set().union(*(set(entries[name]['keys']['article'])
                               for name in self.ledger['historicalArticleOverlap']['scopeEntries']))
        neighbor=set(entries['historical-neighbor-recovery-public-v1']['keys']['article'])
        for part, expected in (('calibration',(122,26,18,140)),('holdout',(131,25,13,144))):
            with self.subTest(part=part):
                articles=set(entries['public-right-context-available-v6-'+part]['keys']['article'])
                self.assertEqual(expected,(len(articles & spelling),len(articles & neighbor),
                    len((articles & neighbor)-spelling),len(articles & (spelling | neighbor))))

    def test_v6_article_overlap_with_its_parent_and_other_registered_entries(self):
        entries={entry['id']:entry for entry in self.ledger['entries']}
        historical=set().union(*(set(entry.get('keys', {}).get('article', []))
            for entry in self.ledger['entries']
            if entry['id'] != PARENT_ENTRY
            and not entry['id'].startswith('public-right-context-available-v6-')))
        parent = set(entries[PARENT_ENTRY]['keys']['article'])
        for part, expected in (('calibration',304),('holdout',289)):
            with self.subTest(part=part):
                articles=set(entries['public-right-context-available-v6-'+part]['keys']['article'])
                self.assertTrue(articles <= parent)
                self.assertEqual(expected,len(articles & historical))

    def test_frozen_natural_and_side_descendants_survive_without_original_data(self):
        entries=[e for e in self.ledger['entries'] if e['id'].startswith('public-frozen-context-descendant-')]
        self.assertEqual(8,len(entries));self.assertEqual(38216,sum(e['rowCount'] for e in entries))
        self.assertTrue(all(not e['missingAxes'] for e in entries))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            assert_disjoint([dict(families=['елена'])],self.ledger,kinds=('family',))
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:article'):
            assert_disjoint([dict(article='7139678')],self.ledger,kinds=('article',))


if __name__ == '__main__':
    unittest.main()
