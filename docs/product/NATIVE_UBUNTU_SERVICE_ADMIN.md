# Ubuntu 服務檔案安裝與移除

目前提供 control／research 服務檔案的管理程式。原生 Ubuntu 24.04、26.04
安裝、systemd、renameat2、重開機與 SSH 驗收仍為 **NOT_RUN**。此工具不會啟用、
啟動或停止服務。連續交易 runtime 尚待 S12 完成，不能從此安裝結果推定已交付。

先按照 [服務前置條件](NATIVE_UBUNTU_SERVICE_PLAN.md) 準備專用非 root 帳戶、
不可變且 root 持有的原生套件、受保護且服務群組可讀的設定，以及服務帳戶持有的
私有本機資料／暫存／共享 scope 目錄。設定、執行版本、建置雜湊與實測記憶體
必須與預覽的完整對象一致。不得以 Windows 測試代替 Ubuntu 驗收。

首次操作還需要固定的 root 私有收據目錄。確認 `/var/lib` 是受保護的本機目錄後，
僅在收據目錄不存在時由操作員執行：

```sh
sudo mkdir --mode=0700 /var/lib/r7-service-admin
```

此命令在目錄已存在時失敗；既有目錄必須檢查為 root:root、0700，不能自動修復
持有人或權限。工具遇到缺少目錄時回傳 `PREREQUISITE_REQUIRED`，不會寫入或呼叫
systemd。工具拒絕連結、非單一硬連結檔案、不安全父目錄與非 root:root 管理身分。

從已安裝套件的絕對路徑執行以下預覽，將大寫佔位內容替換為目前實際完整值：

```sh
sudo /opt/r7/release/install-service.sh \
  --config /etc/r7/settings/product.json \
  --expected-revision FULL_40_CHARACTER_REVISION \
  --expected-build-hash sha256:FULL_BUILD_HASH \
  --expected-config-hash sha256:FULL_CONFIG_HASH \
  --expected-memory-bytes MEASURED_PHYSICAL_MEMORY_BYTES \
  --service-user r7-worker
```

預設 `DRY_RUN` 列出兩個 unit 與 creation-only scope 規則、檔案雜湊與
`operation_hash`。確認後，以相同參數追加 `--apply --operation-hash sha256:...`。
程式會重新核對完整原生對象、目標檔案與 systemd 狀態，再以排他建立方式寫入。
固定收據最後寫入 `/var/lib/r7-service-admin/installed-services.json`。已安裝且完整
一致的重試回傳 `ALREADY_INSTALLED`。中斷或部分失敗回傳 `INCOMPLETE` 並保留現況，
不會自動刪除、覆寫或把部分狀態當成成功。

管理的固定檔案為 `/etc/systemd/system/r7-control.service`、
`/etc/systemd/system/r7-research.service` 與 `/etc/tmpfiles.d/r7-scopes.conf`。
工具要求相關服務 inactive、disabled 或 static，沒有 pending job、drop-in 或
外來 fragment。檔案完成後僅執行 `systemctl daemon-reload`，另行回報結果；
reload 失敗會以非零退出碼回報。外部檔案、缺少收據或位元組改變均拒絕處理。

移除時改用套件內 `uninstall-service.sh`，先用相同完整對象參數預覽，再以顯示的
移除操作雜湊明確套用。先由操作員另行安排維護並確認服務已停止；此工具不會停止
任何程序。保持原本套件、設定與硬體對象不變，完成移除後才能更換版本或設定。
若原對象已漂移，工具拒絕移除，操作員必須檢查既有檔案與收據。

移除採用同一父目錄下新建的 root 私有 0700 暫存目錄與
`renameat2(RENAME_NOREPLACE)`。移入後先驗證原 inode、metadata 與位元組，才刪除
確認過的檔案。遭替換的檔案會以不覆寫方式還原；若原名稱已被另一檔案佔用，兩者
都保留，並在 `INCOMPLETE.preserved_removals` 回報私有暫存位置。刪除後出現的新
替換檔案也保留並回報未完成。只移除自己建立且空的暫存目錄，沒有遞迴清理。
此協定處理公開檔名的競態，不宣稱能隔離惡意主機管理員。

移除 disposition 以操作雜湊命名，保存在 root 私有收據目錄。二進位、設定、
資料庫、暫存、使用者狀態及共享 scope／鎖 inode 都保留。原生 Linux 確認之前，
受控 backend 測試僅證明程式協定；不代表 kernel 或 systemd 已通過。

參考：[Linux renameat2 API](https://man7.org/linux/man-pages/man2/rename.2.html)。
