#!/usr/bin/env python3
"""No-inference, source-bound contextual controller attribution. No scoring command."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parent
REPO = HERE.parents[4]
sys.path.insert(0, str(PIPELINE))
import contextual_quality as cq

SCOPE = 'contextual-controller-attribution'
BOUNDARIES = [' ', ', ', ': ', '; ', '. ', '? ', '! ']
UNSCORED = {'PAYLOAD_MISMATCH', 'NEW_CONTEXTUAL_REQUEST', 'MISSING_RESPONSE'}
UNRESOLVED = UNSCORED | {'UNREPRESENTABLE_REPLY'}
HOST_CASES = ['independent-editor', *[f'boundary-tap-{i}' for i in range(1,7)],
    'original-and-thresholds','spelling-precedence','canonical-precedence','protected-unknown-exhausted',
    'stale-token-owner-and-session','refused-tap-and-hidden-strip','manual-original-veto',
    'uppercase-expansion-and-grapheme','reply-then-space-no-automatic-contextual-edit',
    'numeric-tsv-and-malformed-utf8','candidate-owner-denial','candidate-route-denial-and-validated-readers',
    'candidate-reply-stale-and-unready','candidate-secondary-reasons-without-labels','numeric-error-no-suggestion']
SECONDARY_REASONS = ['SESSION_CLOSED','OWNER_INELIGIBLE','OWNERSHIP_UNAVAILABLE','ORIGINAL_SELECTED','PROTECTED',
    'ROUTE_PROTECTED','ROUTE_REQUEST_DENIED','ROUTE_NOT_READY','CANDIDATE_REQUEST_UNAVAILABLE','REQUEST_INELIGIBLE',
    'REPLY_SESSION_MISMATCH','REPLY_REVISION_MISMATCH','REPLY_REQUEST_MISMATCH','LIVE_SESSION_MISMATCH',
    'LIVE_REVISION_MISMATCH','ACTIVE_LANGUAGE_CHANGED','ORIGINAL_TOKEN_MISMATCH','COMPOSITION_CHANGED',
    'ADMISSION_EPOCH_CHANGED','CANDIDATES_REJECTED','CANONICAL_CASE_PRECEDENCE','INCOMPLETE_GENERATION',
    'UNKNOWN_NO_ALTERNATIVES','NO_OWNED_SPACE','ENGINE_EXCLUDED','MODEL_REQUEST_NOT_ADMITTED']
ASSETS = REPO / 'app/src/main/assets'
ARCHIVE_COMMANDS = PIPELINE / 'results/2026-09-06-command-dot-safety/commands.json'
# Explicit current-source closure owned by this tool; archives are comparison evidence only.
COMPILE_SOURCES = (
    'app/src/main/java/io/github/mesteriis/rune/keyboard/ime/model/KeyboardState.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/ime/model/EditorContext.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/ime/editor/DoubleSpacePeriod.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/settings/KeyboardSettings.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/intelligence/ipc/ScoringContract.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/TokenUnicode.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/ProtectedTokenPolicy.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/CasePattern.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/KeyboardDistance.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/WeightedDamerauLevenshtein.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/CandidateRanker.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/CalibratedSpellingPolicy.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/SpellingQualification.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/LanguageRouter.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateLexicon.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CanonicalCaseLexicon.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateGenerator.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PackedCandidateLexicon.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PackedLexiconData.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PackedLexiconManifest.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/FrozenPackedLexicons.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/TopCandidateSelection.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PackedTopSeven.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PrefixDistance.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CanonicalCaseData.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/FrozenCanonicalCaseLexicons.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/LocalCandidateWorker.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/TypingSessionController.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/TypingSessionState.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/ComposingSegment.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/SessionTextContext.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/UndoableTextEdit.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/MechanicalPunctuationPlan.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/MechanicalPunctuationPlanner.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/ContextualPunctuationEngine.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/punctuation/ContextualPunctuationPolicy.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/ui/CandidateUiItem.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/ui/SmartTypingViewState.kt',
    'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/telemetry/SmartTypingTrace.kt',
)
MODEL_SHA = '7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4'
RUNNER_SHA = 'bc3f78bdf3ac41009a7603ca5dd6b6c4d5e8d6c2bdcaf3a692cfd95a3b3d2553'
ERROR_SOURCE = REPO / 'runtime-llama/src/main/java/io/github/mesteriis/rune/runtime/llama/LocalModelRuntime.kt'
ERROR_MAP = {'INVALID_REQUEST':12,'INVALID_UTF8':8,'TOO_MANY_CANDIDATES':14,
             'CONTEXT_TOO_LONG':13,'CANCELLED':9,'TOKENIZE_FAILED':5,
             'CONTEXT_CREATE_FAILED':4,'SCORING_FAILED':15}
ACTION_CONTRACT = {'version':2,'candidateAdmission':'current-owner/validated-route/live-reply-guards','input':'exact-prefix + ASCII-space + exact-currentWord',
    'step':'Unicode-code-point','priorWordCandidateCallbacks':False,'doubleSpaceGesture':False,
    'settings':'KeyboardSettings.DEFAULT','qualification':'SpellingQualification.CURRENT',
    'availability':'final-target-ready-host-transport','diagnostics':'NoTypingDiagnostics',
    'graphemes':'JDK17-java.text.BreakIterator','nativeCalls':0,'realInputConnection':False,
    'nativeDuration':'preserve original; truncate toward zero only for integral host callback field; no wait'}


def require(condition, code):
    if not condition: raise ValueError(code)


def sha(path):
    with Path(path).open('rb') as f:
        h=hashlib.sha256()
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        return h.hexdigest()


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as f:f.write(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')


def write_jsonl(path,rows):
    with Path(path).open('x',encoding='utf-8') as f:
        for row in rows:f.write(canonical(row).decode()+'\n')


def read_json(path):return json.loads(Path(path).read_text())


def read_jsonl(path):
    data=Path(path).read_bytes()
    require(not data or data.endswith(b'\n'),'INCOMPLETE_JSONL')
    return [json.loads(line) for line in data.splitlines()]


def fresh_output(path,build_root=None):
    path=Path(path).resolve()
    base=(build_root or REPO/'build').resolve()
    require(path.is_relative_to(base) and path!=base and not path.exists(),'FRESH_OUTPUT_REQUIRED')
    path.mkdir(parents=True)
    return path


def verify_files(files):
    require(isinstance(files,dict) and files,'MISSING_FILE_BINDINGS')
    for name,expected in files.items():
        p=Path(name)
        require(p.is_absolute() and p.is_file() and sha(p)==expected,'BOUND_FILE_DRIFT')


def payload_differences(actual,exported):
    if actual is None:return []
    expected={'prefix':exported['prefix'],'candidateIds':[v['id'] for v in exported['variants']],
              'continuations':[v['continuation'] for v in exported['variants']]}
    return [key for key,value in expected.items() if actual.get(key)!=value]


def payload_status(actual,exported):
    if actual is None:return 'NO_CONTEXTUAL_REQUEST'
    variants=exported['variants']
    if not variants:return 'NEW_CONTEXTUAL_REQUEST'
    if (actual.get('prefix')!=exported['prefix'] or
        actual.get('candidateIds')!=[v['id'] for v in variants] or
        actual.get('continuations')!=[v['continuation'] for v in variants]):return 'PAYLOAD_MISMATCH'
    return 'EXACT_CACHE'


def admit_response(actual,exported,response):
    status=payload_status(actual,exported)
    if status!='EXACT_CACHE':return {'status':status,'response':None}
    if response is None:return {'status':'MISSING_RESPONSE','response':None}
    cq.evaluator().validate_response({'id':exported['id'],'candidates':actual['continuations']},response)
    if 'error' in response:return {'status':'EXACT_CACHE_ERROR','response':response}
    scores=response['scores']
    representable=([s['id'] for s in scores]==actual['candidateIds'] and
                   all(1<=s['scoredTokenCount']<=255 for s in scores) and
                   response['durationMillis']<2**63)
    return {'status':'EXACT_CACHE_OK' if representable else 'UNREPRESENTABLE_REPLY','response':response}


def validate_envelopes(actual,rows):
    require(len(actual)==len(rows),'HOST_ROW_COUNT')
    require(len({r['id'] for r in rows})==len(rows),'INPUT_DUPLICATE_IDS')
    for i,(value,row) in enumerate(zip(actual,rows)):
        require(value.get('schemaVersion')==1 and value.get('scope')==SCOPE and
                type(value.get('index')) is int and value['index']==i and value.get('id')==row['id'],'HOST_ROW_IDENTITY')


def build_metrics(rows):
    require(len({r['id'] for r in rows})==len(rows),'METRIC_DUPLICATE_IDS')
    require(all(r['observedBoundary'] in (' ', ', ', ': ', '. ') and
        r['decisionId'] in [None,*range(7)] and r['deliveredDecisionId'] in [None,*range(7)] for r in rows),'METRIC_FIELDS')
    rate=cq.evaluator().rate
    n=len(rows);unknown=sum(r['bindingStatus'] in UNRESOLVED for r in rows)
    require(all((r['decisionId'] is None)==(r['bindingStatus'] in UNRESOLVED or r['harnessError'] is not None)
                for r in rows),'UNRESOLVED_DECISION')
    errors=sum(r['harnessError'] is not None for r in rows)
    known=[r for r in rows if r['decisionId'] is not None]
    matches=sum(BOUNDARIES[r['decisionId']]==r['observedBoundary'] for r in known)
    offers=sum(r['offer'] for r in rows);attempts=sum(r['tapAttempted'] for r in rows);success=sum(r['tapSuccess'] for r in rows)
    require(0<=success<=attempts<=offers<=n,'ACTION_COUNTS')
    abstentions=sum(not r['offer'] for r in known)
    engine_offers=sum(r['engineDecisionId']!=0 for r in rows)
    spaces=[r for r in rows if r['observedBoundary']==' ']
    forbidden=sum(r['forbiddenEdits'] for r in rows);unsolicited=sum(r['unsolicitedEdits'] for r in rows)
    return {'rows':n,'routingCounts':dict(sorted(Counter(r['routing'] for r in rows).items())),
        'bindingCounts':dict(sorted(Counter(r['bindingStatus'] for r in rows).items())),
        'engineExcludedRows':sum(r['engineExcluded'] for r in rows),'inputChangedRows':sum(r['inputChanged'] for r in rows),
        'engineOffers':engine_offers,'engineSourceAgreement':rate(sum(BOUNDARIES[r['engineDecisionId']]==r['observedBoundary'] for r in rows),n),
        'engineSuggestionCoverage':rate(engine_offers,n),
        'engineDecisionCounts':{str(i):sum(r['engineDecisionId']==i for r in rows) for i in range(7)},
        'changedDecisionIds':[r['id'] for r in known if r['decisionId']!=r['engineDecisionId']],
        'unresolvedDecisionIds':[r['id'] for r in rows if r['decisionId'] is None],
        'unusedEngineResponseRows':sum(r.get('engineResponsePresent',False) and r['bindingStatus']=='NO_CONTEXTUAL_REQUEST' for r in rows),
        'engineErrorRows':sum(r.get('engineResponseError') is not None for r in rows),
        'offers':offers,'abstentions':abstentions,'unscoredPayloads':sum(r['bindingStatus'] in UNSCORED for r in rows),'unresolvedRows':unknown,'harnessErrors':errors,
        'unrepresentableReplies':sum(r['bindingStatus']=='UNREPRESENTABLE_REPLY' for r in rows),
        'inputMechanicalEditSteps':sum(step.get('lastAutoEdit') is not None for r in rows for step in r.get('inputSteps',[])),
        'measuredAbstentionRate':rate(abstentions,n),
        'inputChangedIds':[r['id'] for r in rows if r['inputChanged']],
        'sourceBoundaryAgreement':None if unknown or errors else rate(matches,n),
        'knownSourceMatchesPerAllRows':rate(matches,n),'suggestionCoverage':rate(offers,n),
        'suggestedSourceAgreement':rate(sum(r['offer'] and BOUNDARIES[r['decisionId']]==r['observedBoundary'] for r in known),offers),
        'decisionCounts':{str(i):sum(r['decisionId']==i for r in rows) for i in range(7)},
        'insertionAtObservedSpaces':rate(sum(r['offer'] for r in spaces),len(spaces)),
        'tapAttempts':attempts,'tapSuccesses':success,'tapRefusals':attempts-success,'tapSuccessRate':rate(success,attempts),
        'deliveredSourceAgreement':None if unknown or errors else rate(sum(r['deliveredDecisionId'] is not None and
            BOUNDARIES[r['deliveredDecisionId']]==r['observedBoundary'] for r in rows),n),
        'deliveredInsertionsAtObservedSpaces':rate(sum(r['tapSuccess'] for r in spaces),len(spaces)),
        'forbiddenEdits':forbidden,'automaticContextualEdits':unsolicited,
        'attributionComplete':not (unknown or errors or forbidden or unsolicited or offers-attempts or attempts-success)}


def admit_score_split(directory,records,binding,split,export_sha,frozen):
    complete,scores=cq.load_scores(Path(directory),cq.requests(records,split),binding)
    require(complete['split']==split and complete['exportReceiptSha256']==export_sha and
            complete['frozenConfigSha256']==(None if split=='calibration' else frozen['configSha256']),'SCORE_CHAIN')
    cq.require_backend(frozen['modelIdentity'],complete['identity'])
    return complete,scores


def admit_inputs(corpus,export,calibration,holdout,config,protocol):
    records=cq.load_export(Path(export)) # strict full export/loader replay, no legacy fallback
    binding=cq.records_binding(records)
    require(binding==cq.v5_binding(),'V5_REQUIRED')
    rows=cq.corpus_rows(Path(corpus),cq.V5_FORMAT)
    require([r['id'] for r in rows]==[r['id'] for r in records],'CORPUS_EXPORT_ORDER')
    counts=Counter((r['split'],r['language'],r['observedBoundary']) for r in rows)
    require(counts==Counter({(s,l,b):50 for s in ('calibration','holdout') for l in ('en','ru','es')
                             for b in (' ', ', ', ': ', '. ')}),'V5_PARTITIONS')
    ep=Path(export)/'provenance.json';ep_sha=sha(ep)
    require(read_json(ep)['corpusDirectory']==str(Path(corpus).resolve().relative_to(REPO)),'CORPUS_LOCATION')
    frozen=cq.load_frozen(Path(config),ep_sha,binding)
    complete={};scores={}
    for split,directory in [('calibration',Path(calibration)),('holdout',Path(holdout))]:
        completion,response=admit_score_split(directory,records,binding,split,ep_sha,frozen)
        complete[split]=completion;scores[split]=response
    require(frozen['calibrationCompleteSha256']==sha(Path(calibration)/'complete.json') and
            frozen['calibrationScoresSha256']==complete['calibration']['scoresSha256'],'CALIBRATION_CHAIN')
    prot=read_json(protocol);content={k:v for k,v in prot.items() if k!='freezeSha256'}
    require(cq.evaluator().digest(content)==prot['freezeSha256'] and
        prot['scope']=='pre-score-contextual-v5-protocol-freeze' and prot['corpusFormat']==cq.V5_FORMAT and
        prot['corpusVersion']==5 and prot['labelSemantics']==cq.V5_LABEL,'PROTOCOL')
    require(prot['corpusDirectory']==str(Path(corpus).resolve().relative_to(REPO)) and
        prot['policy']==cq.policy_binding()['policy'] and prot['policySourceSha256']==cq.shared.sha(cq.POLICY) and
        prot['qualitySourceSha256']==sha(PIPELINE/'contextual_quality.py'),'PROTOCOL_SOURCE')
    cq.require_corpus_binding(prot,binding)
    for name,expected in prot['sources'].items():require(sha(REPO/name)==expected,'PROTOCOL_SOURCE')
    for name,expected in prot['corpusFiles'].items():require(sha(Path(corpus)/name)==expected,'PROTOCOL_CORPUS')
    backend=Path(protocol).with_name('backend-config.json')
    require(sha(backend)==prot['backendConfigSha256'],'BACKEND_CONFIG')
    backend_config=read_json(backend)
    require(cq.evaluator().digest({k:v for k,v in backend_config.items() if k!='configSha256'})==backend_config['configSha256'],'BACKEND_DIGEST')
    for identity in [prot['backendIdentity'],backend_config['modelIdentity'],frozen['modelIdentity']]:
        require(identity['modelSha256']==MODEL_SHA and identity['runnerSha256']==RUNNER_SHA and
                identity['protocol']=='rune-score-jsonl-v1','BACKEND_IDENTITY')
    require(prot['policyVerificationSha256']==frozen['policyVerificationSha256'],'PARITY_LINK')
    # Scores are validated but never consumed by prepare's Kotlin input or routing summaries.
    return {'rows':rows,'records':records,'scores':scores,'complete':complete,'config':frozen,'protocol':prot}


def input_tsv(rows):
    enc=lambda s:base64.b64encode(s.encode('utf-8')).decode('ascii')
    return ''.join('\t'.join([str(i),enc(r['id']),r['language'],enc(r['prefix']),enc(r['currentWord'])])+'\n' for i,r in enumerate(rows))


def asset_paths():
    return [ASSETS/f'smarttyping/lexicon/{suffix}' for l in ('en','ru','es')
            for suffix in (f'{l}.trie',f'{l}.trie.lengths',f'frequency/{l}.ranks',f'case/{l}.case')]


def compile_inputs(java,cache,android):
    sources=[REPO/p for p in COMPILE_SOURCES]
    prod=REPO/'app/src/main/java/io/github/mesteriis/rune/keyboard'
    sources += [prod/p for p in ['smarttyping/diagnostics/TypingDiagnostics.kt',
        'smarttyping/session/LocalCandidateCoordinator.kt','smarttyping/session/ModelCandidateCoordinator.kt',
        'smarttyping/lexicon/LazyPackedLexicons.kt','smarttyping/correction/ModelRuntimeQualification.kt',
        'intelligence/client/ModelScoringClient.kt','intelligence/client/ModelDemand.kt','intelligence/client/ModelReadinessSource.kt']]
    sources += [HERE/'HostTypingEditExecutor.kt',HERE/'ContextualControllerAttribution.kt']
    sources=list(dict.fromkeys(sources));require(all(p.is_file() for p in sources),'COMPILE_SOURCE_MISSING')
    jars=cq.toolchain(Path(cache))
    version=subprocess.run([str(java),'-version'],capture_output=True,timeout=15,check=True)
    require(b'version "17.' in version.stderr,'JAVA_17')
    require(Path(android).is_file(),'ANDROID_STUB')
    return sources,jars,version.stderr.decode()


def validate_runtime_error_codes(source):
    runtime_codes={name:int(value) for name,value in re.findall(r'([A-Z_][A-Z0-9_]*)\((\d+)\)',source)}
    require(all(runtime_codes.get(name)==value for name,value in ERROR_MAP.items()),'RUNTIME_ERROR_CODES')


def bind_runtime(java,android,sources,jars):
    validate_runtime_error_codes(ERROR_SOURCE.read_text())
    home=Path(java).resolve().parent.parent
    runtime=[home/p for p in ('bin/java','release','lib/modules','lib/libjli.dylib','lib/server/libjvm.dylib')]
    files=[*sources,*jars,*runtime,Path(android),ERROR_SOURCE,*asset_paths(),ARCHIVE_COMMANDS,cq.TOOLCHAIN_MANIFEST,
           *[HERE/p for p in ('contextual_controller_attribution.py','test_contextual_controller_attribution.py','README.md')],
           Path(sys.executable).resolve(),PIPELINE/'export_calibration.py',PIPELINE/'score_product_holdout.py',
           PIPELINE/'test_contextual_v5_adapter.py',PIPELINE/'contextual_quality.py',cq.shared.REPO/'tools/eval/smart-typing-0.3/evaluate.py']
    return {str(p.resolve()):sha(p) for p in files}


def host_commands(out,java,android,sources,jars):
    binary=out/'contextual-controller.jar';cp=os.pathsep.join(map(str,[jars[1],jars[2],android]))
    cmd=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join(map(str,jars)),
         'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','17',
         '-classpath',cp,'-d',str(binary),*map(str,sources)]
    run=[str(java),'-XX:ActiveProcessorCount=2','-Xmx768m','-cp',os.pathsep.join([str(binary),cp]),
         'io.github.mesteriis.rune.keyboard.smarttyping.session.ContextualControllerAttribution']
    return {'compile':cmd,'run':run}


def compile_host(out,java,android,sources,jars,version):
    commands=host_commands(out,java,android,sources,jars)
    cmd=commands['compile'];run=commands['run']
    write_json(out/'commands.json',commands)
    (out/'java-version.txt').write_text(version)
    for source in sources:
        target=out/'sources'/source.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
    with (out/'compile.log').open('xb') as log:subprocess.run(cmd,stdout=log,stderr=log,check=True,timeout=180)
    return run


def run_host(command,out,name,args):
    with (out/name).open('xb') as data,(out/(name+'.log')).open('xb') as log:
        subprocess.run(command+list(map(str,args)),stdout=data,stderr=log,check=True,timeout=600)
    return read_jsonl(out/name)


def input_files(args,bundle):
    paths=[args.protocol,Path(args.protocol).with_name('backend-config.json'),args.config,
           Path(args.corpus)/'manifest.json',*[Path(args.corpus)/name for name in bundle['protocol']['corpusFiles']],
           *[Path(args.export)/n for n in ('provenance.json','inputs.tsv','actual.tsv','rows.jsonl','contextual-export.jar')]]
    paths += [Path(d)/n for d in (args.calibration,args.holdout) for n in ('run-input.json','complete.json','scores.jsonl')]
    paths += [REPO/p for p in bundle['protocol']['sources']]
    paths += [REPO/p for p in bundle['protocol']['corpusLoaderSources']]
    verification=REPO/bundle['config']['policyVerificationDirectory']
    paths += [verification/'verification.json',*[verification/n for n in cq.VERIFICATION_FILES]]
    manifest=read_json(Path(args.corpus)/'manifest.json'); runtime=manifest['toolchain']
    paths += [Path(runtime['pythonExecutable']), *map(Path,runtime['pythonLibraryFiles']),
              *[Path(runtime['pyarrowDirectory'])/p for p in runtime['pyarrowFiles']],
              *[REPO/p for p in manifest['identity']['exclusionFiles']],
              *[cq.v5_loader().INPUTS/p for p in manifest['identity']['sourceFiles']]]
    return {str(Path(p).resolve()):sha(p) for p in paths}


def prepare(args):
    out=fresh_output(args.output)
    try:
        bundle=admit_inputs(args.corpus,args.export,args.calibration,args.holdout,args.config,args.protocol)
        java=Path(args.java).resolve();android=Path(args.android_jar).resolve()
        sources,jars,version=compile_inputs(java,args.gradle_cache,android)
        files={**bind_runtime(java,android,sources,jars),**input_files(args,bundle)}
        locations={key:str(Path(getattr(args,key)).resolve()) for key in ('corpus','export','calibration','holdout','config','protocol')}
        protocol={'schemaVersion':1,'scope':SCOPE,'phase':'prepare','actionContract':ACTION_CONTRACT,
            'runtime':{'java':str(java),'androidJar':str(android),'gradleCache':str(Path(args.gradle_cache).resolve())},
            'locations':locations,'rowsSha256':digest(bundle['rows']),'engineRowsSha256':digest(bundle['records']),
            'files':files,'nativeCalls':0,'fullCorpusNumericResultsConsumed':False}
        write_json(out/'protocol.json',{**protocol,'protocolSha256':digest(protocol)})
        write_json(out/'admitted-inputs.json',{'rows':bundle['rows'],'records':bundle['records']})
        (out/'inputs.tsv').write_text(input_tsv(bundle['rows']),encoding='ascii')
        command=compile_host(out,java,android,sources,jars,version)
        actual=run_host(command,out,'actual-requests.jsonl',['prepare',out/'inputs.tsv',ASSETS])
        validate_envelopes(actual,bundle['rows']);validate_host_records(actual)
        bindings=[];unscored=[]
        for row,old,observed in zip(bundle['rows'],bundle['records'],actual):
            request=observed['modelRequest'] if observed['routing']=='CONTEXTUAL_REQUEST' else None
            status=payload_status(request,old)
            bindings.append({'id':row['id'],'split':row['split'],'language':row['language'],'status':status,
                             'engineExcluded':not old['variants'],'actualRequest':request,'differences':payload_differences(request,old)})
            if status in ('PAYLOAD_MISMATCH','NEW_CONTEXTUAL_REQUEST'):
                unscored.append({'id':row['id'],'split':row['split'],'language':row['language'],
                    'prefix':request['prefix'],'candidateIds':request['candidateIds'],'candidates':request['continuations'],
                    'status':status,'differences':payload_differences(request,old),'originalExportRequest':{'prefix':old['prefix'],'variants':old['variants']}})
        write_jsonl(out/'payload-bindings.jsonl',bindings);write_jsonl(out/'unscored-requests.jsonl',unscored)
        req={'scope':'contextual-controller-unscored-requests','schemaVersion':1,'preparedProtocolSha256':digest(protocol),
            'requestsSha256':sha(out/'unscored-requests.jsonl'),'requestCount':len(unscored),
            'backendIdentity':bundle['protocol']['backendIdentity'],'policy':bundle['protocol']['policy'],'nativeCalls':0,
            'corpusRevealed':True,'thresholdSearch':False}
        write_json(out/'unscored-request-receipt.json',{**req,'receiptSha256':digest(req)})
        verify_files(files)
        outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()}
        write_json(out/'prepare-complete.json',{'schemaVersion':1,'scope':SCOPE,'phase':'prepare',
            'rows':len(actual),'routingCounts':dict(Counter(r['routing'] for r in actual)),
            'payloadCounts':dict(Counter(r['status'] for r in bindings)),
            'harnessErrors':sum(r['harnessError'] is not None for r in actual),
            'unscoredPayloads':len(unscored),'files':outputs,'nativeCalls':0,
            'fullCorpusNumericResultsConsumed':False})
        print(json.dumps({'rows':len(actual),'routingCounts':dict(Counter(r['routing'] for r in actual)),
                         'unscoredPayloads':len(unscored),'nativeCalls':0}))
    except Exception as e:
        if not (out/'failure.json').exists():write_json(out/'failure.json',{'phase':'prepare','errorType':type(e).__name__,'errorCode':str(e) if re.fullmatch('[A-Z_]+',str(e)) else None})
        raise


def validate_secondary_reasons(reasons):
    require(isinstance(reasons,list) and all(type(v) is str for v in reasons) and
            reasons==[v for v in SECONDARY_REASONS if v in reasons], 'HOST_SECONDARY_REASONS')


def validate_host_records(records):
    expected={'schemaVersion','scope','index','id','language','inputExpected','inputChanged','inputSteps',
        'beforeCandidates','fullGeneration','requestGeneration','candidatesAccepted','routing','secondaryReasons','gateFacts',
        'modelRequest','requestCount','harnessError','responseStatus','replyDelivered','replyCurrent','afterReply',
        'offer','decisionId','responseEdited','tapAttempted','tapResult','afterTap','tapEdits','allowedTapChange',
        'duplicateResult','duplicateEdits'}
    for r in records:
        require(set(r)==expected,'HOST_SCHEMA')
        validate_secondary_reasons(r['secondaryReasons'])
        require(type(r['inputChanged']) is bool and type(r['offer']) is bool and type(r['responseEdited']) is bool
                and type(r['requestCount']) is int and r['requestCount'] in (0,1),'HOST_TYPES')
        require(r['routing']!='CONTEXTUAL_REQUEST' or r['modelRequest'] is not None,'HOST_REQUEST')
        require(r['language'] in ('en','ru','es') and isinstance(r['inputSteps'],list) and isinstance(r['gateFacts'],dict), 'HOST_FIELDS')
        require(all(type(r[k]) is bool for k in ('candidatesAccepted','replyDelivered','tapAttempted','allowedTapChange')) and
                r['replyCurrent'] in (None,True,False) and type(r['duplicateEdits']) is int and r['duplicateEdits']>=0,'HOST_ACTION_TYPES')
        require(r['decisionId'] is None or type(r['decisionId']) is int and r['decisionId'] in range(1,7),'HOST_DECISION')
        if r['harnessError'] is None:
            require(r['offer']==r['tapAttempted'] and r['offer']==(r['decisionId'] is not None),'HOST_OFFER_ACTION')
        q=r['modelRequest']
        if q is not None:
            require(set(q)=={'prefix','candidateIds','continuations','sessionId','revision','requestId'} and
                isinstance(q['prefix'],str) and isinstance(q['candidateIds'],list) and isinstance(q['continuations'],list) and
                all(type(v) is int for v in q['candidateIds']) and all(isinstance(v,str) for v in q['continuations']) and
                len(q['candidateIds'])==len(q['continuations']) and len(set(q['candidateIds']))==len(q['candidateIds']) and
                all(type(q[k]) is int and q[k]>0 for k in ('sessionId','requestId')) and type(q['revision']) is int and q['revision']>=0,
                'HOST_REQUEST_FIELDS')
            require(r['routing']!='CONTEXTUAL_REQUEST' or q['candidateIds']==list(range(7)),'HOST_SEVEN_VARIANTS')


def load_prepared(directory):
    directory=Path(directory).resolve(strict=True);complete=read_json(directory/'prepare-complete.json')
    require(complete['scope']==SCOPE and complete['phase']=='prepare' and complete['rows']==1200,'PREPARED_SCOPE')
    for name,h in complete['files'].items():
        require(Path(name).name==name and sha(directory/name)==h,'PREPARED_OUTPUT_DRIFT')
    protocol=read_json(directory/'protocol.json')
    require(digest({k:v for k,v in protocol.items() if k!='protocolSha256'})==protocol['protocolSha256'] and
            protocol['actionContract']==ACTION_CONTRACT,'PREPARED_PROTOCOL')
    verify_files(protocol['files'])
    l=protocol['locations'];bundle=admit_inputs(*(Path(l[k]) for k in ('corpus','export','calibration','holdout','config','protocol')))
    require(digest(bundle['rows'])==protocol['rowsSha256'] and digest(bundle['records'])==protocol['engineRowsSha256'],'PREPARED_INPUT_REPLAY')
    require(read_json(directory/'admitted-inputs.json')=={'rows':bundle['rows'],'records':bundle['records']} and
            (directory/'inputs.tsv').read_text()==input_tsv(bundle['rows']),'PREPARED_ACTION_REPLAY')
    actual=read_jsonl(directory/'actual-requests.jsonl');validate_envelopes(actual,bundle['rows']);validate_host_records(actual)
    from types import SimpleNamespace
    runtime=protocol['runtime']; java=Path(runtime['java']);android=Path(runtime['androidJar'])
    sources,jars,version=compile_inputs(java,runtime['gradleCache'],android)
    expected_files={**bind_runtime(java,android,sources,jars),**input_files(SimpleNamespace(**l),bundle)}
    require(protocol['files']==expected_files,'PREPARED_SOURCE_CLOSURE')
    require(read_json(directory/'commands.json')==host_commands(directory,java,android,sources,jars) and
            (directory/'java-version.txt').read_text()==version,'PREPARED_COMMANDS')
    for source in sources:
        require(sha(directory/'sources'/source.relative_to(REPO))==sha(source),'SOURCE_SNAPSHOT')
    return directory,protocol,bundle,actual


SUPPLEMENT_SCOPE = 'contextual-controller-supplement'


def validate_supplement_responses(requests,responses):
    require(len(responses)==len(requests) and len({r['id'] for r in requests})==len(requests),
            'SUPPLEMENT_RESPONSE_COUNT')
    admitted=[]
    for request,response in zip(requests,responses):
        cq.evaluator().validate_response(request,response)
        require(request['candidateIds']==list(range(7)),'SUPPLEMENT_CANDIDATE_IDS')
        if 'error' not in response:
            require([r['id'] for r in response['scores']]==request['candidateIds'],'SUPPLEMENT_RESPONSE_ORDER')
        old={'id':request['id'],'prefix':request['prefix'],
             'variants':[{'id':i,'continuation':v} for i,v in zip(request['candidateIds'],request['candidates'])]}
        actual={'prefix':request['prefix'],'candidateIds':request['candidateIds'],'continuations':request['candidates']}
        value=admit_response(actual,old,response)
        value['status']={'EXACT_CACHE_OK':'SUPPLEMENT_OK','EXACT_CACHE_ERROR':'SUPPLEMENT_ERROR'}.get(value['status'],value['status'])
        admitted.append(value)
    return admitted


def supplement_document(directory,protocol,bundle,prior,freeze_directory):
    requests=[]
    for source,old,r in zip(bundle['rows'],bundle['records'],prior):
        q=r['modelRequest'] if r['routing']=='CONTEXTUAL_REQUEST' else None
        if payload_status(q,old) in ('PAYLOAD_MISMATCH','NEW_CONTEXTUAL_REQUEST'):
            require(q['candidateIds']==list(range(7)),'SUPPLEMENT_SEVEN_VARIANTS')
            requests.append({'id':source['id'],'split':source['split'],'language':source['language'],
                'prefix':q['prefix'],'candidateIds':q['candidateIds'],'candidates':q['continuations']})
    require(len({r['id'] for r in requests})==len(requests) and
            all(r['split'] in ('calibration','holdout') for r in requests),'SUPPLEMENT_UNIVERSE')
    backend=Path(protocol['locations']['protocol']).with_name('backend-config.json')
    config=Path(protocol['locations']['config']);identity=bundle['protocol']['backendIdentity'];b=read_json(backend)
    require(identity==b['modelIdentity'] and identity=={'protocol':'rune-score-jsonl-v1',
        'modelSha256':MODEL_SHA,'runnerSha256':RUNNER_SHA},'SUPPLEMENT_BACKEND')
    runner=(REPO/b['runner']).resolve(strict=True);model=(REPO/b['model']).resolve(strict=True)
    require(sha(runner)==RUNNER_SHA and sha(model)==MODEL_SHA and model.stat().st_size==b['modelBytes'],'SUPPLEMENT_BACKEND_FILES')
    return {'schemaVersion':1,'scope':SUPPLEMENT_SCOPE,'prepared':str(directory),'freezeDirectory':str(Path(freeze_directory).resolve()),
        'preparedProtocolSha256':protocol['protocolSha256'],
        'preparedCompleteSha256':sha(directory/'prepare-complete.json'),
        'files':{str(p.resolve()):sha(p) for p in (directory/'protocol.json',directory/'prepare-complete.json',
            directory/'unscored-request-receipt.json',backend,config,runner,model)},
        'backendIdentity':identity,'runner':str(runner),'model':str(model),'modelBytes':b['modelBytes'],
        'policy':bundle['protocol']['policy'],'configSha256':bundle['config']['configSha256'],
        'requests':requests,'requestsSha256':digest(requests),
        'splitCounts':dict(Counter(r['split'] for r in requests)),
        'order':'calibration-complete-before-holdout-stage','thresholdSearch':False,
        'corpusRevealed':True,'nativeCallsAtFreeze':0}


def freeze_supplement(args):
    context=load_prepared(args.prepared)
    value=supplement_document(*context,args.output)
    out=fresh_output(args.output)
    write_json(out/'freeze.json',{**value,'freezeSha256':digest(value)})
    print(json.dumps({'supplementFreeze':str(out),'requests':len(value['requests']),'splitCounts':value['splitCounts']}))


def load_supplement_freeze(directory,context=None):
    path=Path(directory).resolve(strict=True)/'freeze.json';frozen=read_json(path)
    require(frozen.get('scope')==SUPPLEMENT_SCOPE and frozen.get('schemaVersion')==1,'SUPPLEMENT_SCOPE')
    content={k:v for k,v in frozen.items() if k!='freezeSha256'}
    require(digest(content)==frozen.get('freezeSha256'),'SUPPLEMENT_FREEZE_HASH')
    context=context or load_prepared(frozen['prepared'])
    require(canonical(content)==canonical(supplement_document(*context,directory)),'SUPPLEMENT_FREEZE_REPLAY')
    verify_files(frozen['files'])
    return frozen,context


def supplement_run_artifacts(frozen,freeze_directory,run,split,calibration):
    require(split in ('calibration','holdout'),'SUPPLEMENT_SPLIT')
    require(run==Path(frozen['freezeDirectory'])/split and
            Path(freeze_directory).resolve()==Path(frozen['freezeDirectory']),'SUPPLEMENT_RUN_SLOT')
    calibration_complete=None
    if split=='calibration':require(calibration is None,'SUPPLEMENT_CALIBRATION_PARENT')
    else:
        require(calibration is not None,'SUPPLEMENT_CALIBRATION_REQUIRED')
        calibration=Path(calibration).resolve(strict=True)
        load_completed_supplement(frozen,freeze_directory,calibration,'calibration')
        calibration_complete=sha(calibration/'complete.json')
    requests=[{k:r[k] for k in ('id','prefix','candidates')} for r in frozen['requests'] if r['split']==split]
    identity={'backendIdentity':frozen['backendIdentity'],'runner':frozen['runner'],'model':frozen['model'],
              'modelBytes':frozen['modelBytes']}
    command={'argv':[frozen['runner'],frozen['model']],'cwd':str(REPO),
        'stdin':str(run/'requests.jsonl'),'stdout':str(run/'responses.jsonl'),'stderr':str(run/'stderr.log')}
    receipt={'schemaVersion':1,'scope':SUPPLEMENT_SCOPE,'split':split,
        'freezeDirectory':str(Path(freeze_directory).resolve()),'freezeSha256':frozen['freezeSha256'],
        'freezeFileSha256':sha(Path(freeze_directory)/'freeze.json'),
        'preparedCompleteSha256':frozen['preparedCompleteSha256'],'backendIdentity':frozen['backendIdentity'],
        'policy':frozen['policy'],'configSha256':frozen['configSha256'],
        'requests':len(requests),'calibrationDirectory':str(calibration) if calibration else None,
        'calibrationCompleteSha256':calibration_complete,
        'files':{name:sha(run/name) for name in ('requests.jsonl','identity.json','command.json') if (run/name).is_file()}}
    return requests,identity,command,receipt


def stage_supplement(args):
    freeze_directory=Path(args.freeze).resolve(strict=True);frozen,_=load_supplement_freeze(freeze_directory)
    run=Path(args.output).resolve()
    requests,identity,command,_=supplement_run_artifacts(frozen,freeze_directory,run,args.split,args.calibration)
    run=fresh_output(run)
    write_jsonl(run/'requests.jsonl',requests);write_json(run/'identity.json',identity);write_json(run/'command.json',command)
    _,_,_,receipt=supplement_run_artifacts(frozen,freeze_directory,run,args.split,args.calibration)
    write_json(run/'run-input.json',receipt)
    print(json.dumps({'staged':str(run),'split':args.split,'requests':len(requests),'nativeCalls':0}))


def inspect_supplement_run(frozen,freeze_directory,run,split,calibration=None):
    run=Path(run).resolve(strict=True)
    requests,identity,command,expected=supplement_run_artifacts(frozen,freeze_directory,run,split,calibration)
    require(canonical(read_json(run/'run-input.json'))==canonical(expected),'SUPPLEMENT_RUN_RECEIPT')
    require(read_jsonl(run/'requests.jsonl')==requests and read_json(run/'identity.json')==identity
            and read_json(run/'command.json')==command,'SUPPLEMENT_RUN_ARTIFACTS')
    execution={'schemaVersion':1,'attempts':1,'exitCode':0,
        'commandSha256':sha(run/'command.json'),'runInputSha256':sha(run/'run-input.json'),
        'requestsSha256':sha(run/'requests.jsonl'),'responsesSha256':sha(run/'responses.jsonl'),
        'stderrSha256':sha(run/'stderr.log')}
    require(canonical(read_json(run/'execution.json'))==canonical(execution),'SUPPLEMENT_EXECUTION')
    selected=[r for r in frozen['requests'] if r['split']==split]
    responses=read_jsonl(run/'responses.jsonl');admitted=validate_supplement_responses(selected,responses)
    completion={'schemaVersion':1,'scope':SUPPLEMENT_SCOPE,'split':split,'requests':len(selected),
        'responses':len(responses),'freezeSha256':frozen['freezeSha256'],
        'calibrationCompleteSha256':expected['calibrationCompleteSha256'],
        'errorIds':[r['id'] for r in responses if 'error' in r],
        'unrepresentableIds':[r['id'] for r,b in zip(selected,admitted) if b['status']=='UNREPRESENTABLE_REPLY'],
        'files':{name:sha(run/name) for name in ('run-input.json','requests.jsonl','identity.json',
            'command.json','execution.json','responses.jsonl','stderr.log')}}
    return completion,{r['id']:{**b,'request':r,'provenance':{'kind':'supplement','split':split,
        'directory':str(run),'freezeSha256':frozen['freezeSha256'],
        'responseFileSha256':sha(run/'responses.jsonl')}} for r,b in zip(selected,admitted)}


def complete_supplement(args):
    frozen,_=load_supplement_freeze(args.freeze);run=Path(args.run).resolve(strict=True)
    require(not (run/'complete.json').exists(),'SUPPLEMENT_ALREADY_COMPLETE')
    receipt=read_json(run/'run-input.json')
    completion,_=inspect_supplement_run(frozen,args.freeze,run,receipt['split'],receipt['calibrationDirectory'])
    write_json(run/'complete.json',completion)
    print(json.dumps({'admitted':str(run),'responses':completion['responses'],'errors':len(completion['errorIds']),
                      'unrepresentable':len(completion['unrepresentableIds']),'numericDelivery':False}))


def load_completed_supplement(frozen,freeze_directory,run,split,calibration=None):
    completion,admitted=inspect_supplement_run(frozen,freeze_directory,run,split,calibration)
    require(canonical(read_json(Path(run)/'complete.json'))==canonical(completion),'SUPPLEMENT_COMPLETION')
    for b in admitted.values():b['provenance']['completeSha256']=sha(Path(run)/'complete.json')
    return completion,admitted


def load_supplements(freeze_directory,calibration,holdout,context):
    frozen,_=load_supplement_freeze(freeze_directory,context)
    _,cal=load_completed_supplement(frozen,freeze_directory,calibration,'calibration')
    _,hold=load_completed_supplement(frozen,freeze_directory,holdout,'holdout',calibration)
    require(not set(cal)&set(hold),'SUPPLEMENT_DUPLICATE_IDS')
    return {**cal,**hold}


def make_response_bindings(bundle,prior,supplied=None):
    supplied=supplied or {};used=set();bindings=[]
    for source,old,r in zip(bundle['rows'],bundle['records'],prior):
        q=r['modelRequest'] if r['routing']=='CONTEXTUAL_REQUEST' else None
        b=admit_response(q,old,bundle['scores'][source['split']].get(source['id']))
        provenance={'kind':'original-v5-cache','split':source['split'],
            'responseFileSha256':bundle['complete'][source['split']]['scoresSha256']} if b['response'] is not None else None
        if source['id'] in supplied:
            require(b['status'] in ('PAYLOAD_MISMATCH','NEW_CONTEXTUAL_REQUEST'),'SUPPLEMENT_ROUTE')
            value=supplied[source['id']];expected={'id':source['id'],'split':source['split'],'language':source['language'],
                'prefix':q['prefix'],'candidateIds':q['candidateIds'],'candidates':q['continuations']}
            require(value['request']==expected,'SUPPLEMENT_LIVE_PAYLOAD')
            b={'status':value['status'],'response':value['response']};provenance=value['provenance'];used.add(source['id'])
        bindings.append({'id':source['id'],'request':q,**b,'provenance':provenance})
    require(used==set(supplied),'SUPPLEMENT_UNUSED_IDS')
    return bindings


def supplement_locations(args):
    values=[getattr(args,key,None) for key in ('supplement_freeze','supplement_calibration','supplement_holdout')]
    require(not any(values) or all(values),'SUPPLEMENT_ALL_SPLITS_REQUIRED')
    return dict(zip(('freeze','calibration','holdout'),[str(Path(v).resolve(strict=True)) for v in values])) if all(values) else None


def supplied_for_locations(locations,context):
    return load_supplements(locations['freeze'],locations['calibration'],locations['holdout'],context) if locations else {}


def response_tsv(bindings):
    enc=lambda s:base64.b64encode(s.encode()).decode()
    lines=[]
    for i,b in enumerate(bindings):
        q=b['request'];r=b['response'];scores=r.get('scores') if r else None
        error=r.get('error') if r else None
        lines.append('\t'.join([str(i),enc(b['id']),b['status'],enc(q['prefix']) if q else '-',
            ','.join(map(str,q['candidateIds'])) if q else '-',','.join(enc(v) for v in q['continuations']) if q else '-',
            error or '-',str(ERROR_MAP[error]) if error in ERROR_MAP else '-',
            repr(r['durationMillis']) if r and 'durationMillis' in r else '-',
            ','.join(f"{s['id']}:{repr(s['sumLogProbability'])}:{s['scoredTokenCount']}" for s in scores) if scores else '-'])+'\n')
    return ''.join(lines)


def joined_rows(bundle,actual,bindings):
    values=[]
    engine_decisions={}
    for split in ('calibration','holdout'):
        records=[r for r in bundle['records'] if r['split']==split]
        engine_decisions.update(zip([r['id'] for r in records],cq.decisions(records,bundle['scores'][split])))
    for source,old,r,b in zip(bundle['rows'],bundle['records'],actual,bindings):
        unknown=b['status'] in UNRESOLVED or r['harnessError'] is not None
        decision=None if unknown else r['decisionId'] or 0
        success=r['tapResult']=='HANDLED'
        values.append({**r,'split':source['split'],'observedBoundary':source['observedBoundary'],
            'sourceSelectionHash':source['selectionHash'],'source':source['source'],
            'bindingStatus':b['status'],'responseEvidence':b['response'],'responseProvenance':b['provenance'],
            'engineExcluded':not old['variants'],'engineDecisionId':engine_decisions[source['id']],
            'engineResponsePresent':source['id'] in bundle['scores'][source['split']],
            'engineResponseError':bundle['scores'][source['split']].get(source['id'],{}).get('error'),
            'engineResponseSha256':digest(bundle['scores'][source['split']][source['id']]) if source['id'] in bundle['scores'][source['split']] else None,
            'actualInputSha256':digest({'input':r['inputExpected'],'steps':r['inputSteps']}),
            'responseSha256':digest(b['response']) if b['response'] else None,
            'decisionId':decision,'tapSuccess':success,'deliveredDecisionId':None if unknown else decision if success else 0,
            'forbiddenEdits':int(r['tapAttempted'] and not r['allowedTapChange'])+int(r['duplicateEdits']!=0 or
                r['tapAttempted'] and r['duplicateResult']!='REJECTED'),
            'unsolicitedEdits':int(r['responseEdited'])})
    return values


def report_rows(rows):
    return {'schemaVersion':1,'scope':SCOPE,'qualityGateEstablished':False,'semanticCorrectnessEvaluated':False,
        'thresholdsFittedOnHoldout':False,'unseenGeneralization':False,'realInputConnection':False,
        'physicalAvailabilityMeasured':False,'nativeCalls':0,'all':build_metrics(rows),
        'splits':{s:{l:{**build_metrics([r for r in rows if r['split']==s and r['language']==l]),
            'byObservedBoundary':{('space','comma','colon','period')[i]:build_metrics([r for r in rows if r['split']==s and r['language']==l
                and r['observedBoundary']==b]) for i,b in enumerate((' ', ', ', ': ', '. '))}}
            for l in ('en','ru','es')} for s in ('calibration','holdout')}}


def replay(args):
    directory,protocol,bundle,prior=load_prepared(args.prepared)
    out=fresh_output(args.output)
    locations=supplement_locations(args)
    bindings=make_response_bindings(bundle,prior,supplied_for_locations(locations,(directory,protocol,bundle,prior)))
    write_jsonl(out/'response-bindings.jsonl',bindings)
    (out/'responses.tsv').write_text(response_tsv(bindings),encoding='ascii')
    command=read_json(directory/'commands.json')['run']
    actual=run_host(command,out,'actual.jsonl',['replay',directory/'inputs.tsv',ASSETS,out/'responses.tsv'])
    validate_envelopes(actual,bundle['rows']);validate_host_records(actual)
    observed_keys=['inputExpected','inputChanged','inputSteps','beforeCandidates','fullGeneration','requestGeneration',
                   'candidatesAccepted','routing','secondaryReasons','gateFacts','modelRequest','requestCount','harnessError']
    require(all(all(a[k]==p[k] for k in observed_keys) for a,p in zip(actual,prior)),'ACTUAL_REQUEST_REPLAY')
    rows=joined_rows(bundle,actual,bindings);write_jsonl(out/'row-evidence.jsonl',rows)
    write_jsonl(out/'unscored-requests.jsonl',[b for b in bindings if b['status'] in UNSCORED])
    report=report_rows(rows);write_json(out/'report.json',report)
    verify_files(protocol['files'])
    receipt={'schemaVersion':1,'scope':SCOPE,'phase':'replay','prepared':str(directory),
        'preparedCompleteSha256':sha(directory/'prepare-complete.json'),'supplement':locations,
        'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'attributionComplete':report['all']['attributionComplete']}
    write_json(out/'provenance.json',receipt)
    write_json(out/('complete.json' if receipt['attributionComplete'] else 'incomplete.json'),
               {'provenanceSha256':sha(out/'provenance.json'),'attributionComplete':receipt['attributionComplete']})
    print(json.dumps({'rows':len(rows),'attributionComplete':receipt['attributionComplete'],'nativeCalls':0}))


def verify(args):
    directory,protocol,bundle,prior=load_prepared(args.prepared)
    out=Path(args.replay).resolve(strict=True);receipt=read_json(out/'provenance.json')
    require(receipt['scope']==SCOPE and receipt['phase']=='replay' and receipt['prepared']==str(directory)
            and receipt['preparedCompleteSha256']==sha(directory/'prepare-complete.json'),'REPLAY_BINDING')
    for name,h in receipt['files'].items():require(Path(name).name==name and sha(out/name)==h,'REPLAY_FILE_DRIFT')
    bindings=make_response_bindings(bundle,prior,supplied_for_locations(receipt['supplement'],(directory,protocol,bundle,prior)))
    require(bindings==read_jsonl(out/'response-bindings.jsonl') and response_tsv(bindings)==(out/'responses.tsv').read_text(),'RESPONSE_BINDING_REPLAY')
    actual=read_jsonl(out/'actual.jsonl');validate_envelopes(actual,bundle['rows']);validate_host_records(actual)
    rows=joined_rows(bundle,actual,bindings)
    require(rows==read_jsonl(out/'row-evidence.jsonl') and report_rows(rows)==read_json(out/'report.json'),'REPORT_REPLAY')
    require(receipt['attributionComplete']==build_metrics(rows)['attributionComplete'],'COMPLETION_VERDICT')
    marker=out/('complete.json' if receipt['attributionComplete'] else 'incomplete.json')
    require(read_json(marker)=={'provenanceSha256':sha(out/'provenance.json'),'attributionComplete':receipt['attributionComplete']} and
            not (out/('incomplete.json' if receipt['attributionComplete'] else 'complete.json')).exists(),'COMPLETION_MARKER')
    verify_current_host(directory,protocol,out,prior,actual)
    print('Verified full contextual attribution bindings and all row denominators; no inference.')


def verify_current_host(directory,protocol,out,prior,actual):
    # Self-consistent receipt/JAR rehashing cannot substitute a different controller.
    # Recompile the current bound closure, then require both row ledgers to match it.
    runtime=protocol['runtime'];java=Path(runtime['java']);android=Path(runtime['androidJar'])
    verify_files(protocol['files'])
    sources,jars,version=compile_inputs(java,runtime['gradleCache'],android)
    with tempfile.TemporaryDirectory(prefix='contextual-controller-verify-',dir=REPO/'build') as temporary:
        work=Path(temporary)
        try:
            command=compile_host(work,java,android,sources,jars,version)
            for phase,expected,arguments in [('prepare',prior,['prepare',directory/'inputs.tsv',ASSETS]),
                                            ('replay',actual,['replay',directory/'inputs.tsv',ASSETS,out/'responses.tsv'])]:
                result=run_host(command,work,phase+'.jsonl',arguments)
                require(result==expected,'HOST_'+phase.upper()+'_REPLAY')
            verify_files(protocol['files'])
        except Exception as e:
            write_json(work/'failure.json',{'errorType':type(e).__name__,
                'errorCode':str(e) if re.fullmatch('[A-Z_]+',str(e)) else None})
            work.rename(work.with_name(work.name+'-failed'))
            raise


def validate_host_tests(records):
    require([r.get('case') for r in records]==HOST_CASES and all(set(r)=={'case','passed'} and r['passed'] is True for r in records),
            'HOST_SYNTHETIC_FAILURE')


def test_host(args):
    out=fresh_output(args.output);java=Path(args.java).resolve();android=Path(args.android_jar).resolve()
    sources,jars,version=compile_inputs(java,args.gradle_cache,android)
    files=bind_runtime(java,android,sources,jars);write_json(out/'input-receipt.json',{'files':files,'nativeCalls':0})
    command=compile_host(out,java,android,sources,jars,version)
    actual=run_host(command,out,'synthetic.jsonl',['test'])
    validate_host_tests(actual)
    verify_files(files);write_json(out/'complete.json',{'cases':len(actual),'actualSha256':sha(out/'synthetic.jsonl'),
        'inputReceiptSha256':sha(out/'input-receipt.json'),'nativeCalls':0})
    print(f'Host synthetic cases passed: {len(actual)}; no model calls.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    def host(p):
        for name in ('java','gradle-cache','android-jar','output'):p.add_argument('--'+name,required=True)
    p=sub.add_parser('prepare');host(p)
    for name in ('corpus','export','calibration','holdout','config','protocol'):p.add_argument('--'+name,required=True,type=Path)
    p=sub.add_parser('test-host');host(p)
    p=sub.add_parser('replay');p.add_argument('--prepared',required=True);p.add_argument('--output',required=True)
    for name in ('supplement-freeze','supplement-calibration','supplement-holdout'):p.add_argument('--'+name)
    p=sub.add_parser('supplement-freeze');p.add_argument('--prepared',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('supplement-stage');p.add_argument('--freeze',required=True);p.add_argument('--split',required=True,choices=('calibration','holdout'));p.add_argument('--output',required=True);p.add_argument('--calibration')
    p=sub.add_parser('supplement-complete');p.add_argument('--freeze',required=True);p.add_argument('--run',required=True)
    p=sub.add_parser('verify');p.add_argument('--prepared',required=True);p.add_argument('--replay',required=True)
    args=parser.parse_args()
    try:{'prepare':prepare,'test-host':test_host,'replay':replay,'verify':verify,'supplement-freeze':freeze_supplement,'supplement-stage':stage_supplement,'supplement-complete':complete_supplement}[args.command](args)
    except Exception as e:
        print('CONTEXTUAL_ATTRIBUTION_FAILED:'+type(e).__name__+(':'+str(e) if re.fullmatch('[A-Z_]+',str(e)) else ''),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
