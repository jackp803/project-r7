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
