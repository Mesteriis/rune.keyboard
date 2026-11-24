import unittest

from android_chrome_editor import CLASS, METHODS, verify_native_identities


def native_output():
    return ''.join(
        f'INSTRUMENTATION_STATUS: class={CLASS}\n'
        f'INSTRUMENTATION_STATUS: test={method}\n'
        f'INSTRUMENTATION_STATUS_CODE: {status}\n'
        for method in sorted(METHODS) for status in (1, 0)
    ) + 'INSTRUMENTATION_CODE: -1\n'


class ChromeRouteTest(unittest.TestCase):
    def test_allows_numeric_progress_between_case_events(self):
        native = native_output().replace(
            'INSTRUMENTATION_STATUS_CODE: 1\n',
            'INSTRUMENTATION_STATUS_CODE: 1\n'
            'INSTRUMENTATION_STATUS: word=1\nINSTRUMENTATION_STATUS_CODE: 2\n',
        )
        verify_native_identities(native)

    def test_requires_both_exact_cases_to_start_and_pass(self):
        verify_native_identities(native_output())
        for text in (
            native_output().replace('INSTRUMENTATION_CODE: -1\n', ''),
            native_output().replace(CLASS, 'some.other.Test'),
            native_output().replace(sorted(METHODS)[0], sorted(METHODS)[1]),
            native_output().replace('INSTRUMENTATION_STATUS_CODE: 0', 'INSTRUMENTATION_STATUS_CODE: -3'),
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                verify_native_identities(text)
