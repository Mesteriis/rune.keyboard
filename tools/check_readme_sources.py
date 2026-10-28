#!/usr/bin/env python3
"""Check literal local links and Python/project-source references in main READMEs.

This is a bounded Markdown/source-presence check, not command execution,
generated-data validation, remote-link checking or transitive provenance proof.
"""
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('README.md', 'tools/typing_experiments/README.md')
PROJECT_PREFIXES = ('tools/', 'docs/', 'app/', 'runtime-llama/', 'fdroid/', 'build/')


def references(text, document):
    parent = Path(document).parent
    result = []
    for target in re.findall(r'\[[^\]]*\]\(([^)\n]+)\)', text):
        parts = shlex.split(target)
        if not parts:
            raise ValueError('README_LINK_SYNTAX')
        value = parts[0].strip('<>')
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        result.append((parent / unquote(parsed.path)).as_posix())
    blocks = re.findall(r'```[^\n]*\n(.*?)```', text, re.S)
    rest = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.S)
    blocks += re.findall(r'`([^`\n]+)`', rest)
    for block in blocks:
        scripts = re.findall(r'(?<![\w./:-])((?:[\w.-]+/)*[\w.-]+\.py)\b', block)
        paths = re.findall(r'(?<![\w./:-])((?:tools|docs|app|runtime-llama|fdroid)/[\w./-]+)', block)
        for value in scripts + paths:
            path = value.rstrip('/')
            result.append(path if path.startswith(PROJECT_PREFIXES) else (parent / path).as_posix())
        if re.search(r'(?<![\w/])\./gradlew\b', block):
            result.append('gradlew')
        command = block.replace('\\\n', ' ')
        for match in re.finditer(r'-m\s+unittest\s+([^;\n]+)', command):
            tokens = shlex.split(match[1])
            if tokens and tokens[0] == 'discover':
                continue
            for token in tokens:
                if re.fullmatch(r'test_[A-Za-z0-9_]+', token):
                    result.append((parent / (token + '.py')).as_posix())
    return result


def inspect(root=ROOT, documents=DOCUMENTS):
    root = root.resolve()
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0'))
    checked = set()
    generated = set()
    bindings = {}

    def local_path(value):
        path = Path(os.path.abspath(root / value))
        if not path.is_relative_to(root):
            raise ValueError('README_SOURCE_OUTSIDE_ROOT_OR_SYMLINK')
        parts = path.relative_to(root).parts
        if any(root.joinpath(*parts[:i]).is_symlink() for i in range(1, len(parts) + 1)):
            raise ValueError('README_SOURCE_OUTSIDE_ROOT_OR_SYMLINK')
        return path

    for document in documents:
        if document not in tracked:
            raise ValueError('README_DOCUMENT_UNTRACKED ' + document)
        raw = local_path(document).read_bytes()
        bindings[document] = hashlib.sha256(raw).hexdigest()
        for value in references(raw.decode(), document):
            path = local_path(value)
            name = path.relative_to(root).as_posix()
            if name.startswith(('build/', 'app/build/', 'runtime-llama/build/')) and not name.endswith('.py'):
                generated.add(name)
                continue
            if not path.exists() or (name not in tracked and not (
                    path.is_dir() and any(p.startswith(name + '/') for p in tracked))):
                raise ValueError('README_SOURCE_UNTRACKED_OR_MISSING ' + name)
            checked.add(name)
    return dict(scope='MAIN_README_LITERAL_LOCAL_LINKS_AND_PROJECT_PYTHON_SOURCES',
                documents=bindings, checkedPaths=sorted(checked), commandsExecuted=False,
                generatedArtifactPaths=sorted(generated),
                generatedDataValidated=False, remoteLinksVerified=False)


if __name__ == '__main__':
    import json
    print(json.dumps(inspect(), indent=2, sort_keys=True))
