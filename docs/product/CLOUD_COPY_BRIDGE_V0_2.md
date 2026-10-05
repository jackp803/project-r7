# 本機 copy bridge 與回饋

此橋接由使用者先行配置的 rclone 執行檔、受保護設定參照、單一 remote alias 及指定 Google Drive root folder ID 組成。R7 不建立 OAuth 設定、不讀取設定內的 OAuth 位元組、不掃描整個 Drive。開發驗證使用本機檔案模擬遠端，分類為 `OFFLINE_TRANSPORT_SIMULATION`；實際 rclone、雲端、Ubuntu commissioning 仍為 `NOT_RUN`。

設定 JSON 必須保留在本機，schema 為 `r7-rclone-bridge-config-v0.2`。只接受下列欄位：`schema_version`、`executable`（絕對路徑）、`executable_sha256`（`sha256:` 加實際完整摘要）、`rclone_config_ref`（owner-private 設定參照）、`remote_alias`、`drive_root_folder_id`（明確選定 folder ID）、`root_id`、`private_work_root`、`timeout_seconds`（1–300）、`max_listing_bytes`（4096–8388608）、`max_transfer_bytes`（4096–17179869184）。私密工作資料夾必須已存在、在 local data root 內、與 cloud root 分離。Windows 使用目前使用者單一 SID 的 DACL；Linux 使用 owner 0700／0600。R7 不自動修改使用者既有 OAuth 檔案的權限。

本機 cloud stage 及指定遠端 root 必須已有相同 `.r7-root.json`：`{"root_id":"<明確 instance root identity>"}`。檔案遺失或不符時回報 `CLOUD_NOT_CONNECTED`，不初始化替代空資料夾。每次命令重新檢查 profile／執行檔摘要及設定參照權限。套件不能指定執行檔、remote、Drive folder、設定參照或額外 flags。

```text
R7.exe cloud-pull --config <本機 product JSON> --bridge-profile <本機 bridge JSON>
R7.exe cloud-import-dataset --config <同一設定> --bridge-profile <同一橋接> --dataset-id <id> --revision <revision>
R7.exe queue-research-feedback --config <同一設定> --run-id <實際完成的研究 run id>
R7.exe cloud-publish-outbox --config <同一設定> --bridge-profile <同一橋接> --limit 10
```

Ubuntu 使用相同參數的 `r7`；沒有把 Windows 測試移作 Ubuntu PASS。上述 cloud 命令是明確的本機 operator 行動，本次工程驗證不會使用它们連接真實雲端。所有 project workspaces、工具鏈與產物應放在使用者專案資料夾下，不能另建桌面散落的 project-r7 目錄。

下載只複製 `inbox/strategies/` 與 `datasets/`，不刪除作者檔案。先建立私密下載 generation，再檢查實際大小、listing 摘要、遠端名稱衝突及第二次 listing；整批驗證後才以逐檔原子替換將 payload 放進 stage，manifest 最後。單次 listing 最多4096 entries；策略 JSON 最多256KiB，manifest／notes 最多64KiB，dataset Parquet 每檔最多64MiB，批次另外受本機 transfer budget 限制。執行檔／scripts、逃逸路徑、Windows device name、大小寫別名、重複 Drive 名稱及 shortcuts 都拒絕；不呼叫 dedupe。

未成功 intake 的 author stage 可以隨後續同步更新；成功接受的私密 snapshot 與 E6 身分由既有 intake ledger 保護，來源改變會成為 CONFLICT，既有 snapshot 不變。dataset revision stage 不覆寫不同位元組。`cloud-import-dataset` 將已有下載的 manifest／容器摘要驗證並封存到 `local_data_root/datasets/<id>/<revision>/`，保留原始 namespace、manifest 及 Parquet 位元組，不解碼價格或提前觀察 sealed OOS。容器路徑以 dataset manifest 的資料夾為基準；例如本機 policy 的 `dataset_ref` 可指定 `datasets/<id>/<revision>/dataset.json`。完整 E1 logical hash、finality、availability、cost 及 split 驗證仍由實際研究 owner 在正確階段完成；輸出明示 `logical_verification=NOT_RUN`，不替使用者選擇研究或金融 policy。

發布前先驗證所有 payload 的隱私欄位、媒體、路徑、大小與整體傳輸上限；拒絕的內容不得進入可能由另一個客戶端同步的 stage。通過後用既有 folder publisher 留下 `LOCAL_STAGED`，再從新建私密 generation 上傳重新驗證的位元組。payload 先、manifest 後；已存在遠端物件必須逐位元組相同，否則保留原物件並 CONFLICT。上傳後重新 listing 並回讀每個 payload／manifest，確認本機 producer 沒有變化才回報 `CLOUD_ACKNOWLEDGED`。橋接依據官方 [copyto](https://rclone.org/commands/rclone_copyto/)、[cat](https://rclone.org/commands/rclone_cat/)、[lsjson](https://rclone.org/commands/rclone_lsjson/) 及 [Drive](https://rclone.org/drive/) 文件選定 copy／immutable／指定 root／跳過 shortcuts 的操作；文檔閱讀不構成真實工具驗證。

每個本機工具命令由既有 owned process 控制期限、終止及回收子程序樹，無 shell，使用明確設定參照並移除繼承的 rclone、proxy、Python 設定與憑證環境。stderr 丟棄；stdout 留在私密本機 capture，超限、非零或超時不返回部分成功。輸出大小限制是 application soft bound，不是 kernel disk quota；可能短暫超過限制的實際 capture 大小會如實計數。私密 generation／capture 保留供診斷，絕不提交 Git 或作為 cloud feedback。

`queue-research-feedback` 讀取實際研究 journal／finalist／holdout 結果，預設不公開金額或績效數值。需要公開時由本機 operator 明確加上 `--performance-opt-in`；憑證、OAuth、provider account/order/fill IDs、原始回應、完整本機路徑、username、IP inventories 與精確帳戶餘額仍不允許。報告使用版本化 allowlist、Decimal 原始字串、null 及 NOT_RUN；研究 exporter 尚無 forward owner binding，因此 PAPER duration／LIVE summary 明示 NOT_RUN／null。Artifact links 只在有實際發布參照的版本才提供；目前為空清單。

OOS 判定或樣本公開前，先在實際 trial ledger 記錄 `CHAT_OBSERVATION`；預設 opt-out 也不能把已公開判定的 holdout 再稱為未觀察。結果位元組／參照與 outbox PENDING 在研究資料庫同一交易提交，容量1000 items／16MiB。重試沿用原始內容與 operation ID，遠端完成與本機 ACK 之間崩潰可恢復。`cloud-publish-outbox` 在合計 batch limit 內發布 intake receipts 與 research feedback；各自 local owner stores 保有真實狀態。cloud owner 範圍鎖也納入 stopped-owner DB backup fencing。此功能不更改 E5／E6 授權，不啟動 PAPER／LIVE，也不在雲端放 SQLite／backup。

Feedback 包含 `feedback.json` 與自包含 `report.html`。HTML 先顯示實際階段狀態、已平倉交易數及嘗試次數；完整 JSON 可展開核對，缺值顯示 —，不把交易数當作獨立樣本。Bridge 在暫存寫入前及上傳前重新驗證 JSON allowlist、generation path 及與 JSON 完全一致的 HTML renderer 輸出；任意 HTML、remote JavaScript 或改寫版本拒絕。真實 selected-root roundtrip、native Ubuntu、完整服務／restore／host faults、real forward PAPER 及 provider commissioning 仍需分別留下實測證據。

## 有界真實雲端 commissioning 測試（尚未執行）

此測試需要另外取得 operator 的真實雲端授權，以及已配置的受保護 rclone 參照。工程測試不執行以下步驟，不建立 OAuth 或存取真實帳號。測試只使用新建、明確選定的專用測試 root；不得指向使用中的策略或資料集資料夾。

1. operator 確認專用 root folder ID、相同本機／遠端 marker、固定執行檔摘要，以及 timeout 60 秒、listing 上限 1MiB、transfer 上限 16MiB。保留 sanitized profile 摘要、OS、rclone 版本及 R7 distribution identity；不公開設定參照或 token。
2. 使用 authoring helper 產生單一新的合成 legacy 套件，只將這兩個 JSON 由 operator 放入指定測試 root 的 `inbox/strategies/<fresh-id>/`。執行一次 `cloud-pull`，預期 2 檔案及完全相同 byte hashes；執行第二次，預期相同位元組。不要執行 intake/research/runtime。
3. 對固定的合成 receipt／回饋測試資料執行一次 outbox publish；逐個遠端 payload 及 manifest 回讀摘要需等於原始摘要。只有 `CLOUD_ACKNOWLEDGED` 可以算 remote PASS；`LOCAL_STAGED` 算未完成。
4. 再次發布同一 operation，預期不新增物件且 durable ACK 保留。operator 可暫停該專用連線後重試另一個新合成 operation，預期 UNAVAILABLE／INCOMPLETE、不 ACK；恢復後沿用同一 operation 並驗證原始位元組。
5. 專用測試 root 的不同位元組與 duplicate-name 情境由 operator 手動安排；預期 CONFLICT、原始物件保留，無 dedupe／delete。只在該測試 root 模擬 marker 遺失，預期 CLOUD_NOT_CONNECTED、沒有建立替代 root。保留 operator 準備與恢復的事實，不宣稱 R7 執行了未發生的操作。
6. 每個情境分別記錄實際開始／結束 UTC、完整 executable SHA、設定摘要、結果、payload hashes、已回收的 owned commands 及未知／失敗情境。Ubuntu24／26 分開執行並記錄，沒有主機則 NOT_RUN。此 commissioning 不授予 PAPER／LIVE 或資金權限；測試完成後的清理由 operator 在專用 root 自行處理。
