#!/usr/bin/env python3
"""Local-only Telegram personal-chat import and bounded n-gram style support.

All errors and receipts are content-free. Datasets, vocabulary and hashes remain
private artifacts; they must never be committed or uploaded.
"""
import argparse
from collections import Counter
from collections.abc import Iterable
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import unicodedata


MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_MESSAGES = 250_000
MAX_TEXT_CHARS = 16_384
MAX_COUNT = 10_000_000
MAX_NGRAM_ENTRIES = 500_000
SAFE_ENTITIES = {'plain', 'bold', 'italic', 'underline', 'strikethrough'}
WORD = re.compile(r'[^\W\d_]+', re.UNICODE)
CONTACT_OR_CODE = re.compile(
    r'\b[a-zA-Z][a-zA-Z0-9+.-]*://|www\.|(?:\w[\w.+-]*@\w)|(?:^|\s)@[\w]+|'
    r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}\b|'
    r'(?:\+?\d[\s().-]*){7,}|`|[{}]|'
    r'\b\w+_\w+\b|\b[^\W\d_]\w*\d+\w*\b|'
    r'\b[a-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Za-z_][A-Za-z0-9_]*\s*\(|'
    r'(?:^|\s)[/~][\w.-]+(?:/[\w.-]+)+|(?:^|\s)[A-Za-z]:\\')


class ImportFailure(ValueError):
    """An intentionally content-free validation failure."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def _normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).lower().split())


def _words(text: str) -> list[str]:
    return WORD.findall(_normalized(text))


def _segments(text: str) -> list[str]:
    # Keep the final empty segment so a prefix ending at a boundary has no context.
    separated = ''.join('\n' if char in '\r\n' or unicodedata.category(char)[0] in {'P', 'S'}
                        else char for char in text)
    return separated.split('\n')


def _self_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ImportFailure('INVALID_SELF_ID')
    match = re.fullmatch(r'(?:user)?([1-9][0-9]{0,19})', str(value))
    if match is None:
        raise ImportFailure('INVALID_SELF_ID')
    return 'user' + match[1]


def _safe_text(message: dict) -> str | None:
    value = message.get('text')
    if isinstance(value, list):
        if len(value) > MAX_TEXT_CHARS:
            return None
        parts = []
        for part in value:
            if isinstance(part, str):
                parts.append(part)
            elif (isinstance(part, dict) and isinstance(part.get('type'), str)
                  and part['type'] in SAFE_ENTITIES
                  and isinstance(part.get('text'), str)):
                parts.append(part['text'])
            else:
                return None
        value = ''.join(parts)
    if not isinstance(value, str) or len(value) > MAX_TEXT_CHARS:
        return None
    entities = message.get('text_entities', [])
    if not isinstance(entities, list) or any(
        not isinstance(entity, dict) or not isinstance(entity.get('type'), str)
        or entity['type'] not in SAFE_ENTITIES
        or not isinstance(entity.get('text'), str) for entity in entities
    ):
        return None
    if any(unicodedata.category(char).startswith('C') and char not in '\n\r\t'
           for char in value):
        return None
    text = unicodedata.normalize('NFC', value).replace('\r\n', '\n').replace('\r', '\n').strip()
    if not text or CONTACT_OR_CODE.search(text) or not _words(text):
        return None
    return text


def parse_export(payload: object, self_id: str | int) -> list[tuple[str, str]]:
    """Read a single-chat or full-export envelope; never infer the account ID."""
    identity = _self_id(self_id)
    if not isinstance(payload, dict):
        raise ImportFailure('INVALID_EXPORT_ENVELOPE')
    if 'chats' in payload:
        wrapper = payload['chats']
        if not isinstance(wrapper, dict) or not isinstance(wrapper.get('list'), list):
            raise ImportFailure('INVALID_EXPORT_ENVELOPE')
        chats = wrapper['list']
    elif 'type' in payload and 'messages' in payload:
        chats = [payload]
    else:
        raise ImportFailure('INVALID_EXPORT_ENVELOPE')
    if len(chats) > MAX_MESSAGES:
        raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
    rows = []
    seen_messages = 0
    for chat in chats:
        if not isinstance(chat, dict) or not isinstance(chat.get('type'), str):
            raise ImportFailure('INVALID_CHAT_ENVELOPE')
        if chat['type'] != 'personal_chat':
            continue
        chat_id = chat.get('id')
        if (isinstance(chat_id, bool) or not isinstance(chat_id, (str, int))
                or re.fullmatch(r'[1-9][0-9]{0,19}', str(chat_id)) is None
                or not isinstance(chat.get('messages'), list)):
            raise ImportFailure('INVALID_CHAT_ENVELOPE')
        group = _sha(('telegram-personal-chat:' + str(chat_id)).encode())
        seen_messages += len(chat['messages'])
        if seen_messages > MAX_MESSAGES:
            raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
        for message in chat['messages']:
            if not isinstance(message, dict):
                raise ImportFailure('INVALID_MESSAGE_ENVELOPE')
            if (message.get('type') != 'message' or message.get('from_id') != identity
                    or any(key.startswith('forwarded') or key in {'saved_from', 'via_bot', 'via_bot_id'}
                           for key in message)):
                continue
            text = _safe_text(message)
            if text is not None:
                rows.append((group, text))
    return rows


def build_model(texts: Iterable[str]) -> dict:
    """Count normalized words within unique messages, without boundary bridges."""
    messages = set()
    for index, text in enumerate(texts):
        if index >= MAX_MESSAGES or not isinstance(text, str) or len(text) > MAX_TEXT_CHARS:
            raise ImportFailure('TRAINING_LIMIT_EXCEEDED')
        normalized = '\n'.join(_normalized(line) for line in text.splitlines()).strip()
        if normalized:
            messages.add(normalized)
    ordered = sorted(messages)
    counts = {size: Counter() for size in (1, 2, 3)}
    for text in ordered:
        for segment in _segments(text):
            words = _words(segment)
            for size in counts:
                counts[size].update(' '.join(words[i:i + size]) for i in range(len(words) - size + 1))
            if sum(len(counter) for counter in counts.values()) > MAX_NGRAM_ENTRIES:
                raise ImportFailure('MODEL_LIMIT_EXCEEDED')
    result = {'schemaVersion': 1, 'trainingSha256': _sha(_json_bytes(ordered)),
              'messageHashes': sorted(_sha(text.encode()) for text in ordered)}
    for size, name in ((1, 'unigrams'), (2, 'bigrams'), (3, 'trigrams')):
        if any(value > MAX_COUNT for value in counts[size].values()):
            raise ImportFailure('MODEL_LIMIT_EXCEEDED')
        result[name] = dict(sorted(counts[size].items()))
    if len(_json_bytes(result)) > MAX_FILE_BYTES:
        raise ImportFailure('MODEL_LIMIT_EXCEEDED')
    return result


class StyleModel:
    """Validated local n-gram support, never a standalone correction decision."""

    def __init__(self, payload: dict):
        if not isinstance(payload, dict) or type(payload.get('schemaVersion')) is not int or payload['schemaVersion'] != 1:
            raise ImportFailure('INVALID_MODEL_SCHEMA')
        if set(payload) != {'schemaVersion', 'trainingSha256', 'messageHashes', 'unigrams', 'bigrams', 'trigrams'}:
            raise ImportFailure('INVALID_MODEL_SCHEMA')
        digest = payload.get('trainingSha256')
        hashes = payload.get('messageHashes')
        def valid_hash(value: object) -> bool:
            return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None
        if (not valid_hash(digest) or not isinstance(hashes, list) or len(hashes) > MAX_MESSAGES
                or any(not valid_hash(value) for value in hashes) or len(set(hashes)) != len(hashes)):
            raise ImportFailure('INVALID_MODEL_METADATA')
        self._counts = {}
        self._totals = {}
        entries = 0
        for size, name in ((1, 'unigrams'), (2, 'bigrams'), (3, 'trigrams')):
            counts = payload.get(name)
            if not isinstance(counts, dict):
                raise ImportFailure('INVALID_MODEL_COUNTS')
            entries += len(counts)
            if entries > MAX_NGRAM_ENTRIES:
                raise ImportFailure('MODEL_LIMIT_EXCEEDED')
            total = Counter()
            for key, value in counts.items():
                if (not isinstance(key, str) or len(key) > MAX_TEXT_CHARS
                        or ' '.join(_words(key)) != key or len(key.split()) != size
                        or type(value) is not int or not 1 <= value <= MAX_COUNT):
                    raise ImportFailure('INVALID_MODEL_COUNTS')
                if size > 1:
                    total[key.rsplit(' ', 1)[0]] += value
            self._counts[size] = dict(counts)
            self._totals[size] = total
        if len(_json_bytes(payload)) > MAX_FILE_BYTES:
            raise ImportFailure('MODEL_LIMIT_EXCEEDED')

    def bonus(self, prefix: str, candidate: str) -> float:
        if not isinstance(prefix, str) or not isinstance(candidate, str):
            return 0.0
        if len(prefix) > MAX_TEXT_CHARS or len(candidate) > MAX_TEXT_CHARS:
            return 0.0
        context, target = _words(_segments(prefix)[-1])[-2:], _words(candidate)
        if not context or len(target) != 1 or _normalized(candidate) != target[0]:
            return 0.0
        size = 3 if len(context) == 2 else 2
        for width in range(size, 1, -1):
            before = ' '.join(context[-(width - 1):])
            count = self._counts[width].get(before + ' ' + target[0], 0)
            total = self._totals[width].get(before, 0)
            if count and total:
                # Repeated observations strengthen support; a singleton remains weak.
                return min(1.0, count / total * count / (count + 2.0))
        return 0.0


def _read_export(path: Path) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise ImportFailure('INVALID_INPUT_FILE')
            data = source.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
            return data
    except OSError:
        raise ImportFailure('INPUT_READ_FAILED') from None


def _validate_output(output: Path) -> Path:
    path = output.absolute()
    if path.exists() or path.is_symlink() or '..' in path.parts:
        raise ImportFailure('OUTPUT_MUST_BE_FRESH')
    ancestor = path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    try:
        found = subprocess.run(['git', '-C', str(ancestor), 'rev-parse', '--show-toplevel'],
                               capture_output=True, check=True, text=True)
        root = Path(found.stdout.strip()).resolve()
        # Canonicalize system ancestors, then reject links anywhere inside the checkout.
        relative = path.relative_to(Path(found.stdout.strip()))
        if 'build' not in relative.parts[:-1]:
            raise ImportFailure('OUTPUT_REQUIRES_IGNORED_BUILD')
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ImportFailure('OUTPUT_SYMLINK_FORBIDDEN')
        ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', str(current)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ignored.returncode != 0:
            raise ImportFailure('OUTPUT_REQUIRES_IGNORED_BUILD')
        return current
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        if isinstance(error, ImportFailure):
            raise
        raise ImportFailure('OUTPUT_REQUIRES_IGNORED_BUILD') from None


def import_exports(inputs: Iterable[Path], self_id: str | int, output: Path,
                   validation_fraction: float = 0.2) -> dict:
    """Write a fresh private dataset and model; the returned report has no text."""
    _self_id(self_id)
    destination = _validate_output(Path(output))
    if (isinstance(validation_fraction, bool) or not isinstance(validation_fraction, (int, float))
            or not math.isfinite(validation_fraction) or not 0 < validation_fraction <= 0.5):
        raise ImportFailure('INVALID_VALIDATION_FRACTION')
    sources = set()
    unique = {}
    total_bytes = 0
    selected_count = 0
    input_count = 0
    for path in inputs:
        input_count += 1
        if input_count > 100:
            raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
        data = _read_export(Path(path))
        total_bytes += len(data)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
        digest = _sha(data)
        if digest in sources:
            continue
        sources.add(digest)
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeError, RecursionError):
            raise ImportFailure('INVALID_EXPORT_JSON') from None
        rows = parse_export(payload, self_id)
        selected_count += len(rows)
        if selected_count > MAX_MESSAGES:
            raise ImportFailure('EXPORT_LIMIT_EXCEEDED')
        for group, text in rows:
            key = _normalized(text)
            row = (group, text)
            if key not in unique or row < unique[key]:
                unique[key] = row
    if not unique:
        raise ImportFailure('NO_ELIGIBLE_AUTHORED_TEXT')
    groups = sorted({group for group, _ in unique.values()})
    validation_count = max(1, int(len(groups) * validation_fraction)) if len(groups) >= 2 else 0
    group_counts = Counter(group for group, _ in unique.values())
    validation_groups = set()
    held_out_messages = 0
    for group in groups:
        if (len(validation_groups) < validation_count
                and held_out_messages + group_counts[group] <= len(unique) // 2):
            validation_groups.add(group)
            held_out_messages += group_counts[group]
    ordered = sorted(unique.values())
    train = [text for group, text in ordered if group not in validation_groups]
    validation = [text for group, text in ordered if group in validation_groups]
    model = build_model(train)
    StyleModel(model)
    artifacts = {'train.jsonl': b''.join(_json_bytes({'text': text}) for text in train),
                 'validation.jsonl': b''.join(_json_bytes({'text': text}) for text in validation),
                 'model.json': _json_bytes(model)}
    report = {'schemaVersion': 1, 'uniqueExports': len(sources), 'eligibleChats': len(groups),
              'selectedBeforeTextDedup': selected_count, 'uniqueMessages': len(unique),
              'trainMessages': len(train), 'validationMessages': len(validation),
              'validationEligible': len(groups) >= 2,
              'validationFraction': validation_fraction,
              'splitStrategy': 'chat-hash-with-half-message-cap-v1'}
    receipt = {**report, 'sourceSha256': sorted(sources),
               'trainingSha256': model['trainingSha256'],
               'importerSha256': _sha(Path(__file__).read_bytes()),
               'trainChatHashes': sorted(set(groups) - validation_groups),
               'validationChatHashes': sorted(validation_groups),
               'artifactSha256': {name: _sha(data) for name, data in artifacts.items()}}
    artifacts['report.json'] = _json_bytes(report)
    artifacts['receipt.json'] = _json_bytes(receipt)
    created = False
    try:
        missing = []
        parent = destination.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for parent in reversed(missing):
            parent.mkdir(mode=0o700)
        destination.mkdir(mode=0o700)
        created = True
        for name, data in artifacts.items():
            descriptor = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as target:
                target.write(data)
    except OSError:
        if created:
            try:
                for name in artifacts:
                    (destination / name).unlink(missing_ok=True)
                destination.rmdir()
            except OSError:
                raise ImportFailure('OUTPUT_WRITE_FAILED_PARTIAL_PRIVATE_OUTPUT') from None
        raise ImportFailure('OUTPUT_WRITE_FAILED') from None
    return report


def main(argv: list[str] | None = None) -> int:
    class PrivateArgumentParser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            self.exit(2, 'INVALID_ARGUMENTS\n')

    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, action='append', required=True)
    parser.add_argument('--self-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validation-fraction', type=float, default=0.2)
    args = parser.parse_args(argv)
    try:
        report = import_exports(args.input, args.self_id, args.output, args.validation_fraction)
    except ImportFailure as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
