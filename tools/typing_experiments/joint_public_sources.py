"""Validate caller-supplied source locks against the retained public shard identities."""
import hashlib
from pathlib import Path
from import_joint_history import SOURCES, BASE

REPOSITORY='wikimedia/wikipedia'
REVISION='a634f78b1c435397c07001e175fa74cc4ad5e775'


def validate_lock(lock, names):
    if lock.get('repository') != REPOSITORY or lock.get('revision') != REVISION:
        raise ValueError('JOINT_PUBLIC_SOURCE_LOCK')
    files=lock.get('files')
    if not isinstance(files,list):raise ValueError('JOINT_PUBLIC_SOURCE_LOCK')
    for name in names:
        matches=[x for x in files if x.get('path')=='20231101.ru/train/'+name]
        if len(matches)!=1 or matches[0].get('lfs',{}).get('oid')!=SOURCES[BASE+'/'+name]:
            raise ValueError('JOINT_PUBLIC_SOURCE_LOCK')
        if type(matches[0].get('size')) is not int or matches[0]['size']<=0:
            raise ValueError('JOINT_PUBLIC_SOURCE_LOCK')


def validate_training_entry(entry):
    if entry.get('sha256')!=SOURCES['build/typing-ranker-v2/ru-0011.parquet'] or type(entry.get('bytes')) is not int or entry['bytes']<=0:
        raise ValueError('JOINT_PUBLIC_SOURCE_LOCK')


def snapshot(paths):
    """Bind named, verified inputs and refuse replacement before publication."""
    result={}
    for name,(path,expected) in paths.items():
        path=Path(path)
        with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if digest!=expected:raise ValueError('JOINT_PUBLIC_INPUT_IDENTITY')
        result[name]=(path,digest)
    return result


def verify(snapshot):
    for path,digest in snapshot.values():
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=digest:raise ValueError('JOINT_PUBLIC_INPUT_DRIFT')
