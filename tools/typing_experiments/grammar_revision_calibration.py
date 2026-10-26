"""Measure learned revisions relative to the installed result, not older gains.

The metric unit is a change to an existing replacement. Its stage input is the
previous word; the actual editor original is retained separately for auditing.
Eligibility and source admission must be established before calling this code.
"""
from contextual_policy_calibration import proposal_metrics, select_policy


REFERENCE_POLICY = dict(minimumScore=0.0, minimumMargin=0.01)


def stage_records(revisions):
    result = []
    for row in revisions:
        if (any(not isinstance(row.get(k), str) or not row[k]
                for k in ('original', 'previous', 'proposed'))
                or row['previous'] == row['original'] or row['proposed'] == row['original']
                or row['proposed'] == row['previous']):
            raise ValueError('REVISION_STAGE_SCHEMA')
        result.append(dict(id=row['id'], typed=row['previous'], baseline=row['previous'],
                           editorOriginal=row['original'], expected=row['expected'], control=row['control'],
                           reference=dict(candidate=row['previous'], score=0.0, margin=1.0),
                           experimental=dict(candidate=row['proposed'], score=row['score'], margin=row['margin'])))
    return result


def select_revision_policy(revisions, *, required_precision, minimum_correct=100, grid_points=33):
    return select_policy(stage_records(revisions), REFERENCE_POLICY, required_precision=required_precision,
                         minimum_new_correct=minimum_correct, grid_points=grid_points)


def revision_metrics(revisions, policy):
    return proposal_metrics(stage_records(revisions), policy, REFERENCE_POLICY)
