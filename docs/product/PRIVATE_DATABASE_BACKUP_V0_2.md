# 私密本機資料庫備份

此命令為目前原生控制服務及研究工作者建立一致的 SQLite 資料庫快照。先停止服務，保留原始資料，再指定已存在本機父資料夾下的一個全新目的資料夾。

```text
R7.exe backup-databases --config <絕對設定路徑> --destination <全新私密備份路徑>
R7.exe verify-database-backup --config <同一設定路徑> --destination <備份路徑>
```

Linux 使用相同參數的 `r7`。目前 Ubuntu 原生實測仍為 NOT_RUN。`enroll-owner` 也取得 control 範圍鎖；先停止控制服務，再註冊本機 owner，避免註冊同時建立備份未涵蓋的 auth 資料庫。

輸出 `DATABASE_BACKUP_VERIFIED` 表示固定清單中的資料庫內容、結構與檔案雜湊通過檢查。輸出包含數量及備份識別碼，不列出資料列、密碼雜湊、session、路徑或憑證。`financial_authority=NONE`、`restore=NOT_PERFORMED`；備份不構成交易啟動或恢復授權。

清單涵蓋 canonical、intake、queue、research、control command、local auth 及 process supervision 資料庫。不存在的附屬資料庫會記錄在 manifest，canonical 不存在則失敗。其他檔案、dataset、snapshots、policy、owner selection、vault 與雲端設定不在此資料庫快照中；此功能不是完整資料根目錄的備份。

服務範圍鎖會拒絕與同一 instance 的控制／研究／保留 runtime／cloud publication 範圍並行。每個現有資料庫另外持有 `BEGIN IMMEDIATE` 寫入保留，取得全部保留後，以獨立唯讀連線呼叫 SQLite 備份 API。其間保留的 source transaction 關閉時回滾，不修改 canonical schema、資料列、授權或 owner evidence。這保留可恢復的 durable outbox 中間狀態，不宣稱跨資料庫分散式交易。SQLite 備份 API 的行為依據 [Python 3.12 文件](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)。

不複製執行中的 DB/WAL/SHM 檔案。目的資料庫單獨封存為 DELETE journal mode，關閉後再做結構與內容雜湊，manifest 最後才寫入。驗證器只對封存目的檔使用 SQLite immutable 唯讀模式，避免 WAL header 造成副檔寫入；活躍來源不使用 immutable。已存在目的資料夾、links/reparse、hard-link 資料庫、重複路徑、雲端或原資料根重疊路徑都拒絕。

備份資料分類為 `PRIVATE_LOCAL`，雲端發布為 `FORBIDDEN`。Local auth 資料库可能包含本機帳號雜湊與 session，因此備份目的資料夾在寫入任何資料前設為 owner-private：POSIX 0700／檔案 0600；Windows 以目前使用者 SID 建立 protected DACL，移除繼承授權，檔案繼承單一使用者授權。建立與驗證都讀取实际 OS 權限，不只依賴 mkdir 的 mode 參數。Windows 描述子的機制依據 [Microsoft 安全描述子格式](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format)及 [SetFileSecurityW](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-setfilesecurityw)。不讀取或複製 provider vault，亦不使用此命令輸出作為 cloud feedback。

預設操作期限為 30 秒；內部受信 API 可使用 5–300 秒。SQLite 寫入競爭每次最多等候 2 秒，SQL、逐頁備份及逐塊雜湊也有 monotonic deadline。損毀、期限、設定或清單變化會失敗；部分目的產物保留供本機診斷，不覆寫、不自動刪除，也不得用來復原。人工使用前必須再次執行完整驗證；manifest 與雜湊證明一致性，不替代受信來源、原授權或 E4/E5/E6 核對。

唯讀 immutable 語意依據 [SQLite URI 文件](https://www.sqlite.org/uri.html#uriimmutable)；只用於已停止寫入的備份產物。驗證在結構檢查前後重新讀取實際檔案雜湊與權限，期間改變則拒絕，未使用 metadata/content cache。

後續 S12/S13 工作仍包括完整 user-data 備份、復原的新 runtime generation、舊 lease/preflight/activation cache 失效、待處理部位管理交接、migration/upgrade/rollback、實際 trading runtime 範圍整合及各平台 installed-service 驗證。此檢查點不把其中任何一項標為 PASS。
