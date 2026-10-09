# 隔離測試模式的正常 Paper 使用流程

這是 `r7-product-v0.2` 明確標示的 `FIXTURE` 模式：合成資料、隔離模擬帳戶、本機假雲端資料夾，以及合成 UTC 情境時鐘。它用來驗證產品接通。真實 forward 觀察時間保持零；不產生真實績效、金融 Approval、LIVE 或資金權限。

`LOCAL_RESEARCH` 仍是預設。一般 Paper 的 qualified-release mapping 仍為 `PROPOSED_NOT_ACTIVE`，需要 Git 中的 PM/E6 裁定。此流程不改變該狀態。還原的 profile 仍保持 disconnected / inhibited。

## 入口與資料位置

將所有 profile、資料、假雲端及備份放在使用者的專案資料夾內。資料、假雲端與安裝目錄必须互不重疊；不使用桌面上的獨立暫存工作資料夾。

新版本提供以下公開命令。已發布的 `af01b45` 安裝包不包含這次新增命令；完整來源與新原生包須各自驗證，不能把舊原生 PASS 轉給此版本。

```powershell
# 指向包含這些命令、已核對版本的新 r7.exe。
$r7 = Join-Path $packageRoot 'r7.exe'
$profile = Join-Path $projectRoot 'fixture-run\product.json'
$data = Join-Path $projectRoot 'fixture-run\data'
$cloud = Join-Path $projectRoot 'fixture-run\synthetic-cloud'

& $r7 init-profile --config $profile --data-root $data --cloud-root $cloud --execution-mode FIXTURE
& $r7 prepare-fixture --config $profile --scenario positive
& $r7 configure-research --config $profile --selection-profile (Join-Path $data 'fixture-inputs\selection.json')
& $r7 enroll-owner --config $profile --username local-owner
& $r7 serve --config $profile --desktop
```

`enroll-owner` 在互動終端以隱藏輸入建立自己的本機登入密碼。產品没有預設登入密碼。Control Center 以 loopback 提供登入及實際 owner 資料。

在 Control Center 登入、掃描策略 inbox、選取生成的研究政策，並提交研究工作。另一個終端使用正常入口：

```powershell
& $r7 research-worker --config $profile --once
```

工作由獨立且受資源限制的標準子程序執行實際研究、robustness、凍結 finalist 及 sealed OOS。檢查 Control Center 的實際狀態。`positive` 合成案例可產生 CANDIDATE；用另一組全新 profile/data/cloud 執行 `oos-loss` 或 `insufficient-oos` 可分別看到拒絕或證據不足。不得改寫 lifecycle、結果或 sealed ledger 來切換情境。

## Paper 與恢復

停止 control/research/runtime/cloud owners 後，以生成的明確本機輸入選擇 Paper：

```powershell
& $r7 configure-paper --config $profile --selection-profile (Join-Path $data 'fixture-inputs\paper-selection.json')
& $r7 serve --config $profile --desktop
```

在 Control Center 選取實際 CANDIDATE 與隔離 Paper 政策，提交 PaperStart。API 只保存已接受的 E6 初始 run；此時 generation 為零、runtime 為 NOT_STARTED、沒有成交。

另一個終端啟動獨立 worker：

```powershell
& $r7 paper-worker --config $profile --maximum-ticks 2
```

此命名合成情境提供兩根已完成且 UTC 對齊的 `1h` K 線。產品自己的模擬時鐘以整點開始，每 tick 前進一秒；程序健康與本機登入保留實際 UTC。訊號、風控、ACK、後續成交與保護均由既有 E1/E2/E4/E5/E6 owner 產生。此兩 tick 情境可保留 OPEN_PROTECTED 部位後受控停止；停止沒有宣稱已平倉。

在 Control Center 暫停新增交易，然後重新啟動：

```powershell
& $r7 paper-worker --config $profile --maximum-ticks 4
```

worker 從實際 E6 已接受 start 與持久化 checkpoint 恢復，保留 position identity、first-fill anchor、binding 與保護。合成行情再觸發 target 出場；UI 讀取真正的 canonical fills、CLOSED position 及 trade result。generation 由 successor 取得，API 讀取及 pause 不取得 runtime generation。

省略 `--maximum-ticks` 時持續運行，Ctrl+C 使用既有 cooperative stop。tick bound 僅允許 1–10000。公開入口沒有 factory、執行檔、clock 或 PASS 覆寫參數。版本或選定政策變更會被准入檢查拒絕。

## 結果、收據與私密備份

worker 在退出及 quiescent detach 前，以當前實際 owning runtime 產生預設績效 opt-out 的回饋報告。樣本或模擬時間不足會保留 BLOCKED，不會自動升為 READY_FOR_APPROVAL。回饋佇列滿時保留待重試附件與明確錯誤，其他受保護 run 的 deadline 管理繼續。

研究工作畫面提供 `owner_run_id` / `owner_report_ref`。研究回饋及本機 staging 入口為：

```powershell
& $r7 queue-research-feedback --config $profile --namespace FIXTURE --run-id $ownerRunId
& $r7 publish-fixture-outbox --config $profile --limit 1
```

重複 bounded staging 命令可依序到達 intake 收據、研究報告及 Paper 報告。已本機 staged 的項目不反覆占用此隔離入口的 batch budget；一般遠端 publisher 仍保留原本的 staged-item retry。狀態為 LOCAL_STAGED，`cloud_acknowledged=0`、`remote_verification=NOT_RUN`。每個 bundle 的 manifest 記錄 exact operation、payload 與 artifact hashes。這不代表已連接或驗證真實雲端。

所有 owners 停止後：

```powershell
& $r7 backup-product-data --config $profile --destination $privateBackup
& $r7 verify-product-backup --config $profile --destination $privateBackup
& $r7 restore-product-data --config $profile --backup $privateBackup --destination $freshRestore
```

備份包含被選定的研究/Paper 政策、typed owner subject、原始有效期、封存策略、資料 containers 及 owner stores。未知檔案仍是 coverage failure，沒有整個 fixture 資料夾的白名單。備份保持 PRIVATE_LOCAL，不發布。

還原追加 fencing generation，保留原始 financial state/binding/checkpoint；原資料不被修改。還原 profile 的雲端為 disconnected、diagnostic 為 true、Paper runtime 為 false；這個公開 fixture worker 拒絕啟動還原 profile，等待既有 reconciliation / reauthorization。

## 此增量的實測範圍

正常 source composition 已實際跑過上述研究與 Paper owner 流程、獨立 worker 程序、HTTP PaperStart/pause/read、canonical close、limit-one local staging、完整私密備份及 inhibited restore。來源測試使用合成隱藏終端輸入與最小 UI assets；它不代表實際原生互動登入或 browser 點擊驗收。

新原生 Windows 安裝包、其正常互動登入/研究/Paper/browser 流程與 Ubuntu 24/26 必須另行實測。真實雲端、真實資料與真實時間 forward 也保留各自的驗收狀態。fixture 接通不能替代這些驗收。
