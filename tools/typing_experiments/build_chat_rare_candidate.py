#!/usr/bin/env python3
"""Build a disclosed rare-word candidate without modifying or qualifying the APK."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import chat_control_review
import pack_rare_word_lexicon as packer
from holdout_ledger import load_ledger

ROOT=Path(__file__).resolve().parents[2]
PROVENANCE=ROOT/'app/src/main/assets/smarttyping/lexicon/provenance/rare-word-manifest.json'
PACKAGED=ROOT/'app/src/main/assets/smarttyping/lexicon/ru.rare'
SOURCE_LOCK=ROOT/'tools/typing_experiments/public_sources/tatoeba-ru-cc0-20261024/tatoeba-source-lock.json'


def unpack(path):
    """Read the exact packed keys and ranks while checking block integrity."""
    blob=Path(path).read_bytes()
    if len(blob)<56 or blob[:8]!=packer.MAGIC or hashlib.sha256(blob[:-32]).digest()!=blob[-32:]:raise ValueError('RARE_CANDIDATE_PACKED')
    width,count,blocks,data_offset=struct.unpack_from('<IIII',blob,8)
    if width!=packer.BLOCK_SIZE or blocks!=(count+width-1)//width or data_offset!=24+4*(blocks+1) or data_offset>len(blob)-32:
        raise ValueError('RARE_CANDIDATE_PACKED')
    offsets=struct.unpack_from('<'+'I'*(blocks+1),blob,24)
    if offsets[0]!=0 or offsets[-1]!=len(blob)-32-data_offset or any(a>b for a,b in zip(offsets,offsets[1:])):
        raise ValueError('RARE_CANDIDATE_PACKED')
    result={};last=None
    for block in range(blocks):
        position=data_offset+offsets[block];end=data_offset+offsets[block+1];previous=b''
        for _ in range(min(width,count-block*width)):
            if position+6>end:raise ValueError('RARE_CANDIDATE_PACKED')
            prefix,size,rank=struct.unpack_from('<BBI',blob,position);position+=6
            if prefix>len(previous) or not size or position+size>end or not rank:raise ValueError('RARE_CANDIDATE_PACKED')
            previous=previous[:prefix]+blob[position:position+size];position+=size
            word=previous.decode('utf-8')
            if last is not None and word<=last:raise ValueError('RARE_CANDIDATE_PACKED')
            result[word]=rank;last=word
        if position!=end:raise ValueError('RARE_CANDIDATE_PACKED')
    if len(result)!=count or len(set(result.values()))!=count:raise ValueError('RARE_CANDIDATE_PACKED')
    return result


def merge(words,counts,selected):
    if words!=sorted(set(words)) or not words or not selected or selected!=sorted(set(selected)):
        raise ValueError('RARE_CANDIDATE_WORDS')
    if any(not re.fullmatch('[а-яё]{3,32}',word) for word in selected):raise ValueError('RARE_CANDIDATE_WORDS')
    if set(words)&set(selected):raise ValueError('RARE_CANDIDATE_ALREADY_PRESENT')
    lines=counts.splitlines()
    fields=[line.split('\t') for line in lines]
    if any(len(x)!=3 for x in fields) or len(fields)!=len(words) or {x[0] for x in fields}!=set(words):
        raise ValueError('RARE_CANDIDATE_COUNTS')
    if len({x[0] for x in fields})!=len(fields):raise ValueError('RARE_CANDIDATE_COUNTS')
    # Preserve all original ranks; appended zero counts encode editorial words,
    # not a claimed observed frequency.
    return sorted(words+selected),lines+[word+'\t0\t0' for word in selected]


def build(review_path,chat_rows_path,chat_manifest_path,ledger_path,output):
    review_path,chat_rows_path,chat_manifest_path,ledger_path,output=map(Path,(review_path,chat_rows_path,chat_manifest_path,ledger_path,output))
    output=output.resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('RARE_CANDIDATE_OUTPUT')
    provenance=json.loads(PROVENANCE.read_text());lock=json.loads(SOURCE_LOCK.read_text())
    inputs=[PROVENANCE,PACKAGED,SOURCE_LOCK,review_path,chat_rows_path,chat_manifest_path,ledger_path,Path(__file__),Path(packer.__file__),
        ROOT/'tools/typing_experiments/chat_corpus.py',ROOT/'tools/typing_experiments/chat_control_review.py',ROOT/'tools/typing_experiments/holdout_ledger.py']
    bindings={str(p.resolve()):packer.sha256(p) for p in inputs}
    if packer.sha256(PACKAGED)!=provenance['sha256'] or PACKAGED.stat().st_size!=provenance['bytes']:
        raise ValueError('RARE_CANDIDATE_BASE_IDENTITY')
    chat_manifest=json.loads(chat_manifest_path.read_text());review=json.loads(review_path.read_text());ledger=load_ledger(ledger_path)
    if (chat_manifest.get('purpose')!='DISCLOSED_REGRESSION_NOT_QUALIFICATION' or chat_manifest.get('license')!='CC0-1.0'
            or chat_manifest.get('sourceSha256')!=lock['compressedSha256'] or chat_manifest.get('sourceLockSha256')!=packer.sha256(SOURCE_LOCK)
            or chat_manifest.get('rowsSha256')!=packer.sha256(chat_rows_path) or chat_manifest.get('ledgerSha256')!=packer.sha256(ledger_path)
            or chat_manifest.get('generatorSha256')!=packer.sha256(ROOT/'tools/typing_experiments/chat_corpus.py')
            or review.get('purpose')!='POSTHOC_DISCLOSED_REGRESSION_NOT_QUALIFICATION'):
        raise ValueError('RARE_CANDIDATE_SOURCE_IDENTITY')
    rows=[json.loads(line) for line in chat_rows_path.read_text().splitlines()];chat_control_review.verify_exclusions(rows,review,ledger)
    indexed={row['id']:row for row in rows};cases=[item for item in review['cases'] if item.get('label')=='preserve']
    if len(cases)!=8 or len({item['id'] for item in cases})!=8:raise ValueError('RARE_CANDIDATE_REVIEW')
    for item in cases:
        row=indexed.get(item['id'])
        if not row or row.get('typed')!=item.get('typed') or row.get('cohort')!='correct' or row.get('noAuto') is not True:
            raise ValueError('RARE_CANDIDATE_REVIEW')
    selected=sorted({item['typed'] for item in cases})
    if len(selected)!=7:raise ValueError('RARE_CANDIDATE_REVIEW')
    original=unpack(PACKAGED);original_words=sorted(original)
    if len(original)!=provenance['words'] or set(original.values())!=set(range(1,len(original)+1)):
        raise ValueError('RARE_CANDIDATE_BASE_RANKS')
    # Only rank order is recoverable from the asset; zero counts explicitly do
    # not represent or reconstruct the original occurrence statistics.
    ranked=sorted(original,key=original.get)
    original_counts=''.join(word+'\t0\t0\n' for word in ranked)
    words,counts=merge(original_words,original_counts,selected)
    output.mkdir(parents=True,mode=0o700)
    def write_source(directory,source_words,source_counts):
        directory.mkdir();words_path=directory/'words.txt';counts_path=directory/'counts.tsv'
        words_path.write_text(''.join(word+'\n' for word in source_words));counts_path.write_text(''.join(line+'\n' for line in source_counts))
        manifest=dict(schemaVersion=1,containsPrivateText=False,source='rank-only reconstruction from public packaged asset; counts are placeholders',
            originalAssetSha256=provenance['sha256'],reviewSha256=packer.sha256(review_path),
            files={'words.txt':packer.sha256(words_path),'counts.tsv':packer.sha256(counts_path)})
        (directory/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    base=output/'base-source';write_source(base,original_words,original_counts.splitlines())
    repacked=output/'repacked-original.rare';packer.pack(base,repacked,output/'original-pack-receipt.json')
    if repacked.read_bytes()!=PACKAGED.read_bytes():raise ValueError('RARE_CANDIDATE_BASE_REPRODUCTION')
    source=output/'source';write_source(source,words,counts)
    packed=output/'candidate.rare';candidate=packer.pack(source,packed,output/'candidate-pack-receipt.json')
    updated=unpack(packed)
    if (any(updated.get(word)!=rank for word,rank in original.items()) or set(updated)-set(original)!=set(selected)
            or any(updated[word]!=len(original)+i for i,word in enumerate(selected,1))):
        raise ValueError('RARE_CANDIDATE_RANK_DRIFT')
    if any(packer.sha256(Path(path))!=digest for path,digest in bindings.items()):raise ValueError('RARE_CANDIDATE_INPUT_DRIFT')
    receipt=dict(purpose='POSTHOC_PACKED_CANDIDATE_NOT_QUALIFICATION',independentQualification=False,
        previousWords=len(original_words),addedWords=len(selected),previousRanksPreserved=True,
        sourceControls=len(cases),sourceArticlesAlreadyExcluded=True,candidate=candidate,
        baselineSha256=provenance['sha256'],reviewSha256=packer.sha256(review_path),
        candidateSha256=packer.sha256(packed),builderSha256=packer.sha256(Path(__file__)),appAssetChanged=False,
        caveat='Rank-only reconstruction uses placeholder counts; app fingerprints bind the old rare-word SHA and cannot transfer qualification.')
    (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('review','chat-rows','chat-manifest','ledger','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();receipt=build(args.review,args.chat_rows,args.chat_manifest,args.ledger,args.output)
    print(json.dumps({k:receipt[k] for k in ('previousWords','addedWords','previousRanksPreserved','candidateSha256','independentQualification')}))

if __name__=='__main__':main()
