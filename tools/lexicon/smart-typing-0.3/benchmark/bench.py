#!/usr/bin/env python3
"""Portable orchestration around frozen, measured qualification sources.

Never invokes adb or Gradle, downloads dependencies, selects a production reader,
prints query text, or mutates an input pipeline/index cache. Single build writer.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
PROJECT = next(p for p in PACKAGE.parents if (p/'tools/lexicon/smart-typing-0.3/scripts/pipeline_config.py').is_file())
PIPELINE = PROJECT/'tools/lexicon/smart-typing-0.3'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('pipeline_config', PIPELINE/'scripts/pipeline_config.py')
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
FULL_HASH = '39c5b0836e67678d1711f33936ab08cd0c970e679e861b31185411dc3ac8d534'
EXACT_HASH = '88da5e175e0ea5f2c10e9ebf05b7a60c0a909cd8f43d03924c484aa82f953cd6'

class Failure(ValueError):
    """Only static validation codes may leave this process."""

def require(ok, code):
    if not ok:
        raise Failure(code)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def emit(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def checked(path, record):
    require(Path(path).stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'INPUT_IDENTITY')

def package_check():
    require(sha(PACKAGE/'manifests/full.json') == FULL_HASH, 'FULL_MANIFEST_IDENTITY')
    require(sha(PACKAGE/'manifests/exact.json') == EXACT_HASH, 'EXACT_MANIFEST_IDENTITY')
    for item in read_json(PACKAGE/'package-manifest.json')['files']:
        checked(config.safe_path(PACKAGE, item['path']), item)
    config.load_frozen_manifest()
    config.load_lock()

def child(command, *, env=None, seconds=1800):
    # Compiler/oracle diagnostics may include file paths or public probe text.
    # Capture them; the public result is a static code and never a raw exception.
    result = subprocess.run([str(x) for x in command], env=env, capture_output=True, timeout=seconds)
    require(result.returncode == 0, 'CHILD_EXIT')

def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(not destination.exists(), 'OUTPUT_EXISTS')
    shutil.copyfile(source, destination)

def selected(args, *, exists=True):
    root = config.build_root(args.build_dir)
    if exists:
        require((root/'benchmark-owner.json').is_file(), 'BUILD_NOT_PREPARED')
        owner = read_json(root/'benchmark-owner.json')
        require(owner == {'schema':1, 'full_manifest':FULL_HASH, 'exact_manifest':EXACT_HASH}, 'BUILD_OWNER')
        for kind in ('full','exact'):
            for p in (PACKAGE/'source/common').iterdir():
                require(sha(root/kind/'src'/p.name)==sha(p), 'STAGED_SOURCE_IDENTITY')
            for p in (PACKAGE/'source'/kind).iterdir():
                target = root/kind/('device' if p.name=='run.sh' else 'src')/p.name
                require(sha(target)==sha(p), 'STAGED_SOURCE_IDENTITY')
            require(sha(root/kind/'reports/frozen-manifest.json')==sha(PACKAGE/'manifests'/f'{kind}.json'), 'STAGED_MANIFEST_IDENTITY')
        for p in (PACKAGE/'source/builders').iterdir():
            require(sha(root/'lexicon-index-prototype/src'/p.name)==sha(p), 'STAGED_SOURCE_IDENTITY')
    return root

def prepare(args):
    root = selected(args, exists=False)
    require(not root.exists(), 'CHOOSE_NEW_BUILD_DIRECTORY')
    source = Path(args.source_build_dir).resolve()
    require(source != root and source not in root.parents and root not in source.parents, 'INPUT_OUTPUT_OVERLAP')
    frozen = config.load_frozen_manifest()
    # No source generation or holdout reads: use canonical outputs of the pinned pipeline.
    for rec in [x['canonical_keys'] for x in frozen['languages']] + [x['data'] for x in frozen['frequency']]:
        checked(config.safe_path(source, rec['path']), rec)
    root.mkdir(parents=True)
    (root/'.gitignore').write_text('*\n')
    emit(root/'benchmark-owner.json', {'schema':1, 'full_manifest':FULL_HASH, 'exact_manifest':EXACT_HASH})
    canonical = root/'lexicon-prototype'
    copy(PIPELINE/'frozen-output-manifest.json', canonical/'output-manifest.json')
    for rec in [x['canonical_keys'] for x in frozen['languages']] + [x['data'] for x in frozen['frequency']]:
        copy(config.safe_path(source, rec['path']), canonical/rec['path'])
    for flavor in ('full','exact'):
        home = root/flavor
        for name in ('src','bin','reports','packaging','device','fixtures'):
            (home/name).mkdir(parents=True)
        for p in sorted((PACKAGE/'source/common').iterdir()):
            copy(p, home/'src'/p.name)
        for p in sorted((PACKAGE/'source'/flavor).iterdir()):
            copy(p, home/('device' if p.name=='run.sh' else 'src')/p.name)
        copy(PACKAGE/'manifests'/f'{flavor}.json', home/'reports/frozen-manifest.json')
    for rec in read_json(PACKAGE/'manifests/full.json')['assets']:
        relative = rec['path']
        if relative.startswith('assets/'):
            continue
        if relative.startswith('queries/'):
            source_file = PACKAGE/'fixtures/full'/Path(relative).name
        elif relative.startswith('frequency/'):
            source_file = canonical/'outputs'/relative
        elif relative == 'notices/UPSTREAM-PROTOTYPE-NOTICES.md':
            source_file = PACKAGE/'fixtures/UPSTREAM-PROTOTYPE-NOTICES.md'
        elif relative == 'notices/source-lock.json':
            source_file = PIPELINE/'source-lock.json'
        elif relative == 'notices/output-manifest.json':
            source_file = PIPELINE/'frozen-output-manifest.json'
        else:
            source_file = PIPELINE/relative
        checked(source_file, rec)
        copy(source_file, root/'full/fixtures'/relative)
    for rec in read_json(PACKAGE/'manifests/exact.json')['groups']:
        copy(PACKAGE/'fixtures/exact'/f'{rec["language"]}.tsv', root/'exact/fixtures'/f'{rec["language"]}.tsv')
    validate_exact_controls(canonical/'outputs')
    index = root/'lexicon-index-prototype'
    for name in ('src','assets','reports','development/reports','bin','work'):
        (index/name).mkdir(parents=True)
    for p in (PACKAGE/'source/builders').iterdir():
        copy(p, index/'src'/p.name)

def validate_exact_controls(outputs):
    """Streaming independent dictionary membership, no reader under test involved."""
    for group in read_json(PACKAGE/'manifests/exact.json')['groups']:
        lang = group['language']
        rows = [line.split('\t') for line in (PACKAGE/'fixtures/exact'/f'{lang}.tsv').read_text().splitlines()]
        old = [line.split('\t') for line in (PACKAGE/'fixtures/full'/f'{lang}.development.tsv').read_text().splitlines()]
        require(len(rows)==277 and [r[3] for r in rows[:240]] == [r[1] for r in old], 'EXACT_QUERY_IDENTITY')
        require([q['original_id'] for q in group['queries'][:240]] == [r[0] for r in old], 'EXACT_ORIGINAL_IDS')
        wanted = {r[3] for r in rows}
        found = set()
        with (outputs/f'{lang}.words.txt').open(encoding='utf-8') as words:
            for line in words:
                word = line.rstrip('\n')
                if word in wanted:
                    found.add(word)
        require(all((r[3] in found)==(r[2]=='1') and (r[3]=='')==(r[2]=='2') for r in rows), 'EXACT_DICTIONARY_ORACLE')

def indices(args):
    root = selected(args)
    index = root/'lexicon-index-prototype'
    assets = [r for r in read_json(PACKAGE/'manifests/full.json')['assets'] if r['path'].startswith('assets/')]
    require(not any((root/'full/fixtures'/r['path']).exists() for r in assets), 'INDICES_ALREADY_STAGED')
    if args.index_cache:
        cache = Path(args.index_cache).resolve()
        require(cache != root and root not in cache.parents, 'CACHE_OUTPUT_OVERLAP')
        for r in assets:
            checked(cache/Path(r['path']).name, r)
        for r in assets:
            copy(cache/Path(r['path']).name, index/r['path'])
    else:
        require(sys.byteorder == 'little', 'LITTLE_ENDIAN_BUILDER_REQUIRED')
        child([sys.executable, index/'src/build.py'])
        child([args.cxx, '-O2', '-std=c++17', index/'src/delete_builder.cpp', '-o', index/'bin/delete_builder'])
        for lang in ('en','es','ru'):
            child([index/'bin/delete_builder', root/'lexicon-prototype/outputs'/f'{lang}.words.txt', index/'assets'/f'{lang}.delete', index/'work'/lang])
        child([sys.executable, index/'src/build_lengths.py'])
    for r in assets:
        checked(index/r['path'], r)
    (root/'full/fixtures/assets').mkdir()
    for r in assets:
        # Shared immutable bytes, only within the selected build directory.
        os.link(index/r['path'], root/'full/fixtures'/r['path'])

def toolchain(args):
    lock = read_json(PACKAGE/'manifests/toolchain.json')
    cache = Path(args.jar_cache)
    jars = []
    for rec in lock['jars']:
        matches = list((cache/rec['group']/rec['artifact']/rec['version']).glob('*/*.jar'))
        require(len(matches)==1, 'CACHED_JAR_COUNT')
        checked(matches[0], rec)
        jars.append(matches[0])
    sdk = Path(args.sdk)
    android = sdk/'platforms'/lock['android_platform']/'android.jar'
    d8 = sdk/'build-tools'/lock['build_tools']/'lib/d8.jar'
    require(sha(android)==lock['android_jar_sha256'] and sha(d8)==lock['d8_jar_sha256'], 'SDK_JAR_IDENTITY')
    java = Path(args.java_home)/'bin/java'
    version = subprocess.run([str(java), '-version'], capture_output=True, text=True, timeout=15)
    require(version.returncode==0 and 'version "17.' in version.stderr, 'JDK17_REQUIRED')
    return java, jars, android, d8

def compile_harness(args):
    root = selected(args)
    java, jars, android, d8 = toolchain(args)
    std, annotations = jars[1], jars[-1]
    for kind in ('full','exact'):
        home = root/kind
        require(not (home/'bin/benchmark-dex.jar').exists(), 'DEX_EXISTS')
        names = ['LexiconPrototype.kt', 'Benchmark.kt', 'Frozen.kt'] if kind=='full' else ['LexiconPrototype.kt','ExactBenchmark.kt','Frozen.kt','ExactFrozen.kt']
        for target in ('Android','Host'):
            cp = os.pathsep.join(str(p) for p in ([std, android] if target=='Android' else [std]))
            child([java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,jars)), 'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-classpath',cp,'-jvm-target','1.8','-d',home/'bin'/f'benchmark-{target.lower()}.jar',*[home/'src'/n for n in names],home/'src'/f'Platform{target}.kt'], seconds=300)
        dex = home/'bin/benchmark-dex.jar'
        child([java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',d8,'com.android.tools.r8.D8','--min-api','26','--lib',android,'--output',dex,home/'bin/benchmark-android.jar',std,annotations], seconds=300)
        emit(home/'reports/build-identity.json', {'schema':1,'kind':kind,'dex_sha256':sha(dex),'toolchain_lock_sha256':sha(PACKAGE/'manifests/toolchain.json'),'source':{p.name:sha(p) for p in sorted((home/'src').glob('*.kt'))},'historical_identity_reassigned':False})

def package_apk(args):
    root = selected(args)
    sdk = Path(args.sdk)
    lock = read_json(PACKAGE/'manifests/toolchain.json')
    require(sha(sdk/'platforms'/lock['android_platform']/'android.jar')==lock['android_jar_sha256'], 'SDK_JAR_IDENTITY')
    hashes = {name:sha(sdk/'build-tools'/lock['build_tools']/name) for name in ('aapt2','zipalign')}
    require(not (root/'full/packaging/AndroidManifest.xml').exists(), 'PACKAGING_EXISTS')
    child([sys.executable,root/'full/src/package_assets.py'], env={**os.environ,'RUNE_BENCH_SDK':str(sdk)})
    emit(root/'full/reports/packaging-tools.json', {'binary_sha256':hashes,'matches_reference_binaries':all(hashes[n]==lock['packaging_tool_reference'][n]['sha256'] for n in hashes)})

def aggregate(args):
    from records import validate_full, validate_exact, qualified_full
    root = selected(args)
    home = root/args.kind
    directory = Path(args.records).resolve()
    require(root in directory.parents, 'RECORD_SCOPE')
    require(directory.is_dir(), 'RECORD_DIRECTORY')
    data = {p.name:p.read_text() for p in directory.glob('*.tsv')}
    require(not any(p.stat().st_size for p in directory.glob('*.stderr')), 'NONEMPTY_DEVICE_STDERR')
    dex = sha(home/'bin/benchmark-dex.jar')
    manifest = read_json(home/'reports/frozen-manifest.json')
    if args.kind=='full':
        validate_full(data, manifest, dex)
        target = home/'reports'/f'summary-{directory.name}.json'
        require(not target.exists(), 'SUMMARY_EXISTS')
        child([sys.executable,home/'src/aggregate.py',directory], seconds=120)
        emit(home/'reports'/f'qualified-{directory.name}.json', qualified_full(read_json(target)))
    else:
        validate_exact(data, manifest, dex)
        target = home/'reports'/f'summary-{directory.name}.json'
        require(not target.exists(), 'SUMMARY_EXISTS')
        child([sys.executable,home/'src/aggregate.py',directory,target], seconds=120)

def oracle(args):
    """Explicit expensive independent full scan, never part of smoke contracts."""
    root = selected(args)
    out = root/'oracle'
    require(not out.exists(), 'ORACLE_EXISTS')
    out.mkdir()
    child([args.cxx,'-O2','-std=c++17',PACKAGE/'source/builders/oracle.cpp','-o',out/'oracle'])
    child([args.cxx,'-O2','-std=c++17',PACKAGE/'source/full/rank_oracle.cpp','-o',out/'rank'])
    for lang in ('en','es','ru'):
        for profile in ('development','smoke'):
            fixture = [x.split('\t') for x in (PACKAGE/'fixtures/full'/f'{lang}.{profile}.tsv').read_text().splitlines()]
            probes = out/f'{lang}.{profile}.txt'
            probes.write_text(''.join(r[1]+'\n' for r in fixture), encoding='utf-8')
            reference = out/f'{lang}.{profile}.neighbors.tsv'
            words = root/'lexicon-prototype/outputs'/f'{lang}.words.txt'
            child([out/'oracle',words,probes,reference], seconds=3600)
            actual = [x.split('\t') for x in reference.read_text().splitlines()]
            require(len(actual)==len(fixture) and all(a==[b[1]]+([] if not b[5] else b[5].split(',')) for a,b in zip(actual,fixture)), 'FULL_ORACLE_MISMATCH')
            ranked = out/f'{lang}.{profile}.rank.tsv'
            child([out/'rank',lang,words,root/'lexicon-prototype/outputs/frequency'/f'{lang}.tsv',reference,ranked], seconds=3600)
            table = words.read_text().splitlines()
            ranks = [x.split('\t') for x in ranked.read_text().splitlines()]
            require(len(ranks)==len(fixture) and all(a[0]==b[1] and [table[int(i)-1] for i in a[2:]]==([] if not b[4] else b[4].split(',')) for a,b in zip(ranks,fixture)), 'RANK_ORACLE_MISMATCH')
    emit(out/'verification.json', {'status':'PASS','development_queries':720,'smoke_queries':26,'unit_contract_only':True})

class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Failure('ARGUMENTS')

def main():
    parser = Parser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    for name in ('check','prepare','indices','compile','package-apk','aggregate','oracle'):
        command = subs.add_parser(name)
        if name!='check':command.add_argument('--build-dir', required=True)
        if name=='prepare':command.add_argument('--source-build-dir', required=True)
        if name in ('indices','oracle'):command.add_argument('--cxx', default='clang++')
        if name=='indices':command.add_argument('--index-cache')
        if name in ('compile','package-apk'):command.add_argument('--sdk', required=True)
        if name=='compile':
            command.add_argument('--java-home', required=True)
            command.add_argument('--jar-cache', required=True)
        if name=='aggregate':
            command.add_argument('--kind', choices=('full','exact'), required=True)
            command.add_argument('--records', required=True)
    args = parser.parse_args()
    package_check()
    if args.command!='check':
        {'prepare':prepare,'indices':indices,'compile':compile_harness,'package-apk':package_apk,'aggregate':aggregate,'oracle':oracle}[args.command](args)
    print('PASS '+args.command)

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print('FAIL '+(str(error) if isinstance(error,Failure) else type(error).__name__))
        sys.exit(2)
