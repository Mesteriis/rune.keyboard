#!/usr/bin/env python3
"""Fail-closed source dependency gate. No source execution or build-time network."""
import argparse
from collections import Counter
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
    'intelligence.ipc': {'ScoringContract.kt', 'ScoringParcels.kt', 'IModelScoringService.aidl', 'IModelScoringCallback.aidl'},
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
DIAGNOSTICS = BASE + 'smarttyping.diagnostics'
DIAGNOSTIC_PATH = 'app/src/{}/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/'
DIAGNOSTIC_PROVIDERS = {'TypingDiagnosticsProvider', 'DiagnosticsSettingsProvider'}
DIAGNOSTIC_CONTRACT = DIAGNOSTIC_PATH.format('main') + 'TypingDiagnostics.kt'
DIAGNOSTIC_CONTRACT_NAMES = {'DiagnosticKind', 'DiagnosticReason', 'DiagnosticEvent', 'DiagnosticSource', 'DiagnosticCompletion',
                             'DiagnosticText', 'TypingDiagnostics', 'NoTypingDiagnostics'}
FINAL_DIAGNOSTIC_PROVIDERS = {
    'TypingDiagnosticsProvider': '''import android.content.Context
object TypingDiagnosticsProvider {
    fun create(context: Context): TypingDiagnostics = NoTypingDiagnostics
}''',
    'DiagnosticsSettingsProvider': '''import android.app.Activity
import android.widget.LinearLayout
object DiagnosticsSettingsProvider {
    fun contribute(activity: Activity, container: LinearLayout): AutoCloseable = AutoCloseable { }
}''',
}
NO_DIAGNOSTICS = '''object NoTypingDiagnostics : TypingDiagnostics {
    override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
    override fun invalidate() = Unit
    override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) = Unit
}'''
DIAGNOSTICS_INTERFACE = '''interface TypingDiagnostics {
    fun startSession(session: Long, eligible: Boolean, fresh: Boolean)
    fun invalidate()
    fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)? = null)
    fun editorOperation(session: Long, revision: Long): (() -> Unit)? = null
    fun editorOutcome(event: DiagnosticEvent): ((Boolean) -> Unit)? = null
}'''
DIAGNOSTICS_TEXT = '''data class DiagnosticText(
    val input: String = "",
    val context: String = "",
    val original: String = "",
    val candidates: List<String> = emptyList(),
    val result: String = "",
)'''
DIAGNOSTIC_DEBUG_FILES = {
    'TypingDiagnosticsProvider.kt', 'DiagnosticsSettingsProvider.kt', 'DiagnosticsConsent.kt',
    'DiagnosticsRecorder.kt', 'DiagnosticsStorage.kt', 'DiagnosticsEncoding.kt',
    'DiagnosticsSettingsContribution.kt', 'DiagnosticsActivity.kt', 'DiagnosticsAndroidPreferences.kt',
}
EDITOR_READS = re.compile(r'\b(?:getTextBeforeCursor|getTextAfterCursor|getSelectedText|getExtractedText|getSurroundingText|takeSnapshot|getCursorCapsMode|ClipboardManager)\b')

def compact(text):
    # Ignore comments/layout, but retain exact string literals and their whitespace.
    result = []; offset = 0
    for match in STRINGS_COMMENTS.finditer(text):
        result.append(re.sub(r'\s+', '', text[offset:match.start()]))
        if match.group().startswith(('"', "'")): result.append(match.group())
        offset = match.end()
    result.append(re.sub(r'\s+', '', text[offset:]))
    return ''.join(result)


def contract_declaration(text, kind, name):
    """Extract one balanced declaration while ignoring delimiters inside strings/comments."""
    masked = STRINGS_COMMENTS.sub(lambda match: ' ' * len(match.group()), text)
    match = re.search(r'\b' + kind + r'\s+' + name + r'\b', masked)
    if not match: return ''
    offset = match.end()
    while offset < len(masked) and masked[offset].isspace(): offset += 1
    for opening, closing in (('(', ')'), ('{', '}')):
        if offset < len(masked) and masked[offset] == opening:
            depth = 1; offset += 1
            while offset < len(masked) and depth:
                if masked[offset] == opening: depth += 1
                elif masked[offset] == closing: depth -= 1
                offset += 1
            if depth: return ''
            while offset < len(masked) and masked[offset].isspace(): offset += 1
            # These exact contract declarations have no supertypes/delegation. Do not
            # truncate at ':' and accidentally ignore a following serializer body.
            if offset < len(masked) and masked[offset] == ':': return ''
    return text[match.start():offset]


def outer_declarations(text):
    """Mask constructor/function arguments and bodies to find extra top-level helpers."""
    result = []; braces = parentheses = 0
    for char in text:
        if char == '{': braces += 1
        elif char == '(': parentheses += 1
        result.append(char if braces == 0 and parentheses == 0 else ' ')
        if char == '}': braces -= 1
        elif char == ')': parentheses -= 1
    return ''.join(result)

def inspect(sources, variant=None):
    clean = {p: STRINGS_COMMENTS.sub(' ', text) for p, text in sources.items()}
    packages = {}; symbols = {}; imports = {}; edges = {}; declarations = {}
    for p, text in clean.items():
        package = re.search(r'^package\s+([\w.]+)', text, re.M)
        if not package: continue
        packages[p] = package.group(1)
        for name in re.findall(r'\b(?:class|interface|object|typealias)\s+(\w+)', text):
            symbol = packages[p]+'.'+name
            declarations.setdefault(symbol, []).append(p)
            symbols[symbol] = p
        modifiers = r'(?:(?:private|internal|public|protected|inline|suspend|operator|infix|tailrec)\s+)*'
        functions = r'^'+modifiers+r'fun\s+(?:<[^>\n]+>\s*)?(?:[\w.<>?, ]+\.)?(\w+)\s*\('
        for name in re.findall(functions, text, re.M):
            symbols[packages[p]+'.'+name] = p
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
                        package == BASE+'intelligence.ipc' and name == 'ScoringContract.kt' or
                        package == BASE+'intelligence.client' and name in ('ModelReadinessSource.kt', 'ModelDemand.kt') or
                        package == BASE+'intelligence.model' and name in PURE_MODEL):
                    errors.append(f'{area}: {p}: readiness must stay payload-free and read-only')
                if area == 'intelligence.inference' and not (package.startswith((BASE+'intelligence.inference', BASE+'intelligence.ipc', BASE+'intelligence.storage', RUNTIME.rstrip('.'))) or package == BASE+'intelligence.model' and name in PURE_MODEL): errors.append(f'{area}: {p}: dependency outside service adapter boundary')
                if area == 'intelligence.inference' and package == BASE+'intelligence.model' and name not in PURE_MODEL: errors.append(f'{area}: {p}: non-pure model dependency')
                if 'RandomAccessFile' in text and name != 'ModelOperationGate.kt': errors.append(f'{area}: {p}: arbitrary file writes')
            if area == 'ime' and package.startswith(BASE+'intelligence.') and name not in IME_INTELLIGENCE.get(package.removeprefix(BASE), set()):
                errors.append(f'{area}: {p}: outside exact IME model composition allowlist')
    if variant is not None:
        errors.extend(inspect_diagnostics(clean, packages, symbols, declarations, edges, variant, sources))
    return sorted(set(errors))


def inspect_diagnostics(clean, packages, symbols, declarations, edges, variant, sources):
    errors = []
    expected_providers = {DIAGNOSTIC_PATH.format(variant) + name + '.kt' for name in DIAGNOSTIC_PROVIDERS}
    for symbol, paths in declarations.items():
        if symbol.startswith(DIAGNOSTICS + '.') and len(set(paths)) > 1:
            errors.append('duplicate diagnostics declaration: ' + symbol)
    for name in DIAGNOSTIC_PROVIDERS:
        paths = declarations.get(DIAGNOSTICS + '.' + name, [])
        if len(paths) > 1:
            errors.append('duplicate diagnostics declaration: ' + name)
        if paths != [DIAGNOSTIC_PATH.format(variant) + name + '.kt']:
            errors.append('missing variant diagnostics provider: ' + variant + '/' + name)
    allowed = {DIAGNOSTIC_CONTRACT} | expected_providers
    if variant == 'debug':
        allowed |= {DIAGNOSTIC_PATH.format('debug') + name for name in DIAGNOSTIC_DEBUG_FILES}
    roots = [p for p, pkg in packages.items() if pkg == DIAGNOSTICS or pkg.startswith(DIAGNOSTICS + '.')]
    for p in roots:
        if p not in allowed:
            errors.append(p + ': diagnostics declaration outside permitted variant inventory')
        # A permitted filename is not permission to add declarations inside it.
        if p == DIAGNOSTIC_CONTRACT or variant != 'debug':
            expected = DIAGNOSTIC_CONTRACT_NAMES if p == DIAGNOSTIC_CONTRACT else {Path(p).stem}
            actual = Counter(re.findall(r'\b(?:class|interface|object|typealias)\s+(\w+)', clean[p]))
            if (actual != Counter(expected) or '`' in clean[p] or
                    re.search(r'\b(?:fun|val|var|typealias)\b', outer_declarations(clean[p]))):
                errors.append(p + ': diagnostics declaration outside permitted variant inventory')
        if variant != 'debug' and p in expected_providers:
            expected = 'package ' + DIAGNOSTICS + '\n' + FINAL_DIAGNOSTIC_PROVIDERS[Path(p).stem]
            if compact(sources[p]) != compact(expected):
                errors.append(p + ': diagnostics final provider must be exact no-op')
    pending = roots[:]; seen = set()
    storage = DIAGNOSTIC_PATH.format('debug') + 'DiagnosticsStorage.kt'
    preferences = DIAGNOSTIC_PATH.format('debug') + 'DiagnosticsAndroidPreferences.kt'
    theme_preferences = 'app/src/main/java/io/github/mesteriis/rune/keyboard/settings/KeyboardPreferences.kt'
    activity = DIAGNOSTIC_PATH.format('debug') + 'DiagnosticsActivity.kt'
    while pending:
        p = pending.pop()
        if p in seen: continue
        seen.add(p); pending.extend(edges.get(p, ()))
        text = clean[p]
        # SAF URI is a value type, not a network allowance for the containing file.
        network_text = re.sub(r'\bandroid\.net\.Uri\b', ' ', text) if variant == 'debug' and p == activity else text
        if NETWORK.search(network_text) or REFLECTION.search(text) or LOGS.search(text):
            errors.append(p + ': diagnostics network/reflection/logging')
        if EDITOR_READS.search(text) or JNI.search(text) or packages[p].startswith(BASE + 'intelligence.'):
            errors.append(p + ': diagnostics forbidden capability')
        if PERSIST.search(text) and not (variant == 'debug' and p in {storage, preferences, theme_preferences}):
            errors.append(p + ': diagnostics persistence outside exact debug storage')
        file_access = re.search(r'\b(?:File|FileInputStream|RandomAccessFile|FileChannel|Files|Path|Paths)\b|java\.nio\.file', text)
        if file_access and not (variant == 'debug' and p == storage):
            errors.append(p + ': diagnostics filesystem outside exact debug storage')
        if re.search(r'\b(?:openOutputStream|openFileDescriptor)\s*\(', text) and not (variant == 'debug' and p == activity):
            errors.append(p + ': diagnostics SAF output outside exact debug activity')
    # UI construction, even through helpers, must never join the IME factory closure.
    start = symbols.get(DIAGNOSTICS + '.TypingDiagnosticsProvider')
    pending = [start] if start else []; seen = set()
    while pending:
        p = pending.pop()
        if p in seen: continue
        seen.add(p); pending.extend(edges.get(p, ()))
        if (Path(p).name in {'DiagnosticsSettingsProvider.kt', 'DiagnosticsSettingsContribution.kt', 'DiagnosticsActivity.kt'} or
                re.search(r'\b(?:Activity|AlertDialog|ContentResolver|Uri|View|LinearLayout)\b', clean[p])):
            errors.append(p + ': typing diagnostics factory reaches UI/export')
    contract = clean.get(DIAGNOSTIC_CONTRACT, '')
    raw_contract = sources.get(DIAGNOSTIC_CONTRACT, '')
    if compact(contract_declaration(raw_contract, 'interface', 'TypingDiagnostics')) != compact(DIAGNOSTICS_INTERFACE):
        errors.append('diagnostics shared interface shape: exact observer and default-null terminal method required')
    if compact(contract_declaration(raw_contract, r'data\s+class', 'DiagnosticText')) != compact(DIAGNOSTICS_TEXT):
        errors.append('diagnostics shared text DTO shape: exact constructor-only fields required')
    noop = re.search(r'\bobject\s+NoTypingDiagnostics\s*:\s*TypingDiagnostics\s*\{[^{}]*\}', contract)
    if noop is None or compact(noop.group()) != compact(NO_DIAGNOSTICS):
        errors.append('diagnostics main observer must be exact no-op')
    metadata = re.search(r'\bdata\s+class\s+DiagnosticEvent\s*\((.*?)\)\s*(?:\{|\n|$)', contract, re.S)
    if not metadata:
        errors.append('diagnostics metadata declaration missing')
    else:
        allowed_fields = {'kind': 'DiagnosticKind', 'reason': 'DiagnosticReason',
                          'session': 'Long', 'revision': 'Long', 'candidateCount': 'Int',
                          'selectedIndex': 'Int', 'modelUsed': 'Boolean',
                          'source': 'DiagnosticSource', 'completion': 'DiagnosticCompletion',
                          'scoringCode': 'Int', 'elapsedMs': 'Long', 'requestId': 'Long', 'operationId': 'Long'}
        # This frozen metadata DTO has constructor fields only. Reject inferred fields,
        # getters and methods too; scanning explicit property types alone misses them.
        if metadata.group().rstrip().endswith('{'):
            errors.append('diagnostics metadata field type: class body forbidden')
        for enum_name in ('DiagnosticKind', 'DiagnosticReason', 'DiagnosticSource', 'DiagnosticCompletion'):
            if not re.search(r'\benum\s+class\s+' + enum_name + r'\b', contract):
                errors.append('diagnostics metadata enum missing: ' + enum_name)
        if re.search(r'\btypealias\s+(?:DiagnosticKind|DiagnosticReason|DiagnosticSource|DiagnosticCompletion|Long|Int|Boolean)\b', contract):
            errors.append('diagnostics metadata field type alias forbidden')
        fields = re.findall(r'\b(?:val|var)\s+(\w+)\s*:\s*([^=,\n]+)', metadata.group(1))
        if Counter(name for name, _ in fields) != Counter(allowed_fields.keys()):
            errors.append('diagnostics metadata field type: exact field inventory required')
        for name, field_type in fields:
            if field_type.strip() != allowed_fields.get(name):
                errors.append('diagnostics metadata field type: ' + name + ': ' + field_type.strip())
    return errors

def collect(root, variant=None):
    result={}
    areas = ['app/src/main/java', 'runtime-llama/src/main/java']
    if variant is not None:
        areas += [f'app/src/{variant}/java', f'runtime-llama/src/{variant}/java']
    for area in areas:
        for p in (root/area).rglob('*'):
            if p.suffix in ('.kt','.java'): result[str(p.relative_to(root))]=p.read_text()
    for source_set in ('main', variant) if variant else ('main',):
        for p in (root/f'app/src/{source_set}/aidl').rglob('*.aidl'):
            text = STRINGS_COMMENTS.sub(' ', p.read_text())
            package = re.search(r'\bpackage\s+([\w.]+)\s*;', text)
            declaration = re.search(r'\binterface\s+(\w+)', text)
            # Parcelable declarations are implemented by Kotlin/Java and must retain those edges.
            if package and declaration:
                imports = re.findall(r'\bimport\s+([\w.]+)\s*;', text)
                result[str(p.relative_to(root))] = ('package ' + package.group(1) + '\n' +
                    ''.join('import ' + name + '\n' for name in imports) +
                    'interface ' + declaration.group(1))
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
    functional = {'Controller.kt':source('ime','import '+BASE+'helper.Admission\nclass Controller'),
                  'Admission.kt':source('helper','internal fun interface Admission { fun allows(): Boolean }')}
    assert not inspect(functional)
    unsafe_functional = {**functional, 'Admission.kt':source('helper',
        'import java.net.Socket\ninternal fun interface Admission { fun allows(): Boolean }')}
    assert any('network/reflection' in error for error in inspect(unsafe_functional))
    tests.append(unsafe_functional)
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
    extension={'Controller.kt':source('ime','import '+BASE+'telemetry.section\nclass Controller'),
               'Trace.kt':source('telemetry','interface Trace\ninternal inline fun <T> Trace.section(block: () -> T): T = block()')}
    assert not inspect(extension)
    print(f'boundary fixtures PASS: {len(tests)} negative, 6 positive')

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path);parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    if args.root:
        errors=[]
        for variant in ('debug', 'release', 'profile'):
            errors.extend(variant + ': ' + error for error in inspect(collect(args.root, variant), variant=variant))
        if errors: raise SystemExit('\n'.join(errors))
        print('scoring dependency boundary PASS: debug, release, profile')
