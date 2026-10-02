"""Public login shell and locally built assets; authenticated API stays separate."""
from pathlib import Path
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


def mount_control_center(app,asset_root):
    root=Path(asset_root).absolute()
    if root.is_symlink() or not root.is_dir(): raise ValueError('Built local UI root required')
    index=root/'index.html'; assets=root/'assets'
    if index.is_symlink() or not index.is_file() or assets.is_symlink() or not assets.is_dir():
        raise ValueError('Built local UI index/assets required')
    # Assets are a trusted build product. Forbid links into data/config stores.
    for path in assets.rglob('*'):
        if path.is_symlink(): raise ValueError('Linked UI assets forbidden')
    if index.stat().st_size>65536: raise ValueError('Bounded UI entrypoint required')
    app.mount('/assets',StaticFiles(directory=assets,follow_symlink=False),name='control-assets')
    async def shell(): return FileResponse(index,media_type='text/html')
    app.add_api_route('/',shell,methods=['GET'],include_in_schema=False)
