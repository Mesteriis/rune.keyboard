"""Internal unittest child: logs remain raw; receipt retains counts and skips."""
import json
from pathlib import Path
import sys
import unittest


def main():
    module, destination = sys.argv[1:]
    path = Path(module)
    suite = unittest.defaultTestLoader.discover(str(path.parent), pattern=path.name)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {'tests': result.testsRun,
               'failures': [test.id() for test, _ in result.failures],
               'errors': [test.id() for test, _ in result.errors],
               'skipped': [{'test': test.id(), 'reason': reason} for test, reason in result.skipped]}
    Path(destination).write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if result.wasSuccessful() and result.testsRun > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
