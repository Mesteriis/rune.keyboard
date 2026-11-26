"""Capture complete manifest-bound exclusion inputs before corpus selection."""
import hashlib
import json
from bisect import bisect_right
from pathlib import Path
import re
from right_context_sentence_audit import _source_hash
from holdout_ledger import source_segment_hash

SEGMENT_BOUNDARY = re.compile(r'(?<=[.!?])\s+|\n+')


def segment_index(text):
    """Index the historical selector delimiters once per source article."""
    if not isinstance(text, str): raise ValueError('JOINT_SEGMENT_TEXT')
    starts, ends, start = [], [], 0
    for boundary in SEGMENT_BOUNDARY.finditer(text):
        starts.append(start); ends.append(boundary.start()); start = boundary.end()
    starts.append(start); ends.append(len(text))
    return starts, ends


def source_segment_hash_at(text, match, index):
    if match.string is not text: raise ValueError('JOINT_SEGMENT_SOURCE')
    starts, ends = index; position = bisect_right(starts, match.start()) - 1
    if position < 0 or match.start() < starts[position] or match.end() > ends[position]:
        raise ValueError('JOINT_SEGMENT_BOUNDARY')
    return source_segment_hash(text[starts[position]:ends[position]])


def source_context_hash(text, match, generator):
    """Use the established Wikipedia source window, before typo generation."""
    start,end=match.span()
    prefix=generator.bounded_prefix(text[max(0,start-256):start]).rstrip(' \t')
    return _source_hash(prefix,match.group().casefold(),text[end:end+128])


def capture(directory,required):
    directory=Path(directory).resolve();manifest_path=directory/'manifest.json'
    if manifest_path.is_symlink():raise ValueError('EXCLUSION_PATH')
    raw=manifest_path.read_bytes();manifest=json.loads(raw);entries=manifest.get('files')
    if not isinstance(entries,dict) or not entries or not set(required)<=entries.keys():
        raise ValueError('EXCLUSION_MANIFEST_SCOPE')
    counts=manifest.get('counts')
    if not isinstance(counts,dict):raise ValueError('EXCLUSION_COUNTS')
    files={manifest_path:raw};families=set();articles=set()
    for name,digest in sorted(entries.items()):
        if not isinstance(name,str) or Path(name).name!=name or not name.endswith('.jsonl'):
            raise ValueError('EXCLUSION_PATH')
        path=directory/name
        if path.is_symlink():raise ValueError('EXCLUSION_PATH')
        payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('EXCLUSION_IDENTITY')
        files[path]=payload
        part=name.removesuffix('.jsonl');lines=payload.decode('utf-8').splitlines()
        if (part not in ('train','calibration','holdout') or not lines or
                type(counts.get(part,{}).get('rows')) is not int or counts[part]['rows']!=len(lines)):
            raise ValueError('EXCLUSION_COUNTS')
        for line in lines:
            row=json.loads(line)
            if row.get('split')!=part:raise ValueError('EXCLUSION_SPLIT')
            if not isinstance(row.get('family'),str) or not row['family'] or not isinstance(row.get('article'),str) or not row['article']:
                raise ValueError('EXCLUSION_ROW')
            families.add(row['family']);articles.add(row['article'])
    actual={p.name for p in directory.glob('*.jsonl')}
    if actual!=set(entries):raise ValueError('EXCLUSION_UNDECLARED_FILES')
    return dict(files=files,directory=directory,names=set(entries),families=families,articles=articles,manifestSha256=hashlib.sha256(raw).hexdigest())


def verify(snapshot):
    if {p.name for p in snapshot['directory'].glob('*.jsonl')}!=snapshot['names']:
        raise ValueError('EXCLUSION_INPUT_DRIFT')
    for path,raw in snapshot['files'].items():
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('EXCLUSION_INPUT_DRIFT')


def verify_registered(snapshot,ledger):
    """Require each captured split and its manifest in the same ledger entry."""
    matches={}
    for name in sorted(snapshot['names']):
        digest=hashlib.sha256(snapshot['files'][snapshot['directory']/name]).hexdigest()
        found=[]
        for entry in ledger['entries']:
            bindings=entry.get('bindings',{})
            for key,value in bindings.items():
                path=Path(key)
                if path.name==name and value==digest and bindings.get(str(path.parent/'manifest.json'))==snapshot['manifestSha256']:
                    found.append(entry['id'])
        if not found:raise ValueError('EXCLUSION_NOT_REGISTERED')
        matches[name]=sorted(set(found))
    return matches


def verify_public_origin(snapshot):
    """Recognize only exact public historical manifests audited by joint history."""
    from import_joint_history import MANIFESTS
    found=[name for name,digest in MANIFESTS.items() if digest==snapshot['manifestSha256']]
    if len(found)!=1:raise ValueError('EXCLUSION_PUBLIC_ORIGIN_UNVERIFIED')
    return found[0]


def canonical_registry_rows(parts, lexicon):
    """Project native IDs to all dictionary lemmas without changing corpus rows."""
    result=[]; split_lemmas={}; split_contexts={}; split_segments={}; cache={}
    for part,rows in parts.items():
        if part not in ('train','calibration','holdout') or not rows:
            raise ValueError('JOINT_CANONICAL_SPLIT')
        split_lemmas[part]=set();split_contexts[part]=set();split_segments[part]=set()
        for row in rows:
            word=row.get('word')
            expected='@'+word if isinstance(word,str) and row.get('cohort')=='protected' else word
            if (not isinstance(word,str) or not word or row.get('split')!=part
                    or row.get('expectedSpelling')!=expected):
                raise ValueError('JOINT_CANONICAL_TARGET')
            if word not in cache:
                cache[word]=sorted({analysis.lemma for analysis in lexicon.analyses(word)})
            if not cache[word]:raise ValueError('JOINT_CANONICAL_UNRESOLVED')
            split_lemmas[part].update(cache[word])
            context=row.get('contextHash')
            if context is not None:split_contexts[part].add(context)
            segment=row.get('sourceSegmentHash')
            if segment is not None:
                if not isinstance(segment,str) or not re.fullmatch('[0-9a-f]{64}',segment):raise ValueError('JOINT_SOURCE_SEGMENT_SCHEMA')
                split_segments[part].add(segment)
            result.append(row|{'families':cache[word]})
    groups=list(split_lemmas.values())
    if any(left & right for index,left in enumerate(groups) for right in groups[index+1:]):
        raise ValueError('JOINT_CANONICAL_SPLIT_OVERLAP')
    groups=list(split_contexts.values())
    if any(left & right for index,left in enumerate(groups) for right in groups[index+1:]):
        raise ValueError('JOINT_SOURCE_CONTEXT_SPLIT_OVERLAP')
    groups=list(split_segments.values())
    if any(left & right for index,left in enumerate(groups) for right in groups[index+1:]):
        raise ValueError('JOINT_SOURCE_SEGMENT_SPLIT_OVERLAP')
    return result


def canonical_registry_parts(parts, lexicon):
    """Preserve the checked lemmas in the serialized rows consumed downstream."""
    projected={part:[] for part in parts}
    for row in canonical_registry_rows(parts,lexicon):
        projected[row['split']].append(row)
    return projected
