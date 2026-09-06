"""Strict content-free record gate in front of the unchanged measured reducers."""
import copy
import base64
import hashlib
import io
import gzip
import importlib.util
import json
from collections import Counter
from pathlib import Path
from bench import PACKAGE, EXACT_HASH, Failure, require, read_json, sha

ROW_HEADER = 'language format profile phase id repeat search_ns topn_ns cpu_ns allocated_bytes gc_count states verified rows reason expected returned top7_equal prohibits_autoreplace'.split()
MEM_HEADER = 'stage heap_used heap_committed native_allocated pss private_dirty rss peak_rss'.split()

def singleton(lines, name):
    found = [p for p in lines if p[0]==name]
    require(len(found)==1, 'RECORD_SINGLETON')
    return found[0]

def validate_full(files, manifest, dex):
    require(files.get('verify.tsv') == f'DEX\t{dex}\nVERIFY\tPASS\t{len(manifest["assets"])}\n', 'FULL_PREFLIGHT')
    groups = Counter()
    profiles = set()
    for name, raw in files.items():
        if name=='verify.tsv':continue
        lines = [line.split('\t') for line in raw.splitlines()]
        require(all(p[0] in {'META','MEM_HEADER','MEM','FIXTURE','LOAD','ROW_HEADER','ROW','DONE'} for p in lines), 'FULL_RECORD_KIND')
        meta = singleton(lines, 'META')
        require(len(meta)==9 and meta[2] in ('en','es','ru') and meta[3] in ('front','trie','delete') and meta[4] in ('development','smoke') and meta[5] in ('full','cold'), 'FULL_META')
        api,lang,fmt,profile,mode = int(meta[1]),*meta[2:6]
        file_repeats = range(3) if mode=='cold' else range(1)
        require(name in {f'{lang}.{fmt}.{profile}.{mode}.{rep}.tsv' for rep in file_repeats}, 'FULL_RECORD_FILENAME')
        require(meta[6:8]==['3','1'] and 30<=int(meta[8])<=1800, 'FULL_REPETITIONS')
        profiles.add((api,profile,mode))
        groups[lang,fmt] += 1
        fixture = next(q for q in manifest['queries'] if q['language']==lang and q['profile']==profile)
        expected = {q['id']:q for q in fixture['queries']}
        require(singleton(lines,'FIXTURE')==['FIXTURE',fixture['sha256']], 'FULL_FIXTURE')
        require(singleton(lines,'ROW_HEADER')==['ROW_HEADER']+ROW_HEADER, 'FULL_ROW_HEADER')
        require(singleton(lines,'MEM_HEADER')==['MEM_HEADER']+MEM_HEADER, 'FULL_MEM_HEADER')
        loads = [p for p in lines if p[0]=='LOAD']
        require(len(loads)==2 and {p[1] for p in loads}=={'frequency','index'} and all(len(p)==3 and int(p[2])>=0 for p in loads), 'FULL_LOADS')
        memory = [p for p in lines if p[0]=='MEM']
        stages = {'boot','fixtures_loaded','frequency_loaded','index_opened','first_query'}
        if mode=='full':stages |= {'warmup_complete','measure_complete','post_gc_requested'}
        require(len(memory)==len(stages) and {p[1] for p in memory}==stages, 'FULL_MEMORY_STAGES')
        require(all(len(p)==9 and all(int(v)>=-1 for v in p[2:]) for p in memory), 'FULL_MEMORY')
        seen = set()
        complete = 0
        for fields in lines:
            if fields[0]!='ROW':continue
            require(len(fields)==len(ROW_HEADER)+1, 'FULL_ROW_COLUMNS')
            r = dict(zip(ROW_HEADER, fields[1:]))
            require([r['language'],r['format'],r['profile']]==[lang,fmt,profile] and r['id'] in expected, 'FULL_ROW_ID')
            key = r['phase'],r['id'],int(r['repeat'])
            require(key not in seen, 'FULL_DUPLICATE_ROW')
            seen.add(key)
            for field in ('search_ns','topn_ns','states','verified','rows','expected','returned'):
                require(int(r[field])>=0, 'FULL_NEGATIVE_METRIC')
            require(int(r['topn_ns'])>=int(r['search_ns']) and int(r['cpu_ns'])>=-1 and int(r['gc_count'])>=-1, 'FULL_TIME_METRIC')
            int(r['allocated_bytes']) # All Android allocation deltas, including positive ones, are unsupported.
            require(r['reason'] in ('NONE','STATES','VERIFIED') and r['top7_equal'] in ('true','false') and r['prohibits_autoreplace'] in ('true','false'), 'FULL_RESULT_ENUM')
            require(int(r['expected'])==expected[r['id']]['expected_candidates'] and int(r['returned'])<=int(r['expected']), 'FULL_EXPECTED_COUNT')
            if r['phase']=='bounded':
                require(int(r['states'])<=8192 and int(r['verified'])<=64 and (r['reason']!='NONE')==(r['prohibits_autoreplace']=='true'), 'FULL_CAP_CONTRACT')
                complete += r['reason']=='NONE'
            else:
                require(r['reason']=='NONE' and r['prohibits_autoreplace']=='false', 'FULL_REFERENCE_COMPLETE')
            if r['reason']=='NONE':
                require(r['top7_equal']=='true' and r['returned']==r['expected'], 'FULL_ORACLE_RESULT')
        want = {('cold_first',fixture['queries'][0]['id'],0)}
        if mode=='full':
            want |= {('warmup',qid,0) for qid in expected}
            want |= {(phase,qid,rep) for phase in ('reference','bounded') for qid in expected for rep in range(3)}
        require(seen==want, 'FULL_MISSING_OR_EXTRA_ROWS')
        require(singleton(lines,'DONE')==['DONE','PASS',str(len(expected)),str(len(expected)*3 if mode=='full' else 0),str(complete)], 'FULL_DONE')
    require(len(profiles)==1, 'FULL_MIXED_PROFILE')
    api,profile,mode = next(iter(profiles))
    count = 3 if mode=='cold' else 1
    require(groups==Counter({(l,f):count for l in ('en','es','ru') for f in ('front','trie','delete')}), 'FULL_MISSING_OR_EXTRA_PROCESSES')
    return {'api':api,'profile':profile,'mode':mode,'processes':sum(groups.values())}

def exact_module():
    spec = importlib.util.spec_from_file_location('frozen_exact_aggregate',PACKAGE/'source/exact/aggregate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_exact(files, manifest, dex):
    require(files.get('verify.tsv')==f'DEX\t{dex}\nMANIFEST\t{EXACT_HASH}\nVERIFY\tPASS\t{len(manifest["base_assets"])}\t3\n', 'EXACT_PREFLIGHT')
    require(set(files)=={'verify.tsv'}|{f'{l}.{f}.tsv' for l in ('en','es','ru') for f in ('front','trie','delete')}, 'EXACT_PROCESS_SET')
    module = exact_module()
    parsed = {}
    for group in manifest['groups']:
        for fmt in ('front','trie','delete'):
            parsed[group['language'],fmt] = module.parse(files[f'{group["language"]}.{fmt}.tsv'],group,fmt,EXACT_HASH)
    return parsed

def qualified_full(raw):
    qualified = copy.deepcopy(raw)
    for group in qualified['comparisons']:
        if group['api']>=0:
            for record in group['formats'].values():
                if 'reference_allocated_bytes' in record:
                    record['reference_allocated_bytes'] = None
    qualified['android_allocation_evidence'] = 'UNSUPPORTED: API26 ART bytes-allocated is not a monotonic interval counter. All original deltas/distributions, positive or negative, are excluded.'
    qualified['energy_evidence'] = 'NOT_MEASURED'
    return qualified

def historical_records():
    manifest = read_json(PACKAGE/'evidence/records-manifest.json')
    archive = base64.b64decode(b''.join((PACKAGE/'evidence/records.json.gz.b64').read_bytes().splitlines()), validate=True)
    require(hashlib.sha256(archive).hexdigest()==manifest['sha256'], 'ARCHIVE_IDENTITY')
    with gzip.GzipFile(fileobj=io.BytesIO(archive),mode='rb') as stream:
        raw = stream.read(manifest['uncompressed_bytes']+1)
    require(len(raw)==manifest['uncompressed_bytes'], 'ARCHIVE_LENGTH')
    records = json.loads(raw)
    require(set(records)=={r['path'] for r in manifest['records']}, 'ARCHIVE_RECORD_SET')
    for item in manifest['records']:
        data = records[item['path']].encode('utf-8')
        require(len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'], 'ARCHIVE_RECORD_IDENTITY')
    return records

def cohort(records, prefix):
    return {Path(name).name:text for name,text in records.items() if name.startswith(prefix+'/')}
