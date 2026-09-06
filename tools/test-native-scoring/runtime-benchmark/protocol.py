#!/usr/bin/env python3
"""Numeric-only instrumentation capture, strict validation and descriptive summaries."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

REPEATS = {0: 3, 1: 20}
WIDTH = 18

class Invalid(Exception):
    pass

def need(condition, code):
    if not condition:
        raise Invalid(code)

def parse(text):
    rows = []
    for line in text.splitlines():
        need(bool(re.fullmatch(r'-?[0-9]+(,-?[0-9]+){17}', line)), 'row_syntax')
        row = [int(value) for value in line.split(',')]
        need(all(-(2**63) <= value < 2**63 for value in row), 'row_range')
        rows.append(row)
    need(bool(rows), 'rows_missing')
    return rows

def percentile(values, probability):
    """Nearest-rank quantile; no interpolation and no unsupported confidence claim."""
    need(bool(values), 'empty_metric')
    return sorted(values)[max(0, math.ceil(probability * len(values)) - 1)]

def metric(values, optional=False):
    available = [x for x in values if x >= 0]
    result = {'count': len(values), 'available_count': len(available), 'missing_count': len(values)-len(available)}
    # Any unavailable sample suppresses the aggregate, rather than selecting faster survivors.
    result.update({key: None for key in ('p50', 'p95', 'max')})
    if len(available) == len(values):
        result.update(p50=percentile(values, .5), p95=percentile(values, .95), max=max(values))
    else:
        need(optional, 'required_metric_unavailable')
    return result

def expected_visits(rounds):
    return [(1 if rounds == 1 else 2, (slot + 4*iteration) % 9, iteration)
            for iteration in range(rounds) for slot in range(9)]

def validate(rows, proof):
    need(proof.get('schema') == 1 and proof.get('build') in (0, 1), 'proof_invalid')
    need(proof['build'] == 0 or proof.get('matched_release') == 1, 'release_proof_missing')
    need(rows[0][1] == 0 and rows[-1][1] == 6, 'bookends_missing')
    profile = rows[0][2]
    need(profile in REPEATS, 'profile_invalid')
    for seq, row in enumerate(rows):
        need(len(row) == WIDTH and row[0] == 1 and row[2] == profile and row[3] == seq, 'identity_invalid')
        need(row[1] in range(9) and row[1] != 7, 'failure_record')
        if row[1] != 8:
            need(row[7] >= 0 and row[8] >= 0 and row[9] >= 0 and row[10] >= 0 and row[11] >= -1, 'metric_invalid')
            need(all(x >= -1 for x in row[12:16]), 'memory_invalid')
    need(rows[0][16] >= 26 and rows[0][17] == proof['build'], 'platform_invalid')
    expected = [(0,-1,-1), (8,0,-1), (8,1,-1), (3,0,-1), (3,1,-1)]
    expected += expected_visits(1)
    expected += expected_visits(REPEATS[profile])
    expected += [(4,i,-1) for i in range(3)]
    expected += [(5,0,-1), (3,2,-1), (3,3,-1), (6,-1,-1)]
    need([(r[1],r[4],r[5]) for r in rows] == expected, 'schedule_invalid')
    native = proof.get('native', [])
    need(len(native) == 2 and [x.get('id') for x in native] == [0,1], 'native_proof_invalid')
    for row, record in zip(rows[1:3], native):
        need(len(record.get('sha256', [])) == 8 and all(0 <= x < 2**32 for x in row[8:16]), 'hash_invalid')
        need(row[8:16] == record['sha256'], 'native_hash_mismatch')
    for row in rows:
        kind = row[1]
        if kind in (1,2,5):
            count = (2,4,8)[row[4] % 3]
            need(row[6] == 0 and row[10] == count and count <= row[9] <= count*255 and row[11] >= 0, 'score_invalid')
            need(row[16:18] == [0,0], 'score_aux_invalid')
        elif kind == 4:
            need(row[6] in (1,2) and row[16] >= -1 and row[17] >= 10_000_000, 'cancel_invalid')
            if row[6] == 1:
                need(row[9:12] == [0,0,-1] and row[16] >= 0, 'cancelled_metrics_invalid')
            else:
                need(row[10] == 8 and 8 <= row[9] <= 2040 and row[11] >= 0, 'race_metrics_invalid')
        else:
            need(row[6] == 0, 'outcome_invalid')
            if kind != 8:
                need(row[9:11] == [0,0], 'nonrequest_scores')
                need(kind != 3 or row[4] != 1 or row[11] >= 0, 'load_metric_missing')
    return profile

def summarize(rows, proof):
    profile = validate(rows, proof)
    def metrics(group):
        return {name: metric([r[column] for r in group], optional)
                for name,column,optional in [('wall_ns',7,False), ('process_cpu_ms',8,False),
                    ('native_duration_ms',11,True), ('pss_bytes',12,True), ('rss_bytes',13,True),
                    ('native_heap_bytes',14,True), ('java_heap_used_bytes',15,True)]}
    cells=[]
    for config in range(9):
        group=[r for r in rows if r[1] == 2 and r[4] == config]
        cells.append({'config':config, 'language':config//3, 'candidates':(2,4,8)[config%3],
                      'request_count':len(group), 'scored_candidates':sum(r[10] for r in group),
                      'scored_tokens':sum(r[9] for r in group), 'metrics':metrics(group)})
    cancels=[r for r in rows if r[1] == 4]
    return {'schema':1, 'profile':profile, 'sdk':rows[0][16], 'build':proof['build'],
            'matched_release':proof.get('matched_release',0), 'measured_requests':REPEATS[profile]*9,
            'warmup_requests':9, 'measured_cells':cells,
            'lifecycle':[{'operation':r[4], 'metrics':metrics([r])} for r in rows if r[1] == 3],
            'cancellation':{'attempts':3, 'cancelled':sum(r[6]==1 for r in cancels),
                'completion_races':sum(r[6]==2 for r in cancels),
                'completed_before_signal':sum(r[16]==-1 for r in cancels),
                'signal_to_end_ns':metric([r[16] for r in cancels],True), 'metrics':metrics(cancels)},
            'recovery_requests':1, 'total_wall_ns':rows[-1][7], 'total_process_cpu_ms':rows[-1][8]}

def capture(stream):
    numeric=[]; ok=False; finished=False; failed=False
    for line in stream:
        line=line.rstrip('\r\n')
        prefix='INSTRUMENTATION_STATUS: rune_bench='
        if line.startswith(prefix):
            payload=line[len(prefix):]
            parse(payload)  # Reject malformed records without reflecting their contents.
            numeric.append(payload)
        elif line == 'OK (1 test)': ok=True
        elif line == 'INSTRUMENTATION_CODE: -1': finished=True
        elif 'FAILURES!!!' in line or line.startswith(('INSTRUMENTATION_FAILED:', 'INSTRUMENTATION_RESULT: shortMsg=')): failed=True
    need(ok and finished and not failed, 'instrumentation_incomplete')
    return '\n'.join(numeric)+'\n'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode', choices=['collect','summary'])
    parser.add_argument('--proof',required=True, type=Path)
    parser.add_argument('--rows',required=True, type=Path)
    parser.add_argument('--summary',required=True, type=Path)
    args=parser.parse_args()
    try:
        need(not args.summary.exists() and not args.summary.is_symlink(), 'output_exists')
        if args.mode == 'collect': need(not args.rows.exists() and not args.rows.is_symlink(), 'output_exists')
        proof=json.loads(args.proof.read_text())
        text=capture(sys.stdin) if args.mode == 'collect' else args.rows.read_text()
        rows=parse(text); result=summarize(rows,proof)
        if args.mode == 'collect':
            with args.rows.open('x') as output: output.write(text)
        with args.summary.open('x') as output: output.write(json.dumps(result,indent=2)+'\n')
    except Exception as failure:
        print('benchmark_protocol_error:'+ (str(failure) if isinstance(failure,Invalid) else 'invalid_input'),file=sys.stderr)
        return 1
    print('benchmark_protocol_pass')
    return 0

if __name__ == '__main__': sys.exit(main())
