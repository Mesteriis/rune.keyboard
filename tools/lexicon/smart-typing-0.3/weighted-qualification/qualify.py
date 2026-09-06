#!/usr/bin/env python3
"""Explicit offline qualification stages; historical evidence never becomes a fresh run."""
from __future__ import annotations
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from archive import Failure, ORIGINAL_MANIFEST_SHA, digest, load, read_json, require, sha, validate_numeric

PACKAGE = Path(__file__).resolve().parent
FROZEN_SHA = 'ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48'
LOCK_SHA = '28750e183ef99ea33da58b20036e2f0dcb3f7e1f76e8528c21074ac7d6615b70'

class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Failure('ARGUMENTS')

def json_file(path: Path) -> dict | list:
    return read_json(path.read_bytes())

def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def child(command: list, seconds: int, output=None) -> bytes:
    result = subprocess.run([str(x) for x in command], stdout=output if output else subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=seconds)
    require(result.returncode == 0, 'CHILD_EXIT')
    require(not result.stderr, 'CHILD_STDERR')
    return result.stdout or b''

def safe_relative(value: str) -> Path:
    path = Path(value)
    require(not path.is_absolute() and bool(path.parts) and all(p not in ('..','.') for p in path.parts), 'RELATIVE_PATH_REQUIRED')
    return path

def repository(value: str) -> Path:
    root = Path(value).resolve(strict=True)
    require((root / 'app/src/main/java').is_dir() and (root / 'tools/lexicon/smart-typing-0.3').is_dir(), 'REPOSITORY_ROOT')
    return root

def input_dir(root: Path, value: str) -> Path:
    relative = safe_relative(value)
    path = (root / relative).resolve(strict=True)
    require(path.is_relative_to(root) and path.is_dir(), 'INPUT_DIRECTORY')
    return path

def build_path(root: Path, value: str) -> Path:
    relative = safe_relative(value)
    require(len(relative.parts) >= 3 and relative.parts[0] == 'build', 'IGNORED_BUILD_REQUIRED')
    result = root
    for part in relative.parts:
        result = result / part
        require(not result.is_symlink(), 'WRITE_SYMLINK')
    if result.exists():
        require(result.is_dir(), 'BUILD_DIRECTORY')
        for current, dirs, files in os.walk(result, followlinks=False):
            require(all(not (Path(current) / name).is_symlink() for name in dirs + files), 'WRITE_SYMLINK')
    return result

def checked(path: Path, item: dict) -> None:
    require(path.is_file() and path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'INPUT_IDENTITY')

def package_check() -> dict[str, bytes]:
    require(sys.flags.optimize == 0, 'PYTHON_OPTIMIZATION_UNSUPPORTED')
    require(sha(PACKAGE / 'manifests/frozen-output-manifest.json') == FROZEN_SHA, 'SOURCE_MANIFEST_IDENTITY')
    require(sha(PACKAGE / 'manifests/source-lock.json') == LOCK_SHA, 'SOURCE_LOCK_IDENTITY')
    manifest = json_file(PACKAGE / 'package-manifest.json')
    for item in manifest['files']:
        checked(PACKAGE / safe_relative(item['path']), item)
    for item in json_file(PACKAGE / 'manifests/frozen-output-manifest.json')['notices']:
        checked(PACKAGE / safe_relative(item['path']), item)
    records = load(PACKAGE)
    for name in ('reference.py', 'QualificationMain.kt', 'unit_oracle.cpp'):
        require((PACKAGE / 'source' / name).read_bytes() == records['src/' + name], 'UNCHANGED_REFERENCE_IDENTITY')
    require((PACKAGE/'manifests/historical-sources.json').read_bytes() == records['reports/compiled-sources.json'], 'HISTORICAL_SOURCE_LOCK')
    return records

def external_inputs(root: Path, source_value: str, index_value: str, rank_value: str) -> tuple[dict, list[Path]]:
    source = input_dir(root, source_value)
    index = input_dir(root, index_value)
    ranks = input_dir(root, rank_value)
    frozen = json_file(PACKAGE / 'manifests/frozen-output-manifest.json')
    identities = []
    for item in [x['canonical_keys'] for x in frozen['languages']] + [x['data'] for x in frozen['frequency']]:
        path = source / safe_relative(item['path'])
        checked(path, item)
        identities.append({'path': path.relative_to(root).as_posix(), 'bytes': item['bytes'], 'sha256': item['sha256']})
    for language in json_file(PACKAGE / 'manifests/packed-asset-manifest.json'):
        for kind, directory in [('trie', index), ('lengths', index), ('ranks', ranks)]:
            item = language[kind]
            path = directory / Path(item['path']).name
            checked(path, item)
            identities.append({'path': path.relative_to(root).as_posix(), 'bytes': item['bytes'], 'sha256': item['sha256']})
    return {'source_build_dir': safe_relative(source_value).as_posix(), 'index_dir': safe_relative(index_value).as_posix(),
            'rank_dir': safe_relative(rank_value).as_posix(), 'files': identities}, [source,index,ranks]

def original_source_lock(root: Path) -> dict[str, str]:
    historical = json_file(PACKAGE / 'manifests/historical-sources.json')
    result = {}
    for name, expected in historical.items():
        if name.startswith('app/'):
            path = root / name
            require(path.is_file() and sha(path) == expected, 'PRODUCTION_SOURCE_DRIFT')
            result[name] = expected
    require(len(result) == 13, 'PRODUCTION_SOURCE_SET')
    result['qualification/QualificationMain.kt'] = sha(PACKAGE / 'source/QualificationMain.kt')
    return result

def prepare(args, records: dict[str, bytes], root: Path) -> None:
    home = build_path(root, args.build_dir)
    require(not home.exists(), 'CHOOSE_FRESH_BUILD_DIRECTORY')
    inputs, directories = external_inputs(root, args.source_build_dir, args.index_dir, args.rank_dir)
    require(all(home != p and home not in p.parents and p not in home.parents for p in directories), 'INPUT_OUTPUT_OVERLAP')
    sources = original_source_lock(root)
    # Verify every prerequisite before creating a single output file.
    home.mkdir(parents=True)
    (home / '.gitignore').write_text('*\n')
    for name in ('fixtures','oracle','reports','bin'):
        (home / name).mkdir()
    for name, content in records.items():
        if name.startswith(('fixtures/', 'oracle/')):
            (home / name).write_bytes(content)
    write_json(home/'qualification-owner.json', {'schema':1, 'historical_manifest':ORIGINAL_MANIFEST_SHA,
        'inputs':inputs, 'production_sources':sources, 'prepared_expected_sha256':digest(records['fixtures/expected.json']),
        'historical_run_imported':False})

def selected(args, records: dict[str, bytes], root: Path) -> tuple[Path, dict]:
    home = build_path(root, args.build_dir)
    owner = json_file(home / 'qualification-owner.json')
    require(owner['schema'] == 1 and owner['historical_manifest'] == ORIGINAL_MANIFEST_SHA and
            owner['historical_run_imported'] is False, 'BUILD_OWNER')
    require(owner['production_sources'] == original_source_lock(root), 'PRODUCTION_SOURCE_DRIFT')
    for name, content in records.items():
        if name.startswith(('fixtures/', 'oracle/')) and name != 'oracle/provenance.json':
            require((home / name).read_bytes() == content, 'PREPARED_FIXTURE_DRIFT')
    provenance = json_file(home / 'oracle/provenance.json')
    require(provenance['expected_sha256'] == digest(records['fixtures/expected.json']) and
            provenance['inputs_tsv_sha256'] == digest(records['fixtures/inputs.tsv']) and
            provenance['candidates_tsv_sha256'] == digest(records['fixtures/candidates.tsv']) and
            provenance['reference_source_sha256'] == sha(PACKAGE/'source/reference.py'), 'EXPECTED_PROVENANCE')
    for item in owner['inputs']['files']:
        checked(root / safe_relative(item['path']), item)
    return home, owner

def toolchain(args) -> tuple[Path, list[Path]]:
    java = shutil.which(args.java)
    require(java is not None, 'JAVA_REQUIRED')
    # java -version writes its bounded version text on stderr; never publish its path/content.
    version = subprocess.run([java, '-version'], capture_output=True, timeout=15)
    require(version.returncode == 0 and b'version "17.' in version.stderr, 'JAVA_17_REQUIRED')
    cache = Path(args.gradle_cache).resolve(strict=True)
    jars = []
    for item in json_file(PACKAGE/'manifests/reproduction-toolchain.json')['jars']:
        found = list((cache/item['group']/item['artifact']/item['version']).glob('*/*.jar'))
        require(len(found) == 1, 'CACHED_TOOLCHAIN_REQUIRED')
        checked(found[0], item)
        jars.append(found[0])
    return Path(java), jars

def compile_stage(args, records: dict[str, bytes], root: Path) -> None:
    home, owner = selected(args, records, root)
    require(not (home/'reports/compiled.json').exists() and not (home/'bin/qualification.jar').exists(), 'COMPILE_ALREADY_EXISTS')
    java, jars = toolchain(args)
    source_paths = [root/p for p in owner['production_sources'] if p.startswith('app/')]
    source_paths.append(PACKAGE/'source/QualificationMain.kt')
    output = home/'bin/qualification.jar'
    command = [java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,jars)),
        'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','17',
        '-classpath',os.pathsep.join(map(str,jars[1:3])),'-d',output,*source_paths]
    captured = child(command,120)
    require(not captured, 'COMPILER_STDOUT')
    require(original_source_lock(root) == owner['production_sources'], 'PRODUCTION_SOURCE_DRIFT')
    write_json(home/'reports/compiled.json', {'schema':1,'sources':owner['production_sources'], 'jar_sha256':sha(output),
        'compiler_sha256':sha(jars[0]),'jars':[sha(p) for p in jars], 'fresh_compilation':True})

def run_stage(args, records: dict[str, bytes], root: Path) -> None:
    home, owner = selected(args, records, root)
    compiled = json_file(home/'reports/compiled.json')
    java,jars = toolchain(args)
    require(compiled['fresh_compilation'] is True and compiled['sources'] == owner['production_sources'] and
            compiled['jars'] == [sha(p) for p in jars] and compiled['jar_sha256'] == sha(home/'bin/qualification.jar'), 'COMPILED_IDENTITY')
    target = home/'reports/actual.tsv'
    require(not target.exists() and not (home/'reports/run.json').exists(), 'RUN_ALREADY_EXISTS')
    command = [java,'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,[home/'bin/qualification.jar',*jars[1:3]])),
        'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.QualificationMain',home/'fixtures',
        input_dir(root,owner['inputs']['index_dir']),input_dir(root,owner['inputs']['rank_dir'])]
    with target.open('xb') as stream:
        child(command,300,stream)
    validate_numeric(target.read_bytes(),read_json(records['fixtures/inputs.json']))
    require(original_source_lock(root) == owner['production_sources'], 'PRODUCTION_SOURCE_DRIFT')
    write_json(home/'reports/run.json', {'schema':1,'fresh_execution':True,'actual_sha256':sha(target),
        'expected_sha256':digest(records['fixtures/expected.json']),'jar_sha256':compiled['jar_sha256'],
        'historical_actual_sha256':digest(records['reports/actual.tsv']), 'host_timing_is_not_a_measurement':True,
        'comparison_passed':False})

def source_module(name: str):
    sys.path.insert(0,str(PACKAGE/'source'))
    try:
        spec = importlib.util.spec_from_file_location('qualification_'+name, PACKAGE/'source'/f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)

def compare_stage(args, records: dict[str, bytes], root: Path) -> None:
    home, owner = selected(args,records,root)
    identity = json_file(home/'reports/run.json')
    require(identity['fresh_execution'] is True and identity['actual_sha256'] == sha(home/'reports/actual.tsv'), 'FRESH_RUN_IDENTITY')
    require(not (home/'reports/summary.json').exists() and not (home/'reports/comparison.log').exists(), 'COMPARISON_ALREADY_EXISTS')
    validate_numeric((home/'reports/actual.tsv').read_bytes(),read_json(records['fixtures/inputs.json']))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = source_module('analyze').main(home)
    (home/'reports/comparison.log').write_text(output.getvalue())
    require(code == 0 and json_file(home/'reports/summary.json')['validation_pass'] is True, 'SEMANTIC_COMPARISON_FAILED')
    identity['comparison_passed'] = True
    write_json(home/'reports/run.json',identity)

def derive_stage(args, records: dict[str, bytes], root: Path) -> None:
    home, owner = selected(args,records,root)
    require(not (home/'reports/run.json').exists() and not (home/'reports/derivation.json').exists(), 'DERIVATION_STAGE_ORDER')
    compiler = None
    if args.rescan_missing:
        require(args.cxx is not None, 'EXPLICIT_CXX_REQUIRED')
        compiler = shutil.which(args.cxx)
        require(compiler is not None, 'CXX_REQUIRED')
    elif args.cxx is not None:
        raise Failure('CXX_REQUIRES_RESCAN')
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        source_module('derive_oracle').derive(home,input_dir(root,owner['inputs']['source_build_dir'])/'outputs',
            PACKAGE/'manifests/frozen-output-manifest.json',PACKAGE/'source/unit_oracle.cpp',compiler)
    # Exact identities, not merely self-consistent regenerated metadata.
    for name, content in records.items():
        if name.startswith(('fixtures/','oracle/')) and name != 'oracle/provenance.json':
            require((home/name).read_bytes() == content, 'ORACLE_REPRODUCTION_MISMATCH')
    write_json(home/'reports/derivation.json', {'schema':1,'source_derived_expected_match':True,
        'rescan_missing':args.rescan_missing,'saved_missing_neighborhoods_used':not args.rescan_missing,
        'expected_sha256':digest(records['fixtures/expected.json']),'production_executed':False})

def export_history(args, records: dict[str,bytes], root: Path) -> None:
    home = build_path(root,args.build_dir)
    require(not home.exists(),'CHOOSE_FRESH_BUILD_DIRECTORY')
    home.mkdir(parents=True)
    (home/'.gitignore').write_text('*\n')
    for name, content in records.items():
        path = home/safe_relative(name)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(content)
    (home/'evidence-manifest.json').write_bytes((PACKAGE/'evidence/original-manifest.json').read_bytes())
    write_json(home/'HISTORICAL_ONLY.json', {'schema':1,'fresh_execution':False,'binaries_omitted':True})

def parser() -> Parser:
    p = Parser(description=__doc__)
    p.add_argument('--repo-root',default='.')
    commands = p.add_subparsers(dest='stage',required=True)
    commands.add_parser('verify-history')
    for name in ('prepare','compile','run','compare','derive-oracle','export-history'):
        sub = commands.add_parser(name)
        sub.add_argument('--build-dir',required=True)
        if name == 'prepare':
            for argument in ('source-build-dir','index-dir','rank-dir'):
                sub.add_argument('--'+argument,required=True)
        if name in ('compile','run'):
            sub.add_argument('--java',required=True)
            sub.add_argument('--gradle-cache',required=True)
        if name == 'derive-oracle':
            sub.add_argument('--rescan-missing',action='store_true')
            sub.add_argument('--cxx')
    return p

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    records = package_check()
    if args.stage == 'verify-history':
        rows = validate_numeric(records['reports/actual.tsv'],read_json(records['fixtures/inputs.json']))
        summary = read_json(records['reports/summary.json'])
        require(summary['validation_pass'] is True and summary['requests'] == 775 and not summary['violations'] and
                summary['actual_sha256'] == digest(records['reports/actual.tsv']) and
                summary['expected_sha256'] == digest(records['fixtures/expected.json']), 'HISTORICAL_SUMMARY')
        print('HISTORICAL_IDENTITY_PASS TEXTS 41 REQUESTS 775 FRESH_EXECUTION 0')
        return 0
    root = repository(args.repo_root)
    functions = {'prepare':prepare,'compile':compile_stage,'run':run_stage,'compare':compare_stage,
                 'derive-oracle':derive_stage,'export-history':export_history}
    functions[args.stage](args,records,root)
    print('STAGE_PASS',args.stage.upper().replace('-','_'))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        # Includes malformed JSON/base64/numeric records and child exception payloads.
        print('QUALIFICATION_FAILED',file=sys.stderr)
        raise SystemExit(2)
