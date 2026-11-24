import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import register_truncated_text_sources as subject


class TruncatedSourceRegistrationTest(unittest.TestCase):
    def test_new_surface_and_family_are_blocked(self):
        rows,_,_=subject.inputs();first,second,third=subject.entries()
        self.assertEqual(24,len(rows));self.assertEqual(24,len(first['surfaceKeys']))
        self.assertEqual(24,len(third['keys']['family']));self.assertEqual(4,len(third['unsupportedSurfaceKeys']))
        controls=subject.control.load(subject.CONTROL)
        old=dict(controls,entries=[e for e in controls['entries'] if e['id']!=subject.ENTRY])
        surfaces={key for entry in old['entries'] for key in entry.get('surfaceKeys',[])}
        row=next(r for r in rows if subject.control.surface_key('ru',r['typed']) not in surfaces)
        row={k:v for k,v in (row | {'prefix':'Иной контекст '}).items() if k!='article'}
        with self.assertRaisesRegex(ValueError,'CONTROL_COVERAGE_INCOMPLETE'):
            subject.control.assert_disjoint([row],old,'regression')
        with self.assertRaisesRegex(ValueError,'CONTROL_SURFACE_OVERLAP'):
            subject.control.assert_disjoint([row],controls,'regression')
        ledger=subject.lexical.load_ledger(subject.LEXICAL)
        old_lex=dict(ledger,entries=[e for e in ledger['entries'] if e['id'] not in (subject.ENTRY+'-contexts',subject.ENTRY+'-families')])
        families={key for entry in old_lex['entries'] for key in entry['keys'].get('family',[])}
        row=next(r for r in rows if r['families'] and subject.lexical.keys_for([r],'family')-families)
        # Use only the new lemma(s): another analysis of the same head can be old.
        new_keys=subject.lexical.keys_for([row],'family')-families
        with self.assertRaisesRegex(ValueError,'LEDGER_OVERLAP:family'):
            subject.lexical.assert_disjoint([row],ledger,kinds=('family',),require_complete=False)
        self.assertTrue(new_keys <= set(third['keys']['family']))

    def test_modified_archived_helper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'fixture';shutil.copytree(subject.FIXTURE,fixture)
            digest=next(iter(subject.SNAPSHOTS.values()))
            (fixture/'sources'/(digest+'.txt')).write_bytes(b'changed')
            with mock.patch.object(subject,'FIXTURE',fixture):
                with self.assertRaisesRegex(ValueError,'TRUNCATED_REG_BINDING'):
                    subject.inputs()

    def test_rehashed_unrelated_partial_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=Path(directory)/'fixture';shutil.copytree(subject.FIXTURE,fixture)
            path=fixture/'contexts.jsonl';rows=[json.loads(line) for line in path.read_bytes().splitlines()]
            rows[0]['partial']='неподходящий'
            raw=''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in rows).encode()
            path.write_bytes(raw);receipt_path=fixture/'receipt.json';receipt=json.loads(receipt_path.read_bytes())
            receipt['contextsSha256']=hashlib.sha256(raw).hexdigest();receipt_path.write_text(json.dumps(receipt))
            with mock.patch.object(subject,'FIXTURE',fixture):
                with self.assertRaisesRegex(ValueError,'TRUNCATED_REG_RELATION'):
                    subject.inputs()


if __name__=='__main__':unittest.main()
