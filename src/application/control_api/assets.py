"""Public login shell and locally built assets; authenticated API stays separate."""
from pathlib import Path
import stat
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


def _plain_path(path):
    if '..' in path.parts:
        raise ValueError('Canonical built UI path required')
    for current in (*reversed(path.parents),path):
        try:
            info=current.lstat()
        except OSError:
            raise ValueError('Built local UI path required') from None
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('Linked/reparse UI assets forbidden')


def validate_control_center_assets(asset_root):
    root=Path(asset_root).absolute()
    _plain_path(root)
    if root.is_symlink() or not root.is_dir(): raise ValueError('Built local UI root required')
    index=root/'index.html'; assets=root/'assets'
    _plain_path(index);_plain_path(assets)
    if index.is_symlink() or not index.is_file() or assets.is_symlink() or not assets.is_dir():
        raise ValueError('Built local UI index/assets required')
    # Assets are a trusted build product. Forbid links into data/config stores.
    for path in assets.rglob('*'):
        _plain_path(path)
    if index.stat().st_size>65536: raise ValueError('Bounded UI entrypoint required')
    return root


def mount_control_center(app,asset_root):
    root=validate_control_center_assets(asset_root)
    index=root/'index.html'; assets=root/'assets'
    app.mount('/assets',StaticFiles(directory=assets,follow_symlink=False),name='control-assets')
    async def shell(): return FileResponse(index,media_type='text/html')
    app.add_api_route('/',shell,methods=['GET'],include_in_schema=False)
