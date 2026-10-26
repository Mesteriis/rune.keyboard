"""Read bound historical corpus records for sentence/family exclusion audits."""
import json


def exclusion_records(path):
    if path.suffix == '.jsonl':
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        value = json.loads(path.read_text())
        records = value.get('cases', [value]) if isinstance(value, dict) else value
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError('EXCLUSION_RECORD_FORMAT')
    return records
