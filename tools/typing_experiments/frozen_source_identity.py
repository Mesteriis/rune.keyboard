"""Read exact public historical source bytes by original path and digest; never execute."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def read_frozen_source(root,name,digest):
    root=Path(root)
    if (not isinstance(name,str) or not name or '\\' in name or
            PurePosixPath(name).is_absolute() or any(p in ('','.','..') for p in name.split('/'))
            or not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest)):
        raise ValueError('FROZEN_SOURCE_REQUEST')

    def read(path):
        for parent in (path,*path.parents):
            if parent==root:break
            if parent.is_symlink():raise ValueError('FROZEN_SOURCE_SYMLINK')
        return path.read_bytes()

    try:current=read(root/name)
    except FileNotFoundError:current=None
    if current is not None and hashlib.sha256(current).hexdigest()==digest:
        return current
    archive=root/'tools/typing_experiments/frozen_sources'
    entry=json.loads(read(archive/'manifest.json'))['sources'].get(digest)
    if (not isinstance(entry,dict) or entry.get('originalPath')!=name or
            not isinstance(entry.get('file'),str) or not re.fullmatch('[A-Za-z0-9_.-]+\\.py',entry['file'])):
        raise ValueError('FROZEN_SOURCE_ORIGIN')
    raw=read(archive/entry['file'])
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('FROZEN_SOURCE_IDENTITY')
    return raw
