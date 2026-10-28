import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import historical_model_sources as audit


class HistoricalModelSourceTest(unittest.TestCase):
    def test_complete_project_source_index_verifies_without_historical_build(self):
        result = audit.audit()
        self.assertEqual(71, result['sourceVersions'])
        self.assertEqual(29, result['archivedGitSources'])
        self.assertEqual(2, result['exports'])
        self.assertFalse(result['originalReceiptsVerified'])
        self.assertFalse(result['externalRuntimeIdentityEstablished'])
        self.assertFalse(result['candidateGenerationReproduced'])
        self.assertEqual(0, result['modelCalls'])

    def test_changed_archived_source_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            shutil.copytree(audit.DATA, data)
            manifest = json.loads((data / 'manifest.json').read_text())
            record = next(r for r in manifest['sources'] if r['origin'] == 'archived-git')
            (data / record['file']).write_bytes(b'# tampered\n')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_SOURCE_IDENTITY'):
                audit.audit(data=data)

    def test_git_object_metadata_cannot_be_a_command_option(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            shutil.copytree(audit.DATA, data)
            path = data / 'manifest.json'
            manifest = json.loads(path.read_text())
            record = next(r for r in manifest['sources'] if r['origin'] == 'archived-git')
            record['gitObject'] = '--filters'
            path.write_text(json.dumps(manifest))
            with patch.object(audit.subprocess, 'check_output', side_effect=AssertionError('must reject before Git')), \
                 self.assertRaisesRegex(ValueError, 'HISTORICAL_GIT_OBJECT'):
                audit.audit(data=data, verify_git=True)

    def test_unknown_export_source_reference_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            shutil.copytree(audit.DATA, data)
            path = data / 'manifest.json'
            manifest = json.loads(path.read_text())
            export = next(iter(manifest['exports'].values()))
            name = next(iter(export['sources']))
            export['sources'][name] = '0' * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_EXPORT_REFERENCE'):
                audit.audit(data=data)

    def test_all_word_corpus_articles_remain_excluded(self):
        from holdout_ledger import assert_disjoint
        ledger = audit.load_ledger(audit.ROOT / 'tools/typing_experiments/holdout-ledger.json')
        entry = audit.word_entry()
        self.assertEqual(4920, entry['sourceArticleCount'])
        self.assertEqual(9000, entry['rowCount'])
        self.assertEqual(['family', 'sentence', 'context'], entry['missingAxes'])
        source = json.loads((audit.DATA / 'word-data-manifest.json').read_text())
        articles = {a for part in source['partitions'].values() for a in part['articles']}
        self.assertEqual(set(entry['keys']['article']), audit.keys_for([{'article': a} for a in articles], 'article'))
        with self.assertRaisesRegex(ValueError, 'LEDGER_OVERLAP:article'):
            assert_disjoint([{'article': next(iter(articles))}], ledger, kinds=('article',), require_complete=False)
        changed = copy.deepcopy(ledger)
        changed['entries'] = [e for e in changed['entries'] if e['id'] != audit.ENTRY]
        with patch.object(audit, 'load_ledger', return_value=changed), \
             self.assertRaisesRegex(ValueError, 'HISTORICAL_WORD_EXCLUSION'):
            audit.audit()


if __name__ == '__main__':
    unittest.main()
