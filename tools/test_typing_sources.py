import shutil
import tempfile
import unittest
from pathlib import Path

import check_typing_sources as gate


class TypingSourceDocumentationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in set(gate.ENUMS.values()) | {gate.CONTROLLER, gate.PERSONAL, gate.RECOVERY, 'docs/ARCHITECTURE.md'}:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(gate.ROOT / name, p)

    def change(self, path, before, after):
        p = self.root / path
        value = p.read_text()
        self.assertIn(before, value)
        p.write_text(value.replace(before, after, 1))

    def test_current_source_contract(self):
        self.assertEqual([], gate.inspect(self.root))

    def test_other_namespace_cannot_cover_missing_spelling_row(self):
        self.change('docs/ARCHITECTURE.md', '| `MODEL` | Калиброванная', '| `REPLACED` | Калиброванная')
        self.assertIn('SOURCE_NAMESPACE_TABLE SpellingSource', gate.inspect(self.root))

    def test_new_diagnostic_source_requires_a_row(self):
        self.change(gate.ENUMS['DiagnosticSource'], 'enum class DiagnosticSource {',
                    'enum class DiagnosticSource { NEW_SOURCE,')
        self.assertIn('SOURCE_NAMESPACE_TABLE DiagnosticSource', gate.inspect(self.root))

    def test_baseline_branch_change_is_not_documentation_parity(self):
        self.change(gate.CONTROLLER, 'commonId > 0 -> CalibratedRanking',
                    'compactWinner != null -> CalibratedRanking')
        self.assertIn('UNREADABLE_OR_UNREVIEWED_SOURCE_CONTRACT', gate.inspect(self.root))

    def test_reordered_contextual_pipeline_is_rejected(self):
        p = self.root / gate.PERSONAL
        value = p.read_text()
        value = value.replace('ContextualCorrectionPolicy.evaluate(', 'SWAP.evaluate(', 1)
        value = value.replace('InfinitiveRevisionPolicy.evaluate(', 'ContextualCorrectionPolicy.evaluate(', 1)
        value = value.replace('SWAP.evaluate(', 'InfinitiveRevisionPolicy.evaluate(', 1)
        p.write_text(value)
        self.assertIn('SOURCE_BRANCH_ORDER CONTEXTUAL_ORDER', gate.inspect(self.root))

    def test_one_admission_dispatcher_cannot_drift(self):
        self.change(gate.CONTROLLER, 'selection.ranking?.nounCaseRevision == true',
                    'selection.ranking?.grammarRevision == true')
        self.assertIn('SOURCE_BRANCH_ORDER ADMISSION_ORDER/allowsAutomatic', gate.inspect(self.root))

    def test_wrong_status_does_not_advertise_disabled_model_refinement(self):
        self.change(gate.RECOVERY, 'MODEL_QUALIFIED = false', 'MODEL_QUALIFIED = true')
        self.assertIn('MODEL_REFINEMENT_STATUS', gate.inspect(self.root))

    def test_order_marker_is_required(self):
        self.change('docs/ARCHITECTURE.md', 'Q2:LEGACY_ORDER', 'Q2:LEGACY_REMOVED')
        self.assertIn('UNREADABLE_OR_UNREVIEWED_SOURCE_CONTRACT', gate.inspect(self.root))

    def test_missing_source_fails_closed(self):
        (self.root / gate.PERSONAL).unlink()
        self.assertIn('UNREADABLE_OR_UNREVIEWED_SOURCE_CONTRACT', gate.inspect(self.root))


if __name__ == '__main__':
    unittest.main()
