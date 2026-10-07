"""Exact owned execution inputs; collection-only hashes cannot establish PASS."""
import hashlib
from pathlib import Path
import re
import stat


def _digest(path):
    information = path.lstat()
    if (not stat.S_ISREG(information.st_mode) or stat.S_ISLNK(information.st_mode)
            or getattr(information, 'st_file_attributes', 0) & 0x400):
        raise ValueError('Protected regular execution input required')
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def capture_inputs(development, harnesses):
    development = Path(development)
    result = {}
    for path in sorted(development.rglob('*')):
        if path.suffix in ('.py','.sql'):
            result['development/' + path.relative_to(development).as_posix()] = _digest(path)
    for path in map(Path, harnesses):
        key = 'harness/' + path.name
        if key in result:
            raise ValueError('Duplicate owned execution input')
        result[key] = _digest(path)
    if not result:
        raise ValueError('Nonempty owned execution inventory required')
    return result


def require_unchanged_inputs(before, after):
    if (not isinstance(before, dict) or not before or not isinstance(after, dict)
            or before != after or any(not isinstance(name, str) or not name
                or not isinstance(value, str) or not re.fullmatch('sha256:[0-9a-f]{64}', value)
                for name, value in before.items())):
        raise ValueError('Exact execution inputs changed or unavailable')
