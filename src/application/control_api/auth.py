"""Trusted local owner enrollment and opaque, revocable server sessions.

No HTTP enrollment or shipped password. Only hashes enter the local auth store.
The store is separate from canonical financial evidence and cloud publication.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
from threading import RLock

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from argon2.profiles import RFC_9106_LOW_MEMORY
from application.platform.resources import require_local_database_volume
from registry.operational_authority import HumanIdentity


class AuthenticationError(ValueError):
    def __init__(self, code='AUTHORIZATION_REQUIRED'):
        self.code = code
        super().__init__(code)


def _now(clock):
    now = clock()
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        raise AuthenticationError('AUTH_CLOCK_INVALID')
    return now


def _stamp(now): return now.isoformat(timespec='microseconds').replace('+00:00', 'Z')
def _hash(value): return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}', value):
        raise AuthenticationError('INVALID_INPUT')
    return value


@dataclass(frozen=True)
class SessionGrant:
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    actor: str
    expires_at: str
    revision: int


class _ReauthProof:
    __slots__ = ('issuer', 'session_hash', 'revision', 'deadline')
    def __init__(self, issuer, session_hash, revision, deadline):
        self.issuer, self.session_hash, self.revision, self.deadline = issuer, session_hash, revision, deadline
    def __repr__(self): return '<local reauthentication capability>'


class LocalAuth:
    def __init__(self, database_path, *, namespace, clock=lambda: datetime.now(timezone.utc), session_seconds=1800):
        if namespace not in ('FIXTURE', 'LOCAL_RESEARCH') or not callable(clock):
            raise AuthenticationError('INVALID_INPUT')
        if type(session_seconds) is not int or not 60 <= session_seconds <= 86400:
            raise AuthenticationError('INVALID_INPUT')
        self.path = Path(database_path).absolute()
        require_local_database_volume(self.path)
        if self.path.is_symlink(): raise AuthenticationError('INVALID_INPUT')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.namespace, self.clock, self.duration = namespace, clock, session_seconds
        self._hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)
        self._lock = RLock()
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS local_auth_meta(namespace TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_users(username TEXT PRIMARY KEY,password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_sessions(
                    session_hash TEXT PRIMARY KEY,csrf_hash TEXT NOT NULL,actor TEXT NOT NULL,
                    revision INTEGER NOT NULL,created_at TEXT NOT NULL,last_seen TEXT NOT NULL,
                    expires_at TEXT NOT NULL,reauth_deadline TEXT,revoked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS local_login_commands(command_id TEXT PRIMARY KEY,actor TEXT NOT NULL,issued_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS local_auth_throttle(singleton INTEGER PRIMARY KEY CHECK(singleton=1),failures INTEGER NOT NULL,window_start TEXT NOT NULL);
            ''')
            # Serialize the read-before-insert across separate server processes.
            # A damaged/ambiguous binding cannot borrow the first row's authority.
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute('SELECT namespace FROM local_auth_meta LIMIT 2').fetchall()
            if not rows: db.execute('INSERT INTO local_auth_meta VALUES(?)', (namespace,))
            elif len(rows) != 1 or rows[0]['namespace'] != namespace:
                raise AuthenticationError('AUTH_NAMESPACE_CONFLICT')

    def _db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=5000')
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        return _ClosingConnection(db)

    def create_owner(self, username, password):
        """First-run local CLI only. Server JSON never reaches enrollment."""
        _identifier(username)
        if not isinstance(password, str) or not 12 <= len(password) <= 256 or '\x00' in password:
            raise AuthenticationError('INVALID_INPUT')
        hashed = self._hasher.hash(password)
        with self._lock, self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM local_users LIMIT 1').fetchone():
                raise AuthenticationError('OWNER_ALREADY_CONFIGURED')
            db.execute('INSERT INTO local_users VALUES(?,?)', (username, hashed))

    def _throttled(self, db, now):
        row = db.execute('SELECT * FROM local_auth_throttle WHERE singleton=1').fetchone()
        if row is None or (now - datetime.fromisoformat(row['window_start'].replace('Z', '+00:00'))).total_seconds() >= 300:
            db.execute('INSERT OR REPLACE INTO local_auth_throttle VALUES(1,0,?)', (_stamp(now),))
            return False
        if _stamp(now) < row['window_start']: return True
        return row['failures'] >= 5

    def _verify_password(self, db, username, password):
        row = db.execute('SELECT password_hash FROM local_users WHERE username=?', (username,)).fetchone()
        if row is None or not isinstance(password, str) or len(password) > 256: return False
        try: return self._hasher.verify(row['password_hash'], password)
        except (VerificationError, InvalidHashError): return False

    def login(self, username, password, *, command_id, expected_revision):
        _identifier(command_id)
        if type(expected_revision) is not int or expected_revision != 0: raise AuthenticationError('CONFLICT')
        if not isinstance(username, str) or len(username) > 96: raise AuthenticationError()
        with self._lock, self._db() as db:
            now = _now(self.clock)
            if self._throttled(db, now): raise AuthenticationError('AUTHENTICATION_THROTTLED')
            if not self._verify_password(db, username, password):
                db.execute('UPDATE local_auth_throttle SET failures=failures+1 WHERE singleton=1')
                db.commit()  # Preserve the failure even though the protocol rejects.
                raise AuthenticationError()
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('BEGIN IMMEDIATE') if not db.in_transaction else None
            if db.execute('SELECT 1 FROM local_login_commands WHERE command_id=?', (command_id,)).fetchone():
                raise AuthenticationError('CONFLICT')
            if db.execute('SELECT COUNT(*) FROM local_login_commands').fetchone()[0] >= 100000:
                raise AuthenticationError('AUTH_STORE_CAPACITY_REACHED')
            if db.execute('SELECT COUNT(*) FROM local_sessions WHERE revoked=0 AND expires_at>?', (_stamp(now),)).fetchone()[0] >= 32:
                raise AuthenticationError('AUTH_SESSION_CAPACITY_REACHED')
            expires = _stamp(now + timedelta(seconds=self.duration))
            db.execute('INSERT INTO local_login_commands VALUES(?,?,?)', (command_id, username, _stamp(now)))
            db.execute('INSERT INTO local_sessions VALUES(?,?,?,1,?,?,?,NULL,0)',
                       (_hash(token), _hash(csrf), username, _stamp(now), _stamp(now), expires))
            db.execute('UPDATE local_auth_throttle SET failures=0,window_start=? WHERE singleton=1', (_stamp(now),))
            return SessionGrant(token, csrf, username, expires, 1)

    def _session(self, db, session_hash, now):
        row = db.execute('SELECT * FROM local_sessions WHERE session_hash=?', (session_hash,)).fetchone()
        if row is None or row['revoked'] or not row['last_seen'] <= _stamp(now) < row['expires_at']:
            raise AuthenticationError()
        return row

    def _token_hash(self, token):
        if not isinstance(token, str) or not re.fullmatch('[A-Za-z0-9_-]{43}', token): raise AuthenticationError()
        return _hash(token)

    def authenticate(self, token):
        with self._lock, self._db() as db:
            now = _now(self.clock); key = self._token_hash(token); row = self._session(db, key, now)
            db.execute('UPDATE local_sessions SET last_seen=? WHERE session_hash=?', (_stamp(now), key))
            return HumanIdentity(row['actor'], ('ProductOwner',))

    def session_view(self, token):
        with self._db() as db:
            row = self._session(db, self._token_hash(token), _now(self.clock))
            return dict(actor=row['actor'], roles=['ProductOwner'], revision=row['revision'], expires_at=row['expires_at'],
                        reauthenticated_until=row['reauth_deadline'], namespace=self.namespace)

    def configured(self):
        with self._db() as db:
            return db.execute('SELECT 1 FROM local_users LIMIT 1').fetchone() is not None

    def current_reauthentication(self, token):
        """Server reconstructs a capability from current persisted session facts."""
        key = self._token_hash(token)
        with self._db() as db:
            now = _now(self.clock); row = self._session(db, key, now)
            if row['reauth_deadline'] is None or _stamp(now) >= row['reauth_deadline']:
                raise AuthenticationError('REAUTHENTICATION_REQUIRED')
            return _ReauthProof(self, key, row['revision'], row['reauth_deadline'])

    def require_csrf(self, token, csrf_token):
        with self._db() as db:
            row = self._session(db, self._token_hash(token), _now(self.clock))
            if not isinstance(csrf_token, str) or len(csrf_token) != 43 or not hmac.compare_digest(row['csrf_hash'], _hash(csrf_token)):
                raise AuthenticationError('CSRF_REQUIRED')

    def reauthenticate(self, token, password, *, expected_revision):
        key = self._token_hash(token)
        with self._lock, self._db() as db:
            now = _now(self.clock)
            if self._throttled(db, now): raise AuthenticationError('AUTHENTICATION_THROTTLED')
            row = self._session(db, key, now)
            if type(expected_revision) is not int or row['revision'] != expected_revision: raise AuthenticationError('CONFLICT')
            if not self._verify_password(db, row['actor'], password):
                db.execute('UPDATE local_auth_throttle SET failures=failures+1 WHERE singleton=1'); db.commit()
                raise AuthenticationError()
            revision = row['revision'] + 1
            deadline = min(row['expires_at'], _stamp(now + timedelta(seconds=300)))
            changed = db.execute('UPDATE local_sessions SET revision=?,reauth_deadline=?,last_seen=? WHERE session_hash=? AND revision=? AND revoked=0',
                                 (revision, deadline, _stamp(now), key, expected_revision))
            if changed.rowcount != 1: raise AuthenticationError('CONFLICT')
            return _ReauthProof(self, key, revision, deadline)

    def verify_reauthentication(self, proof):
        if not isinstance(proof, _ReauthProof) or proof.issuer is not self: return None
        try:
            with self._db() as db:
                now = _now(self.clock); row = self._session(db, proof.session_hash, now)
                if row['revision'] != proof.revision or row['reauth_deadline'] != proof.deadline or _stamp(now) >= proof.deadline:
                    return None
                return HumanIdentity(row['actor'], ('ProductOwner',))
        except AuthenticationError: return None

    def logout(self, token, *, expected_revision):
        with self._lock, self._db() as db:
            key = self._token_hash(token); row = self._session(db, key, _now(self.clock))
            if type(expected_revision) is not int or row['revision'] != expected_revision: raise AuthenticationError('CONFLICT')
            changed = db.execute('UPDATE local_sessions SET revoked=1,revision=revision+1 WHERE session_hash=? AND revision=? AND revoked=0',
                                 (key, expected_revision))
            if changed.rowcount != 1: raise AuthenticationError('CONFLICT')


class _ClosingConnection:
    def __init__(self, db): self.db = db
    def __enter__(self): return self.db
    def __exit__(self, kind, value, traceback):
        try:
            self.db.rollback() if kind else self.db.commit()
        finally: self.db.close()
