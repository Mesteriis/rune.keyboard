"""Concrete negative source fixtures for the opt-in debug recorder boundary."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('boundary', Path(__file__).with_name('verify-scoring-boundaries.py'))
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
PKG = gate.BASE + 'smarttyping.diagnostics'
ROOT = 'app/src/{}/java/io/github/mesteriis/rune/keyboard/smarttyping/diagnostics/'


def source(body):
    return 'package ' + PKG + '\n' + body


def fixture(variant):
    return {
        ROOT.format('main') + 'TypingDiagnostics.kt': source('''
enum class DiagnosticKind { INPUT }
enum class DiagnosticReason { NONE }
data class DiagnosticEvent(val kind: DiagnosticKind, val reason: DiagnosticReason,
    val candidateCount: Int = 0, val selectedIndex: Int = -1, val modelUsed: Boolean = false,
    val session: Long, val revision: Long)
data class DiagnosticText(
    val input: String = "", val context: String = "", val original: String = "",
    val candidates: List<String> = emptyList(), val result: String = "",
)
interface TypingDiagnostics {
    fun startSession(session: Long, eligible: Boolean, fresh: Boolean)
    fun invalidate()
    fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)? = null)
    fun editorOperation(session: Long, revision: Long): (() -> Unit)? = null
}
object NoTypingDiagnostics : TypingDiagnostics {
    override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) = Unit
    override fun invalidate() = Unit
    override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) = Unit
}
'''),
        ROOT.format(variant) + 'TypingDiagnosticsProvider.kt': source('''import android.content.Context
object TypingDiagnosticsProvider {
    fun create(context: Context): TypingDiagnostics = NoTypingDiagnostics
}'''),
        ROOT.format(variant) + 'DiagnosticsSettingsProvider.kt': source('''import android.app.Activity
import android.widget.LinearLayout
object DiagnosticsSettingsProvider {
    fun contribute(activity: Activity, container: LinearLayout): AutoCloseable = AutoCloseable { }
}'''),
    }


class DiagnosticsBoundaryTest(unittest.TestCase):
    def errors(self, sources, variant='debug'):
        return '\n'.join(gate.inspect(sources, variant=variant))

    def test_complete_variant_contracts_are_accepted(self):
        for variant in ('debug', 'release', 'profile'):
            self.assertEqual('', self.errors(fixture(variant), variant))

    def test_missing_provider_is_not_resolved_by_another_variant(self):
        case = fixture('release')
        del case[ROOT.format('release') + 'TypingDiagnosticsProvider.kt']
        self.assertIn('missing variant diagnostics provider', self.errors(case, 'release'))

    def test_duplicate_provider_cannot_silently_shadow(self):
        case = fixture('debug')
        case[ROOT.format('main') + 'Duplicate.kt'] = source('object TypingDiagnosticsProvider')
        self.assertIn('duplicate diagnostics declaration', self.errors(case))

    def test_unreachable_release_recorder_is_rejected(self):
        for variant in ('main', 'release', 'profile'):
            case = fixture('release')
            case[ROOT.format(variant) + 'DiagnosticsRecorder.kt'] = source('class DiagnosticsRecorder')
            self.assertIn('diagnostics declaration outside permitted variant inventory', self.errors(case, 'release'))

    def test_writer_through_renamed_helper_is_rejected(self):
        case = fixture('debug')
        case[ROOT.format('debug') + 'TypingDiagnosticsProvider.kt'] = source('object TypingDiagnosticsProvider { val helper = Hidden() }')
        case[ROOT.format('debug') + 'Hidden.kt'] = source('import java.io.FileWriter\nclass Hidden')
        self.assertIn('diagnostics persistence outside exact debug storage', self.errors(case))

    def test_typing_provider_must_not_reach_ui(self):
        case = fixture('debug')
        case[ROOT.format('debug') + 'TypingDiagnosticsProvider.kt'] = source('object TypingDiagnosticsProvider { val helper = Bridge() }')
        case[ROOT.format('debug') + 'Bridge.kt'] = source('class Bridge { val activity = DiagnosticsActivity() }')
        case[ROOT.format('debug') + 'DiagnosticsActivity.kt'] = source('class DiagnosticsActivity')
        self.assertIn('typing diagnostics factory reaches UI/export', self.errors(case))

    def test_same_basename_elsewhere_does_not_grant_storage(self):
        case = fixture('debug')
        case['app/src/debug/java/elsewhere/DiagnosticsStorage.kt'] = source('import java.io.FileWriter\nclass DiagnosticsStorage')
        self.assertIn('diagnostics persistence outside exact debug storage', self.errors(case))

    def test_saf_uri_exception_does_not_allow_socket(self):
        case = fixture('debug')
        path = ROOT.format('debug') + 'DiagnosticsActivity.kt'
        case[path] = source('import android.net.Uri\nclass DiagnosticsActivity')
        self.assertEqual('', self.errors(case))
        case[path] = source('import android.net.Uri\nimport java.net.Socket\nclass DiagnosticsActivity')
        self.assertIn('diagnostics network/reflection', self.errors(case))

    def test_metadata_types_fail_closed(self):
        for field_type in ('String', 'Any', 'Char', 'List<Int>', 'PayloadAlias'):
            case = fixture('debug')
            path = ROOT.format('main') + 'TypingDiagnostics.kt'
            case[path] += '\ntypealias PayloadAlias = String\n'
            case[path] = case[path].replace('val revision: Long', 'val revision: ' + field_type)
            self.assertIn('diagnostics metadata field type', self.errors(case))

    def test_metadata_body_payload_is_rejected(self):
        case = fixture('debug')
        path = ROOT.format('main') + 'TypingDiagnostics.kt'
        case[path] = case[path].replace('val session: Long, val revision: Long)',
            'val session: Long, val revision: Long) { var payload: String = "" }')
        self.assertIn('diagnostics metadata field type', self.errors(case))

    def test_final_provider_cannot_hide_nested_encoder(self):
        case = fixture('release')
        path = ROOT.format('release') + 'TypingDiagnosticsProvider.kt'
        case[path] = source('object TypingDiagnosticsProvider { class DiagnosticsEncoding }')
        self.assertIn('diagnostics declaration outside permitted variant inventory', self.errors(case, 'release'))

    def test_metadata_inferred_or_computed_body_property_is_rejected(self):
        for body in ('val payload = "input"', 'val payload: String get() = "input"',
                     'fun payload(): String = "input"'):
            case = fixture('debug')
            path = ROOT.format('main') + 'TypingDiagnostics.kt'
            case[path] = case[path].replace('val session: Long, val revision: Long)',
                'val session: Long, val revision: Long) { ' + body + ' }')
            self.assertIn('diagnostics metadata field type', self.errors(case))

    def test_contract_cannot_hide_nested_or_duplicate_declaration(self):
        for extra in ('class DiagnosticsEncoding', 'object TypingDiagnostics { class Hidden }',
                      'fun encode(text: DiagnosticText) = text.toString()',
                      'class `TypingDiagnostics$DefaultImpls`'):
            case = fixture('release')
            case[ROOT.format('main') + 'TypingDiagnostics.kt'] += '\n' + extra
            self.assertIn('diagnostics declaration outside permitted variant inventory', self.errors(case, 'release'))

    def test_final_provider_must_have_exact_noop_behavior(self):
        for variant in ('release', 'profile'):
            for name, original, replacement in (
                ('TypingDiagnosticsProvider', '= NoTypingDiagnostics', '= object : TypingDiagnostics {}'),
                ('TypingDiagnosticsProvider', '= NoTypingDiagnostics', '= run { context.toString(); NoTypingDiagnostics }'),
                ('DiagnosticsSettingsProvider', 'AutoCloseable { }', 'AutoCloseable { activity.finish() }'),
            ):
                case = fixture(variant)
                path = ROOT.format(variant) + name + '.kt'
                case[path] = case[path].replace(original, replacement)
                self.assertIn('diagnostics final provider must be exact no-op', self.errors(case, variant))

    def test_main_noop_cannot_invoke_supplied_text(self):
        case = fixture('release')
        path = ROOT.format('main') + 'TypingDiagnostics.kt'
        case[path] = case[path].replace('text: (() -> DiagnosticText)?) = Unit',
                                       'text: (() -> DiagnosticText)?) = text?.invoke()')
        self.assertIn('diagnostics main observer must be exact no-op', self.errors(case, 'release'))

    def test_shared_interface_cannot_add_or_change_default_method_implementation(self):
        for mutation in (
            lambda text: text.replace('interface TypingDiagnostics {',
                'interface TypingDiagnostics { fun encode(text: DiagnosticText): String = text.toString()'),
            lambda text: text.replace('fun editorOperation(session: Long, revision: Long): (() -> Unit)? = null',
                'fun editorOperation(session: Long, revision: Long): (() -> Unit)? = { revision.toString() }'),
        ):
            case = fixture('release'); path = ROOT.format('main') + 'TypingDiagnostics.kt'
            case[path] = mutation(case[path])
            self.assertIn('diagnostics shared interface shape', self.errors(case, 'release'))

    def test_shared_text_dto_cannot_gain_serializer_members_or_changed_defaults(self):
        for suffix in (' { fun encode(): String = input + context }',
                       ' { val encoded: String get() = input }',
                       ' : java.io.Serializable { fun encode(): String = input }'):
            case = fixture('release'); path = ROOT.format('main') + 'TypingDiagnostics.kt'
            case[path] = case[path].replace(')\ninterface TypingDiagnostics', ')' + suffix + '\ninterface TypingDiagnostics')
            self.assertIn('diagnostics shared text DTO shape', self.errors(case, 'release'))
        case = fixture('release'); path = ROOT.format('main') + 'TypingDiagnostics.kt'
        case[path] = case[path].replace('val input: String = ""', 'val input: String = "changed"')
        self.assertIn('diagnostics shared text DTO shape', self.errors(case, 'release'))

    def test_recorder_cannot_read_editor_or_clipboard(self):
        for body in ('fun capture() = input.getTextBeforeCursor(12, 0)',
                     'val clipboard: ClipboardManager? = null',
                     'external fun capture(): Int'):
            case = fixture('debug')
            case[ROOT.format('debug') + 'DiagnosticsRecorder.kt'] = source('class DiagnosticsRecorder { ' + body + ' }')
            self.assertIn('diagnostics forbidden capability', self.errors(case))

    def test_exact_storage_and_fixed_preferences_are_accepted(self):
        case = fixture('debug')
        case[ROOT.format('debug') + 'DiagnosticsStorage.kt'] = source('import java.io.FileWriter\nclass DiagnosticsStorage')
        case[ROOT.format('debug') + 'DiagnosticsAndroidPreferences.kt'] = source('import android.content.SharedPreferences\nclass DiagnosticsAndroidPreferences')
        self.assertEqual('', self.errors(case))

    def test_model_storage_is_rejected_transitively(self):
        case = fixture('debug')
        case[ROOT.format('debug') + 'DiagnosticsRecorder.kt'] = source('import ' + gate.BASE + 'intelligence.storage.ActiveModelResolver\nclass DiagnosticsRecorder')
        case['Resolver.kt'] = 'package ' + gate.BASE + 'intelligence.storage\nclass ActiveModelResolver'
        self.assertIn('diagnostics forbidden capability', self.errors(case))

    def test_release_cannot_resolve_debug_only_aidl(self):
        case = fixture('release')
        case[ROOT.format('release') + 'TypingDiagnosticsProvider.kt'] = source('import ' + gate.BASE + 'intelligence.inference.ILifecycleControl\nobject TypingDiagnosticsProvider')
        self.assertIn('unresolved local dependency ' + gate.BASE + 'intelligence.inference.ILifecycleControl', self.errors(case, 'release'))

    def test_collection_keeps_debug_aidl_out_of_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = root / 'app/src/debug/aidl/private/DebugOnly.aidl'
            p.parent.mkdir(parents=True)
            p.write_text('package private; interface DebugOnly {}')
            self.assertTrue(any('DebugOnly' in s for s in gate.collect(root, 'debug').values()))
            self.assertFalse(any('DebugOnly' in s for s in gate.collect(root, 'release').values()))


if __name__ == '__main__':
    unittest.main()
