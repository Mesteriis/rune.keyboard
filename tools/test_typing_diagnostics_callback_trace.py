import unittest
from test_typing_diagnostics_boundary import gate, fixture


class CallbackTraceBoundaryTest(unittest.TestCase):
    def test_exact_final_provider_is_accepted(self):
        for variant in ['release', 'profile']:
            sources = fixture(variant)
            sources[gate.CALLBACK_TRACE_PATH.format(variant)] = gate.FINAL_CALLBACK_TRACE
            self.assertEqual([], gate.inspect(sources, variant=variant))

    def test_final_provider_cannot_record_state_or_add_helpers(self):
        for variant in ['release', 'profile']:
            for change in [
                gate.FINAL_CALLBACK_TRACE.replace('= Unit', '{ history.add(flags) }'),
                gate.FINAL_CALLBACK_TRACE.replace('object EditorCallbackTrace {',
                    'object EditorCallbackTrace { val history = mutableListOf<Int>()'),
                gate.FINAL_CALLBACK_TRACE + '\nobject HiddenProbe\n',
            ]:
                sources = fixture(variant)
                sources[gate.CALLBACK_TRACE_PATH.format(variant)] = change
                with self.subTest(variant=variant, change=change):
                    self.assertIn('callback trace final provider must be exact no-op', '\n'.join(gate.inspect(sources, variant=variant)))

    def test_main_or_duplicate_provider_cannot_hide_variant_implementation(self):
        sources = fixture('release')
        sources[gate.CALLBACK_TRACE_PATH.format('release')] = gate.FINAL_CALLBACK_TRACE
        sources[gate.CALLBACK_TRACE_PATH.format('main')] = gate.FINAL_CALLBACK_TRACE
        self.assertIn('callback trace provider outside exact variant inventory', '\n'.join(gate.inspect(sources, variant='release')))


if __name__ == '__main__': unittest.main()
