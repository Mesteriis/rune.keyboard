import unittest

import phrase_boundary_sources as subject


class PhraseBoundarySourcesTest(unittest.TestCase):
    def test_counts_preservation_final_application_only(self):
        cases = [({'id': 'one', 'label': 'preserve'}, 'x y')]
        observations = [{'id': 'one', 'phraseStages': [
            {'automaticEdit': True, 'boundaryDiagnostics': [{'reason': 'AUTO_REPLACE', 'source': 'LOCAL_POLICY'}]},
            {'automaticEdit': True, 'boundaryDiagnostics': [{'reason': 'AUTO_REPLACE', 'source': 'JOINT_RESCUE'}]},
        ]}]
        self.assertEqual({'JOINT_RESCUE': 1}, subject.summarize(cases, observations))

    def test_missing_duplicate_and_stale_events_are_rejected(self):
        cases = [({'id': 'one', 'label': 'preserve'}, 'x y')]
        for stage in (
            {'automaticEdit': True},
            {'automaticEdit': True, 'boundaryDiagnostics': []},
            {'automaticEdit': True, 'boundaryDiagnostics': [{'reason': 'AUTO_REPLACE', 'source': 'LOCAL_POLICY'}] * 2},
            {'automaticEdit': False, 'boundaryDiagnostics': [{'reason': 'AUTO_REPLACE', 'source': 'LOCAL_POLICY'}]},
        ):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                subject.summarize(cases, [{'id': 'one', 'phraseStages': [stage]}])


if __name__ == '__main__':
    unittest.main()
