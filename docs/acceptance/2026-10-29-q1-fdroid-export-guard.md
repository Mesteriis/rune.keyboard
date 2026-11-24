# Q1: source export Git guard and CLI error handling

The [local F-Droid source tarball](2026-10-29-q1-fdroid-source-export.md) was extracted to an isolated temporary directory without Git metadata. Running its actual prepared-source release check refused it with `RELEASE_GIT_QUERY_FAILED`. This confirms that successful tarball creation is not yet a reproducible release build from that export. The security check remains in force; no synthetic Git repository or bypass was introduced.

The original command printed a Python traceback because executing `release_source_check.py` as `__main__` and importing it from `fdroid_prepared_source.py` produced distinct `SourceCheckError` classes. The prepared-source CLI now translates the imported error into the CLI's own error type. The same extracted source, with only the revised checker copied into its disposable directory, still refuses with exit 1 and the concise message `Release source check failed: RELEASE_GIT_QUERY_FAILED`, without a traceback. The temporary extraction was deleted.

The `test_*source*.py` suite passed 50 tests, including a new non-Git prepared-source CLI regression. Independent build-server, a secure source-export verification design, actual archive-based release build, and distribution acceptance remain open. The physical phone was not used.
