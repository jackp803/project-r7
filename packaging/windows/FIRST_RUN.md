# R7 Windows 本機啟動

此封裝檢查點提供診斷、首次設定、本機帳號與 Control Center。
完整 research/runtime 服務、備份復原與實盤部署仍需各自的驗收證據。
封裝清單的雜湊是本機完整性識別，不是簽署發行證明或交易許可。

解壓縮整個 R7 資料夾。保留 R7.exe、_internal、licenses 和 distribution.json。
正常啟動不需要 Python、Node 或 PYTHONPATH。將設定與資料放在安裝資料夾之外，
也不要把 SQLite 資料庫放在雲端同步資料夾。

在本機終端機執行（請將絕對路徑改成自己的專案資料夾）：

```powershell
.\R7.exe doctor --hardware --data-root 'C:\R7資料' --json
.\R7.exe init-profile --config 'C:\R7資料\設定.json' --data-root 'C:\R7資料\本機資料'
.\R7.exe enroll-owner --config 'C:\R7資料\設定.json' --username local-owner
.\R7.exe serve --config 'C:\R7資料\設定.json' --desktop
```

密碼僅透過終端機隱藏輸入與確認，不接受命令列密碼。
服務模式使用 serve 而不加 --desktop；只綁定 127.0.0.1。
首次設定維持診斷模式，PAPER 未啟用，雲端與交易服務未設定。
重複 init-profile 不會覆寫既有設定。Ctrl+C 停止控制介面服務。
此入口不啟動 SHADOW、PAPER 或 LIVE，不含預設登入密碼或供應商憑證。

## 完成設定後的日常啟動

先讀隨包的 HEADLESS_LOCAL_OPERATIONS.md，建立本機明確選定的 operations.json。
研究資料與政策須先經 configure-research 設定；一般 Paper 另須完整版本資格、
已選定的本機政策與正式產品授權。診斷研究不能藉由日常調度升級為候選。
下列單一入口管理所選服務、收件與報告，不需要 Chat、Codex 或瀏覽器保持開啟：

```powershell
.\R7.exe run-product --config 'C:\R7資料\設定.json' --operations-profile 'C:\R7資料\operations.json'
.\R7.exe product-status --config 'C:\R7資料\設定.json'
.\R7.exe stop-product --config 'C:\R7資料\設定.json' --role coordinator
```

若需關閉啟動用終端機，可在 PowerShell 用下列方式啟動同一個入口：

```powershell
Start-Process -FilePath (Join-Path (Get-Location) 'R7.exe') -ArgumentList 'run-product --config "C:\R7資料\設定.json" --operations-profile "C:\R7資料\operations.json"' -WindowStyle Hidden
```

這不會登錄開機啟動項。主機重新開機後需重新啟動同一入口；自動開機啟動、
電源／休眠與安全設定均須先列明必要變更並取得另外同意。不要複製另一台機器的
operations.json 當作移機授權。停止不等於平倉；先透過 Control Center 核對持倉。

## 私人備份與移機

先停止 coordinator，再確認 control、research、runtime、cloud 服務均已停止。
有外部自行啟動的 owner 時，依其實際狀態另外停止；備份入口仍會檢查 owner 排他鎖。
使用全新的本機目的目錄，保留原資料及既有備份：

```powershell
.\R7.exe backup-product-data --config 'C:\R7資料\設定.json' --destination 'C:\R7備份\新備份'
.\R7.exe verify-product-backup --config 'C:\R7資料\設定.json' --destination 'C:\R7備份\新備份'
.\R7.exe restore-product-data --config 'C:\R7資料\設定.json' --backup 'C:\R7備份\新備份' --destination 'C:\R7資料\全新復原目錄'
```

復原保持 RESTORED_INHIBITED，不恢復雲端連線或運行授權。活躍 SQLite 留在本機，
不要放進雲端同步資料夾。公開行情暫存診斷有界且不包含於產品備份；需保留時另行封存。
安裝包只包含程式與授權文件，不包含開發者設定、登入、資料庫、私鑰或帳戶憑證。

一般 Paper 的政策與原始資格證據會按既有選擇、收據及雜湊完整備份，包含失敗歷史。
修改政策時應保留原檔，使用不同版本檔名；若多個已保存世代將同一路徑綁定到不同
內容，備份會拒絕，不能把新內容當作舊證據。資格驗證的暫存工作資料與登入資料
不會混入資格證據檔；備份仍拒絕未識別檔案。現有整體檔案與傳輸上限保持有效，
政策選擇及資格歷史各有 256 筆檢查上限；達限時保留資料並處理容量，系統不自動刪除。

目標機驗收清單：

1. 核對隨交付 build-result.json 的完整版本、ZIP SHA-256；完整解壓到全新目錄。
2. 執行 doctor，保留實際 CPU、RAM、可用記憶體、本機磁碟與 SOFT_LIMIT_ONLY 限制。
3. 使用新設定與本機隱藏輸入建立新帳號，確認 loopback Control Center、拒絕未登入操作。
4. 依該版本與目標機執行資格及正常使用流程；開發機結果不等於舊電腦或 Ubuntu 合格。
5. 測試單一入口啟動、停止、重複啟動與崩潰後恢復，確認外部 owner 不會被接管。
6. 驗證私人備份及全新目錄復原保持禁用；重新選定本機政策及工作流程後才可運行。
7. 真實雲端設定、正式政策與足夠真實時間樣本分別保留待驗收，不能用 FIXTURE 結果替代。
