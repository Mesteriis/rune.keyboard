#!/usr/bin/env python3
"""Fail-closed source dependency gate. No source execution or build-time network."""
import argparse
import re
from pathlib import Path

BASE = 'io.github.mesteriis.rune.keyboard.'
RUNTIME = 'io.github.mesteriis.rune.runtime.llama.'
AREAS = ('ime', 'intelligence.client', 'intelligence.ipc', 'intelligence.storage', 'intelligence.inference', 'intelligence.readiness')
PURE_MODEL = {'ModelTypes.kt', 'ModelManifestParser.kt'}
PURE_CLIENT = {'ModelScoringClient.kt', 'ModelDemand.kt', 'ModelReadinessSource.kt'}
FACTORY = 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/android/AndroidModelCandidates.kt'
IME_INTELLIGENCE = {
    'intelligence.client': PURE_CLIENT | {'BoundModelScoringClient.kt', 'LatestReplyGuard.kt'},
    'intelligence.ipc': {'ScoringContract.kt', 'ScoringParcels.kt'},
    'intelligence.readiness': {'ActiveModelReadiness.kt', 'DiskModelReadinessProbe.kt'},
    'intelligence.storage': {'ActiveModelResolver.kt', 'ActiveModelPointer.kt', 'ActiveModelPointerCodec.kt', 'ModelOperationGate.kt'},
    'intelligence.model': PURE_MODEL,
}
GENERATED = {BASE + 'R', BASE + 'BuildConfig', BASE + 'intelligence.ipc.IModelScoringService', BASE + 'intelligence.ipc.IModelScoringCallback'}
STRINGS_COMMENTS = re.compile(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
NETWORK = re.compile(r'\b(?:java\.net\.(?!URI\b)|javax\.net\.|android\.net\.|DownloadManager|Socket|ServerSocket|URLConnection|HttpURLConnection|okhttp|retrofit|ktor|firebase|analytics|Sentry)')
LOGS = re.compile(r'\b(?:Log|Logger|Timber)\b|\b(?:println|printStackTrace)\s*\(|System\.(?:out|err)')
PERSIST = re.compile(r'\b(?:FileOutputStream|FileWriter|SharedPreferences|DataStore|SQLiteDatabase|RoomDatabase|ClipboardManager)\b|\b(?:writeText|writeBytes|appendText|appendBytes|openFileOutput|getSharedPreferences|outputStream|writer|bufferedWriter)\s*\(')
REFLECTION = re.compile(r'Class\.forName|java\.lang\.reflect|\b(?:DexClassLoader|PathClassLoader|Runtime\.getRuntime|ProcessBuilder)\b')
JNI = re.compile(r'runtime[-_.]llama|\bexternal\s+fun|System\.load(?:Library)?\s*\(')

def inspect(sources):
    clean = {p: STRINGS_COMMENTS.sub(' ', text) for p, text in sources.items()}
    packages = {}; symbols = {}; imports = {}; edges = {}
    for p, text in clean.items():
        package = re.search(r'^package\s+([\w.]+)', text, re.M)
        if not package: continue
        packages[p] = package.group(1)
        for name in re.findall(r'\b(?:class|interface|object|typealias)\s+(\w+)|^(?:private |internal )?fun\s+(\w+)', text, re.M):
            for n in name:
                if n: symbols[packages[p]+'.'+n] = p
        imports[p] = re.findall(r'^import\s+([\w.*]+)', text, re.M)
    errors = []
    for p, text in clean.items():
        if p not in packages: continue
        dependencies = set(imports[p])
        for symbol in symbols:
            short = symbol.rsplit('.',1)[1]
            if symbol.startswith(packages[p]+'.') and re.search(r'\b'+re.escape(short)+r'\b', text): dependencies.add(symbol)
            if symbol in text: dependencies.add(symbol)
        edges[p] = {symbols[d] for d in dependencies if d in symbols and symbols[d] != p}
        for d in dependencies:
            if d.startswith((BASE,RUNTIME)) and d not in symbols and d not in GENERATED:
                errors.append(f'{p}: unresolved local dependency {d}')
            if d.endswith('.*') and packages[p].startswith(tuple(BASE+a for a in AREAS)):
                errors.append(f'{p}: wildcard dependency forbidden')
    for area in AREAS:
        roots = [p for p,pkg in packages.items() if pkg == BASE+area or pkg.startswith(BASE+area+'.')]
        pending = roots[:]; seen = set()
        while pending:
            p = pending.pop()
            if p in seen: continue
            seen.add(p); pending.extend(edges.get(p,()))
            text = clean[p]; package = packages[p]; name = Path(p).name
            if package == BASE+'intelligence.client' and name in PURE_CLIENT:
                for dependency in edges.get(p, ()):
                    if not (packages[dependency] == BASE+'intelligence.client' and Path(dependency).name in PURE_CLIENT or
                            packages[dependency] == BASE+'intelligence.ipc' and Path(dependency).name == 'ScoringContract.kt'):
                        errors.append(f'{area}: {p}: impure client contract')
            if area == 'ime':
                for dependency in edges.get(p, ()):
                    target = packages[dependency]
                    pure = (target == BASE+'intelligence.client' and Path(dependency).name in PURE_CLIENT or
                            target == BASE+'intelligence.ipc' and Path(dependency).name == 'ScoringContract.kt')
                    if target.startswith(BASE+'intelligence.') and not pure and not package.startswith(BASE+'intelligence.') and p != FACTORY:
                        errors.append(f'{area}: {p}: intelligence implementation entry only through AndroidModelCandidates')
            if p == FACTORY and (LOGS.search(text) or PERSIST.search(text) or
                    re.search(r'getTextBeforeCursor|getTextAfterCursor|getSurroundingText|getExtractedText', text)):
                errors.append(f'{area}: {p}: factory payload I/O')
            if NETWORK.search(text) or REFLECTION.search(text) or re.search(r'\b(?:openConnection|openStream|toURL|connect|sendto)\s*\(', text): errors.append(f'{area}: {p}: network/reflection')
            if re.search(r'\bjava\.net\.URI\b',text) and name != 'ModelManifestParser.kt': errors.append(f'{area}: {p}: URI only allowed in manifest parser')
            if '.intelligence.delivery' in package or '.intelligence.runtime' in package: errors.append(f'{area}: {p}: delivery/activation')
            if package.startswith(BASE+'intelligence.inference') and any(i.startswith(RUNTIME) for i in imports[p]) and name != 'ActiveModelScoringEngine.kt': errors.append(f'{area}: {p}: JNI runtime only via scoring engine adapter')
            if area != 'intelligence.inference' and JNI.search(text): errors.append(f'{area}: {p}: JNI dependency')
            if area.startswith('intelligence.'):
                if LOGS.search(text) or PERSIST.search(text): errors.append(f'{area}: {p}: logs/payload persistence')
                if area in ('intelligence.client','intelligence.ipc'):
                    if not package.startswith((BASE+'intelligence.client',BASE+'intelligence.ipc')): errors.append(f'{area}: {p}: dependency outside bounded client/IPC')
                    if re.search(r'\b(?:java\.io|java\.nio\.file|File|RandomAccessFile)\b',text): errors.append(f'{area}: {p}: filesystem')
                if area == 'intelligence.storage' and not (package.startswith(BASE+'intelligence.storage') or package == BASE+'intelligence.model' and name in PURE_MODEL): errors.append(f'{area}: {p}: non-neutral storage dependency')
                if area == 'intelligence.readiness' and not (package.startswith((BASE+'intelligence.readiness', BASE+'intelligence.storage')) or
                        package == BASE+'intelligence.client' and name in ('ModelReadinessSource.kt', 'ModelDemand.kt') or
                        package == BASE+'intelligence.model' and name in PURE_MODEL):
                    errors.append(f'{area}: {p}: readiness must stay payload-free and read-only')
                if area == 'intelligence.inference' and not (package.startswith((BASE+'intelligence.inference', BASE+'intelligence.ipc', BASE+'intelligence.storage', RUNTIME.rstrip('.'))) or package == BASE+'intelligence.model' and name in PURE_MODEL): errors.append(f'{area}: {p}: dependency outside service adapter boundary')
                if area == 'intelligence.inference' and package == BASE+'intelligence.model' and name not in PURE_MODEL: errors.append(f'{area}: {p}: non-pure model dependency')
                if 'RandomAccessFile' in text and name != 'ModelOperationGate.kt': errors.append(f'{area}: {p}: arbitrary file writes')
            if area == 'ime' and package.startswith(BASE+'intelligence.') and name not in IME_INTELLIGENCE.get(package.removeprefix(BASE), set()):
                errors.append(f'{area}: {p}: outside exact IME model composition allowlist')
    return sorted(set(errors))

def collect(root):
    result={}
    for area in ('app/src/main/java','runtime-llama/src/main/java'):
        for p in (root/area).rglob('*'):
            if p.suffix in ('.kt','.java'): result[str(p.relative_to(root))]=p.read_text()
    return result

def self_test():
    def source(package,body): return 'package '+BASE+package+'\n'+body
    tests=[
        {'Client.kt':source('intelligence.client','import '+BASE+'intelligence.delivery.Manager\nclass Client'), 'Manager.kt':source('intelligence.delivery','class Manager')},
        {'Client.kt':source('intelligence.client','import '+BASE+'helper.Helper\nclass Client'), 'Helper.kt':source('helper','import java.net.Socket\nclass Helper')},
        {'Store.kt':source('intelligence.storage','import '+RUNTIME+'Runtime\nclass Store'), 'Runtime.kt':'package '+RUNTIME.rstrip('.')+'\nclass Runtime'},
        {'Service.kt':source('intelligence.inference','import '+BASE+'helper.Helper\nclass Service'),'Helper.kt':source('helper','import java.io.FileOutputStream\nclass Helper')},
        {'Controller.kt':source('ime','import '+BASE+'intelligence.client.BoundModelScoringClient\nclass Controller'), 'Bound.kt':source('intelligence.client','class BoundModelScoringClient')},
        {'Service.kt':source('intelligence.inference','import android.util.Log\nclass Service')},
        {'Client.kt':source('intelligence.client','import '+BASE+'intelligence.ipc.*\nclass Client')},
        {'Client.kt':source('intelligence.client','class Client { val x = Class.forName("hidden") }')},
    ]
    tests += [
        {FACTORY:source('smarttyping.android','import java.io.FileWriter\nclass AndroidModelCandidates'),
         'Ime.kt':source('ime','import '+BASE+'smarttyping.android.AndroidModelCandidates\nclass Ime')},
        {'Hint.kt':source('intelligence.readiness','import '+BASE+'intelligence.delivery.Manager\nclass Hint'),
         'Manager.kt':source('intelligence.delivery','class Manager')},
        {'Hint.kt':source('intelligence.readiness','import '+BASE+'smarttyping.session.Payload\nclass Hint'),
         'Payload.kt':source('smarttyping.session','class Payload')},
        {'Ime.kt':source('ime','import '+BASE+'helper.Helper\nclass Ime'),
         'Helper.kt':source('helper','import '+BASE+'intelligence.client.BoundModelScoringClient\nclass Helper'),
         'BoundModelScoringClient.kt':source('intelligence.client','class BoundModelScoringClient')},
        {'Ime.kt':source('ime','import '+BASE+'intelligence.client.ModelScoringClient\nclass Ime'),
         'ModelScoringClient.kt':source('intelligence.client','import '+BASE+'intelligence.client.BoundModelScoringClient\nclass ModelScoringClient'),
         'BoundModelScoringClient.kt':source('intelligence.client','class BoundModelScoringClient')},
        {'Controller.kt':source('ime','import '+BASE+'intelligence.client.ModelDemand\nclass Controller'),
         'ModelDemand.kt':source('intelligence.client','import java.io.File\nclass ModelDemand')},
        {'Service.kt':source('intelligence.inference','import '+RUNTIME+'Adapter\nclass Service'), 'Adapter.kt':'package '+RUNTIME.rstrip('.')+'\nclass Adapter'},
        {'Store.kt':source('intelligence.storage','import '+BASE+'helper.Helper\nclass Store'), 'Helper.kt':source('helper','import '+BASE+'intelligence.delivery.Manager\nclass Helper'), 'Manager.kt':source('intelligence.delivery','class Manager')},
    ]
    for n,case in enumerate(tests):
        if not inspect(case): raise AssertionError(f'negative fixture {n} escaped')
    positive={'Client.kt':source('intelligence.client','import '+BASE+'intelligence.ipc.Token\nclass Client'),'Token.kt':source('intelligence.ipc','class Token')}
    assert not inspect(positive)
    adapter={'ActiveModelScoringEngine.kt':source('intelligence.inference','import '+RUNTIME+'Adapter\nclass ActiveModelScoringEngine'), 'Adapter.kt':'package '+RUNTIME.rstrip('.')+'\nclass Adapter'}
    assert not inspect(adapter)
    demand={'Controller.kt':source('ime','import '+BASE+'intelligence.client.ModelDemand\nclass Controller'),
            'ModelDemand.kt':source('intelligence.client','class ModelDemand')}
    assert not inspect(demand)
    factory={'Ime.kt':source('ime','import '+BASE+'smarttyping.android.AndroidModelCandidates\nclass Ime'),
             FACTORY:source('smarttyping.android','import '+BASE+'intelligence.client.BoundModelScoringClient\nclass AndroidModelCandidates'),
             'BoundModelScoringClient.kt':source('intelligence.client','class BoundModelScoringClient')}
    assert not inspect(factory)
    print(f'boundary fixtures PASS: {len(tests)} negative, 4 positive')

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    if args.root:
        errors=inspect(collect(args.root))
        if errors: raise SystemExit('\n'.join(errors))
        print('scoring dependency boundary PASS')
