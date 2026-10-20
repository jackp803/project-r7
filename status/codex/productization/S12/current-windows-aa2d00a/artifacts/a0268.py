"""Write actual local launch and clean-transfer instructions after verification."""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.platform.supervision import _local_path
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from application.platform.distribution import verify_distribution
from application.config import load_config
from application.platform.supervision import config_hash
from verify_portable_checkpoint import archive_subject,sha

def require_delivery_binding(revision,facts,portable,archive,packed):
    if (portable.get('revision')!=revision or portable.get('identity')!=facts
            or portable.get('archive_ref')!=archive.relative_to(PROJECT).as_posix()
            or portable.get('archive_hash')!=sha(packed)):
        raise ValueError('Delivered ZIP differs from actual passed portable installation')
def run(revision,qualification_attempt='first',backup_attempt='first'):
    from run_current_checkpoint import qualification_output
    names=('qualify','portable','headless','unattended','qualified-backup')
    stages={name:BASE/(name+'-'+revision[:7]+'-first') for name in names}
    stages['qualify']=qualification_output(revision,qualification_attempt)
    from verify_qualified_backup_checkpoint import backup_output
    stages['qualified-backup']=backup_output(revision,backup_attempt)
    checks={name:json.loads((path/'checkpoint.json').read_bytes()) for name,path in stages.items()}
    if any(not value['passed'] or value['revision']!=revision for value in checks.values()):raise ValueError('Actual completed current checkpoint required')
    installed=PROJECT/checks['portable']['installation_ref'];facts=verify_distribution(installed)
    _guard(ROOT,revision,installed,facts,fixed_profile(current_target()))
    build=BASE/('build-'+revision[:7]);archive,metadata,packed=archive_subject(build,revision,facts)
    require_delivery_binding(revision,facts,checks['portable'],archive,packed)
    digest=sha(packed)[7:]
    config=PROJECT/checks['unattended']['owning_profile']['config_ref'];selected=load_config(config)
    if (checks['unattended']['owning_profile']['config_hash']!=config_hash(selected)
            or checks['qualified-backup'].get('owning_profile')!=checks['unattended']['owning_profile']):
        raise ValueError('Actual stopped diagnostic configuration required')
    host=selected.control_api_host
    control_url='http://'+('['+host+']' if ':' in host else host)+':'+str(selected.control_api_port)
    target=PROJECT/'deliveries'/('current-windows-'+revision[:7]);_local_path(target)
    if not target.resolve().is_relative_to(PROJECT.resolve()) or target.exists():raise ValueError('Fresh local project delivery required')
    if not target.parent.exists():create_private_directory(target.parent)
    create_private_directory(target)
    exe=installed/'R7.exe';operations=stages['unattended']/'operations.json'
    guide=f'''# R7 目前 Windows 檢查點

版本：`{revision}`。Master：`IN_PROGRESS`。

完整安裝 ZIP：`{archive}`

SHA-256：`{digest}`

目前機器的乾淨安裝：`{installed}`。安裝包包含完整程式、資源、授權與首次設定文件；正常使用不需 Python、Node、Chat、Codex 或瀏覽器保持開啟。

## 目前電腦啟動

此設定已透過正常入口，完成工程基準的公開資料診斷研究、自動收件與耐久報告；正式審核政策仍未選定，研究保留 BLOCKED。一般 Paper 的 Windows 軟體資格 PASS 與實際策略／風控／工作流程選定分開；目前一般 Paper 與真實時間觀察未啟動。

先在 PowerShell 設定以下實際位置：

```powershell
$R7Executable='{exe}'
$R7Configuration='{config}'
$R7Operations='{operations}'
```

首次使用本機 Control Center 時，由你自行在終端機隱藏輸入新密碼；此資料夾沒有預設帳號密碼：

```powershell
& $R7Executable enroll-owner --config $R7Configuration --username local-owner
```

日常只啟動一個 coordinator，它管理所選 control/research 服務和調度：

```powershell
Start-Process -FilePath $R7Executable -ArgumentList ('run-product --config "'+$R7Configuration+'" --operations-profile "'+$R7Operations+'"') -WindowStyle Hidden
& $R7Executable product-status --config $R7Configuration
```

Control Center：`{control_url}`。瀏覽器可關閉，coordinator 仍運行。查看結果與停止：

若操作顯示 `RESPONSE_UNKNOWN` 與「待核對原命令」，請保留該命令並查核原結果，再按「使用原命令重試」。此入口沿用原命令 ID、內容與版本，取回已完成收據；若顯示 `COMMAND_IN_PROGRESS`，保留原命令，稍後再次查核。軟體驗收分別保留首次回應遺失的來源回歸，以及原生流程實際走到的分支。

```powershell
& $R7Executable product-status --config $R7Configuration
& $R7Executable stop-product --config $R7Configuration --role coordinator
& $R7Executable product-status --config $R7Configuration
```

停止是合作式請求。重複查詢 `product-status`，確認 coordinator、control、research 均為 `STOPPED`，才重新啟動或備份；尚未停止時先保留狀態與錯誤，不要強制改寫資料庫。

報告已產生於本機 durable outbox；自動上傳／真實雲端 ACK 未設定。本機實際報告：`{stages['unattended']/'observed-owner-report/report.html'}`。研究輸入是既有公開捕捉，這些驗證沒有新增公開 API 請求。公開捕捉累計實際 8 次請求／8 次回應，私人／交易／轉帳介面 0，無金鑰或資金。

這次驗證後的狀態為停止。沒有登錄開機啟動項、變更休眠或安全設定；重開機後可用同一入口啟動。若需要自動開機啟動，須先列明並另行同意主機變更。

## 移機與備份

將完整 ZIP 搬到目標機，核對 SHA-256、完整解壓。按照隨包 `FIRST_RUN.md` 建立全新資料／設定／帳號，先執行 `doctor --hardware --data-root <新本機資料位置> --json`，再完成該目標機的原生資格及正常使用驗收。

以上目前機器的 config／operations 與資格資料夾不放進移機安裝包。不要複製展示登入、開發秘密或另一台機器的運行授權。舊電腦（先前回報24GB，尚未實測）、Ubuntu24.04/26.04、真實雲端與正式政策選定仍是分開的外部項目；不需要現在取得舊機截圖。

實際完整備份／驗證／復原／再備份紀錄：`{stages['qualified-backup']}`。復原保持 `RESTORED_INHIBITED`，沒有恢復雲端或金融權限。新備份仍應在所有 owner 停止後，透過 `backup-product-data`、`verify-product-backup`、`restore-product-data` 正式入口完成；不要手改資料庫。

Chat authoring kit：`{stages['portable']/'chat-authoring-kit'}`。目前策略是明確標示的工程基準，不是 GPT 策略成果，也不是獲利證據。原始資料範圍／雜湊、成本／資金費率假設與分離的開發／封存區段保留；獨立 OOS 與真實時間樣本沒有冒充完成。

資源隔離目前為 `SOFT_LIMIT_ONLY`。本次資格不建立硬性記憶體上限、最大處理容量或保護輪詢時限保證；隔離測試保留了實際程序觀測，部位與券商時鐘仍明確標示為合成 FIXTURE 時鐘。

個別需求的語意對應、已識別的補測與其餘 Master 本機工作持續執行；本文件不宣稱 Master 全部完成。沒有真實交易金鑰、10U 下單、LIVE、資金、付費 API、GitHub compute 或 main 合併。
'''
    _guard(ROOT,revision,installed,facts,fixed_profile(current_target()))
    final_archive,final_metadata,final_packed=archive_subject(build,revision,facts)
    if final_metadata!=metadata or final_packed!=packed:raise ValueError('ZIP changed before delivery emission')
    require_delivery_binding(revision,facts,checks['portable'],final_archive,final_packed)
    write_private_new(target/'README.md',guide.encode())
    write_private_new(target/'SHA256SUMS.txt',(digest+'  '+archive.name+'\n').encode())
    write_private_new(target/'version.json',(json.dumps(dict(revision=revision,identity=facts,archive_ref=archive.relative_to(PROJECT).as_posix(),archive_sha256=digest,
        installation_ref=installed.relative_to(PROJECT).as_posix(),master='IN_PROGRESS',actual_verified_stages=list(checks),financial_authority='NONE'),indent=2)+'\n').encode())
    print(json.dumps(dict(guide=str(target/'README.md'),revision=revision,archive_sha256=digest)))
if __name__=='__main__':run(*sys.argv[1:])
