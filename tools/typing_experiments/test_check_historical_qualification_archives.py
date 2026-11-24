import io
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import check_historical_qualification_archives as subject
import control_ledger
import holdout_ledger
import recover_historical_spelling_articles as spelling
import replay_historical_qualification as replay
from recover_historical_punctuation_attribution import HERE, PREFIX
from recover_historical_spelling_attribution import MAPS, digest, scan_article_metadata


class HistoricalQualificationArchiveTest(unittest.TestCase):
    def test_punctuation_and_ru_attribution_agree_with_the_registries(self):
        directory = subject.ROOT / 'punctuation-ru-attribution'
        controls = {e['id']: e for e in control_ledger.load(HERE / 'control-ledger.json')['entries']}
        lexical = {e['id']: e for e in holdout_ledger.load_ledger(HERE / 'holdout-ledger.json')['entries']}
        for version, source in spelling.inputs().items():
            corpus = 'qualification-v2' if version == 'v2' else f'compact-{version}'
            for language in ('en', 'es', 'ru'):
                with self.subTest(version=version, language=language):
                    report = json.loads((directory / f'{version}-{language}.json').read_bytes())
                    self.assertEqual((version, language), (report['version'], report['language']))

                    def ids(mapping, filename, digest_field):
                        raw = source[filename]
                        self.assertEqual(digest(raw), report[digest_field])
                        self.assertEqual({json.loads(line)['id'] for line in raw.splitlines()}, set(mapping))
                        self.assertTrue(all(mapping.values()))
                        return {article for group in mapping.values() for article in group}

                    pun_ids = ids(report['punctuation'], f'punctuation-{language}.jsonl', 'punctuationRowsSha256')
                    entry = controls[f'{corpus}-punctuation-{language}']
                    self.assertEqual(set(entry['articleKeys']), {control_ledger.article_key(
                        {'article': article, 'language': language}) for article in pun_ids})
                    all_ids = pun_ids
                    if language == 'ru':
                        spell_ids = ids(report['ruSpelling'], 'spelling-ru.jsonl', 'ruSpellingRowsSha256')
                        self.assertEqual(set(lexical[PREFIX + corpus]['keys']['article']),
                                         holdout_ledger.keys_for([{'article': article} for article in spell_ids], 'article'))
                        all_ids = all_ids | spell_ids
                    self.assertEqual(sorted(all_ids, key=int), [row['article'] for row in report['articles']])
                    self.assertTrue(all(set(row) == {'article', 'title', 'url'} for row in report['articles']))

    def test_attribution_matches_every_frozen_article_map(self):
        maps = subject.ROOT / 'article-maps'
        directory = maps / 'attribution'
        manifest = json.loads((directory / 'manifest.json').read_bytes())
        self.assertEqual(set(MAPS), {(entry['version'], entry['language']) for entry in manifest})
        self.assertEqual(len(MAPS), len(manifest))
        for entry in manifest:
            version, language = entry['version'], entry['language']
            with self.subTest(version=version, language=language):
                key = f'{version}-{language}'
                source = (maps / f'{key}.json').read_bytes()
                self.assertEqual(MAPS[(version, language)], entry['articleMapSha256'])
                self.assertEqual(digest(source), entry['articleMapSha256'])
                report = json.loads(source)
                for field in ('sourceShardSha256', 'sourceRevision', 'sourcePath'):
                    self.assertEqual(report[field], entry[field])
                raw = (directory / f'{key}.jsonl').read_bytes()
                self.assertEqual(digest(raw), entry['outputSha256'])
                rows = [json.loads(line) for line in raw.splitlines()]
                expected = {article for group in report['matchingArticlesByRow'].values() for article in group}
                self.assertEqual(sorted(expected, key=int), [row['article'] for row in rows])
                self.assertEqual(len(rows), entry['articles'])
                self.assertTrue(all(set(row) == {'article', 'title', 'url'} and row['title']
                                    and row['url'].startswith(f'https://{language}.wikipedia.org/wiki/')
                                    for row in rows))

    def test_attribution_refuses_wrong_language_missing_and_duplicate_articles(self):
        def batch(article, url):
            values = ([article], ['Article title'], [url])
            return SimpleNamespace(column=lambda i: SimpleNamespace(to_pylist=lambda: values[i]))

        en = batch('42', 'https://en.wikipedia.org/wiki/Article_title')
        es = batch('42', 'https://es.wikipedia.org/wiki/Article_title')
        self.assertEqual('42', scan_article_metadata([en], {'42'}, 'en')[0]['article'])
        for batches, code in (([es], 'URL'), ([], 'COVERAGE'), ([en, en], 'ARTICLE')):
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, f'HISTORICAL_ATTRIBUTION_{code}'):
                scan_article_metadata(batches, {'42'}, 'en')

    def test_retained_archives_match_original_manifests(self):
        self.assertEqual({'files': {'v3': 8, 'v4': 8}, 'independentQualification': False}, subject.check())

    def test_replay_fingerprints_and_manifests_are_frozen(self):
        raw = (subject.ROOT / 'replay-index.json').read_bytes()
        self.assertEqual(replay.INDEX_SHA256, subject.digest(raw))
        data = json.loads(raw)
        self.assertEqual(1, data['schema'])
        self.assertEqual(set(subject.MANIFESTS), set(data['versions']))
        for version, entry in data['versions'].items():
            generator, _ = replay.load_generator(entry['manifest'])
            manifest = generator.canonical(entry['manifest']) + b'\n'
            self.assertEqual(subject.MANIFESTS[version], subject.digest(manifest))
            for language, selected in entry['languages'].items():
                maps = replay.article_sets(version, language, selected['sourceMaps'])
                for kind, count in replay.KINDS.items():
                    self.assertTrue(maps[kind])
                    self.assertEqual(count, len(replay.fingerprint_set(selected['fingerprints'][kind], count)))

    def test_authored_protected_components_reproduce_original_bytes(self):
        for version, data in subject.load().items():
            manifest = json.loads(data['manifest.json'])
            path, checksum = next((path, checksum) for path, checksum in manifest['sources'].items()
                                  if path.endswith('/generate_corpus.py'))
            source = spelling.archived_source(spelling.ROOT, path, checksum)
            spec = importlib.util.spec_from_file_location('frozen_protected_generator', source)
            generator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generator)
            rows = [row for language in generator.LANGUAGES for row in generator.protected_rows(language)]
            rows.sort(key=lambda row: (row['split'] != 'calibration', row['id']))
            with self.subTest(version=version):
                self.assertEqual(1800, len(rows))
                self.assertEqual(data['protected-tokens.jsonl'],
                                 b''.join(generator.canonical(row) + b'\n' for row in rows))

    def test_spelling_selection_identities_match_all_archived_languages(self):
        for version, data in spelling.inputs().items():
            manifest = json.loads(data['manifest.json'])

            def archived(suffix):
                return next(spelling.archived_source(spelling.ROOT, path, digest)
                            for path, digest in manifest['sources'].items() if path.endswith('/' + suffix))

            spec = importlib.util.spec_from_file_location('frozen_spelling', archived('generate_corpus.py'))
            generator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generator)
            seed = 3042026 if version == 'v2' else json.loads(archived('source-lock.json').read_bytes())['corpusSeed']
            for lang in ('en', 'es', 'ru'):
                with self.subTest(version=version, language=lang):
                    rows = [json.loads(line) for line in data[f'spelling-{lang}.jsonl'].splitlines()]
                    self.assertEqual(3400, len(spelling.selection_index(rows, generator, seed, lang)))
                    broken = dict(rows[0], prefix=rows[0]['prefix'] + ' changed')
                    with self.assertRaisesRegex(ValueError, 'HISTORICAL_SPELLING_IDENTITY'):
                        spelling.selection_index([broken], generator, seed, lang)
                    if lang in ('en', 'es'):
                        report = json.loads((subject.ROOT / 'article-maps' / f'{version}-{lang}.json').read_bytes())
                        matches = report['matchingArticlesByRow']
                        self.assertEqual((version, lang), (report['version'], report['language']))
                        self.assertEqual(manifest['files'][f'spelling-{lang}.jsonl'], report['rowsSha256'])
                        self.assertEqual({row['id'] for row in rows}, set(matches))
                        self.assertTrue(all(ids and ids == sorted(set(ids), key=int) for ids in matches.values()))
                        self.assertEqual(sum(len(ids) > 1 for ids in matches.values()), report['ambiguousRows'])
                        self.assertEqual([], report['missingRows'])

    def test_changed_row_is_rejected_even_with_recomputed_archive_hash(self):
        catalog = json.loads((subject.ROOT / 'catalog.json').read_text())
        entry = catalog['archives']['v3']
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / 'changed.tar.bz2'
            with tarfile.open(subject.ROOT / entry['archive'], 'r:bz2') as original, tarfile.open(changed, 'w:bz2') as output:
                for member in original.getmembers():
                    content = original.extractfile(member).read()
                    if member.name == 'spelling-ru.jsonl':
                        content += b'\n'
                    info = tarfile.TarInfo(member.name)
                    info.size = len(content)
                    output.addfile(info, io.BytesIO(content))
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ROW_IDENTITY'):
                subject.check_archive(changed, subject.digest(changed.read_bytes()), entry['manifestSha256'], 3)

    def test_restore_requires_fresh_directory_and_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            build = Path(folder) / 'build'
            build.mkdir()
            output = build / 'restored'
            result = subject.restore(output, build=build)
            self.assertFalse(result['independentQualification'])
            original = subject.load()
            for label, files in original.items():
                self.assertEqual(set(files), {p.name for p in (output / label).iterdir()})
                for name, content in files.items():
                    self.assertEqual(content, (output / label / name).read_bytes())
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_RESTORE_OUTPUT'):
                subject.restore(output, build=build)
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_RESTORE_OUTPUT'):
                subject.restore(Path(folder) / 'outside', build=build)
            link = build / 'link'
            link.symlink_to(build / 'missing')
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_RESTORE_OUTPUT'):
                subject.restore(link, build=build)

    def test_restore_cleans_only_its_new_directory_on_write_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            build = Path(folder) / 'build'; build.mkdir()
            existing = build / 'keep'; existing.write_bytes(b'unchanged')
            output = build / 'restored'
            original_open = Path.open

            def fail_write(path, *args, **kwargs):
                if path.name == 'spelling-ru.jsonl' and args and args[0] == 'xb':
                    raise OSError('injected write failure')
                return original_open(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_write):
                with self.assertRaisesRegex(OSError, 'injected write failure'):
                    subject.restore(output, build=build)
            self.assertFalse(output.exists())
            self.assertEqual(b'unchanged', existing.read_bytes())

    def test_traversal_member_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'bad.tar.bz2'
            with tarfile.open(archive, 'w:bz2') as output:
                for name in sorted(subject.NAMES - {'manifest.json'}) + ['../manifest.json']:
                    info = tarfile.TarInfo(name)
                    output.addfile(info, io.BytesIO(b''))
            with self.assertRaisesRegex(ValueError, 'HISTORICAL_ARCHIVE_MEMBERS'):
                subject.check_archive(archive, subject.digest(archive.read_bytes()), subject.MANIFESTS['v3'], 3)
            self.assertFalse((Path(folder).parent / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
