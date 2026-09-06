"""One-off retained synthetic production variant parity driver; no corpus/model reads."""
import json
import os
from pathlib import Path
import subprocess
import sys

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'tools/eval/smart-typing-0.3/pipeline'))
import contextual_quality as cq

output=Path(__file__).resolve().parent/'adapter-variant-parity'
assert not output.exists()
java=Path('/opt/homebrew/opt/openjdk@17/bin/java').resolve(strict=True)
jars=cq.toolchain(Path('/Users/avm/.gradle/caches/modules-2/files-2.1'))
sources=(cq.LANGUAGE,cq.ENGINE,cq.HARNESS,cq.POLICY)
source_hashes={str(path.relative_to(REPO)):cq.shared.sha(path) for path in sources}
binding=cq.policy_binding();corpus_binding=cq.v5_binding()
rows=[];eligible=[]
for language,left,word in (('en','ordinary fixture','word'),('ru','обычный пример','слово'),('es','otro ejemplo','palabra')):
    for number,(prefix,allowed) in enumerate(((left,True),(left+' 2011',False),(left+' NASA',False),(left+' Café',True))):
        rows.append({'id':f'synthetic-{language}-{number}','corpusVersion':5,'labelSemantics':cq.V5_LABEL,
            'language':language,'split':'holdout','task':'punctuation','prefix':prefix,'currentWord':word,
            'observedBoundary':cq.V5_BOUNDARIES[number],'noAuto':True})
        eligible.append(allowed)
output.mkdir()
(output/'inputs.tsv').write_text(cq.export_inputs(rows),encoding='ascii')
version=subprocess.run([str(java),'-version'],capture_output=True,check=True,timeout=15)
assert b'version "17.' in version.stderr
(output/'java-version.txt').write_bytes(version.stderr)
binary=output/'contextual-export.jar'
compile_command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx512m','-cp',os.pathsep.join(map(str,jars)),
    'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','17',
    '-classpath',os.pathsep.join(map(str,jars[1:3])),'-d',str(binary),*map(str,sources)]
run_command=[str(java),'-XX:ActiveProcessorCount=2','-Xmx512m','-cp',os.pathsep.join(map(str,[binary,*jars[1:3]])),
    'io.github.mesteriis.rune.keyboard.smarttyping.punctuation.ContextualExport',str(output/'inputs.tsv')]
with (output/'compile.log').open('xb') as log:
    subprocess.run(compile_command,stdout=log,stderr=log,check=True,timeout=120)
with (output/'actual.tsv').open('xb') as data,(output/'run.log').open('xb') as log:
    subprocess.run(run_command,stdout=data,stderr=log,check=True,timeout=120)
parsed=cq.parse_output((output/'actual.tsv').read_text(),rows,cq.V5_FORMAT)
assert [bool(row['variants']) for row in parsed]==eligible
assert all(len(row['variants'])==(7 if expected else 0) for row,expected in zip(parsed,eligible))
assert all(not any(key in row for key in ('ambiguous','expectedCandidate')) for row in parsed)
assert cq.records_binding(parsed)==corpus_binding
assert cq.policy_binding()==binding
assert source_hashes=={str(path.relative_to(REPO)):cq.shared.sha(path) for path in sources}
(output/'parsed-synthetic.json').write_text(json.dumps(parsed,ensure_ascii=False,sort_keys=True)+'\n')
files=('inputs.tsv','actual.tsv','parsed-synthetic.json','java-version.txt','contextual-export.jar','compile.log','run.log')
receipt={**binding,**corpus_binding,'scope':'contextual-v5-synthetic-production-export-parity',
    'syntheticOnly':True,'sourceCorpusLoaded':False,'modelScoringPerformed':False,'frozen':False,
    'rows':len(parsed),'eligibleRows':sum(eligible),'productionExcludedRows':len(eligible)-sum(eligible),
    'driverSha256':cq.shared.sha(Path(__file__)),'sources':source_hashes,'java':str(java),'javaSha256':cq.shared.sha(java),
    'jars':{str(path):cq.shared.sha(path) for path in jars},'toolchainManifestSha256':cq.shared.sha(cq.TOOLCHAIN_MANIFEST),
    'compileCommand':compile_command,'runCommand':run_command,'files':{name:cq.shared.sha(output/name) for name in files}}
cq.shared.write_json(output/'verification.json',{**receipt,'receiptSha256':cq.evaluator().digest(receipt)})
print(json.dumps({'rows':len(parsed),'eligibleRows':sum(eligible),'productionExcludedRows':len(eligible)-sum(eligible),
    'syntheticOnly':True,'modelScoringPerformed':False,'receiptSha256':cq.shared.sha(output/'verification.json')},sort_keys=True))
