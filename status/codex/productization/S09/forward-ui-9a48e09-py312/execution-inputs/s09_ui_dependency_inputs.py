"""Bounded ordinary Node inputs and fresh derived caches for local UI evidence."""
from pathlib import Path
import json,os,stat
from s09_normal_fixture_source_qualify import REPO
from application.platform.supervision import _local_path
from application.platform.private_files import create_private_directory
from application.cloud.safe_files import _windows_read,_posix_read
from s09_owner_worker_native_regression import sha

ROOT=REPO/'ui/node_modules'
CACHES=('.vite','.vite-temp')
def protected_bytes(path,limit=128*1024**2):
    _local_path(path)
    return (_windows_read if os.name=='nt' else _posix_read)(path,limit,require_single_link=True)
def walk(root):
    def reject(error):raise error
    for folder,dirs,files in os.walk(root,followlinks=False,onerror=reject):
        current=Path(folder);_local_path(current)
        for name in dirs:_local_path(current/name)
        yield current,dirs,files

def installed_dependencies():
    _local_path(ROOT);result={}
    for current,dirs,files in walk(ROOT):
        if current==ROOT:dirs[:]=[name for name in dirs if name not in CACHES]
        for name in sorted(files):
            path=current/name
            result[path.relative_to(ROOT).as_posix()]=sha(protected_bytes(path))
    assert result
    return result

def cache_inventory():
    result={};total=0
    for name in CACHES:
        root=ROOT/name;_local_path(root)
        if not os.path.lexists(root):continue
        assert root.is_dir()
        result[name+'/']='DIRECTORY'
        for current,dirs,files in walk(root):
            assert len(result)+len(dirs)+len(files)<=4096
            for child in dirs:result[(current/child).relative_to(ROOT).as_posix()+'/']='DIRECTORY'
            for child in files:
                path=current/child;raw=protected_bytes(path,64*1024**2)
                total+=len(raw);assert total<=64*1024**2
                result[path.relative_to(ROOT).as_posix()]=sha(raw)
    return result

def fresh_caches(output):
    prior=cache_inventory()
    archive=output/'private-previous-caches'
    create_private_directory(archive)
    root_resolved=ROOT.resolve(strict=True);output_resolved=output.resolve(strict=True)
    for name in CACHES:
        source=ROOT/name;destination=archive/name
        if not os.path.lexists(source):continue
        _local_path(source);_local_path(destination)
        assert source.resolve(strict=True).is_relative_to(root_resolved)
        assert destination.resolve(strict=False).is_relative_to(output_resolved)
        assert not os.path.lexists(destination)
        os.replace(source,destination)
    assert cache_inventory()=={}
    return dict(preexisting_cache_inventory=prior,preserved_at='private-previous-caches',
        excluded_from_publication=True,fresh_derived_cache_inventory={})
