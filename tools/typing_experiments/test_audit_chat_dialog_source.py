import io
from pathlib import Path
import tempfile
import unittest
from audit_chat_dialog_source import analyze,audit,normalized


class DialogSourceAuditTest(unittest.TestCase):
    def test_normalization_and_exact_control_overlap(self):
        data=io.StringIO('q,a\nПривет как дела?,всё хорошо\nПривет как дела!,совсем другое\n')
        self.assertEqual(dict(dialogues=2,questionEligible=2,answerEligible=2,uniqueEligible=3,
                              uniqueExactPriorControls=1),analyze(data,{'привет как дела'}))
        self.assertIsNone(normalized('тут, запятая'))
        self.assertIsNone(normalized('один'))

    def test_schema_and_bad_rows_fail_closed(self):
        for data in ('wrong,a\nx,y\n','q,a\nx\n','q,a\n','q,a\nx,y,z\n'):
            with self.assertRaises(ValueError):analyze(io.StringIO(data),set())

    def test_unpinned_sources_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/name for name in ('source','readme','prior')]
            for path in paths:path.write_text('changed',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'DIALOG_SOURCE_IDENTITY'):audit(*paths)


if __name__=='__main__':unittest.main()
