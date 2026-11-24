"""Gate legacy collectors on durable exclusions; historical replay is explicit."""
from pathlib import Path
import hashlib
import re
import sys
import unicodedata
from functools import lru_cache

import control_ledger
from holdout_ledger import source_segment_hash,validate_ledger
from public_corpus_preparation_v1 import preflight,registry_bindings,english_surface_bindings
from joint_exclusion_inputs import source_context_hash
import joint_public_sources
import selector_text_format_v1 as text_format
import json

HERE=Path(__file__).resolve().parent


def attach_selector_segment(row, sentence, snapshot):
    """Bind a selected whole source segment without changing historical rows."""
    if snapshot is not None:
        row['sourceSegmentHash']=source_segment_hash(sentence)
    return row


_BOUNDARY=re.compile(r'(?<=[.!?])\s+|\n+')


def selector_segments(text):
    """Yield the same segments as the historical split, with source offsets."""
    start=0
    for boundary in _BOUNDARY.finditer(text):
        yield text[start:boundary.start()],start
        start=boundary.end()
    yield text[start:],start


def whole_selector_token(text, sentence, start, match, snapshot):
    """Do not promote a Cyrillic fragment of a larger source token as a word."""
    if snapshot is None:
        return True  # Historical reproduction preserves its original selector.
    if (text[start:start+len(sentence)] != sentence or match.string is not sentence or
            start < 0 or not match.group()):
        raise ValueError('SELECTOR_SOURCE_MISMATCH')
    first=start+match.start();last=start+match.end()
    def joins(char):
        return bool(char) and (char.isalnum() or char=='_' or unicodedata.category(char)=='Pd' or
                               unicodedata.category(char).startswith('M') or
                               unicodedata.category(char)=='Cf')
    left=text[first-1:first] if first else '';right=text[last:last+1]
    if joins(left) or joins(right):
        return False
    apostrophes="'’ʼ"
    if (left and left in apostrophes and first>=2 and joins(text[first-2:first-1])):
        return False
    if (right and right in apostrophes and joins(text[last+1:last+2])):
        return False
    return True


@lru_cache(maxsize=1)
def _context_generator():
    from prepare_external_spelling_holdout import load_generator
    return load_generator()


def attach_selector_source(row,text,sentence,start,match,snapshot):
    """Bind the article and original source window to the selected target."""
    if snapshot is None:
        return row
    if not whole_selector_token(text,sentence,start,match,snapshot):
        raise ValueError('SELECTOR_PARTIAL_SOURCE_TOKEN')
    if (text[start:start+len(sentence)] != sentence or match.string is not sentence
            or match.group() != row.get('expectedSpelling')):
        raise ValueError('SELECTOR_SOURCE_MISMATCH')
    absolute=re.compile(r'[а-яё]+',re.IGNORECASE).match(text,start+match.start())
    if absolute is None or absolute.group()!=match.group():
        raise ValueError('SELECTOR_SOURCE_MISMATCH')
    article=row.get('articleId')
    if not isinstance(article,str) or not article.isascii() or not article.isdecimal():
        raise ValueError('SELECTOR_ARTICLE_ID')
    row['article']=article
    row['contextHash']=source_context_hash(text,absolute,_context_generator())
    return attach_selector_segment(row,sentence,snapshot)


def project_selector_families(rows,lexicon):
    """Use all pinned dictionary analyses and reject cross-partition leakage."""
    by_part={};cache={}
    for row in rows:
        target=row.get('expectedSpelling');part=row.get('partition')
        if not isinstance(target,str) or not target or part not in ('train','dev','test'):
            raise ValueError('SELECTOR_TARGET_SCHEMA')
        if target not in cache:
            cache[target]=sorted({analysis.lemma for analysis in lexicon.analyses(target)})
        if not cache[target]:raise ValueError('SELECTOR_CANONICAL_UNRESOLVED')
        row['families']=cache[target]
        by_part.setdefault(part,set()).update(cache[target])
    groups=list(by_part.values())
    if any(left & right for i,left in enumerate(groups) for right in groups[i+1:]):
        raise ValueError('SELECTOR_CANONICAL_SPLIT_OVERLAP')
    return rows


def validate_selector_partitions(rows):
    """Prevent shared source identities between generated partitions."""
    axes=('article','contextHash','sourceSegmentHash')
    parts={}
    for row in rows:
        part=row.get('partition')
        if part not in ('train','dev','test'):raise ValueError('SELECTOR_PARTITION_SCHEMA')
        keys=parts.setdefault(part,{axis:set() for axis in axes})
        for axis in axes:
            value=row.get(axis)
            if not isinstance(value,str) or not value:raise ValueError('SELECTOR_SOURCE_SCHEMA')
            keys[axis].add(value)
    groups=list(parts.values())
    for i,left in enumerate(groups):
        for right in groups[i+1:]:
            if any(left[axis] & right[axis] for axis in axes):
                raise ValueError('SELECTOR_SOURCE_SPLIT_OVERLAP')


class SelectorAdmission:
    """Reserve source identities and all known lemmas only for accepted rows."""
    def __init__(self,lexicon):
        self.lexicon=lexicon
        self.owners={axis:{} for axis in ('article','contextHash','sourceSegmentHash','family')}
        self.counts={'accepted':0,'unresolved':0,'overlap':0}

    def accept(self,row):
        part=row.get('partition');target=row.get('expectedSpelling')
        if part not in ('train','dev','test') or not isinstance(target,str) or not target:
            raise ValueError('SELECTOR_TARGET_SCHEMA')
        values={axis:{row.get(axis)} for axis in ('article','contextHash','sourceSegmentHash')}
        if any(not isinstance(next(iter(value)),str) or not next(iter(value)) for value in values.values()):
            raise ValueError('SELECTOR_SOURCE_SCHEMA')
        values['family']={analysis.lemma for analysis in self.lexicon.analyses(target)}
        if not values['family']:
            self.counts['unresolved']+=1
            return False
        if any(self.owners[axis].get(value,part)!=part for axis,items in values.items() for value in items):
            self.counts['overlap']+=1
            return False
        for axis,items in values.items():
            for value in items:self.owners[axis][value]=part
        row['families']=sorted(values['family'])
        self.counts['accepted']+=1
        return True


def selector_admission(snapshot):
    if snapshot is None:return None
    sys.path.insert(0,str(HERE.parent/'morphology'))
    from ranker import PymorphyLexicon
    return SelectorAdmission(PymorphyLexicon(cache_size=16384))


def reject_unchecked_texts(snapshot,texts):
    """Word-row identities do not certify separately emitted training text."""
    if snapshot is not None and any(texts.values()):
        raise ValueError('SELECTOR_TEXT_CORPUS_UNCHECKED')


def check_selected_source_text(snapshot, source, fragment):
    """Reject untrusted source fragments before adding future selected text."""
    if snapshot is None:
        return  # Historical reproduction keeps its original byte selection.
    result = text_format.inspect(source, fragment)
    if result['formatFragments']:
        raise ValueError('SELECTOR_TEXT_FORMAT_FRAGMENT')
    if result['truncated']:
        raise ValueError('SELECTOR_TEXT_TRUNCATED')
    # The cleaned text removes punctuation and non-Cyrillic characters. A
    # resulting fragment must still cover whole source tokens under the same
    # boundary rule used for selected word rows.
    normalized = unicodedata.normalize('NFC', source)
    fragment_words = list(re.finditer(r'[а-яё]+', fragment, re.IGNORECASE))
    source_words = re.finditer(r'[а-яё]+', normalized, re.IGNORECASE)
    for _, match in zip(fragment_words, source_words):
        if not whole_selector_token(normalized, normalized, 0, match, snapshot):
            raise ValueError('SELECTOR_TEXT_PARTIAL_SOURCE_TOKEN')


def selector_families(snapshot,rows):
    if snapshot is None:return None
    validate_selector_partitions(rows)
    sys.path.insert(0,str(HERE.parent/'morphology'))
    from ranker import PymorphyLexicon
    lexicon=PymorphyLexicon(cache_size=16384)
    project_selector_families(rows,lexicon)
    return lexicon.receipt()


def selector_inputs(snapshot,parquet,parquet_hash,frequency,frequency_hash,collector=None):
    if snapshot is None:return None
    root=HERE.parents[1]
    sources=[HERE/'independent_corpus_guard.py',HERE/'selector_text_format_v1.py',HERE/'joint_exclusion_inputs.py',HERE/'prepare_refinement.py',
             HERE/'right_context_sentence_audit.py',HERE/'prepare_external_spelling_holdout.py',
             HERE.parent/'morphology/ranker.py',
             root/'tools/eval/smart-typing-0.3/qualification-v2/generate_corpus.py']
    if collector is not None:sources.append(Path(collector))
    inputs={'parquet':(parquet,parquet_hash),'frequency':(frequency,frequency_hash)}
    for path in sources:
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        inputs[str(path.relative_to(root))]=(path,digest)
    return joint_public_sources.snapshot(inputs)


def prior_input_snapshot(root, datasets, helpers=()):
    """Capture the exact prior data graphs and helper sources used by a selector."""
    root = Path(root)
    inputs = {}
    for dataset, observation in datasets:
        base = Path('build') / dataset
        names = [base / 'data/manifest.json', base / observation / 'manifest.json']
        names.extend(base / 'data' / f'{part}-{kind}.jsonl'
                     for part in ('train', 'dev', 'test') for kind in ('rows', 'text'))
        for name in names:
            path = root / name
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            inputs[str(name)] = (path, digest)
    for path in helpers:
        path = Path(path)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        inputs[str(path.relative_to(HERE.parents[1]))] = (path, digest)
    return joint_public_sources.snapshot(inputs)


def verify_selector_inputs(snapshot):
    if snapshot is not None:joint_public_sources.verify(snapshot)


def begin(historical_reproduction=False):
    if type(historical_reproduction) is not bool:
        raise ValueError('HISTORICAL_REPRODUCTION_BOOLEAN')
    if historical_reproduction:
        return None
    lexical=(HERE/'holdout-ledger.json').read_bytes()
    controls=(HERE/'control-ledger.json').read_bytes()
    left=validate_ledger(json.loads(lexical));right=control_ledger.validate(json.loads(controls))
    if not left['coverage']['complete'] or not right['coverageComplete']:
        raise ValueError('NEW_HOLDOUT_REGISTRY_COVERAGE_INCOMPLETE')
    bindings=registry_bindings(lexical,controls)
    return dict(lexical=left,controls=right,registryBindings=bindings,
                englishSurfaceBindings=bindings['englishSurfaceBindings'])


def finish(snapshot,rows):
    sources={str((HERE/name).relative_to(HERE.parents[1])):
        hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in (
            'independent_corpus_guard.py','public_corpus_preparation_v1.py',
            'control_ledger.py','holdout_ledger.py','conversation_split_checks.py',
            'source_identities.py','recover_legacy_families.py')}
    if snapshot is None:
        return dict(scope='historical-disclosed-regression',newUnseenHoldout=False,
                    independentQualification=False,historicalReproduction=True,
                    registryGuardSources=sources)
    report=preflight(rows,'spelling',snapshot['lexical'],snapshot['controls'],'new-families')
    if report['status']!='READY_TO_FREEZE':
        raise ValueError('NEW_HOLDOUT_'+report['status'])
    current=registry_bindings((HERE/'holdout-ledger.json').read_bytes(),(HERE/'control-ledger.json').read_bytes())
    if current!=snapshot['registryBindings']:
        raise ValueError('NEW_HOLDOUT_REGISTRY_DRIFT')
    surface_bindings=english_surface_bindings()
    if surface_bindings!=snapshot['englishSurfaceBindings']:
        raise ValueError('NEW_HOLDOUT_SURFACE_DRIFT')
    return dict(scope='registry-checked-corpus-proposal',independentQualification=False,
                historicalReproduction=False,registryBindings=current,registryGuardSources=sources,
                englishSurfaceBindings=surface_bindings)
