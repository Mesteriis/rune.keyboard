"""Read exact source bytes used by disclosed historical replay fixtures."""
import hashlib
from pathlib import Path, PurePosixPath
import re

ARCHIVES={
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/correction/AutoCorrectionAdmissionGuard.kt',
     '76dec4aac8631daad21f716d98d37f4dad6b0b3cb0e9597741c5f885cd76856f'):'AutoCorrectionAdmissionGuard-76dec4aa.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/ContextualCorrectionPolicy.kt',
     'a7946c3907fa8e1986b9077e54e61e5d485cb2e35b2380356e2553b5a7c74a8f'):'ContextualCorrectionPolicy-a7946c39.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/experiments/JointCorrectionPolicy.kt',
     '1a30c167af91a9241a18f964419f060617448082cb035c954fc08926088ffc6f'):'JointCorrectionPolicy-1a30c167.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/CandidateGenerator.kt',
     '4d830724cc66f967f7c7736efedd540da9f5e27892d1f09cb753dabaa592e684'):'CandidateGenerator-4d830724.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/NeighborRecoverySearch.kt',
     '0c30517b0f59e4d2d1b4927c5e654d22d190119d059af6cdcfbe059309032b55'):'NeighborRecoverySearch-0c30517b.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/lexicon/PackedCandidateLexicon.kt',
     '0d59152024c64263cf7d1d178cd353446ab0c0a1bea79ee3b8f55ec4fe788d54'):'PackedCandidateLexicon-0d591520.kt',
    ('app/src/main/java/io/github/mesteriis/rune/keyboard/intelligence/ipc/ScoringContract.kt',
     '085f7e03aa3ed8f1387ead50e7928137b23da706ae01ee64e3726939efd67de8'):'ScoringContract-085f7e0.kt',
    ('tools/eval/smart-typing-0.3/pipeline/final_product_replay.py',
     'bf63b2ddf9b8eebe62f2110fd9b00d8a8cc03f708d43bb670100e800a7a57618'):'final_product_replay-bf63b2dd.py',
    ('tools/eval/smart-typing-0.3/pipeline/final_product_replay_sources.json',
     '5d32bb0de271691af9ea5e06281725fc9871597ca805e05b83cce84b5b5ba407'):'final_product_replay_sources-5d32bb0d.json',
}


def read(repo,name,digest):
    repo=Path(repo).resolve()
    if (not isinstance(name,str) or not name or '\\' in name or PurePosixPath(name).is_absolute() or
            any(part in ('','.','..') for part in name.split('/')) or not isinstance(digest,str) or
            not re.fullmatch('[0-9a-f]{64}',digest)):
        raise ValueError('CAPTURE_SOURCE_REQUEST')
    def read_file(path):
        for part in (path,*path.parents):
            if part==repo:break
            if part.is_symlink():raise ValueError('CAPTURE_SOURCE_SYMLINK')
        if not path.resolve().is_relative_to(repo):raise ValueError('CAPTURE_SOURCE_PATH')
        try:return path.read_bytes()
        except FileNotFoundError:return None
    current=read_file(repo/name)
    if current is not None and hashlib.sha256(current).hexdigest()==digest:return current
    archive=ARCHIVES.get((name,digest))
    if archive is None:raise ValueError('CAPTURE_SOURCE_IDENTITY')
    raw=read_file(repo/'tools/ci/fixtures/captured-sources'/archive)
    if raw is None or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('CAPTURE_SOURCE_ARCHIVE_IDENTITY')
    return raw
