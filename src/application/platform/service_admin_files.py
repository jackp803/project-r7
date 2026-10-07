"""Pinned fixed Ubuntu root-owned targets; never recursive or data operations."""
import ctypes,hashlib,os,re,stat,subprocess,uuid
from pathlib import Path,PurePosixPath
from application.platform.service_guard import _native_ubuntu
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.service_admin_removal import remove_verified_leaf

PARENTS=('/etc/systemd/system','/etc/tmpfiles.d','/var/lib/r7-service-admin')
FILES={'/etc/systemd/system/r7-control.service','/etc/systemd/system/r7-research.service','/etc/tmpfiles.d/r7-scopes.conf',
    '/var/lib/r7-service-admin/installed-services.json'}
PROPERTIES=('LoadState','ActiveState','SubState','UnitFileState','FragmentPath','DropInPaths','Job')

class ServiceAdminPrerequisiteError(ValueError):
    required_directory=PARENTS[2]
    def __init__(self):
        super().__init__('Create the missing /var/lib/r7-service-admin directory as root:root mode 0700; preserve existing directories')
def _protected(info,*,directory):
    if (info.st_uid!=0 or info.st_gid!=0 or info.st_mode&0o022
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink!=1)):
        raise ValueError('Protected root-owned regular target or directory required')
def _facts(info):return dict(device=info.st_dev,inode=info.st_ino,mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid)
def _stable(info):return (_facts(info),info.st_size,info.st_mtime_ns,info.st_nlink)
def _allowed(path):
    if path not in FILES and not re.fullmatch('/var/lib/r7-service-admin/uninstalled-[0-9a-f]{64}\\.json',path):
        raise ValueError('Fixed R7 administration target required')
    return PurePosixPath(path)

def _rename_noreplace(source_fd,source_name,target_fd,target_name):
    # Ubuntu's renameat2 is required; never fall back to an overwriting rename.
    library=ctypes.CDLL(None,use_errno=True)
    try:rename=library.renameat2
    except AttributeError:raise ValueError('Native renameat2 no-replace support required') from None
    rename.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint)
    rename.restype=ctypes.c_int
    if rename(source_fd,os.fsencode(source_name),target_fd,os.fsencode(target_name),1)!=0:
        error=ctypes.get_errno();raise OSError(error,os.strerror(error))

class _PinnedRemoval:
    def __init__(self,backend,selected,expected):
        self.backend=backend;self.selected=selected;self.expected=expected
        self.parent=backend.parents[str(selected.parent)];self.fd=None;self.created=False;self.identity=None
        self.name='.r7-removal-'+uuid.uuid4().hex;self.path=str(selected.parent/self.name)
    def __enter__(self):
        self.backend._check_parents()
        try:
            os.mkdir(self.name,0o700,dir_fd=self.parent);self.created=True
            self.fd=os.open(self.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.parent)
            info=os.fstat(self.fd);_protected(info,directory=True)
            if stat.S_IMODE(info.st_mode)!=0o700:raise ValueError('Fresh root-private removal quarantine required')
            self.identity=_facts(info);os.fsync(self.parent)
            return self
        except BaseException:
            self.__exit__();raise
    def _check(self):
        self.backend._check_parents()
        if self.identity is None:raise ValueError('Private removal quarantine was not verified')
        opened=os.fstat(self.fd);current=os.stat(self.name,dir_fd=self.parent,follow_symlinks=False)
        _protected(opened,directory=True);_protected(current,directory=True)
        if _facts(opened)!=self.identity or _facts(current)!=self.identity:
            raise ValueError('Private removal quarantine changed')
    def expect_original(self,expected):
        self._check();actual,_=self.backend.snapshot(str(self.selected))
        if not actual['exists'] or actual!=expected:raise ValueError('Exact owned removal target changed')
    def move_to_quarantine(self):
        self._check();_rename_noreplace(self.parent,self.selected.name,self.fd,'item')
        os.fsync(self.parent);os.fsync(self.fd)
    def quarantined_facts(self):
        self._check()
        return self.backend._snapshot_leaf(self.fd,'item',str(self.selected.parent)==PARENTS[2])[0]
    def restore_noreplace(self):
        self._check();_rename_noreplace(self.fd,'item',self.parent,self.selected.name)
        os.fsync(self.fd);os.fsync(self.parent)
    def unlink_verified(self):
        if self.quarantined_facts()!=self.expected:raise ValueError('Verified private removal subject changed')
        os.unlink('item',dir_fd=self.fd);os.fsync(self.fd)
    def original_exists(self):
        self._check()
        try:os.stat(self.selected.name,dir_fd=self.parent,follow_symlinks=False)
        except FileNotFoundError:return False
        return True
    def __exit__(self,*args):
        if self.fd is not None:
            try:
                self._check()
                try:os.stat('item',dir_fd=self.fd,follow_symlinks=False)
                except FileNotFoundError:
                    os.rmdir(self.name,dir_fd=self.parent);os.fsync(self.parent)
                else:self.backend.preserved_removals.append(self.path+'/item')
            except (OSError,ValueError):
                self.backend.preserved_removals.append(self.path)
            finally:os.close(self.fd);self.fd=None
        elif self.created:
            self.backend.preserved_removals.append(self.path)

class LinuxServiceBackend:
    def __init__(self):
        _native_ubuntu()
        if os.geteuid()!=0 or os.getegid()!=0:raise ValueError('Explicit native root administration identity required')
        self.parents={};self.baseline={};self.preserved_removals=[]
        try:
            for value in PARENTS:
                try:self._pin(PurePosixPath(value))
                except FileNotFoundError:
                    if value==PARENTS[2]:raise ServiceAdminPrerequisiteError() from None
                    raise
            if stat.S_IMODE(os.fstat(self.parents[PARENTS[2]]).st_mode)!=0o700:
                raise ValueError('Existing service receipt directory must already be root:root mode 0700')
            self.baseline={name:_facts(os.fstat(fd)) for name,fd in self.parents.items()}
        except BaseException:
            self.close();raise
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        for fd in self.parents.values():os.close(fd)
        self.parents.clear()
    def _pin(self,path):
        if '/' not in self.parents:
            fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);self.parents['/']=fd
            _protected(os.fstat(fd),directory=True)
        selected=PurePosixPath('/')
        for part in path.parts[1:]:
            parent=selected;selected=selected/part
            if str(selected) not in self.parents:
                fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.parents[str(parent)])
                self.parents[str(selected)]=fd;_protected(os.fstat(fd),directory=True)
        return self.parents[str(path)]
    def _check_parents(self):
        for name,fd in self.parents.items():
            opened=os.fstat(fd);current=os.lstat(name);_protected(opened,directory=True);_protected(current,directory=True)
            if _facts(opened)!=self.baseline[name] or _facts(current)!=self.baseline[name]:
                raise ValueError('Pinned protected service administration parent changed')
    def parent_facts(self):
        self._check_parents();return dict(self.baseline)
    def snapshot(self,path):
        selected=_allowed(path);self._check_parents();parent=self.parents[str(selected.parent)]
        return self._snapshot_leaf(parent,selected.name,str(selected.parent)==PARENTS[2])
    def _snapshot_leaf(self,parent,name,private):
        try:before=os.stat(name,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError:return dict(exists=False,sha256=None),None
        _protected(before,directory=False)
        if private and stat.S_IMODE(before.st_mode)&0o077:
            raise ValueError('Root-private ownership receipt or audit required')
        if before.st_size>64*1024:raise ValueError('Bounded owned service metadata required')
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            if _stable(os.fstat(fd))!=_stable(before):raise ValueError('Owned target changed during pinned open')
            raw=os.read(fd,64*1024+1);after=os.fstat(fd)
            current=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if _stable(after)!=_stable(before) or _stable(current)!=_stable(before) or len(raw)!=before.st_size:
                raise ValueError('Owned target changed during bounded pinned read')
        finally:os.close(fd)
        return dict(exists=True,sha256='sha256:'+hashlib.sha256(raw).hexdigest(),**_facts(before),size=before.st_size,mtime_ns=before.st_mtime_ns,links=before.st_nlink),raw
    def has_dropin(self,name):
        if name not in ('r7-control.service','r7-research.service'):raise ValueError('Fixed unit required')
        self._check_parents()
        try:os.stat(name+'.d',dir_fd=self.parents[PARENTS[0]],follow_symlinks=False)
        except FileNotFoundError:return False
        return True
    def write_new(self,path,raw,mode):
        selected=_allowed(path);self._check_parents()
        if type(raw) is not bytes or len(raw)>64*1024 or mode not in (0o600,0o644):raise ValueError('Bounded typed owned service bytes required')
        parent=self.parents[str(selected.parent)]
        fd=os.open(selected.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode,dir_fd=parent)
        try:
            os.fchmod(fd,mode)
            view=memoryview(raw)
            while view:
                count=os.write(fd,view)
                if count<=0:raise OSError('Incomplete owned service write')
                view=view[count:]
            os.fsync(fd)
        finally:os.close(fd)
        os.fsync(parent);self._check_parents()
        actual,copied=self.snapshot(path)
        if copied!=raw or actual['mode']!=mode:raise ValueError('Committed owned service bytes or mode changed')
    def remove_exact(self,path,expected):
        selected=_allowed(path)
        with _PinnedRemoval(self,selected,expected) as operation:remove_verified_leaf(operation,expected)
        self._check_parents()
    def _manager_command(self,argv):
        owned=spawn_owned(argv,cwd=Path('/'),limits=ResourceLimits(15),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            env=dict(PATH='',LANG='C',LC_ALL='C',SYSTEMD_PAGER='',SYSTEMD_COLORS='0'))
        code=owned.wait()
        if not owned.termination_report.reaped or owned.termination_report.reason=='TIMEOUT':
            owned.process.stdout.close();raise ValueError('Manager command did not finish with owned cleanup')
        try:raw=owned.process.stdout.read(8193)
        finally:owned.process.stdout.close()
        if code!=0 or len(raw)>8192:raise ValueError('Exact successful bounded manager response required')
        return raw.decode('utf-8')
    def manager_state(self,name):
        if name not in ('r7-control.service','r7-research.service'):raise ValueError('Fixed unit required')
        text=self._manager_command(['/usr/bin/systemctl','show',name,'--all','--no-pager','--property='+','.join(PROPERTIES)])
        result={}
        for line in text.splitlines():
            if '=' not in line:raise ValueError('Explicit manager property response required')
            key,value=line.split('=',1)
            if key in result or key not in PROPERTIES:raise ValueError('Exact unique manager properties required')
            result[key]=value
        if set(result)!=set(PROPERTIES):raise ValueError('Complete manager properties required')
        return result
    def reload(self):
        self._manager_command(['/usr/bin/systemctl','daemon-reload']);return True
