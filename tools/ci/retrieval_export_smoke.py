"""Compile the actual manual retrieval observer and capture four disclosed rows."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]


def run(output,java):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('FRESH_RETRIEVAL_EXPORT_OUTPUT')
    output.mkdir(parents=True,exist_ok=False)
    old_path=sys.path[:]
    try:
        sys.path[:0]=[str(ROOT/'tools/ci'),str(ROOT/'tools/typing_experiments')]
        from word_evaluation_smoke import validate_capture
        from export_retrieval import export
        import retrieval_evaluation_receipt as binding
        fixture_path=ROOT/'tools/ci/fixtures/word-ranking-bounded-capture.json'
        fixture=json.loads(fixture_path.read_text());validate_capture(fixture)
        rows=output/'rows.jsonl';rows.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in fixture['rows']))
        export(rows,output/'export',Path(java))
        frozen=binding.freeze(output/'export',True,ROOT);binding.shared.verify(frozen)
        receipt=dict(scope='actual current JVM manual retrieval; four disclosed rows; no numerical or Android qualification',
            rows=len(frozen['rows']),independentQualification=False,productionQualified=False,
            driverSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            fixtureSha256=hashlib.sha256(fixture_path.read_bytes()).hexdigest(),evaluationBinding=frozen['receipt'])
        (output/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
        return receipt
    finally:sys.path[:]=old_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--java',type=Path,required=True)
    args=parser.parse_args();result=run(args.output,args.java)
    print(json.dumps(dict(rows=result['rows'],independentQualification=False)))


if __name__=='__main__':main()
