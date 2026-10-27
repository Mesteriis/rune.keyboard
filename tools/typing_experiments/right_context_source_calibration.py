"""Incremental calibration of independently source-certified contextual changes.

Both raw acquisitions and reconsidered replacements are counted relative to the
observed previous text. Existing spelling gains never satisfy the new-gain gate.
"""
from contextual_policy_calibration import proposal_metrics, select_policy

REFERENCE_POLICY = dict(minimumScore=0.0, minimumMargin=0.01)


def source_stage_records(changes):
    records = []
    for row in changes:
        if (any(not isinstance(row.get(key), str) or not row[key]
                for key in ['original', 'previous', 'proposed'])
                or row['proposed'] in {row['previous'], row['original']}
                or row.get('sourceCertified') is not True):
            raise ValueError('CONTEXTUAL_SOURCE_STAGE_SCHEMA')
        records.append(dict(id=row['id'], typed=row['previous'], baseline=row['previous'],
            editorOriginal=row['original'], expected=row['expected'], control=row['control'],
            acquisition=row['original'] == row['previous'],
            reference=dict(candidate=row['previous'], score=0.0, margin=1.0),
            experimental=dict(candidate=row['proposed'], score=row['score'], margin=row['margin'])))
    return records


def select_source_policy(changes, *, required_precision, minimum_correct=100, grid_points=33):
    return select_policy(source_stage_records(changes), REFERENCE_POLICY, required_precision=required_precision,
                         minimum_new_correct=minimum_correct, grid_points=grid_points)


def source_metrics(changes, policy):
    return proposal_metrics(source_stage_records(changes), policy, REFERENCE_POLICY)
