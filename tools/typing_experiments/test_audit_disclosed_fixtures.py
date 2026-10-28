import json
from unittest.mock import patch
import unittest

import audit_disclosed_fixtures as audit
from holdout_ledger import keys_for


class DisclosedFixturesTest(unittest.TestCase):
    def setUp(self):
        directory = audit.ROOT / audit.FIXTURES
        self.rows = [json.loads(s) for s in (directory / next(iter(audit.PINS))).read_text().splitlines()]
        self.document = json.loads((directory / 'conversation_supervised_false_proposals_20261026.json').read_text())

    def registry(self):
        rows = [r | dict(sourceRepository='tatoeba') for r in self.rows]
        keys = {axis: sorted(keys_for(rows, axis)) for axis in ('article', 'sentence', 'context')}
        cases = [dict(sourceRepository='tatoeba', language='ru', article=c['sourceSentence'])
                 for c in self.document['cases']]
        keys['article'] = sorted(set(keys['article']) | keys_for(cases, 'article'))
        return dict(entries=[dict(keys=keys)])

    def test_retained_schema_and_both_fixture_sets_are_covered(self):
        audit.validate_fixtures(self.rows, self.document)
        coverage = audit.require_registry_coverage(self.rows, self.document, self.registry())
        self.assertEqual(5, coverage['detailed_article'])
        self.assertGreater(coverage['cc0_context'], 0)

    def test_duplicate_regression_identity_is_rejected(self):
        self.rows[-1]['id'] = self.rows[0]['id']
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_ROW_IDENTITY'):
            audit.validate_fixtures(self.rows, self.document)

    def test_regression_cannot_be_relabeled_as_training(self):
        self.rows[0]['purpose'] = 'TRAINING'
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_REGRESSION_ROLE'):
            audit.validate_fixtures(self.rows, self.document)

    def test_changed_raw_winner_cannot_be_a_recorded_regression(self):
        self.rows[0]['rejectedRawWinner'] = self.rows[0]['expectedSpelling']
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_REGRESSION_ROLE'):
            audit.validate_fixtures(self.rows, self.document)

    def test_added_sentence_context_is_rejected_from_minimized_five_case_schema(self):
        self.document['cases'][0]['prefix'] = 'unexpected context'
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_CASE_SCHEMA_OR_ATTRIBUTION'):
            audit.validate_fixtures(self.rows, self.document)

    def test_attribution_url_must_identify_the_declared_source_sentence(self):
        self.document['cases'][0]['sourceSentenceUrl'] = 'https://example.invalid/'
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_CASE_SCHEMA_OR_ATTRIBUTION'):
            audit.validate_fixtures(self.rows, self.document)

    def test_missing_contributor_is_rejected(self):
        self.document['cases'][0]['sourceContributor'] = ''
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_CASE_SCHEMA_OR_ATTRIBUTION'):
            audit.validate_fixtures(self.rows, self.document)

    def test_context_exclusion_cannot_be_omitted(self):
        registry = self.registry()
        registry['entries'][0]['keys']['context'] = []
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_REGISTRY_GAP context'):
            audit.require_registry_coverage(self.rows, self.document, registry)

    def test_five_case_sentence_exclusions_are_required_separately(self):
        registry = self.registry()
        registry['entries'][0]['keys']['article'] = sorted(keys_for(
            [r | dict(sourceRepository='tatoeba') for r in self.rows], 'article'))
        with self.assertRaisesRegex(ValueError, 'DISCLOSED_REGISTRY_GAP detailed_article'):
            audit.require_registry_coverage(self.rows, self.document, registry)

    def test_real_registry_pass_does_not_claim_model_or_source_execution(self):
        report = audit.audit()
        self.assertFalse(report['historicalSourcesVerified'])
        self.assertFalse(report['modelExecutionEstablished'])
        self.assertFalse(report['freshQualificationEstablished'])
        self.assertFalse(report['canonicalFamilyCoverageEstablished'])

    def test_byte_drift_fails_before_source_or_model_work(self):
        with patch.object(audit, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'DISCLOSED_FIXTURE_BYTES'):
                audit.audit()


if __name__ == '__main__':
    unittest.main()
