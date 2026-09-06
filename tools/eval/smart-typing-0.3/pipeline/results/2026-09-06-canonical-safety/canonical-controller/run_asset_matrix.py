#!/usr/bin/env python3
"""Additional public-fixture diagnostic; preserves completed controller evidence byte-for-byte."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess

OUT = Path(__file__).resolve().parent

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + '\n')

assert not (OUT / 'asset-matrix-receipt.json').exists()
controller_receipt = OUT / 'execution-receipt.json'
controller = json.loads(controller_receipt.read_text())
bound = dict(controller['inputHashes'])
bound[str(controller_receipt)] = sha(controller_receipt)
bound.update({str(OUT / name): digest for name, digest in controller['artifacts'].items()})
assert all(sha(Path(p)) == digest for p, digest in bound.items())
fixtures = ['clay', 'resistance', 'campo', 'puerto', 'arrecife', 'que', 'si', 'will', 'may', 'brown',
            'paris', 'london', 'москва', 'juan']
(OUT / 'asset-matrix-fixtures.txt').write_text('\n'.join(fixtures) + '\n')
commands = json.loads((OUT / 'commands.json').read_text())
compile_cmd = commands['compile'][:]
compile_cmd[compile_cmd.index('-d') + 1] = str(OUT / 'canonical-asset-matrix.jar')
assert compile_cmd[-1].endswith('CanonicalControllerDiagnostic.kt')
compile_cmd[-1] = str(OUT / 'CanonicalAssetMatrix.kt')
runtime_cmd = commands['execute'][:]
runtime_cmd[runtime_cmd.index('-cp') + 1] = runtime_cmd[runtime_cmd.index('-cp') + 1].replace(
    str(OUT / 'canonical-controller.jar'), str(OUT / 'canonical-asset-matrix.jar'))
runtime_cmd[-3] = 'io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CanonicalAssetMatrix'
runtime_cmd[-2] = str(OUT / 'asset-matrix-fixtures.txt')
write('asset-matrix-commands.json', {'compile': compile_cmd, 'execute': runtime_cmd})
with (OUT / 'asset-matrix-compile.log').open('wb') as log:
    subprocess.run(compile_cmd, stdout=log, stderr=log, timeout=180, check=True)
with (OUT / 'asset-matrix.tsv').open('wb') as data, (OUT / 'asset-matrix-run.log').open('wb') as log:
    subprocess.run(runtime_cmd, stdout=data, stderr=log, timeout=120, check=True)
rows = [{'token': token, 'routes': [], 'assetLookups': []} for token in fixtures]
for line in (OUT / 'asset-matrix.tsv').read_text().splitlines():
    f = line.split('\t'); index = int(f[1])
    assert base64.b64decode(f[2]).decode() == fixtures[index]
    if f[0] == 'R':
        assert len(f) == 7
        rows[index]['routes'].append(dict(activeLanguage=f[3], primary=f[4], fallback=f[5], protectedReason=f[6]))
    else:
        assert f[0] == 'M' and len(f) == 9 and f[8] == 'true'
        rows[index]['assetLookups'].append(dict(language=f[3], exactMembership=f[4],
            canonicalText=None if f[5] == 'NONE' else base64.b64decode(f[5]).decode(),
            canonicalUnambiguous=None if f[6] == 'NONE' else f[6] == 'true', inspectedStates=int(f[7])))
assert all(len(r['routes']) == 3 and len(r['assetLookups']) == 3 for r in rows)
write('asset-matrix.json', {'scope': 'actual-current-kotlin-route-and-exact-case-assets-public-fixtures',
    'rows': rows, 'changedPolicyExecuted': False, 'modelCalls': 0, 'modelCacheReads': 0})
assert all(sha(Path(p)) == digest for p, digest in bound.items())
names = ['CanonicalAssetMatrix.kt', 'run_asset_matrix.py', 'asset-matrix-fixtures.txt',
    'asset-matrix-commands.json', 'asset-matrix-compile.log', 'asset-matrix-run.log',
    'canonical-asset-matrix.jar', 'asset-matrix.tsv', 'asset-matrix.json']
write('asset-matrix-receipt.json', {'schemaVersion': 1, 'complete': True, 'publicFixtures': len(fixtures),
    'routeObservations': 42, 'assetObservations': 42, 'originalControllerEvidenceUnchanged': True,
    'originalReceiptSha256': sha(controller_receipt), 'sourceAssetToolchainInputBinding': controller['inputHashes'],
    'artifacts': {name: sha(OUT / name) for name in names}})
for r in rows:
    print(r['token'], [(a['language'], a['exactMembership'], a['canonicalText'], a['canonicalUnambiguous']) for a in r['assetLookups']])
