"""Actual private product backup/verify/restore of a controlled volume archive.

Fresh storage-only profile; no strategy, source admission, account, credentials,
runtime or financial permission. Original volume evidence stays untouched.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import shutil
import time

from application.config import ProductConfig,load_config
from application.local_owners import LocalOwners
from application.paper.capture_archive import ROOT
from application.platform.private_files import create_private_directory
from application.platform.product_backup import create_product_backup,verify_product_backup,restore_product_backup
from application.platform.restoration import require_valid_restoration
from tools.verify_public_archive_volume import peak_memory


def run(output,volume):
    if output.exists():raise ValueError('Fresh isolated backup volume output required')
    create_private_directory(output);data=output/'data';create_private_directory(data)
    archive=data/ROOT;create_private_directory(archive)
    original=json.loads((volume/'result.json').read_bytes())
    result=dict(protocol='ACTUAL_PRIVATE_PRODUCT_BACKUP_CONTROLLED_VOLUME_NOT_NATIVE_QUALIFICATION',
        logical_captures=original['logical_requests'],actual_provider_requests=0,actual_provider_responses=0,
        runtime='NOT_STARTED',financial_authority='NONE',capital='NONE',phases=[],
        source_hashes={p:'sha256:'+hashlib.sha256((Path(__file__).parents[1]/p).read_bytes()).hexdigest() for p in
            ('tools/verify_public_archive_backup_volume.py','src/application/platform/product_backup.py',
             'src/application/platform/database_restore.py','src/application/paper/capture_archive.py')})
    started=time.perf_counter();cpu=time.process_time()
    def record(name,producer):
        began=time.perf_counter()
        try:
            facts=producer();row=dict(phase=name,status='PASS',wall_seconds=time.perf_counter()-began,facts=facts)
        except (ValueError,RuntimeError,OSError) as error:
            row=dict(phase=name,status='FAIL',wall_seconds=time.perf_counter()-began,error_code=str(error))
            result['phases'].append(row);print(json.dumps(row),flush=True);raise
        result['phases'].append(row);print(json.dumps(row),flush=True)
    try:
        if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
        def copy():
            count=size=0
            for source in sorted((volume/'archive').iterdir()):
                if not source.is_file():raise ValueError('Fixed flat archive inventory required')
                target=archive/source.name;shutil.copyfile(source,target);count+=1;size+=target.stat().st_size
            return dict(files=count,bytes=size)
        record('COPY_FRESH_STORAGE_PROFILE',copy)
        config=ProductConfig('r7-product-config-v0.2','public-archive-volume-fixture',data,None,data/'canonical.sqlite3')
        with LocalOwners(config).registry_factory() as registry:registry.lifecycle_counts()
        record('CREATE_FULL_PRODUCT_BACKUP',lambda:create_product_backup(config,output/'backup',timeout_seconds=300))
        record('INDEPENDENT_VERIFY_FULL_PRODUCT_BACKUP',lambda:verify_product_backup(config,output/'backup',timeout_seconds=300))
        record('RESTORE_FULL_PRODUCT_BACKUP',lambda:restore_product_backup(config,output/'backup',output/'restored',timeout_seconds=300))
        restored=load_config(output/'restored/restored-product.json')
        state=require_valid_restoration(restored)
        if state['status']!='RESTORED_INHIBITED':raise ValueError('Restoration must remain inhibited')
        result['restoration']=state
        result['status']='ACTUAL_CONTROLLED_VOLUME_PRIVATE_BACKUP_VERIFY_RESTORE_PASS'
    except (ValueError,RuntimeError,OSError):result['status']='CONTROLLED_VOLUME_BACKUP_INCOMPLETE'
    finally:
        result.update(wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,**peak_memory())
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        print(json.dumps(result),flush=True)
    return 0 if result['status']=='ACTUAL_CONTROLLED_VOLUME_PRIVATE_BACKUP_VERIFY_RESTORE_PASS' else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--volume',type=Path,required=True);args=parser.parse_args()
    raise SystemExit(run(args.output.absolute(),args.volume.absolute()))
