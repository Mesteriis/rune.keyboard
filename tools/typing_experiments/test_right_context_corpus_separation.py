import json
from pathlib import Path
import tempfile
import unittest
from right_context_corpus_separation import exclusion_records


class ExclusionRecordsTest(unittest.TestCase):
    def test_jsonl_pretty_json_disclosed_cases_and_array_are_all_read(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rows=[{'sourceSentence':'tatoeba:1'},{'article':'tatoeba:2'}]
            for name,content in [('rows.jsonl','\n'.join(json.dumps(r) for r in rows)+'\n'),
                                 ('disclosed.json',json.dumps({'cases':rows},indent=2)),
                                 ('list.json',json.dumps(rows,indent=2))]:
                path=root/name;path.write_text(content);self.assertEqual(rows,exclusion_records(path))
            path=root/'one.json';path.write_text(json.dumps(rows[0],indent=2));self.assertEqual(rows[:1],exclusion_records(path))

    def test_malformed_record_collections_are_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'invalid.json'
            for value in [None,{'cases':None},{'cases':[1]},[1]]:
                path.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError,'EXCLUSION_RECORD_FORMAT'):exclusion_records(path)


if __name__ == '__main__':unittest.main()
