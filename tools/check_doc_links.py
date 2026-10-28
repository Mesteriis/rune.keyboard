#!/usr/bin/env python3
"""Read-only local Markdown navigation audit, including pinned submodule files."""
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_readme_sources import ROOT, local_links, local_path

DOCUMENTS = ('README.md', 'tools/typing_experiments/README.md',
             'docs/USER_GUIDE.ru.md', 'docs/typing-candidate-retrieval.md')


def inspect(root=ROOT, documents=DOCUMENTS, maximum_documents=512):
    root = root.resolve()
    records = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=root)
    members = {}
    for record in records.split(b'\0'):
        if not record:
            continue
        fields, name = record.split(b'\t', 1)
        mode, digest, stage = fields.decode().split()
        if stage == '0':
            members[name.decode()] = (mode, digest)
    gitlinks = {name: digest for name, (mode, digest) in members.items() if mode == '160000'}
    checked, submodule_files = set(), {}

    def require_member(value):
        path = local_path(root, value)
        name = path.relative_to(root).as_posix()
        if not path.exists():
            raise ValueError('DOC_LINK_MISSING ' + name)
        if name in members:
            if name in gitlinks:
                head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path).decode().strip()
                if head != gitlinks[name]:
                    raise ValueError('DOC_SUBMODULE_HEAD_DRIFT')
        elif path.is_dir() and any(p.startswith(name + '/') for p in members):
            pass
        else:
            parent = next((p for p in sorted(gitlinks, key=len, reverse=True)
                           if name.startswith(p + '/')), None)
            if parent is None or not path.is_file():
                raise ValueError('DOC_LINK_UNTRACKED ' + name)
            repo = root / parent
            pin = gitlinks[parent]
            if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo).decode().strip() != pin:
                raise ValueError('DOC_SUBMODULE_HEAD_DRIFT')
            relative = name[len(parent) + 1:]
            original = subprocess.check_output(['git', '--no-replace-objects', 'cat-file', 'blob', pin + ':' + relative], cwd=repo)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if hashlib.sha256(original).hexdigest() != digest:
                raise ValueError('DOC_SUBMODULE_FILE_DRIFT')
            submodule_files[name] = dict(commit=pin, sha256=digest)
        checked.add(name)
        return name, path

    queue = deque(documents)
    bindings = {}
    while queue:
        name, path = require_member(queue.popleft())
        if name in bindings:
            continue
        if len(bindings) >= maximum_documents:
            raise ValueError('DOC_LINK_GRAPH_BOUND')
        raw = path.read_bytes()
        bindings[name] = hashlib.sha256(raw).hexdigest()
        # Examples inside fenced code are not rendered navigation links.
        text = re.sub(r'```[^\n]*\n.*?```', '', raw.decode(), flags=re.S)
        for target in local_links(text, name):
            target_name, target_path = require_member(target)
            if target_path.is_file() and target_path.suffix.lower() == '.md':
                queue.append(target_name)
    return dict(scope='REACHABLE_LOCAL_MARKDOWN_LINKS', documents=bindings,
                checkedPaths=sorted(checked), pinnedSubmoduleFiles=submodule_files,
                remoteLinksVerified=False, anchorsVerified=False, commandsExecuted=False)


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2, sort_keys=True))
