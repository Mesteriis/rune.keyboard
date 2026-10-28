import copy
import io
import json
import threading
import unittest
import urllib.error
import urllib.request

import serve
import verify

NATIVE = 'INSTRUMENTATION_STATUS_CODE: 0\nINSTRUMENTATION_STATUS_CODE: 0\nOK (2 tests)\n'


def row(profile, flag=None, length=0, words=0, corrections=0, last=0):
    result = {key: 0 for key in verify.FIELDS - {'profile'}}
    result.update(profile=profile, length=length, words=words, corrections=corrections, lastCorrected=last)
    if flag:
        result[flag] = 1
    return result


def fixture():
    return [row('ordinary'), row('ordinary', 'firstFive', 20, 5, 5, 1),
            row('ordinary', 'undo', 19, 5, 4), row('ordinary', 'sixth', 24, 6, 5, 1),
            row('no-suggestions'), row('no-suggestions', 'literalFive', 20, 5),
            row('no-suggestions', 'literalBackspace', 19, 5)]


class OracleTest(unittest.TestCase):
    def test_complete_independent_outcomes(self):
        self.assertTrue(verify.verify(fixture(), NATIVE)['passed'])

    def test_native_pass_cannot_replace_any_dom_stage(self):
        for index in range(7):
            with self.subTest(index=index), self.assertRaises(ValueError):
                verify.verify(fixture()[:index] + fixture()[index + 1:], NATIVE)

    def test_order_and_exact_counts_are_required(self):
        for mutate in ['reverse', 'length', 'corrections', 'last']:
            rows = fixture()
            if mutate == 'reverse':
                rows[1:4] = reversed(rows[1:4])
            else:
                rows[3][{'last': 'lastCorrected'}.get(mutate, mutate)] -= 1
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                verify.verify(rows, NATIVE)

    def test_text_bool_extra_fields_or_bad_profile_are_rejected(self):
        for key, value in [('length', 'private'), ('words', True), ('payload', 'private'),
                           ('profile', []), ('undo', 2)]:
            rows = fixture()
            rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify.verify(rows, NATIVE)

    def test_failed_skipped_or_partial_native_run_is_rejected(self):
        for native in ['', NATIVE.replace('2 tests', '1 test'), NATIVE + 'FAILURES!!!',
                       NATIVE + 'INSTRUMENTATION_STATUS_CODE: -3\n', NATIVE + 'INSTRUMENTATION_FAILED']:
            with self.subTest(native=native), self.assertRaises(ValueError):
                verify.verify(fixture(), native)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.server = serve.http.server.HTTPServer(('127.0.0.1', 0), serve.FixtureHandler)
        self.server.receipt = io.StringIO()
        self.server.records = 0
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def post(self, payload):
        return urllib.request.urlopen(urllib.request.Request(
            self.base + '/rune-q8-metrics/ordinary', data=json.dumps(payload).encode()), timeout=3)

    def test_only_two_fixed_documents_are_served_without_cache(self):
        for path, content in [('/rune-q8', serve.HTML), ('/rune-q8-no-suggestions', serve.NO_SUGGESTIONS)]:
            with urllib.request.urlopen(self.base + path) as response:
                self.assertEqual(content, response.read())
                self.assertEqual('no-store', response.headers['Cache-Control'])
        for path in ['/', '/../serve.py', '/rune-q8?input=private']:
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.base + path)
            self.assertEqual(404, caught.exception.code)

    def test_only_numeric_schema_reaches_receipt(self):
        value = row('ordinary', 'firstFive', 20, 5, 5, 1)
        value.pop('profile')
        with self.post(value) as response:
            self.assertEqual(204, response.status)
        self.assertEqual(row('ordinary', 'firstFive', 20, 5, 5, 1),
                         json.loads(self.server.receipt.getvalue()))
        original = self.server.receipt.getvalue()
        for change in [{'payload': 'private'}, {'words': 'private'}, {'words': True}, {'undo': 2}]:
            bad = copy.deepcopy(value)
            bad.update(change)
            with self.subTest(change=change), self.assertRaises(urllib.error.HTTPError) as caught:
                self.post(bad)
            self.assertEqual(400, caught.exception.code)
        self.assertEqual(original, self.server.receipt.getvalue())

    def test_receipt_is_bounded(self):
        self.server.records = 512
        value = row('ordinary')
        value.pop('profile')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post(value)
        self.assertEqual(429, caught.exception.code)
        self.assertEqual('', self.server.receipt.getvalue())


if __name__ == '__main__':
    unittest.main()
