# 透過 SSH 查看本機控制中心

控制中心預設只監聽 `127.0.0.1`。Ubuntu 主機上的控制服務必須先由
管理者完成安裝、專用帳戶及本機設定；目前 Ubuntu 原生安裝、systemd
啟停與真實 SSH 通道驗收仍為 `NOT_RUN`。

1. 確認 Ubuntu 控制中心的連接埠，例如 `8765`，以及既有 SSH 主機、
   非 root 使用者、主機金鑰信任與登入方式。連線資料由操作者明確提供。
2. 在 Windows 的 R7 安裝目錄產生指令：

   ```powershell
   .\R7.exe plan-ssh-tunnel --host r7.example.test --username operator --port 8765 --ssh-port 22
   ```

   這只輸出 JSON 中的 `argv`，不建立連線、不讀取 SSH 設定或私鑰。
   `r7.example.test` 是文件範例，必須換成已確認的主機。
3. 核對目的地主機與連接埠後，由操作者在獨立終端執行輸出的 SSH 指令。
   對上述範例，指令為：

   ```powershell
   ssh -N -T -a -F none -o ExitOnForwardFailure=yes -o GatewayPorts=no -o StrictHostKeyChecking=yes -p 22 -l operator -L 127.0.0.1:8765:127.0.0.1:8765 r7.example.test
   ```

   主機金鑰必須已經過獨立核對；不要關閉嚴格主機金鑰檢查。若本機
   `8765` 已被其他服務使用，先停止衝突服務，或明確變更 Ubuntu 的控制
   埠並產生新指令。本機與遠端控制埠必須相同，才能符合實際 Host／Origin
   檢查。指令不轉送 agent、不執行遠端命令，且明確綁定本機迴路位址。
4. 在 Windows 執行：

   ```powershell
   .\R7.exe probe-control-access --port 8765 --expected-namespace LOCAL_RESEARCH --deadline-seconds 4
   ```

   `PUBLIC_AUTH_STATUS_AVAILABLE` 只表示本機迴路端點回傳符合格式的公開
   登入狀態。檢查不使用 cookie、密碼或 token，不登入，也不呼叫交易
   提供者。它不能證明回應來自 SSH 目的地主機；另一個本機 R7 服務可能
   使用同一個埠。仍需核對 SSH 終端及目的地主機。
5. 在瀏覽器開啟 `http://127.0.0.1:8765/`，使用既有 R7 本機操作者登入。
   關閉瀏覽器不會停止服務；關閉 SSH 終端會關閉通道，不會替代遠端服務
   的啟停操作。財務核准與交易恢復仍由本機權限和擁有者服務驗證。

檢查程序只接觸 `/api/v1/auth/status`，忽略環境代理、不跟隨重新導向，
限制回應大小及執行時間，並回收自己的子程序。`UNAVAILABLE` 與非零
結束碼表示檢查未通過。控制中心 API 不提供自動開放 LAN、防火牆或
遠端登入設定的功能。

實際開發驗證：22 項 SSH／CLI 測試通過，包含真正的受控迴路 HTTP
端點、代理忽略、重新導向拒絕、格式／命名空間錯誤及逾時程序回收。
Windows 已讀取的版本是 OpenSSH_for_Windows 9.5p2；本文件指令的選項
已與 [OpenSSH 手冊](https://man.openbsd.org/ssh)核對。這些證據不代表
Ubuntu 或真實 SSH 通道已驗收。Windows 原生新指令另需確切版本套件驗證。
