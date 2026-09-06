"""Strict, punctuation-only v5 input contract. No scoring or threshold dependency."""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
INPUTS = REPO / 'build/smart-typing-0.3/qualification-v4/wikipedia-20231101'
LANGUAGES = ('en', 'ru', 'es')
SPLITS = ('calibration', 'holdout')
BOUNDARIES = (': ', '. ', ', ', ' ')
LABEL = 'observed_wikipedia_boundary'
SCOPE = 'smart-typing-0.3-contextual-v5-source-observations'
FILES = tuple(f'punctuation-{lang}.jsonl' for lang in LANGUAGES) + ('attribution.jsonl',)
ALPHABETS = {'en': 'abcdefghijklmnopqrstuvwxyz', 'ru': 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
             'es': 'abcdefghijklmnñopqrstuvwxyzáéíóúü'}
BOUNDARY_RE = re.compile(r'([.,:]|\s)(\s*)([^\W\d_]+)', re.UNICODE)
HEX = re.compile(r'^[0-9a-f]{64}$')
# Filled once from the independently recorded recipe, never from an input receipt at runtime.
PINNED_LOCKS = {'source-lock.json': 'b70c04203de82dd1f315f2e66b5c780484352809833adb6068d741c2b2bd1f7c', 'exclusion-lock.json': '7054bae1871a1bf23e6f3875c6f31714cfd65c8066a0ae338f9a0182b5bb8043'}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def decode_json(text):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('NONFINITE_JSON')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path):
    return decode_json(Path(path).read_text(encoding='utf-8'))


def verify_files(root, files):
    root = Path(root).resolve(strict=True)
    for name, expected in files.items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts and HEX.fullmatch(expected),
                'INPUT_PATH_OR_DIGEST')
        path = root / relative
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root), 'INPUT_MISSING_OR_SYMLINK')
        require(sha(path) == expected, 'INPUT_DIGEST')


def locks():
    verify_files(HERE, PINNED_LOCKS)
    source = read_json(HERE / 'source-lock.json')
    exclusions = read_json(HERE / 'exclusion-lock.json')
    require(source['articleSelection'] == {'seed': 7042026, 'modulus': 4, 'residue': 3}, 'ARTICLE_RULE')
    require(len(exclusions['files']) == 40 and exclusions['schemaVersion'] == 1, 'EXCLUSION_LOCK')
    return source, exclusions


def norm(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def observation(text):
    return tuple(re.findall(r'[^\W\d_]+', norm(text), re.UNICODE)[-12:])


class Exclusions:
    def __init__(self):
        self.prefixes = {lang: set() for lang in LANGUAGES}
        self.observations = {lang: set() for lang in LANGUAGES}

    @classmethod
    def from_rows(cls, rows):
        result = cls()
        for row in rows:
            lang, prefix = row.get('language'), row.get('prefix')
            require(lang in LANGUAGES and isinstance(prefix, str), 'PRIOR_LANGUAGE_PREFIX')
            if 'chosen' in row or 'rejected' in row:
                endings = [row.get('chosen'), row.get('rejected')]
                require(all(isinstance(value, str) and value for value in endings), 'PRIOR_PAIR_SCHEMA')
            else:
                candidates = row.get('candidates')
                require(isinstance(candidates, list) and candidates and
                        all(isinstance(value, str) and value for value in candidates), 'PRIOR_CANDIDATE_SCHEMA')
                word = row.get('currentWord', row.get('typed'))
                require(isinstance(word, str) and word, 'PRIOR_WORD_SCHEMA')
                endings = [word, *candidates]
                if 'expectedSpelling' in row:
                    require(isinstance(row['expectedSpelling'], str) and row['expectedSpelling'], 'PRIOR_EXPECTED_SCHEMA')
                    endings.append(row['expectedSpelling'])
            result.prefixes[lang].add(norm(prefix))
            for ending in endings:
                result.observations[lang].add(observation(prefix + ' ' + ending))
        return result

    def blocks(self, lang, prefix, word):
        return norm(prefix) in self.prefixes[lang] or observation(prefix + ' ' + word) in self.observations[lang]

    def counts(self):
        return {lang: {'prefixes': len(self.prefixes[lang]), 'observations': len(self.observations[lang])}
                for lang in LANGUAGES}


def load_exclusions():
    _, excluded = locks()
    verify_files(REPO, excluded['files'])
    def rows():
        for name in sorted(excluded['files']):
            with (REPO / name).open(encoding='utf-8') as stream:
                for line in stream:
                    yield decode_json(line)
    return Exclusions.from_rows(rows())


def admitted(lang, article_id):
    rank = int.from_bytes(hashlib.sha256(f'7042026:{lang}:{article_id}'.encode()).digest()[:8], 'big')
    return rank % 4 == 3


def article_split(lang, article_id):
    return SPLITS[hashlib.sha256(f'contextual-v5-split:{lang}:{article_id}'.encode()).digest()[0] % 2]


def bounded_prefix(value):
    value = unicodedata.normalize('NFC', value).lstrip()
    encoded = value.encode('utf-8')
    if len(encoded) <= 256:
        return value
    tail = encoded[-256:].decode('utf-8', errors='ignore')
    boundary = re.search(r'\s', tail)
    return tail[boundary.end():] if boundary else ''


def selection_hash(lang, boundary, prefix, word):
    return text_sha(f'5062026:punctuation:{lang}:{boundary}:{prefix}:{word}')


def verify_article(row, article):
    source = row['source']
    require(article['id'] == source['articleId'] and article['url'] == source['url'] and
            article['title'] == source['title'], 'SOURCE_ARTICLE_IDENTITY')
    raw = article['text'] or ''
    normalized = unicodedata.normalize('NFC', raw)
    require(text_sha(raw) == source['articleSha256'] and text_sha(normalized) == source['normalizedArticleSha256'], 'ARTICLE_TEXT_DIGEST')
    span = source['span']
    require(normalized[span['windowStart']:span['boundaryStart']] == span['window'] and
            normalized[span['boundaryStart']:span['wordStart']] == span['separator'] and
            normalized[span['wordStart']:span['wordEnd']] == span['observedWord'], 'SOURCE_SPAN_MISMATCH')


def validate_rows(rows, exclusions):
    require(isinstance(rows, list) and len(rows) == 1200, 'EXACT_CORPUS_COUNT')
    ids, articles, observations = set(), set(), set()
    counts = Counter()
    source_lock, _ = locks()
    for row in rows:
        require(set(row) == {'corpusVersion','id','language','split','task','prefix','currentWord',
                'originalContinuation','observedBoundary','labelSemantics','noAuto','selectionHash','source'}, 'ROW_SCHEMA')
        lang, split, word = row['language'], row['split'], row['currentWord']
        require(type(row['corpusVersion']) is int and row['corpusVersion'] == 5 and row['task'] == 'punctuation' and
                row['labelSemantics'] == LABEL and row['noAuto'] is True and lang in LANGUAGES and split in SPLITS, 'ROW_CONTRACT')
        boundary, prefix = row['observedBoundary'], row['prefix']
        require(boundary in BOUNDARIES and isinstance(prefix,str) and 0 < len(prefix.encode('utf-8')) <= 256 and
                unicodedata.normalize('NFC',prefix) == prefix and prefix == prefix.rstrip(), 'PREFIX_OR_BOUNDARY')
        require(isinstance(word,str) and 3 <= len(word) <= 20 and all(char in ALPHABETS[lang] for char in word) and
                word == unicodedata.normalize('NFC',word) and row['originalContinuation'] == ' '+word, 'ORIGINAL_WORD')
        expected_hash = selection_hash(lang,boundary,prefix,word)
        require(row['selectionHash'] == expected_hash and row['id'] == f'{lang}-{split}-v5-{expected_hash}', 'ROW_IDENTITY')
        source = row['source']
        require(set(source) == {'articleId','url','title','repositoryPath','parquetRow','articleSha256',
                'normalizedArticleSha256','span','transformations'}, 'SOURCE_SCHEMA')
        article_id = source['articleId']
        require(isinstance(article_id,str) and article_id.isdecimal() and admitted(lang,article_id) and
                split == article_split(lang,article_id), 'ARTICLE_PARTITION')
        require(source['repositoryPath'] == source_lock['files'][source_lock['languageFiles'][lang]]['repositoryPath'] and
                type(source['parquetRow']) is int and source['parquetRow'] >= 0 and
                isinstance(source['url'],str) and source['url'].startswith(f'https://{lang}.wikipedia.org/wiki/') and
                isinstance(source['title'],str) and source['title'] and
                all(isinstance(source[key],str) and HEX.fullmatch(source[key]) for key in ('articleSha256','normalizedArticleSha256')),
                'SOURCE_IDENTITY')
        require(source['transformations'] == TRANSFORMATIONS, 'TRANSFORMATION_CONTRACT')
        span = source['span']
        require(set(span) == {'windowStart','boundaryStart','wordStart','wordEnd','window','separator','observedWord'}, 'SPAN_SCHEMA')
        require(all(type(span[key]) is int for key in ('windowStart','boundaryStart','wordStart','wordEnd')) and
                0 <= span['windowStart'] <= span['boundaryStart'] < span['wordStart'] < span['wordEnd'] and
                span['windowStart'] == max(0,span['boundaryStart']-512), 'SPAN_OFFSETS')
        require(all(isinstance(span[key],str) for key in ('window','separator','observedWord')) and
                len(span['window']) == span['boundaryStart']-span['windowStart'] and
                len(span['separator']) == span['wordStart']-span['boundaryStart'] and
                len(span['observedWord']) == span['wordEnd']-span['wordStart'] and
                bounded_prefix(span['window']).rstrip() == prefix and span['observedWord'].casefold() == word,
                'SPAN_TRANSFORMATION')
        separator = span['separator']
        require((boundary == ' ' and separator == ' ' and span['observedWord'] == word) or
                (boundary != ' ' and separator[0] == boundary[0] and len(separator)>1 and separator[1:].isspace() and
                 (span['observedWord'][:1] == span['observedWord'][:1].upper() if boundary == '. ' else span['observedWord'] == word)),
                'SOURCE_BOUNDARY_CASE')
        identity=(lang,article_id); context=(lang,observation(prefix+' '+word))
        require(row['id'] not in ids and identity not in articles and context not in observations, 'ROW_ARTICLE_CONTEXT_OVERLAP')
        require(not exclusions.blocks(lang,prefix,word), 'PRIOR_OBSERVATION_OVERLAP')
        ids.add(row['id']);articles.add(identity);observations.add(context)
        counts[(lang,split,boundary)] += 1
    require(all(counts[(lang,split,boundary)] == 50 for lang in LANGUAGES for split in SPLITS for boundary in BOUNDARIES), 'BOUNDARY_QUOTAS')
    return {'rows':len(rows),'uniqueArticles':len(articles),'uniqueObservations':len(observations),
            'counts':{f'{lang}/{split}/{BOUNDARY_NAMES[boundary]}':count for (lang,split,boundary),count in sorted(counts.items())}}


BOUNDARY_NAMES = {' ':'space', ', ':'comma', ': ':'colon', '. ':'period'}
TRANSFORMATIONS = {'articleNormalization':'NFC', 'offsetUnit':'NFC Unicode code points',
    'prefixWindowMaximumCodePoints':512, 'prefixMaximumUtf8Bytes':256,
    'prefixTransform':'lstrip; retain last 256 UTF-8 bytes at next whitespace if oversized; rstrip',
    'wordTransform':'Unicode casefold', 'separatorTransform':'observed marker plus ASCII space',
    'sentenceCandidateTransform':'first code point uppercase; applied by production variant exporter'}


def toolchain_identity():
    import pyarrow
    import _hashlib
    import _json
    base=Path(pyarrow.__file__).resolve().parent
    files={str(p.relative_to(base)):sha(p) for p in sorted(base.rglob('*'))
           if p.is_file() and p.suffix in ('.py','.so','.dylib') and '__pycache__' not in p.parts}
    standard_files = {Path(module.__file__).resolve() for module in
                      (hashlib, _hashlib, _json, unicodedata)}
    for module in (json, re):
        standard_files.update(Path(module.__file__).resolve().parent.glob('*.py'))
    return {'pythonVersion':sys.version, 'pythonExecutable':str(Path(sys.executable).resolve()),
            'pythonExecutableSha256':sha(Path(sys.executable).resolve()), 'unicodeVersion':unicodedata.unidata_version,
            'pythonLibraryFiles':{str(path):sha(path) for path in sorted(standard_files)},
            'pyarrowVersion':pyarrow.__version__, 'pyarrowDirectory':str(base), 'pyarrowFiles':files}


def current_identity():
    source,excluded=locks()
    verify_files(REPO, {source['priorSourceLock']['path']:source['priorSourceLock']['sha256'],
                        source['referenceGenerator']['path']:source['referenceGenerator']['sha256']})
    verify_files(INPUTS,{name:item['sha256'] for name,item in source['files'].items()})
    require(all((INPUTS/name).stat().st_size==item['bytes'] for name,item in source['files'].items()), 'PARQUET_SIZE')
    verify_files(REPO,excluded['files'])
    return {'implementation':{name:sha(HERE/name) for name in ('generate_corpus.py','corpus_contract.py','source-lock.json','exclusion-lock.json')},
            'sourceFiles':{name:item['sha256'] for name,item in source['files'].items()},
            'exclusionFiles':excluded['files'],'recipe':source['recipe']}


def read_artifacts(directory, expected_identity):
    """Digest/manifest layer; use load_corpus for the complete admission check."""
    directory=Path(directory).resolve(strict=True)
    manifest=read_json(directory/'manifest.json')
    require(set(manifest)=={'schemaVersion','corpusVersion','scope','labelSemantics','modelScoringPerformed',
            'qualityQualified','frozen','identity','toolchain','generationCounts','validation','files'}, 'MANIFEST_SCHEMA')
    require(type(manifest['schemaVersion']) is int and manifest['schemaVersion']==1 and
            type(manifest['corpusVersion']) is int and manifest['corpusVersion']==5 and manifest['scope']==SCOPE and
            manifest['labelSemantics']==LABEL and manifest['modelScoringPerformed'] is False and
            manifest['qualityQualified'] is False and manifest['frozen'] is False and
            manifest['identity']==expected_identity, 'MANIFEST_IDENTITY')
    require(set(manifest['files'])==set(FILES) and {p.name for p in directory.iterdir()}==set(FILES)|{'manifest.json'}, 'ARTIFACT_FILE_SET')
    verify_files(directory,manifest['files'])
    rows=[]
    for lang in LANGUAGES:
        with (directory/f'punctuation-{lang}.jsonl').open(encoding='utf-8') as stream:
            language_rows=[decode_json(line) for line in stream]
        require(all(row.get('language')==lang for row in language_rows), 'LANGUAGE_FILE')
        require(language_rows==sorted(language_rows,key=lambda row:(row['split']!='calibration',row['id'])), 'ROW_ORDER')
        rows.extend(language_rows)
    with (directory/'attribution.jsonl').open(encoding='utf-8') as stream:
        attribution=[decode_json(line) for line in stream]
    require(attribution==[{'id':row['id'],'language':row['language'],'source':row['source']} for row in rows], 'ATTRIBUTION_LINK')
    return rows,manifest


def validate_generation_counts(rows, counts, exclusions):
    require(isinstance(counts,dict) and set(counts)=={'exclusions','languages'} and
            counts['exclusions']==exclusions.counts() and set(counts['languages'])==set(LANGUAGES), 'GENERATION_COUNT_SCHEMA')
    for lang in LANGUAGES:
        stats=counts['languages'][lang]
        require(set(stats)=={'articlesScanned','residue3ArticlesInspected',
                'priorObservationCandidatesRejected','selectedObservationCandidatesRejected'} and
                all(type(value) is int and value>=0 for value in stats.values()), 'GENERATION_COUNT_VALUES')
        scanned=max(row['source']['parquetRow'] for row in rows if row['language']==lang)+1
        require(stats['articlesScanned']==scanned and 400<=stats['residue3ArticlesInspected']<=scanned, 'GENERATION_SCAN_COUNT')


def verify_selection(rows, counts, exclusions, articles_by_language):
    """Replay the actual fixed selector, including candidates rejected before selection."""
    spec=importlib.util.spec_from_file_location('contextual_v5_selector_replay',HERE/'generate_corpus.py')
    generator=importlib.util.module_from_spec(spec)
    # The exporter imports its sibling contract by name. Do not resolve another
    # corpus package when this entry point is itself loaded through importlib.
    previous_path=list(sys.path)
    try:
        sys.path.insert(0,str(HERE))
        spec.loader.exec_module(generator)
    finally:
        sys.path[:]=previous_path
    require(Path(generator.c.__file__).resolve()==Path(__file__).resolve(), 'SELECTOR_CONTRACT_MODULE')
    selected=[]
    measured={'exclusions':exclusions.counts(),'languages':{}}
    for lang in LANGUAGES:
        selector=generator.Selector(lang,exclusions)
        for ordinal,article in enumerate(articles_by_language[lang]):
            selector.consider(article,ordinal)
            if selector.complete:break
        require(selector.complete, 'SELECTION_REPLAY_INCOMPLETE')
        selected.extend(selector.rows)
        measured['languages'][lang]=dict(selector.stats)
    def ordered(values):
        return sorted(values,key=lambda row:(LANGUAGES.index(row['language']),row['split']!='calibration',row['id']))
    require(canonical(ordered(rows))==canonical(ordered(selected)), 'SELECTION_REPLAY_ROWS')
    require(canonical(counts)==canonical(measured), 'SELECTION_REPLAY_COUNTS')


def verify_parquet_rows(rows, counts, exclusions):
    import pyarrow.parquet as parquet
    source,_=locks()
    def articles(path):
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=64,columns=['id','url','title','text']):
            yield from batch.to_pylist()
    verify_selection(rows,counts,exclusions,
                     {lang:articles(INPUTS/source['languageFiles'][lang]) for lang in LANGUAGES})


def load_corpus(directory):
    """Root integration entry point: strict v5 only, no legacy guard changes."""
    identity=current_identity()
    rows,manifest=read_artifacts(directory,identity)
    require(manifest['toolchain']==toolchain_identity(), 'TOOLCHAIN_IDENTITY')
    exclusions=load_exclusions()
    report=validate_rows(rows,exclusions)
    require(report==manifest['validation'], 'VALIDATION_RECEIPT')
    validate_generation_counts(rows,manifest['generationCounts'],exclusions)
    verify_parquet_rows(rows,manifest['generationCounts'],exclusions)
    require(identity==current_identity(), 'INPUT_CHANGED_DURING_VALIDATION')
    return rows,manifest
