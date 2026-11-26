"""Exercise the actual versioned registries in an isolated no-build checkout."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools/typing_experiments'
FILES = ('holdout_ledger.py', 'control_ledger.py', 'conversation_split_checks.py',
         'source_identities.py', 'recover_legacy_families.py', 'public_corpus_preparation_v1.py',
         'english_family_keys.py', 'holdout-ledger.json', 'control-ledger.json',
         'ewt_surface_exclusions_v1.py', 'ewt-surface-exclusions-v1.json',
         'import_english_ewt_exposure.py', 'public_sources/ud-ewt-2.18/source-lock.json')


class RegistryWithoutBuildTest(unittest.TestCase):
    def test_real_registries_refuse_overlap_and_incomplete_coverage_without_build(self):
        script = '''
import hashlib, json, pathlib, sys
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from public_corpus_preparation_v1 import prepare, preflight, verify_registry_bindings
assert not (root.parent.parent / 'build').exists()
lex = root / 'holdout-ledger.json'; controls = root / 'control-ledger.json'
def run(name, article):
    row = dict(id=name, language='ru', article=article, families=['цщжцщж'],
               contextHash='0'*64, sourceSegmentHash='f'*64,
               prefix='Уникальный контекст цщжцщж ', typed='цщжцщж', expectedSpelling='цщжцщж')
    rows = root / (name + '.jsonl'); rows.write_text(json.dumps(row, ensure_ascii=False) + '\\n')
    manifest = root / (name + '.manifest.json')
    manifest.write_text(json.dumps(dict(containsPersonalMessages=False, frozenBeforeScoring=True,
        files={rows.name: hashlib.sha256(rows.read_bytes()).hexdigest()})))
    output = root / (name + '-out')
    report = prepare(rows, manifest, output, 'spelling', lex, controls, 'new-families')
    assert not output.exists()
    verify_registry_bindings(report, lex, controls)
    return report
blocked = run('overlap', '8825104')
assert blocked['status'] == 'BLOCKED_OVERLAP' and blocked['lexicalOverlaps']['article'] > 0
unseen = run('unseen', '99999999999999999999')
assert unseen['status'] == 'BLOCKED_COVERAGE', (unseen['status'], unseen['identityErrors'], unseen['lexicalOverlaps'], unseen['controlOverlaps'])
assert not unseen['lexicalCoverageComplete'] and not unseen['controlCoverageComplete']
assert unseen['registryBindings']['schema'] == 'rune-acceptance-registry-bindings-v2'
surface = root / 'ewt-surface-exclusions-v1.json'; original_surface = surface.read_bytes()
surface.write_bytes(original_surface + b' ')
try:
    verify_registry_bindings(unseen, lex, controls)
except ValueError as error:
    assert str(error) == 'EWT_SURFACE_IDENTITY'
else:
    raise AssertionError('modified surface exclusions accepted')
surface.write_bytes(original_surface)
english = dict(id='english-unseen-source', language='en', sourceRepository='tatoeba',
    article='tatoeba:999999999', sentenceHash='f'*64, prefix='we ', typed='went', expectedSpelling='went')
result = preflight([english], 'spelling', json.loads(lex.read_bytes()), json.loads(controls.read_bytes()), 'new-families')
assert result['status'] == 'BLOCKED_OVERLAP' and result['englishSourceSurfaceOverlaps'] == 1
lex.write_bytes(lex.read_bytes() + b' ')
try:
    verify_registry_bindings(unseen, lex, controls)
except ValueError as error:
    assert str(error) == 'ACCEPTANCE_REGISTRY_DRIFT'
else:
    raise AssertionError('modified registry accepted')
assert not (root.parent.parent / 'build').exists()
print(json.dumps({'overlap':blocked['status'], 'unseen':unseen['status'], 'buildAbsent': True}))
'''
        with tempfile.TemporaryDirectory(prefix='rune-no-build-') as folder:
            root = Path(folder); target = root / 'tools' / 'typing_experiments'; target.mkdir(parents=True)
            for name in FILES:
                (target / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(TOOLS / name, target / name)
            driver = target / 'exercise.py'; driver.write_text(script)
            result = subprocess.run([sys.executable, '-I', str(driver)], cwd=root,
                                    text=True, capture_output=True, timeout=120)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({'overlap': 'BLOCKED_OVERLAP', 'unseen': 'BLOCKED_COVERAGE', 'buildAbsent': True},
                             json.loads(result.stdout))
            self.assertFalse((root / 'build').exists())


if __name__ == '__main__': unittest.main()
