"""Public native enrollment on a real OS terminal, with disposable test input.

The private qualification child owns the console and unchanged enroll-owner
command. No isatty/getpass override or authentication database writes are used.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def enroll(executable, config, password, *, env, timeout=45):
    if (not isinstance(password, str) or not 12 <= len(password) <= 128
            or any(c not in '0123456789abcdef' for c in password)):
        raise ValueError('Disposable hexadecimal local test input required')
    if os.name != 'nt':
        return _posix_enroll(executable, config, password, env=env, timeout=timeout)
    from application.platform.processes import _WindowsJob
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0  # Qualification helper is a hidden background console.
    job = _WindowsJob()
    process = None
    try:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), '--console-enroll',
             str(executable), str(config)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=Path(config).parent, env=env, startupinfo=startup,
            creationflags=subprocess.CREATE_NEW_CONSOLE)
        # The child waits at its private pipe before launching the native target.
        job.assign(process.pid)
        raw, errors = process.communicate(password.encode('ascii') + b'\n', timeout=timeout)
        if password.encode() in raw + errors or process.returncode:
            raise ValueError('Public native console enrollment failed')
        result = json.loads(raw)
        if result != dict(status='OWNER_CONFIGURED', actual_tty=True,
                          password_echoed=False, exit_code=0,
                          mechanism='WINDOWS_HIDDEN_OS_CONSOLE_PUBLIC_ENROLL_OWNER',
                          synthetic_local_login='EPHEMERAL_TEST_ONLY'):
            raise ValueError('Actual native terminal observations missing')
        if not job.terminate_and_wait(time.monotonic() + 5):
            raise ValueError('Native enrollment tree not reaped')
        return {**result, 'tree_reaped': True}
    finally:
        try:
            if process is not None and process.poll() is None:
                job.terminate_and_wait(time.monotonic() + 5)
                process.wait(timeout=5)
        finally:
            job.close()


def _console_child(executable, config):
    """Read real screen output and write real console keyboard events."""
    import msvcrt
    from ctypes import wintypes as w
    password = sys.stdin.buffer.readline(130).rstrip(b'\n')
    if not 12 <= len(password) <= 128 or any(c not in b'0123456789abcdef' for c in password):
        raise ValueError('Bounded disposable local test input required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)

    class COORD(ctypes.Structure):
        _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

    class CHAR(ctypes.Union):
        _fields_ = [('UnicodeChar', w.WCHAR), ('AsciiChar', ctypes.c_char)]

    class KEY_EVENT(ctypes.Structure):
        _fields_ = [('down', w.BOOL), ('repeat', w.WORD), ('virtual_key', w.WORD),
                    ('scan', w.WORD), ('character', CHAR), ('control', w.DWORD)]

    class EVENT(ctypes.Union):
        _fields_ = [('key', KEY_EVENT), ('padding', ctypes.c_byte * 16)]

    class INPUT_RECORD(ctypes.Structure):
        _fields_ = [('kind', w.WORD), ('event', EVENT)]

    declarations = {
        'CreateFileW': ([w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE], w.HANDLE),
        'GetConsoleMode': ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        'ReadConsoleOutputCharacterW': ([w.HANDLE, w.LPWSTR, w.DWORD, COORD, ctypes.POINTER(w.DWORD)], w.BOOL),
        'WriteConsoleInputW': ([w.HANDLE, ctypes.POINTER(INPUT_RECORD), w.DWORD, ctypes.POINTER(w.DWORD)], w.BOOL),
        'CloseHandle': ([w.HANDLE], w.BOOL),
    }
    for name, (arguments, result) in declarations.items():
        function = getattr(kernel, name)
        function.argtypes, function.restype = arguments, result
    files = []
    process = None

    def checked(value):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())

    try:
        handles = []
        for name, mode, flags in (('CONIN$', 'rb', os.O_RDONLY), ('CONOUT$', 'wb', os.O_WRONLY)):
            handle = kernel.CreateFileW(name, 0xc0000000, 3, None, 3, 0, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            observed = w.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(observed)):
                kernel.CloseHandle(handle)
                raise ValueError('Actual native OS console required')
            stream = os.fdopen(msvcrt.open_osfhandle(handle, flags | os.O_BINARY), mode, buffering=0)
            files.append(stream)
            handles.append(handle)
        process = subprocess.Popen(
            [executable, 'enroll-owner', '--config', config, '--username', 'native-fixture-owner'],
            stdin=files[0], stdout=files[1], stderr=files[1], cwd=Path(config).parent)
        deadline = time.monotonic() + 35

        def screen():
            buffer = ctypes.create_unicode_buffer(16384)
            count = w.DWORD()
            checked(kernel.ReadConsoleOutputCharacterW(handles[1], buffer, len(buffer), COORD(0, 0), ctypes.byref(count)))
            return buffer[:count.value]

        for marker in ('至少 12 字元', '再次輸入本機密碼'):
            while marker not in screen():
                if process.poll() is not None:
                    raise ValueError('Public native enrollment exited before hidden prompt')
                if time.monotonic() >= deadline:
                    raise ValueError('Actual native hidden prompt deadline')
                time.sleep(.05)
            for character in password.decode('ascii') + '\r':
                event = INPUT_RECORD()
                event.kind = 1
                event.event.key.down = True
                event.event.key.repeat = 1
                event.event.key.virtual_key = 13 if character == '\r' else 0
                event.event.key.character.UnicodeChar = character
                count = w.DWORD()
                checked(kernel.WriteConsoleInputW(handles[0], ctypes.byref(event), 1, ctypes.byref(count)))
                if count.value != 1:
                    raise ValueError('Native terminal keyboard input incomplete')
        code = process.wait(timeout=max(.1, deadline - time.monotonic()))
        observed = screen()
        if code or password.decode('ascii') in observed or 'OWNER_CONFIGURED' not in observed:
            raise ValueError('Actual public native hidden enrollment failed')
        print(json.dumps(dict(status='OWNER_CONFIGURED', actual_tty=True,
                             password_echoed=False, exit_code=code,
                             mechanism='WINDOWS_HIDDEN_OS_CONSOLE_PUBLIC_ENROLL_OWNER',
                             synthetic_local_login='EPHEMERAL_TEST_ONLY')))
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for stream in files:
            stream.close()


def _posix_enroll(executable, config, password, *, env, timeout):
    import pty
    import select
    import signal
    master, slave = pty.openpty()
    process = None
    raw = b''
    deadline = time.monotonic() + timeout
    try:
        process = subprocess.Popen(
            [str(executable), 'enroll-owner', '--config', str(config), '--username', 'native-fixture-owner'],
            stdin=slave, stdout=slave, stderr=slave, cwd=Path(config).parent,
            env=env, start_new_session=True)
        os.close(slave)
        slave = None
        for marker in ('至少 12 字元', '再次輸入本機密碼'):
            while marker not in raw.decode('utf-8', errors='replace'):
                if time.monotonic() >= deadline or process.poll() is not None:
                    raise ValueError('Actual native hidden prompt deadline')
                if select.select([master], [], [], .1)[0]:
                    raw += os.read(master, 4096)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Native terminal output bound')
            os.write(master, password.encode('ascii') + b'\n')
        code = process.wait(timeout=max(.1, deadline - time.monotonic()))
        while select.select([master], [], [], .1)[0]:
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                raw += data
            except OSError:
                break
        if code or password.encode() in raw or b'OWNER_CONFIGURED' not in raw:
            raise ValueError('Actual public native hidden enrollment failed')
    finally:
        reaped=False
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            cleanup_deadline=time.monotonic()+5
            while time.monotonic()<cleanup_deadline:
                try:os.killpg(process.pid,0)
                except ProcessLookupError:
                    reaped=True;break
                time.sleep(.01)
        os.close(master)
        if slave is not None:
            os.close(slave)
        if process is not None and not reaped:
            raise ValueError('Native POSIX enrollment tree cleanup unconfirmed')
    return dict(status='OWNER_CONFIGURED', actual_tty=True, password_echoed=False,
                exit_code=0, tree_reaped=reaped, mechanism='POSIX_PTY_PUBLIC_ENROLL_OWNER',
                synthetic_local_login='EPHEMERAL_TEST_ONLY')


if __name__ == '__main__':
    if os.name == 'nt' and len(sys.argv) == 4 and sys.argv[1] == '--console-enroll':
        _console_child(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit('Fixed native enrollment transport only')
