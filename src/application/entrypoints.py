"""Trusted native/source first-run and actual local E6 control composition."""
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from application.config import load_config
from application.platform.paths import absolute_path
from application.platform.resources import require_local_database_volume


NAMESPACE = 'LOCAL_RESEARCH'


def installed_root():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else None


def _outside_installation(path):
    installation = installed_root()
    if installation is not None and path.is_relative_to(installation):
        raise ValueError('User data and configuration must be outside the installation')


def initialize_profile(config_path, data_root, *, instance_id, port=8765, cloud_root=None):
    """Publish one fully validated complete profile without replacing any file."""
    config_path = absolute_path(str(config_path), 'config')
    data_root = absolute_path(str(data_root), 'local_data_root')
    _outside_installation(config_path)
    _outside_installation(data_root)
    if cloud_root is not None:
        cloud_root = absolute_path(str(cloud_root), 'cloud_root')
        _outside_installation(cloud_root)
        if config_path.is_relative_to(cloud_root):
            raise ValueError('Local configuration must be outside cloud staging')
    if not isinstance(instance_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', instance_id):
        raise ValueError('Invalid product instance identifier')
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Invalid loopback control port')
    require_local_database_volume(data_root / 'canonical.sqlite3')
    if config_path.exists():
        raise ValueError('Existing profile must be preserved')
    payload = dict(schema_version='r7-product-config-v0.2', product_instance_id=instance_id,
        local_data_root=str(data_root), cloud_root=None if cloud_root is None else str(cloud_root), control_api_host='127.0.0.1',
        control_api_port=port, diagnostic_only=True, paper_runtime_enabled=False)
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix='.r7-profile-', dir=config_path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write((json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        load_config(Path(temporary))
        try:
            os.link(temporary, config_path)
        except FileExistsError:
            raise ValueError('Existing profile must be preserved') from None
    finally:
        Path(temporary).unlink(missing_ok=True)
    return dict(status='PROFILE_CREATED', namespace=NAMESPACE, diagnostic_only=True,
                paper_runtime_enabled=False, cloud='NOT_CONNECTED', runtime='NOT_STARTED')


def enroll_owner(config, username):
    if sys.stdin is None or not sys.stdin.isatty():
        raise ValueError('Owner enrollment requires a local interactive terminal')
    _outside_installation(config.local_data_root)
    from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
    # Enrollment is an actual native database writer. Acquire before prompting
    # so stopped-owner backup cannot miss a newly created authentication store.
    with ProcessScopeLock('control:' + config.product_instance_id, lock_root=operational_lock_root(config)):
        password = getpass.getpass('本機密碼（至少 12 字元）: ')
        confirmation = getpass.getpass('再次輸入本機密碼: ')
        if password != confirmation:
            raise ValueError('Password confirmation does not match')
        from application.control_api.auth import LocalAuth
        auth = LocalAuth(config.local_data_root / 'local-auth.sqlite', namespace=NAMESPACE)
        auth.create_owner(username, password)
    return dict(status='OWNER_CONFIGURED', namespace=NAMESPACE)


def default_asset_root():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / 'ui'
    return Path(__file__).resolve().parents[2] / 'ui' / 'dist'


def create_local_app(config, *, asset_root=None):
    """Local research namespace only; operational owners require later selection."""
    from application.control_api.app import create_app
    from application.control_api.assets import mount_control_center, validate_control_center_assets
    from application.control_api.auth import LocalAuth
    from application.control_api.commands import CommandLedger
    from application.local_owners import LocalOwners

    _outside_installation(config.local_data_root)
    root = validate_control_center_assets(default_asset_root() if asset_root is None else asset_root)
    clock = lambda: datetime.now(timezone.utc)
    composition = LocalOwners(config, namespace=NAMESPACE, clock=clock)
    auth = LocalAuth(config.local_data_root / 'local-auth.sqlite', namespace=NAMESPACE, clock=clock)
    commands = CommandLedger(config.local_data_root / 'control-commands.sqlite', namespace=NAMESPACE, clock=clock)
    owners = composition.control_services()
    app = create_app(config, auth=auth, commands=commands, services=owners)
    app.state.local_auth = auth
    app.state.local_owners = composition
    mount_control_center(app, root)
    return app


def serve(config, *, desktop=False, config_path=None,stop=None):
    import uvicorn
    import webbrowser
    import threading
    from application.platform.supervision import ProcessSupervisor, SupervisionError
    from application.platform.shutdown import ManagedStop
    stop=ManagedStop() if stop is None else stop
    if not isinstance(stop,ManagedStop):raise ValueError('Actual managed stop scope required')
    with stop, ProcessSupervisor(config, 'control', config_path=config_path) as supervisor:
        app = create_local_app(config)
        app.state.process_supervisor = supervisor
        server = uvicorn.Server(uvicorn.Config(app, host=config.control_api_host, port=config.control_api_port,
                                               log_level='warning', access_log=False, workers=1))
        finished = threading.Event()
        def watch():
            opened = False
            while not finished.wait(0.2):
                try:
                    supervisor.require_current()
                except SupervisionError:
                    server.should_exit = True
                    return
                if stop.requested:
                    server.should_exit=True
                    return
                if desktop and server.started and not opened:
                    opened = True
                    host = config.control_api_host
                    webbrowser.open(f'http://{"[" + host + "]" if ":" in host else host}:{config.control_api_port}/')
        watcher = threading.Thread(target=watch, name='r7-control-supervision', daemon=True)
        watcher.start()
        try:
            server.run()
        finally:
            finished.set()
            watcher.join(3)
            if watcher.is_alive(): raise SupervisionError('CONTROL_STOP_NOT_CONFIRMED')
        supervisor.require_current()
    return 0
