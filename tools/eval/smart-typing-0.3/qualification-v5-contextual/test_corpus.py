"""Synthetic controls only. No score/model/cache or private editor input."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

try:
    contract = importlib.import_module('corpus_contract')
    generator = importlib.import_module('generate_corpus')
except ModuleNotFoundError:
    contract = generator = None


def article(number, text):
    return {'id': str(number), 'url': f'https://en.wikipedia.org/wiki/Fixture_{number}',
            'title': f'Fixture {number}', 'text': text}


class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(contract, 'punctuation-only corpus contract is not implemented')
        self.assertIsNotNone(generator, 'score-independent generator is not implemented')

    def test_extraction_records_exact_nfc_offsets_separator_and_case(self):
        text = '  Cafe\u0301 uno:\n palabra. Árbol verde'
        found = generator.extract(text, 'es')
        colon = next(x for x in found if x['boundary'] == ': ')
        self.assertEqual(('Café uno', 'palabra'), (colon['prefix'], colon['word']))
        self.assertEqual(':\n ', colon['sourceSpan']['separator'])
        self.assertEqual('palabra', colon['sourceSpan']['observedWord'])
        period = next(x for x in found if x['boundary'] == '. ')
        self.assertEqual('árbol', period['word'])
        self.assertEqual('Árbol', period['sourceSpan']['observedWord'])
        normalized = '  Café uno:\n palabra. Árbol verde'
        span = period['sourceSpan']
        self.assertEqual('Árbol', normalized[span['wordStart']:span['wordEnd']])

    def test_extraction_declines_double_space_and_period_lowercase(self):
        self.assertEqual([], generator.extract('uno  palabra', 'es'))
        self.assertEqual([], generator.extract('uno. palabra', 'es'))
        self.assertEqual([], generator.extract('uno,palabra', 'es'))

    def test_prefix_truncation_is_utf8_bounded_at_a_whole_word(self):
        found = generator.extract(('árbol ' * 100) + ': palabra', 'es')
        item = next(x for x in found if x['boundary'] == ': ')
        self.assertLessEqual(len(item['prefix'].encode()), 256)
        self.assertTrue(item['prefix'].startswith('árbol'))
        self.assertNotIn('\ufffd', item['prefix'])

    def test_contract_preserves_recipe_leading_space_after_truncation(self):
        rows=self.full_rows()
        previous=rows[0]
        source=article(previous['source']['articleId'],'a'*300+'  context: alpha')
        item=next(value for value in generator.extract(source['text'],'en') if value['boundary']==': ')
        self.assertEqual(' context',item['prefix'])
        rows[0]=generator.materialize(source,'en',previous['source']['parquetRow'],item)
        try:
            report=contract.validate_rows(rows,contract.Exclusions())
        except ValueError as error:
            self.fail(f'exact extraction prefix was rejected: {error}')
        self.assertEqual(1200,report['rows'])

    def test_exclusions_cover_pair_corpus_candidates_and_normalized_suffixes(self):
        prior = [dict(language='es', prefix='Café uno', chosen=' palabra', rejected=', rival'),
                 dict(language='en', prefix='Different prefix', typed='typed', candidates=[' typed', 'target'], expectedSpelling='other'),
                 dict(language='ru', prefix='другой пример', currentWord='слово', candidates=[' слово'])]
        exclusions = contract.Exclusions.from_rows(prior)
        self.assertTrue(exclusions.blocks('es', 'CAFE\u0301  UNO', 'newword'))
        self.assertTrue(exclusions.blocks('es', 'Café, uno', 'rival'))
        self.assertTrue(exclusions.blocks('en', 'Different, prefix', 'other'))
        self.assertTrue(exclusions.blocks('ru', 'другой, пример', 'слово'))
        self.assertFalse(exclusions.blocks('es', 'nuevo contexto', 'palabra'))

    def test_prior_input_schema_is_fail_closed(self):
        for row in ({'language':'en', 'prefix':'x'}, {'language':'xx','prefix':'x','chosen':' y','rejected':' z'},
                    {'language':'en','prefix':'x','chosen':None,'rejected':' z'}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                contract.Exclusions.from_rows([row])

    def test_article_partition_preserves_same_seed_disjointness(self):
        for number in range(200):
            rank = int.from_bytes(hashlib.sha256(f'7042026:en:{number}'.encode()).digest()[:8], 'big')
            self.assertEqual(rank % 4 == 3, contract.admitted('en', str(number)))
            if contract.admitted('en', str(number)):
                self.assertNotEqual(2, rank % 4)
        # A different seed plus a different residue does NOT prove disjointness.
        overlaps = [n for n in range(200) if contract.admitted('en',str(n)) and
                    int.from_bytes(hashlib.sha256(f'3052026:en:{n}'.encode()).digest()[:8],'big') % 4 == 2]
        self.assertTrue(overlaps)

    def test_selection_uses_priority_one_row_per_article_and_skips_old_residue(self):
        selected = generator.Selector('en', contract.Exclusions())
        number = next(n for n in range(100) if contract.admitted('en',str(n)))
        selected.consider(article(number, 'prefix words: alpha, bravo. Charlie delta'), 0)
        self.assertEqual(1, len(selected.rows))
        self.assertEqual(': ', selected.rows[0]['observedBoundary'])
        with self.assertRaises(ValueError):
            selected.consider(article(number, 'another context: word'), 1)
        other = next(n for n in range(100) if not contract.admitted('en',str(n)))
        selected.consider(article(other, 'different context: word'), 2)
        self.assertEqual(1, len(selected.rows))

    def full_rows(self):
        rows=[]
        for lang, word in [('en','alpha'),('ru','слово'),('es','palabra')]:
            counts={}
            number=0
            while len([x for x in rows if x['language']==lang]) < 400:
                identity=str(number); number+=1
                if not contract.admitted(lang,identity): continue
                split=contract.article_split(lang,identity)
                boundary=next((b for b in (': ','. ',', ',' ') if counts.get((split,b),0)<50),None)
                if boundary is None: continue
                code=''.join(chr(97+int(c)) for c in identity)
                prefix='independent fixture context '+code
                observed=word[:1].upper()+word[1:] if boundary=='. ' else word
                source=article(identity,prefix+boundary+observed)
                source['url']=f'https://{lang}.wikipedia.org/wiki/Fixture_{identity}'
                item=next(x for x in generator.extract(source['text'],lang) if x['boundary']==boundary and x['word']==word)
                rows.append(generator.materialize(source,lang,number-1,item))
                counts[(split,boundary)]=counts.get((split,boundary),0)+1
        return rows

    def test_full_synthetic_contract_has_exact_quotas_and_no_semantic_labels(self):
        rows=self.full_rows()
        report=contract.validate_rows(rows, contract.Exclusions())
        self.assertEqual(1200,report['rows'])
        self.assertEqual(24,len(report['counts']))
        self.assertEqual({50},set(report['counts'].values()))
        self.assertTrue(all('ambiguous' not in row and row['labelSemantics']=='observed_wikipedia_boundary' for row in rows))

    def test_contract_rejects_missing_quota_mixed_schema_and_semantic_label(self):
        rows=self.full_rows()
        for mutate in ('missing','version','semantic','spelling','automatic'):
            changed=copy.deepcopy(rows)
            if mutate=='missing': changed.pop()
            if mutate=='version': changed[0]['corpusVersion']=4
            if mutate=='semantic': changed[0]['ambiguous']=False
            if mutate=='spelling': changed[0]['task']='spelling'
            if mutate=='automatic': changed[0]['noAuto']=False
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                contract.validate_rows(changed,contract.Exclusions())

    def test_contract_rejects_article_overlap_context_overlap_and_prior_observation(self):
        rows=self.full_rows()
        changed=copy.deepcopy(rows)
        changed[1]['source']['articleId']=changed[0]['source']['articleId']
        with self.assertRaises(ValueError): contract.validate_rows(changed,contract.Exclusions())
        changed=copy.deepcopy(rows);changed[1]=copy.deepcopy(changed[0])
        with self.assertRaises(ValueError): contract.validate_rows(changed,contract.Exclusions())
        excluded=contract.Exclusions.from_rows([{'language':rows[0]['language'],'prefix':rows[0]['prefix'],
            'chosen':' '+rows[0]['currentWord'],'rejected':' alternative'}])
        with self.assertRaises(ValueError): contract.validate_rows(rows,excluded)

    def test_contract_rejects_changed_span_case_prefix_boundary_and_selection_hash(self):
        rows=self.full_rows()
        for key in ('wordEnd','separator','observedWord','window'):
            changed=copy.deepcopy(rows)
            changed[0]['source']['span'][key]=999 if key=='wordEnd' else 'tampered'
            with self.subTest(key=key),self.assertRaises(ValueError):
                contract.validate_rows(changed,contract.Exclusions())
        for key in ('prefix','currentWord','observedBoundary','selectionHash'):
            changed=copy.deepcopy(rows);changed[0][key]='tampered'
            with self.subTest(key=key),self.assertRaises(ValueError):
                contract.validate_rows(changed,contract.Exclusions())

    def test_source_span_verification_rejects_different_article_text(self):
        row=self.full_rows()[0]
        with self.assertRaises(ValueError):
            contract.verify_article(row, article(row['source']['articleId'],'different text'))

    def test_file_verification_rejects_missing_changed_and_escaping_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'input').write_bytes(b'fixture')
            files={'input':hashlib.sha256(b'fixture').hexdigest()}
            contract.verify_files(root,files)
            (root/'input').write_bytes(b'changed')
            with self.assertRaises(ValueError):contract.verify_files(root,files)
            with self.assertRaises(ValueError):contract.verify_files(root,{'missing':'0'*64})
            with self.assertRaises(ValueError):contract.verify_files(root,{'../input':'0'*64})

    def test_json_loader_rejects_duplicate_keys_and_nonfinite_values(self):
        for value in ('{"a":1,"a":2}','{"a":NaN}'):
            with self.assertRaises(ValueError): contract.decode_json(value)

    def test_artifact_roundtrip_and_tampering_rejection(self):
        rows=self.full_rows()
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'corpus'
            identity={'fixture':'a'*64}
            generator.write_artifacts(target,rows,identity,{'fixture':1}, {'fixture':'b'*64})
            loaded,_=contract.read_artifacts(target,identity)
            self.assertEqual(1200,len(loaded))
            with self.assertRaises(ValueError):contract.read_artifacts(target,{'fixture':'c'*64})
            path=target/'punctuation-en.jsonl';path.write_bytes(path.read_bytes()+b'\n')
            with self.assertRaises(ValueError):contract.read_artifacts(target,identity)
            with self.assertRaises(ValueError):generator.write_artifacts(target,rows,identity,{}, {})

    def test_generation_counts_cannot_claim_wrong_scan_or_unchecked_fields(self):
        self.assertTrue(hasattr(contract,'validate_generation_counts'), 'generation count validation is not implemented')
        rows=self.full_rows();exclusions=contract.Exclusions()
        counts={'exclusions':exclusions.counts(),'languages':{}}
        for lang in ('en','ru','es'):
            scanned=max(row['source']['parquetRow'] for row in rows if row['language']==lang)+1
            counts['languages'][lang]={'articlesScanned':scanned,'residue3ArticlesInspected':400,
                'priorObservationCandidatesRejected':0,'selectedObservationCandidatesRejected':0}
        contract.validate_generation_counts(rows,counts,exclusions)
        for mutate in ('scan','unknown','negative','exclusions'):
            changed=copy.deepcopy(counts)
            if mutate=='scan':changed['languages']['en']['articlesScanned']+=1
            if mutate=='unknown':changed['languages']['en']['qualityPass']=True
            if mutate=='negative':changed['languages']['en']['priorObservationCandidatesRejected']=-1
            if mutate=='exclusions':changed['exclusions']['en']['prefixes']=1
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                contract.validate_generation_counts(rows,changed,exclusions)

    def replay_fixture(self):
        articles={};prior=[]
        words={'en':('alpha','bravo','Charlie','delta'),
               'ru':('слово','ответ','Далее','снова'),
               'es':('palabra','otra','Luego','verde')}
        for lang in ('en','ru','es'):
            admitted=[n for n in range(100) if contract.admitted(lang,str(n))][:2]
            items=[]
            for number in range(5000):
                code=''.join(chr(97+int(c)) for c in str(admitted[0] if number in admitted else number))
                a,b,c,d=words[lang]
                text=f'fixture{code} source: {a}, {b}. {c} {d}'
                item=article(number,text);item['url']=f'https://{lang}.wikipedia.org/wiki/Fixture_{number}'
                items.append(item)
            articles[lang]=items
            blocked=next(value for value in generator.extract(items[admitted[0]]['text'],lang) if value['boundary']==': ')
            prior.append({'language':lang,'prefix':blocked['prefix'],'chosen':' '+a,'rejected':' unused'})
        exclusions=contract.Exclusions.from_rows(prior)
        rows=[];counts={'exclusions':exclusions.counts(),'languages':{}}
        for lang in ('en','ru','es'):
            selector=generator.Selector(lang,exclusions)
            for ordinal,item in enumerate(articles[lang]):
                selector.consider(item,ordinal)
                if selector.complete:break
            self.assertTrue(selector.complete)
            self.assertGreater(selector.stats['priorObservationCandidatesRejected'],0)
            self.assertGreater(selector.stats['selectedObservationCandidatesRejected'],0)
            rows.extend(selector.rows);counts['languages'][lang]=dict(selector.stats)
        return rows,counts,exclusions,articles

    def test_selector_replay_rejects_consistently_shortened_source_word(self):
        rows,counts,exclusions,articles=self.replay_fixture()
        changed=copy.deepcopy(rows)
        row=next(value for value in changed if len(value['currentWord'])>3)
        row['currentWord']=row['currentWord'][:-1]
        row['originalContinuation']=' '+row['currentWord']
        row['source']['span']['observedWord']=row['source']['span']['observedWord'][:-1]
        row['source']['span']['wordEnd']-=1
        row['selectionHash']=contract.selection_hash(row['language'],row['observedBoundary'],row['prefix'],row['currentWord'])
        row['id']=f"{row['language']}-{row['split']}-v5-{row['selectionHash']}"
        # The old substring-only checks accept this internally consistent truncation.
        contract.validate_rows(changed,exclusions)
        contract.verify_article(row,articles[row['language']][row['source']['parquetRow']])
        self.assertTrue(hasattr(contract,'verify_selection'), 'exact selector replay is not implemented')
        contract.verify_selection(rows,counts,exclusions,articles)
        with self.assertRaisesRegex(ValueError,'SELECTION_REPLAY_ROWS'):
            contract.verify_selection(changed,counts,exclusions,articles)

    def test_selector_replay_rejects_all_six_zeroed_rejection_counters(self):
        rows,counts,exclusions,articles=self.replay_fixture()
        changed=copy.deepcopy(counts)
        for lang in ('en','ru','es'):
            changed['languages'][lang]['priorObservationCandidatesRejected']=0
            changed['languages'][lang]['selectedObservationCandidatesRejected']=0
        # Nonnegative counts alone are insufficient provenance.
        contract.validate_generation_counts(rows,changed,exclusions)
        self.assertTrue(hasattr(contract,'verify_selection'), 'exact selector replay is not implemented')
        with self.assertRaisesRegex(ValueError,'SELECTION_REPLAY_COUNTS'):
            contract.verify_selection(rows,changed,exclusions,articles)

    def test_full_admission_rejects_rehashed_rows_and_counts(self):
        rows,counts,exclusions,articles=self.replay_fixture()
        source,_=contract.locks()
        by_filename={source['languageFiles'][lang]:items for lang,items in articles.items()}
        fake_parquet=types.ModuleType('pyarrow.parquet')
        class ParquetFile:
            def __init__(self,path):self.items=by_filename[Path(path).name]
            def iter_batches(self,batch_size,columns):
                for offset in range(0,len(self.items),batch_size):
                    items=self.items[offset:offset+batch_size]
                    yield types.SimpleNamespace(to_pylist=lambda items=items:items)
        fake_parquet.ParquetFile=ParquetFile
        fake_arrow=types.ModuleType('pyarrow');fake_arrow.parquet=fake_parquet
        identity={'synthetic':'a'*64};toolchain={'synthetic':True}
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.dict('sys.modules',{'pyarrow':fake_arrow,'pyarrow.parquet':fake_parquet}), \
             mock.patch.object(contract,'current_identity',return_value=identity), \
             mock.patch.object(contract,'toolchain_identity',return_value=toolchain), \
             mock.patch.object(contract,'load_exclusions',return_value=exclusions):
            good=Path(temp)/'good'
            generator.write_artifacts(good,rows,identity,counts,toolchain)
            admitted,_=contract.load_corpus(good)
            self.assertEqual(1200,len(admitted))
            for mutation,code in (('word','SELECTION_REPLAY_ROWS'),('counts','SELECTION_REPLAY_COUNTS')):
                changed_rows=copy.deepcopy(rows);changed_counts=copy.deepcopy(counts)
                if mutation=='word':
                    row=next(value for value in changed_rows if len(value['currentWord'])>3)
                    row['currentWord']=row['currentWord'][:-1]
                    row['originalContinuation']=' '+row['currentWord']
                    row['source']['span']['observedWord']=row['source']['span']['observedWord'][:-1]
                    row['source']['span']['wordEnd']-=1
                    row['selectionHash']=contract.selection_hash(row['language'],row['observedBoundary'],row['prefix'],row['currentWord'])
                    row['id']=f"{row['language']}-{row['split']}-v5-{row['selectionHash']}"
                else:
                    for stats in changed_counts['languages'].values():
                        stats['priorObservationCandidatesRejected']=0
                        stats['selectedObservationCandidatesRejected']=0
                target=Path(temp)/mutation
                generator.write_artifacts(target,changed_rows,identity,changed_counts,toolchain)
                with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,code):
                    contract.load_corpus(target)


if __name__=='__main__': unittest.main()
