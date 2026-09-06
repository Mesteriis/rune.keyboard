#!/usr/bin/env python3
"""Deterministic, dependency-free front-coded and packed-trie asset builder."""
import argparse,array,hashlib,json,pathlib,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'lexicon-prototype'
MAGIC_F=b'RFC1'; MAGIC_T=b'RTR1'
def build(lang):
    src=SOURCE/'outputs'/f'{lang}.words.txt'
    expected={entry['language']:entry['canonical_keys']['sha256'] for entry in json.loads((SOURCE/'output-manifest.json').read_text())['languages']}
    assert hashlib.sha256(src.read_bytes()).hexdigest()==expected[lang], 'Frozen source drift'
    words=src.read_text().splitlines()
    assert words==sorted(set(words))
    assert all(0<len(w)<=32 for w in words)
    # Blocks of 16 UTF-8 strings; prefix length counts bytes, decoding after reassembly.
    data=bytearray(); offsets=[]; prev=b''
    for i,w in enumerate(words):
        b=w.encode(); n=0
        if i%16==0: offsets.append(len(data)); prev=b''
        while n<min(len(b),len(prev)) and b[n]==prev[n]: n+=1
        data.extend(bytes([n,len(b)-n]));data.extend(b[n:]);prev=b
    front=ROOT/'assets'/f'{lang}.front'
    with front.open('wb') as f:
        f.write(struct.pack('<4sIII',MAGIC_F,len(words),16,len(offsets)))
        f.write(struct.pack('<%dI'%len(offsets),*offsets)); f.write(data)
    # Ordered sibling/first-child trie; four uint32 values per node, root at zero.
    label=array.array('I',[0]);child=array.array('I',[0]);sibling=array.array('I',[0]);term=array.array('I',[0]);last=array.array('I',[0])
    stack=[0];prev=''
    for wi,w in enumerate(words):
        common=0
        while common<min(len(w),len(prev)) and w[common]==prev[common]:common+=1
        del stack[common+1:]
        for cp in map(ord,w[common:]):
            p=stack[-1];n=len(label)
            label.append(cp);child.append(0);sibling.append(0);term.append(0);last.append(0)
            if last[p]:sibling[last[p]]=n
            else:child[p]=n
            last[p]=n;stack.append(n)
        term[stack[-1]]=wi+1;prev=w
    trie=ROOT/'assets'/f'{lang}.trie'
    with trie.open('wb') as f:
        f.write(struct.pack('<4sIII',MAGIC_T,len(words),len(label),16))
        for rec in zip(label,child,sibling,term):f.write(struct.pack('<IIII',*rec))
    # Frozen public, synthetic evaluation only: equally spaced canonical entries,
    # one deletion, one adjacent transposition; explicit Unicode/protected probes.
    probes=[]
    for numerator in (1,3,7):
        w=words[len(words)*numerator//11]
        probes.extend([w,w[:len(w)//2]+w[len(w)//2+1:]])
    w=words[len(words)//2]; j=max(0,len(w)//2-1)
    probes.append(w[:j]+w[j+1]+w[j]+w[j+2:])
    probes.extend({'en':['form','from','café'],'es':['esta','está','niño'],'ru':['все','всё','ёлка']}[lang])
    word_set=set(words)
    (ROOT/'reports'/f'{lang}.exact.tsv').write_text(''.join(q+'\t'+str(q in word_set).lower()+'\n' for q in dict.fromkeys(probes)))
    (ROOT/'reports'/f'{lang}.probes.txt').write_text('\n'.join(dict.fromkeys(probes))+'\n')
    return {'language':lang,'words':len(words),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'trie_nodes':len(label)}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('languages',nargs='*',default=['en','es','ru']);args=a.parse_args()
    out=[build(l) for l in args.languages]
    (ROOT/'reports'/'build-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))
