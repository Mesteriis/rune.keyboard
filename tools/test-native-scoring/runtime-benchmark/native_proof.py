#!/usr/bin/env python3
"""Read-only APK native-entry identity check. Output contains no machine paths."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

LIBRARIES=('librune_llama.so','libc++_shared.so')
def chunks(data):
    digest=hashlib.sha256(data).digest()
    return [int.from_bytes(digest[i:i+4],'big') for i in range(0,32,4)]

def apk(path):
    with zipfile.ZipFile(path) as archive:
        native=[]
        for index,name in enumerate(LIBRARIES):
            entry='lib/arm64-v8a/'+name
            if archive.namelist().count(entry) != 1: raise ValueError('entry')
            data=archive.read(entry)
            native.append({'id':index,'bytes':len(data),'sha256':chunks(data)})
    return {'apk_sha256':chunks(path.read_bytes()),'native':native}

def proof(test_path, build, release_path=None):
    test=apk(test_path)
    result={'schema':1,'build':0 if build=='debug' else 1,'matched_release':0,
            'test_apk_sha256':test['apk_sha256'],'native':test['native']}
    if build=='release':
        if release_path is None: raise ValueError('release_required')
        release=apk(release_path)
        if test['native'] != release['native']: raise ValueError('release_mismatch')
        result.update(matched_release=1,release_apk_sha256=release['apk_sha256'])
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--test-apk',type=Path,required=True)
    parser.add_argument('--app-release-apk',type=Path); parser.add_argument('--build',choices=['debug','release'],required=True)
    parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink(): raise ValueError('output_exists')
        result=proof(args.test_apk,args.build,args.app_release_apk)
        with args.output.open('x') as output: output.write(json.dumps(result,indent=2)+'\n')
    except Exception:
        print('native_proof_rejected',file=sys.stderr); return 1
    print('native_proof_pass'); return 0
if __name__ == '__main__': sys.exit(main())
