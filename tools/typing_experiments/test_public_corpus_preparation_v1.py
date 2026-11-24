import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from control_ledger import SCHEMA,key_for,article_key
from holdout_ledger import keys_for,source_segment_hash,require_source_segment
from public_corpus_preparation_v1 import (preflight,prepare,registry_bindings,registry_bindings_v1,
    verify_registry_bindings,verify_historical_registry_bindings_v1)
from test_holdout_ledger import ledger
from source_identities import unsupported_surface_key
from joint_exclusion_inputs import canonical_registry_parts


def candidate(**changes):
    return dict(id='new',language='ru',article='999999999',families=['пробный'],contextHash='0'*64,sourceSegmentHash='f'*64,
                prefix='Новый контекст проверки',typed='пробный',expectedSpelling='пробный')|changes


def controls():
    return dict(schema=SCHEMA,publicDataOnly=True,coverageComplete=False,pending=['pending'],entries=[
        dict(id='punct',kind='punctuation',language='ru',rowCount=1,bindings={'file':'a'*64},
             keys=[key_for(dict(language='ru',prefix='Пунктуация',currentWord='слово',expectedBoundary=', '),'punctuation')],
             articleKeys=sorted([article_key(dict(language='ru',article='777')),article_key(dict(language='en',article='123'))])),
        dict(id='protected',kind='protected',language='ru',rowCount=1,bindings={'file':'b'*64},
             keys=[key_for(dict(language='ru',prefix='Сохранить',typed='API36'),'protected')])])


class PreparationGateTest(unittest.TestCase):
    def test_source_selector_projection_reaches_both_registry_checks(self):
        import re
        from unittest.mock import patch
        import independent_corpus_guard as guard
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma='готовый')]
        text='Это обычный текст готовы сегодня.'
        sentence,start=next(guard.selector_segments(text))
        row=dict(id='new',language='ru',articleId='999999999',partition='test',
                 typed='готвы',expectedSpelling='готовы',prefix='Это обычный текст ')
        generator=SimpleNamespace(bounded_prefix=lambda value:value.lstrip())
        with patch.object(guard,'_context_generator',return_value=generator):
            guard.attach_selector_source(row,text,sentence,start,re.search('готовы',sentence),{})
        guard.project_selector_families([row],Lexicon())
        result=preflight([json.loads(json.dumps(row))],'spelling',ledger(False),controls(),'new-families')
        self.assertEqual([],result['identityErrors'])
        self.assertEqual(1,result['lexicalOverlaps']['family'])
        self.assertEqual('BLOCKED_OVERLAP',result['status'])

    def test_serialized_joint_rows_keep_canonical_families_for_later_gate(self):
        class Lexicon:
            def analyses(self,word):
                return [SimpleNamespace(lemma='готовый')] if word=='готовы' else []
        row=candidate(word='готовы',family='172788',split='holdout',cohort='typo',
                      typed='готвы',expectedSpelling='готовы')
        del row['families']
        original=preflight([row],'spelling',ledger(False),controls(),'new-families')
        self.assertIn('lexical-family-schema',original['identityErrors'])
        projected=canonical_registry_parts({'holdout':[row]},Lexicon())['holdout']
        restored=json.loads(json.dumps(projected,ensure_ascii=False))
        result=preflight(restored,'spelling',ledger(False),controls(),'new-families')
        self.assertNotIn('lexical-family-schema',result['identityErrors'])
        self.assertEqual(1,result['lexicalOverlaps']['family'])
        self.assertEqual('172788',restored[0]['family'])
        self.assertEqual(['готовый'],restored[0]['families'])
        self.assertNotIn('families',row)

    def test_native_numeric_family_cannot_pass_as_dictionary_lemma(self):
        result = preflight([candidate(families=['172788'])], 'spelling', ledger(), controls(), 'new-families')
        self.assertIn('lexical-family-schema', result['identityErrors'])
        self.assertNotEqual('READY_TO_FREEZE', result['status'])

    def test_entry_digest_is_canonical_but_snapshot_digest_binds_exact_bytes(self):
        lex=ledger(False);ctrl=controls()
        raw=json.dumps(lex).encode();control_raw=json.dumps(ctrl).encode()
        first=registry_bindings(raw,control_raw)
        reordered=json.dumps(lex,sort_keys=True,indent=2).encode()
        second=registry_bindings(reordered,control_raw)
        a=first['registries']['lexical-ledger.json'];b=second['registries']['lexical-ledger.json']
        self.assertNotEqual(a['sha256'],b['sha256'])
        self.assertEqual(a['entrySha256'],b['entrySha256'])
        entry=lex['entries'][0]
        expected=hashlib.sha256(json.dumps(entry,ensure_ascii=False,sort_keys=True,
            separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self.assertEqual(expected,a['entrySha256'][entry['id']])
        self.assertFalse(a['coverageComplete'])
        for change in ('binding','keys','metadata'):
            modified=copy.deepcopy(lex)
            if change=='binding':modified['entries'][0]['bindings']['new']='d'*64
            if change=='keys':modified['entries'][0]['keys']['article']=['f'*64]
            if change=='metadata':modified['entries'][0]['note']='disclosed origin'
            changed=registry_bindings(json.dumps(modified).encode(),control_raw)
            self.assertNotEqual(a['entrySha256'],changed['registries']['lexical-ledger.json']['entrySha256'])

    def test_preparation_binds_both_snapshots_and_entries_even_when_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=root/'proposal.jsonl';manifest=root/'manifest.json'
            lex=root/'lexical.json';ctrl=root/'control.json';output=root/'final'
            rows.write_text(json.dumps(candidate())+'\n')
            manifest.write_text(json.dumps(dict(containsPersonalMessages=False,frozenBeforeScoring=True,
                files={rows.name:hashlib.sha256(rows.read_bytes()).hexdigest()})))
            lex.write_text(json.dumps(ledger(False)));ctrl.write_text(json.dumps(controls()))
            report=prepare(rows,manifest,output,'spelling',lex,ctrl)
            self.assertEqual('BLOCKED_COVERAGE',report['status']);self.assertFalse(output.exists())
            result=verify_registry_bindings(report,lex,ctrl)
            self.assertEqual({'lexical-ledger.json','control-ledger.json'},set(result['registries']))
            self.assertEqual(result['englishSurfaceBindings'],
                {name:report['builderBindings'][name] for name in result['englishSurfaceBindings']})
            old=copy.deepcopy(report);old['registryBindings']=registry_bindings_v1(lex.read_bytes(),ctrl.read_bytes())
            verify_historical_registry_bindings_v1(old,lex,ctrl)
            from unittest.mock import patch
            import ewt_surface_exclusions_v1 as surfaces
            with patch.object(surfaces,'FIXTURE',root/'missing-surface.json'):
                verify_historical_registry_bindings_v1(old,lex,ctrl)
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                verify_registry_bindings(old,lex,ctrl)
            tampered=copy.deepcopy(report);tampered['registryBindings']['englishSurfaceBindings']['ewt-surface-exclusions-v1.json']='0'*64
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                verify_registry_bindings(tampered,lex,ctrl)
            for name,value in result['registries'].items():
                self.assertEqual(report['inputBindings'][name],value['sha256'])
                self.assertTrue(value['entrySha256']);self.assertFalse(value['coverageComplete'])
            for path in (lex,ctrl):
                original=path.read_bytes();path.write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                    verify_registry_bindings(report,lex,ctrl)
                path.write_bytes(original)
            missing=copy.deepcopy(report)
            missing['registryBindings']['registries']['control-ledger.json']['entrySha256']={}
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                verify_registry_bindings(missing,lex,ctrl)
            conflict=copy.deepcopy(report)
            conflict['inputBindings']['lexical-ledger.json']='a'*64
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                verify_registry_bindings(conflict,lex,ctrl)
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_REGISTRY_DRIFT'):
                verify_registry_bindings({},lex,ctrl)

    def test_invalid_registry_cannot_produce_acceptance_entry_bindings(self):
        for lex,ctrl in (({},controls()),(ledger(False),{})):
            with self.assertRaises(ValueError):registry_bindings(json.dumps(lex).encode(),json.dumps(ctrl).encode())

    def test_registry_binding_includes_and_validates_english_surface_exclusions(self):
        from unittest.mock import patch
        import ewt_surface_exclusions_v1 as surfaces
        raw=json.dumps(ledger(False)).encode(); ctrl=json.dumps(controls()).encode()
        binding=registry_bindings(raw,ctrl)
        self.assertEqual('rune-acceptance-registry-bindings-v2',binding['schema'])
        self.assertEqual(surfaces.FIXTURE_SHA,binding['englishSurfaceBindings']['ewt-surface-exclusions-v1.json'])
        with tempfile.TemporaryDirectory() as folder:
            altered=Path(folder)/'fixture.json';altered.write_bytes(surfaces.FIXTURE.read_bytes()+b' ')
            with patch.object(surfaces,'FIXTURE',altered):
                with self.assertRaisesRegex(ValueError,'EWT_SURFACE_IDENTITY'):
                    registry_bindings(raw,ctrl)

    def test_unsupported_surface_cannot_be_hidden_by_a_claimed_canonical_family(self):
        lex=ledger(False);lex['entries'][0]['unsupportedSurfaceKeys']=[unsupported_surface_key('дарси')]
        result=self.report(candidate(typed='ДАРСИ',expectedSpelling='дарси',families=['fixture-only-family']),lexical=lex)
        self.assertEqual('BLOCKED_OVERLAP',result['status']);self.assertEqual(1,result['unsupportedTargetOverlaps'])

    def test_english_disclosed_surface_in_lexical_registry_blocks_family_profile(self):
        from control_ledger import surface_key
        lex=ledger(False)
        lex['entries'][0]['unsupportedSurfaceKeys']=[surface_key('en','unusualword')]
        row=candidate(language='en',sourceRepository='tatoeba',article='tatoeba:999999999',
                      sentenceHash='f'*64,prefix='a ',typed='unusualword',expectedSpelling='unusualword')
        strict=preflight([row],'spelling',lex,controls(),'new-families')
        self.assertEqual('BLOCKED_OVERLAP',strict['status'])
        self.assertEqual(1,strict['unsupportedTargetOverlaps'])
        self.assertIn('en',strict['unsupportedLexicalLanguages'])
        self.assertEqual(0,preflight([row],'spelling',lex,controls(),'new-sentences')['unsupportedTargetOverlaps'])

    def test_english_apostrophe_variants_cannot_evade_surface_exclusions(self):
        from control_ledger import surface_key
        lex = ledger(False)
        lex['entries'][0]['unsupportedSurfaceKeys'] = [surface_key('en', "we're")]
        for token in ("we’re", "weʼre"):
            row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                            sentenceHash='f'*64, prefix='different ', typed=token, expectedSpelling=token)
            result = preflight([row], 'spelling', lex, controls(), 'new-families')
            self.assertEqual(1, result['unsupportedTargetOverlaps'])
            self.assertEqual('BLOCKED_OVERLAP', result['status'])

    def test_english_apostrophe_variants_cover_controls_and_multiple_marks(self):
        from control_ledger import surface_key
        registry = controls()
        registry['entries'].append(dict(id='english-surface', kind='regression', language='en', rowCount=1,
            bindings={'file':'d'*64}, keys=[key_for(dict(language='en', prefix='original ', typed="y'all'd"), 'regression')],
            surfaceKeys=[surface_key('en', "y'all'd")]))
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:999999999',
                        sentenceHash='f'*64, prefix='different ', typed='y’allʼd', expectedSpelling='y’allʼd')
        result = preflight([row], 'spelling', ledger(False), registry, 'new-sentences')
        self.assertEqual(1, result['controlOverlaps']['surface'])
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        too_many = row | dict(typed="a'b'c'd'e'f", expectedSpelling="a'b'c'd'e'f")
        result = preflight([too_many], 'spelling', ledger(False), registry, 'new-families')
        self.assertIn('english-surface-schema', result['identityErrors'])
        self.assertNotEqual('READY_TO_FREEZE', result['status'])

    def test_wikipedia_segment_overlap_checks_full_text_namespace_and_requires_hash(self):
        text_hash = source_segment_hash('  ИЗВЕСТНЫЙ   фрагмент. ')
        source = {'sourceRepository': 'tatoeba', 'language': 'ru', 'article': 'tatoeba:7', 'sentenceHash': text_hash}
        lex = ledger(False)
        lex['entries'].append(dict(id='full-segment', usage='historical-source-exclusion', bindings={'source':'a'*64},
            keys={axis: sorted(keys_for([source], axis)) for axis in ('article','sentence')}, missingAxes=[]))
        result = self.report(candidate(sourceSegmentHash=text_hash), lexical=lex)
        self.assertEqual('BLOCKED_OVERLAP', result['status'])
        self.assertEqual(1, result['lexicalOverlaps']['sentence'])
        missing = candidate(); del missing['sourceSegmentHash']
        self.assertIn('source-segment-schema', self.report(missing)['identityErrors'])
        with self.assertRaisesRegex(ValueError, 'LEDGER_SOURCE_SEGMENT_SCHEMA'):
            require_source_segment(missing)
        require_source_segment(candidate(sourceSegmentHash=text_hash))
        self.assertIn('source-segment-schema', self.report(candidate(sourceSegmentHash='bad'))['identityErrors'])

    def report(self,row=None,task='spelling',**changes):
        args=dict(rows=[row or candidate()],task=task,lexical=ledger(False),controls=controls())|changes
        return preflight(**args)

    def test_unknown_rows_are_blocked_by_both_incomplete_registries(self):
        result=self.report()
        self.assertEqual('BLOCKED_COVERAGE',result['status']);self.assertFalse(result['lexicalCoverageComplete'])
        self.assertFalse(result['controlCoverageComplete']);self.assertEqual([],result['identityErrors'])

    def test_lexical_and_control_articles_each_block_spelling_preparation(self):
        word=self.report(candidate(article='123'));control=self.report(candidate(article='777'))
        self.assertEqual(1,word['lexicalOverlaps']['article']);self.assertEqual('BLOCKED_OVERLAP',word['status'])
        self.assertEqual(1,control['controlOverlaps']['article']);self.assertEqual(0,control['lexicalOverlaps']['article'])
        self.assertEqual('BLOCKED_OVERLAP',control['status'])

    def test_protected_controls_are_checked_even_when_task_is_spelling(self):
        result=self.report(candidate(prefix='Сохранить',typed='API36',expectedSpelling='API36'))
        self.assertEqual(1,result['controlOverlaps']['protected']);self.assertEqual('BLOCKED_OVERLAP',result['status'])

    def test_changed_punctuation_label_still_blocks_preparation(self):
        row=candidate(prefix='Пунктуация',currentWord='слово',expectedBoundary='. ',task='punctuation',noAuto=True)
        result=self.report(row,task='punctuation')
        self.assertEqual(1,result['controlOverlaps']['punctuation']);self.assertEqual('BLOCKED_OVERLAP',result['status'])

    def test_family_profiles_preserve_supervised_versus_historical_semantics(self):
        row=candidate(families=['готовый'])
        self.assertEqual(0,self.report(row)['lexicalOverlaps']['family'])
        self.assertEqual(1,self.report(row,profile='new-families')['lexicalOverlaps']['family'])
        lex=ledger(False);lex['entries'].append(dict(id='train',usage='supervised',bindings={'file':'c'*64},
            keys={'family':sorted(keys_for([row],'family'))},missingAxes=[]))
        self.assertEqual(1,self.report(row,lexical=lex)['lexicalOverlaps']['family'])

    def test_identity_errors_do_not_skip_control_checks_and_languages_do_not_alias(self):
        result=self.report(candidate(article=1,prefix='Сохранить',typed='API36',expectedSpelling='API36'))
        self.assertTrue(result['identityErrors']);self.assertEqual(1,result['controlOverlaps']['protected'])
        result=self.report(candidate(article='123'))
        self.assertEqual(0,result['controlOverlaps']['article']) # EN 123 is distinct from RU 123.

    def test_empty_duplicate_and_unsupported_language_inputs_fail_closed(self):
        with self.assertRaises(ValueError):self.report(rows=[])
        self.assertEqual('BLOCKED_IDENTITIES',self.report(rows=[candidate(),candidate()])['status'])
        self.assertIn('unsupported-spelling-language',self.report(candidate(language='en'))['identityErrors'])

    def test_invalid_second_registry_cannot_be_ignored_on_a_known_lexical_overlap(self):
        invalid=controls();invalid['coverageComplete']=True
        with self.assertRaisesRegex(ValueError,'CONTROL_LEDGER_SCHEMA'):self.report(candidate(article='123'),controls=invalid)

    def test_prepared_training_quarantine_blocks_default_family_profile(self):
        lex=ledger(False);row=candidate()
        lex['entries'].append(dict(id='prepared',usage='prepared-training-quarantine',bindings={'audit':'a'*64},
            keys={'family':sorted(keys_for([row],'family'))},missingAxes=[]))
        result=self.report(row,lexical=lex)
        self.assertEqual('BLOCKED_OVERLAP',result['status']);self.assertEqual(1,result['lexicalOverlaps']['family'])

    def test_disclosed_english_sources_are_checked_even_when_qualification_is_unsupported(self):
        for repository, article in (('tatoeba', 'tatoeba:123'), ('ud-english-ewt', 'ewt:example-doc')):
            row = candidate(language='en', sourceRepository=repository, article=article, sentenceHash='b'*64,
                            prefix='I am ', typed='helo', expectedSpelling='hello')
            lex = ledger(False)
            lex['entries'].append(dict(id='english-source', usage='historical-source-exclusion',
                bindings={'source':'a'*64}, keys={axis:sorted(keys_for([row],axis)) for axis in ('article','sentence')},
                missingAxes=[]))
            result = self.report(row, lexical=lex)
            self.assertEqual('BLOCKED_OVERLAP',result['status'])
            self.assertEqual(1,result['lexicalOverlaps']['article'])
            self.assertEqual(1,result['lexicalOverlaps']['sentence'])
            self.assertIn('en',result['unsupportedLexicalLanguages'])
            self.assertIn('unsupported-spelling-language',result['identityErrors'])
            self.assertNotIn('source-article-schema',result['identityErrors'])
            protected = row | dict(cohort='protected',noAuto=True,expectedCandidate=0,candidates=[' '+row['typed']])
            result = self.report(protected,task='protected',lexical=lex)
            self.assertEqual('BLOCKED_OVERLAP',result['status'])
            self.assertEqual(1,result['lexicalOverlaps']['article'])
            self.assertEqual(1,result['lexicalOverlaps']['sentence'])
            self.assertIn('en',result['unsupportedLexicalLanguages'])

    def test_english_ewt_control_source_overlap_is_checked(self):
        row = candidate(language='en',sourceRepository='ud-english-ewt',article='ewt:example-doc',
                        sentenceHash='b'*64,prefix='I am ',typed='helo',expectedSpelling='hello')
        ctrl = controls()
        ctrl['entries'].append(dict(id='ewt',kind='source',language='en',rowCount=1,bindings={'source':'a'*64},
                                    keys=[],articleKeys=[article_key(row)]))
        result = self.report(row,controls=ctrl)
        self.assertEqual('BLOCKED_OVERLAP',result['status'])
        self.assertEqual(1,result['controlOverlaps']['article'])
        self.assertNotIn('source-article-schema',result['identityErrors'])
        self.assertIn('en',result['unsupportedLexicalLanguages'])

    def test_historical_spelling_article_blocks_new_context_in_its_language(self):
        import register_historical_spelling_articles as history

        ctrl = controls()
        entries = list(history.derive())
        ctrl['entries'].extend(entries)
        for language in ('en', 'es'):
            with self.subTest(language=language):
                path = history.archives.ROOT / 'article-maps' / f'v2-{language}.json'
                matches = json.loads(path.read_bytes())['matchingArticlesByRow']
                # A secondary possible article must be excluded as well.
                article = next(articles[1] for articles in matches.values() if len(articles) > 1)
                row = candidate(language=language, article=article, prefix='A distinct test prefix ',
                                typed='sampleword', expectedSpelling='sampleword')
                result = self.report(row, controls=ctrl)
                self.assertEqual('BLOCKED_OVERLAP', result['status'])
                self.assertEqual(1, result['controlOverlaps']['article'])
                result = self.report(row | {'language': 'ru'}, controls=ctrl)
                self.assertEqual(0, result['controlOverlaps']['article'])

    def test_ru_historical_article_blocks_even_when_lexical_input_lacks_it(self):
        import register_historical_ru_spelling_articles as history

        current = history.control.load(history.CONTROL)
        prior_entries = [entry for entry in current['entries'] if not entry['id'].startswith(history.PREFIX)]
        previous = current | {'entries': prior_entries}
        old_keys = {key for entry in prior_entries for key in entry.get('articleKeys', [])}
        matches = json.loads((history.ARCHIVES / 'punctuation-ru-attribution/v2-ru.json').read_bytes())['ruSpelling']
        article = next(article for group in matches.values() for article in group
                       if article_key({'language': 'ru', 'article': article}) not in old_keys)
        row = candidate(article=article, typed='рюниксфв', expectedSpelling='рюниксфв')
        before = self.report(row, controls=previous)
        self.assertEqual(0, before['controlOverlaps']['article'])
        after = self.report(row, controls=current)
        self.assertEqual(0, after['lexicalOverlaps']['article'])
        self.assertEqual(1, after['controlOverlaps']['article'])
        self.assertEqual('BLOCKED_OVERLAP', after['status'])

    def test_english_sentence_overlap_crosses_source_namespaces(self):
        disclosed = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:123', sentenceHash='c'*64)
        proposed = candidate(language='en', sourceRepository='ud-english-ewt', article='ewt:other', sentenceHash='c'*64)
        lex = ledger(False)
        lex['entries'].append(dict(id='english-source',usage='historical-source-exclusion',bindings={'source':'a'*64},
            keys={axis:sorted(keys_for([disclosed],axis)) for axis in ('article','sentence')},missingAxes=[]))
        result = self.report(proposed,lexical=lex)
        self.assertEqual('BLOCKED_OVERLAP',result['status'])
        self.assertEqual(0,result['lexicalOverlaps']['article'])
        self.assertEqual(1,result['lexicalOverlaps']['sentence'])
        self.assertIn('en',result['unsupportedLexicalLanguages'])

    def test_actual_disclosed_english_tatoeba_row_is_detected(self):
        from import_english_tatoeba_screen import DIGEST, ROOT, SOURCE, rows_from_bytes
        from holdout_ledger import load_ledger
        source = (ROOT / SOURCE).read_bytes()
        self.assertEqual(DIGEST,hashlib.sha256(source).hexdigest())
        row = candidate(language='en', prefix='I am ', typed='helo', expectedSpelling='hello') | rows_from_bytes(source)[0]
        result = self.report(row,lexical=load_ledger(ROOT/'tools/typing_experiments/holdout-ledger.json'))
        self.assertEqual('BLOCKED_OVERLAP',result['status'])
        self.assertGreaterEqual(result['lexicalOverlaps']['article'],1)
        self.assertGreaterEqual(result['lexicalOverlaps']['sentence'],1)
        self.assertIn('en',result['unsupportedLexicalLanguages'])

    def test_unsupported_source_backed_protected_language_remains_blocked(self):
        row = candidate(language='es',sourceRepository='tatoeba',article='tatoeba:5',sentenceHash='d'*64,
                        cohort='protected',noAuto=True,expectedCandidate=0,candidates=[' '+candidate()['typed']])
        result = self.report(row,task='protected')
        self.assertIn('es',result['unsupportedLexicalLanguages'])
        self.assertNotEqual('READY_TO_FREEZE',result['status'])

    def test_english_annotated_lemma_overlap_is_diagnostic_only(self):
        from english_family_keys import key_for
        row = candidate(language='en',sourceRepository='tatoeba',article='tatoeba:123',
                        sentenceHash='b'*64,englishLemmas=['go'],prefix='I ',typed='went',expectedSpelling='went')
        lex = ledger(False)
        lex['entries'].append(dict(id='english-lemma',usage='historical-family-exclusion',
            bindings={'source':'a'*64},keys={'family':[key_for('go')]},missingAxes=[]))
        result = self.report(row,lexical=lex,profile='new-families')
        self.assertEqual('BLOCKED_OVERLAP',result['status'])
        self.assertEqual(1,result['lexicalOverlaps']['family'])
        self.assertIn('en',result['unsupportedLexicalLanguages'])
        invalid = self.report(row | dict(englishLemmas=['bad form']),lexical=lex,profile='new-families')
        self.assertIn('lexical-en-family-schema',invalid['identityErrors'])
        self.assertNotEqual('READY_TO_FREEZE',invalid['status'])

    def test_english_source_without_sentence_identity_remains_blocked(self):
        row = candidate(language='en', sourceRepository='tatoeba', article='tatoeba:123', sentenceHash=None)
        result = self.report(row)
        self.assertIn('lexical-sentence-schema',result['identityErrors'])
        self.assertNotEqual('READY_TO_FREEZE',result['status'])

    def test_tatoeba_source_namespace_and_source_backed_protected_rows_are_checked(self):
        row=candidate(sourceRepository='tatoeba',article='tatoeba:123',sentenceHash='b'*64)
        result=self.report(row)
        self.assertEqual(0,result['lexicalOverlaps']['article']);self.assertEqual([],result['identityErrors'])
        lex=ledger(False);lex['entries'].append(dict(id='tt',usage='historical-source-exclusion',bindings={'source':'a'*64},
            keys={axis:sorted(keys_for([row],axis)) for axis in ('article','sentence')},missingAxes=[]))
        row.update(cohort='protected',noAuto=True,expectedCandidate=0,candidates=[' '+row['typed']])
        result=self.report(row,task='protected',lexical=lex)
        self.assertEqual(1,result['lexicalOverlaps']['article']);self.assertEqual(1,result['lexicalOverlaps']['sentence'])


if __name__=='__main__':unittest.main()
