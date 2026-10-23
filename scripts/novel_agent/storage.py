"""Crash-safe storage primitives, with no dependency on CLI utility modules."""
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager

from novel_agent.errors import ConflictError, DataCorruptionError


def read_json(path, *, default_factory):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return default_factory()
    except (ValueError, UnicodeError) as exc:
        raise DataCorruptionError('invalid JSON at {}: {}'.format(path, exc))
    if not isinstance(payload, dict):
        raise DataCorruptionError('JSON object required at {}'.format(path))
    return payload


def validate_schema(payload, path, *, version=1, fields=None):
    if payload.get('version', version) != version:
        raise DataCorruptionError('unsupported version at {}'.format(path))
    for key, expected in (fields or {}).items():
        if key in payload and not isinstance(payload[key], expected):
            raise DataCorruptionError('invalid {} at {}'.format(key, path))
    return payload


def atomic_write_text(path, text):
    path = os.path.abspath(path)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.exists(path):
            os.chmod(temporary, os.stat(path).st_mode & 0o777)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path, payload):
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def text_content_hash(path):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
    except FileNotFoundError:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@contextmanager
def project_lock(project_dir):
    directory = os.path.join(project_dir, 'runtime')
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, '.project_write.lock')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ConflictError('project is locked by another writer: {} (inspect a stale lock before removing it)'.format(path))
    identity = os.fstat(fd)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(str(os.getpid()) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        try:
            current = os.stat(path)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                os.unlink(path)
        except FileNotFoundError:
            pass
