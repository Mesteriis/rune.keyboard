import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import register_a2_window_contexts as subject


class A2WindowContextsTest(unittest.TestCase):
    def test_all_six_disclosed_contexts_are_in_the_real_registry(self):
        expected=subject.entry();ledger=subject.control.load(subject.LEDGER)
        self.assertEqual([expected],[e for e in ledger['entries'] if e['id']==subject.ENTRY])
        self.assertEqual(6,len(expected['keys']))
        legacy_id = 'a2-bounded-prefix-native-probe-v1'
        legacy, = [entry for entry in ledger['entries'] if entry['id'] == legacy_id]
        self.assertEqual(expected['keys'], legacy['keys'])
        self.assertNotEqual(expected['bindings'], legacy['bindings'])
        prior = {key for entry in ledger['entries']
                 if entry['id'] not in (subject.ENTRY, legacy_id) and entry['kind'] == 'regression'
                 for key in entry['keys']}
        self.assertFalse(set(expected['keys'])&prior)
        for first,last in ((17,39),(17,40),(34,56)):
            prefix=''.join(f'word{i:02d} ' for i in range(first,last+1))
            for typed in ('hello','helllo'):
                row=dict(language='en',prefix=prefix,typed=typed)
                with self.assertRaisesRegex(ValueError,'CONTROL_OVERLAP:regression'):
                    subject.control.assert_disjoint([row],ledger,'regression')

    def test_changed_android_probe_fails_before_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            altered=Path(folder)/'probe.kt'
            altered.write_text(subject.ANDROID.read_text().replace('"hello", "helllo"','"hello", "different"'))
            with mock.patch.object(subject,'ANDROID',altered):
                with self.assertRaisesRegex(ValueError,'A2_WINDOW_ANDROID_SCOPE'):
                    subject.entry()


if __name__=='__main__':unittest.main()
