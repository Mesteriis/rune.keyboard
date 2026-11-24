import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import build_chat_rare_candidate as candidate
import replay_chat_packed_candidate as candidate_replay
import chat_packed_impact


SCRIPT = Path(__file__).with_name("pack_rare_word_lexicon.py")
SPEC = importlib.util.spec_from_file_location("pack_rare_word_lexicon", SCRIPT)
packer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(packer)


class PackRareWordsTest(unittest.TestCase):
    def test_packs_identity_bound_front_coded_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            words = source / "words.txt"
            counts = source / "counts.tsv"
            words.write_text("абава\nабаза\nабака\n", encoding="utf-8")
            counts.write_text("абака\t5\t3\nабава\t4\t3\nабаза\t3\t2\n", encoding="utf-8")
            (source / "manifest.json").write_text(json.dumps({"schemaVersion": 1,
                "containsPrivateText": False, "files": {"words.txt": packer.sha256(words),
                "counts.tsv": packer.sha256(counts)}}))
            output, receipt = root / "words.bin", root / "receipt.json"
            result = packer.pack(source, output, receipt)
            self.assertEqual(b"RUNERAR1", output.read_bytes()[:8])
            self.assertEqual(3, result["words"])
            self.assertEqual(result, json.loads(receipt.read_text()))
            self.assertEqual({'абака':1,'абава':2,'абаза':3},candidate.unpack(output))
            damaged=bytearray(output.read_bytes());damaged[-1]^=1;output.write_bytes(damaged)
            with self.assertRaisesRegex(ValueError,'RARE_CANDIDATE_PACKED'):
                candidate.unpack(output)

    def test_candidate_preserves_ranking_and_rejects_duplicate_inputs(self):
        words=['абава','абаза'];counts='абаза\t3\t2\nабава\t2\t1\n'
        merged,ranked=candidate.merge(words,counts,['админку','токсиков'])
        self.assertEqual(sorted(words+['админку','токсиков']),merged)
        self.assertEqual(['абаза\t3\t2','абава\t2\t1','админку\t0\t0','токсиков\t0\t0'],ranked)
        for selected in (['абава'],['токсиков','админку'],['админку','админку'],['слово;']):
            with self.assertRaises(ValueError):candidate.merge(words,counts,selected)

    def test_candidate_replay_changes_only_resource_identity(self):
        old='a'*64;new='b'*64
        source=f'const val ASSET_BYTES = 3_000L\nconst val ASSET_SHA256 = "{old}"\nval intact = 7\n'
        actual=candidate_replay.candidate_constants(source,old,new,3012)
        self.assertEqual(f'const val ASSET_BYTES = 3012L\nconst val ASSET_SHA256 = "{new}"\nval intact = 7\n',actual)
        with self.assertRaisesRegex(ValueError,'PACKED_REPLAY_SOURCE'):
            candidate_replay.candidate_constants(source+source,old,new,3012)
        with self.assertRaisesRegex(ValueError,'PACKED_REPLAY_CONSTANTS'):
            candidate_replay.candidate_constants(source,old,'bad',3012)

    def test_candidate_replay_checks_all_copied_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);original=root/'original';copy=root/'copy'
            for base in (original,copy):
                (base/'smarttyping/lexicon').mkdir(parents=True)
                (base/'other').write_bytes(b'unchanged')
            (original/'smarttyping/lexicon/ru.rare').write_bytes(b'old')
            (copy/'smarttyping/lexicon/ru.rare').write_bytes(b'new')
            replacement=root/'candidate';replacement.write_bytes(b'new')
            candidate_replay.verify_assets(original,copy,replacement)
            (copy/'other').write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError,'PACKED_REPLAY_ASSET_DRIFT'):
                candidate_replay.verify_assets(original,copy,replacement)
            (copy/'other').unlink()
            with self.assertRaisesRegex(ValueError,'PACKED_REPLAY_ASSET_SCOPE'):
                candidate_replay.verify_assets(original,copy,replacement)

    def test_packed_impact_counts_stopped_and_started_changes_without_accuracy_claim(self):
        rows=[];before=[];after=[]
        for index in range(4728):
            row=dict(id=f'row-{index}',split='holdout',language='ru',prefix='мы',typed='слово',
                     cohort='unlabeled' if index<4720 else 'correct',noAuto=index>=4720)
            common=dict(index=index,status='COMPLETE',split='holdout',language='ru',prefix='мы',typed='слово',
                        beforeBoundary={'text':'мы слово'},restoredBeforeBoundaryExactly=True)
            old_changed=index==0;new_changed=index==1
            old=common|dict(id=row['id'],afterBoundary={'text':'мы иное ' if old_changed else 'мы слово '},
                            boundaryChangedBeyondInsertedSpace=old_changed)
            new=common|dict(id=f'joint-replay-{index:08d}',afterBoundary={'text':'мы иное ' if new_changed else 'мы слово '},
                            boundaryChangedBeyondInsertedSpace=new_changed)
            rows.append(row);before.append(old);after.append(new)
        report=chat_packed_impact.analyze(rows,before,after)
        self.assertEqual(1,report['counts']['baselineChangedCandidateUnchanged'])
        self.assertEqual(1,report['counts']['baselineUnchangedCandidateChanged'])
        self.assertEqual(8,report['counts']['reviewedPreserved'])
        self.assertIs(False,report['independentQualification'])
        after[0]=after[0]|{'boundaryChangedBeyondInsertedSpace':True}
        with self.assertRaisesRegex(ValueError,'PACKED_IMPACT_EDITOR'):
            chat_packed_impact.analyze(rows,before,after)


if __name__ == "__main__":
    unittest.main()
