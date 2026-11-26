import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
import unittest

import quality_period as q


class QualityPeriodTest(unittest.TestCase):
    def setUp(self):
        self.start = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        self.zero = [0] * q.COUNTS

    def test_threshold_and_period(self):
        end = self.zero.copy()
        end[q.SOURCE_OFFSET:q.SOURCE_OFFSET + 8] = [100, 5, 2, 1, 99, 1, 0, 0]
        result = q.compare((self.start, self.zero), (self.start + dt.timedelta(days=14), end))
        self.assertTrue(result['at_least_14_days'])
        self.assertEqual(result['sources']['COMMON_CONFUSION']['undo_per_application'], .05)
        self.assertIsNone(result['sources']['GENERAL_LOCAL']['undo_per_application'])
        self.assertFalse(result['continuity_and_ordinary_owner_use_verified'])
        self.assertFalse(result['reset_excluded'])
        self.assertTrue(result['sources']['COMMON_CONFUSION']['cross_boundary_undo_possible'])

    def test_source_order_matches_persisted_kotlin_schema(self):
        root = Path(__file__).resolve().parents[2]
        recorder = (root / 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/quality/QualityRecorder.kt').read_text()
        body = re.search(r'enum class AutomaticQualitySource\s*\{([^}]*)\}', recorder).group(1)
        self.assertEqual(tuple(re.findall(r'[A-Z][A-Z_]*', body)), q.SOURCES)
        outcomes = re.search(r'enum class AutomaticQualityOutcome\s*\{([^}]*)\}', recorder).group(1)
        self.assertEqual(re.findall(r'[A-Z][A-Z_]*', outcomes),
                         ['APPLIED', 'EXPLICIT_UNDO', 'KEPT_ORIGINAL', 'WINDOW_EXPIRED'])

    def test_short_period_and_cross_boundary_undo(self):
        end = self.zero.copy()
        end[q.SOURCE_OFFSET + 1] = 1
        result = q.compare((self.start, self.zero), (self.start + dt.timedelta(days=13), end))
        self.assertFalse(result['at_least_14_days'])
        self.assertIsNone(result['sources']['COMMON_CONFUSION']['undo_per_application'])

    def test_decrease_saturation_and_time_are_rejected(self):
        later = self.start + dt.timedelta(days=1)
        old = self.zero.copy(); old[0] = 1
        with self.assertRaisesRegex(ValueError, 'decreased'):
            q.compare((self.start, old), (later, self.zero))
        full = self.zero.copy(); full[0] = q.MAX_COUNT
        with self.assertRaisesRegex(ValueError, 'saturated'):
            q.compare((self.start, self.zero), (later, full))
        with self.assertRaisesRegex(ValueError, 'later'):
            q.compare((self.start, self.zero), (self.start, self.zero))

    def test_snapshot_codec_hash_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'quality'; meta = Path(directory) / 'meta.json'
            raw = b'RUNE_QUALITY_3\n' + b'0\n' * q.COUNTS
            snapshot.write_bytes(raw)
            metadata = {'snapshot_sha256': hashlib.sha256(raw).hexdigest(), 'captured_utc': '2026-01-01T00:00:00Z'}
            meta.write_text(json.dumps(metadata))
            self.assertEqual(q.read_snapshot(snapshot, meta), (self.start, self.zero))
            snapshot.write_bytes(raw + b'0')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                q.read_snapshot(snapshot, meta)
            malformed = raw.replace(b'0\n', b'-1\n', 1)
            snapshot.write_bytes(malformed)
            metadata['snapshot_sha256'] = hashlib.sha256(malformed).hexdigest()
            meta.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'invalid counter'):
                q.read_snapshot(snapshot, meta)
            snapshot.write_bytes(raw)
            metadata.update(snapshot_sha256=hashlib.sha256(raw).hexdigest(), captured_utc='2026-01-01T00:00:00')
            meta.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'timezone'):
                q.read_snapshot(snapshot, meta)

    def test_capture_reads_only_user_zero_opt_in_and_bounded_counters(self):
        raw = b'RUNE_QUALITY_3\n' + b'0\n' * q.COUNTS
        commands = []
        responses = iter([b'device\n', b'0\n', b'1\n', raw, b'1\n'])

        def run(command, *, capture_output, timeout):
            self.assertTrue(capture_output)
            self.assertEqual(timeout, 15)
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, next(responses), b'')

        with tempfile.TemporaryDirectory() as root:
            directory = q.capture_snapshot('fold-fixture', Path(root), execute=run)
            snapshot, metadata_path = directory / 'quality.txt', directory / 'metadata.json'
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(snapshot.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(metadata_path.stat().st_mode), 0o600)
            self.assertEqual(q.read_snapshot(snapshot, metadata_path)[1], self.zero)
            metadata = json.loads(metadata_path.read_bytes())
            self.assertEqual(set(metadata), {
                'captured_utc', 'snapshot_sha256', 'quality_metrics_enabled_before_and_after',
            })
            self.assertTrue(metadata['quality_metrics_enabled_before_and_after'])

        self.assertEqual([command[:3] for command in commands], [['adb', '-s', 'fold-fixture']] * 5)
        self.assertEqual(commands[0][3:], ['get-state'])
        self.assertEqual(commands[1][3:], ['shell', 'am', 'get-current-user'])
        self.assertEqual(commands[2], commands[4])
        pref = shlex.split(commands[2][-1])
        snapshot = shlex.split(commands[3][-1])
        self.assertEqual(pref, ['run-as', q.PACKAGE, '--user', '0', 'sed', '-n',
                                f's|{q.PREFERENCE}|1|p', q.PREFERENCES])
        self.assertEqual(snapshot, ['run-as', q.PACKAGE, '--user', '0', 'head', '-c', '2049', q.COUNTER_FILE])
        self.assertEqual([command[3] for command in commands[2:]], ['exec-out'] * 3)

    def test_capture_leaves_no_files_on_failed_transport_or_unconfirmed_data(self):
        raw = b'RUNE_QUALITY_3\n' + b'0\n' * q.COUNTS
        for responses, reason in (
            ([(1, b'')], 'ADB read failed'),
            ([(0, b'offline')], 'online device'),
            ([(0, b'device'), (0, b'10')], 'Android user 0'),
            ([(0, b'device'), (0, b'0'), (0, b'')], 'preference'),
            ([(0, b'device'), (0, b'0'), (0, b'1'), (0, raw + b'x')], 'schema'),
            ([(0, b'device'), (0, b'0'), (0, b'1'), (0, raw), (0, b'1\n1\n')], 'preference'),
        ):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as root:
                pending = iter(responses)

                def run(command, **kwargs):
                    code, data = next(pending)
                    return subprocess.CompletedProcess(command, code, data, b'private transport details')

                with self.assertRaisesRegex(ValueError, reason) as failure:
                    q.capture_snapshot('fold-fixture', Path(root), execute=run)
                self.assertNotIn('private transport details', str(failure.exception))
                self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
