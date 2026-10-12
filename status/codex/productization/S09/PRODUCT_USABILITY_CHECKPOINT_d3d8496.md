Later current Windows native3-outcome checkpoint: [dd53369](PRODUCT_USABILITY_CHECKPOINT_dd53369.md). Its package includes the forward-seconds fix;the historical evidence below retains its original scope.

# 正常產品隔離流程檢查點：d3d8496

Master：CODEX-R7-PRODUCTIZATION-MASTER-20261002，分支 codex/r7-productization-master-20261002，狀態 IN_PROGRESS。2026-10-12 重新 fetch 的 main 為 9fd277798b1c51d1bc79b29a61bec81b552efeb1，沒有新裁定。M1–M11 均未完成；此檢查點沒有完整 requirement PASS 宣稱。

## 版本、安裝包與啟動

- 程式版本：d3d849642f278ccd39723355367bf1030d8f0619。
- Implementation：sha256:8d39e6f6adf87e18450ef6a7fc43dafee7f5b1ba43b1be20ac2c3781b4039fc6。
- Native build：sha256:cda73cb8bfbba31a84289272e0960b4aec028b9a4ce4a9e795c2467cee5da04e。
- 安裝包：C:\Users\jackp\Desktop\交易機器人主體\artifacts\r7-native-windows-S09-normal-fixture-d3d8496\r7-product-0.2.0-windows-d3d8496.zip。
- Archive：sha256:4b86a16aa38fc0953c5202efed8ce6a1e83d3648eadc67ce3415078e882ef32c。
- 已展開執行檔：C:\Users\jackp\Desktop\交易機器人主體\artifacts\r7-native-windows-S09-normal-fixture-d3d8496\dist\R7\R7.exe。

依 [正常隔離流程指南](../../../../docs/product/v0_2/NORMAL_FIXTURE_PAPER_FLOW.md) 建立全新 profile/data/synthetic-cloud，選 FIXTURE、prepare-fixture、configure-research、互動 enroll-owner、serve --desktop。UI 登入、scan/enqueue 後，在另一個終端執行 research-worker --once。產生候選後停止 owners、configure-paper、重新 serve、UI PaperStart，再於另一終端執行 paper-worker。指南末尾「native 尚待實測」是本次執行之前的來源敘述；以本報告逐項結果為準。所有執行／資料目錄放在專案根內且各根互不重疊。使用者自行以隱藏終端建立本機密碼，沒有預設密碼。

此包可試用明確標示的合成隔離流程。普通 LOCAL_RESEARCH 的 qualified-release mapping 仍未獲 Git PM/E6 接受；此包沒有取得普通 Paper 或 LIVE 啟動權限。

## 正常入口使用流程

| 步驟 | 來源入口 | 本次 Windows native 正常入口 |
|---|---|---|
| 首次設定／登入 | PASS；synthetic hidden TTY seam、最小 UI assets | PASS；公開 CLI、真正 native hidden TTY enrollment、Edge UI 登入 |
| 隔離資料／政策／假雲端／收到策略 | PASS；生成合成 Parquet／策略與選定政策、actual intake | PASS；prepare-fixture/configure-research、UI scan/enqueue |
| 研究／robustness／凍結 finalist／sealed OOS | PASS；標準獨立 child、actual E2/E3/E6 | PASS；frozen research-worker、獨立 child |
| 候選結果 | PASS，CANDIDATE | PASS，CANDIDATE；無 lifecycle/PASS 直接寫入 |
| OOS-loss 拒絕 | PASS，REJECTED | NOT_RUN；待全新隔離 profile |
| OOS 證據不足 | PASS，BLOCKED/BACKTESTING | NOT_RUN；待全新隔離 profile |
| 隔離 Paper 選定／啟動 | PASS | PASS；configure-paper、UI PaperStart，generation0/runtime NOT_STARTED/無 fills |
| 訊號／風控／模擬成交／保護 | PASS；actual E1/E2/E4/E5/E6 | PASS；獨立 paper-worker，OPEN_PROTECTED/generation1 |
| UI 實際狀態 | 既有來源 fixture UI 證據另列 | 5 個 actual packaged browser stages PASS；known forward label gap 見下文 |
| 暫停／worker 受控停止 | PASS | PASS；UI pause、公開 bounded ManagedStop，停止時保留保護部位 |
| 重啟／恢復／出場 | PASS | PASS；同 binding/position/opened_at、successor generation2、2 canonical fills/1 CLOSED trade |
| owner 結果／收據 staging | PASS | PASS；2 Paper reports，limit-one 可到 intake/research/Paper；LOCAL_STAGED、0 remote ACK |
| private backup／verify／restore | PASS | PASS；公開命令、原來源不變、追加 fence、保留 financial state/binding |
| 還原禁止啟動 | PASS | PASS；disconnected/diagnostic/disabled；worker exit2，actual RESTORED_INHIBITED，前後 journal 相同 |
| control server graceful stop | 無本次 credit | NOT_RUN；3 sessions 由 owned FORCED cleanup 回收 |

UI 現有缺口：讀 forward_observations.actual_elapsed_seconds，但 owner 回傳 real_elapsed_ns。本次 raw 值 0、UI「未提供」，下一步修正 owner-derived 秒數並加回歸。Entry order role raw 值確實為 null，「未提供」是實際未知，不補造 ENTRY。Protected/paused 與 closed 真實截图由 Codex 自我檢視；沒有 independent visual acceptance。

合成 UTC 時鐘／假行情／假雲端皆明確隔離；健康與登入仍用真實 UTC。real_elapsed_ns=0、assessment BLOCKED、performance OPT_OUT，無 READY_FOR_APPROVAL／financial Approval。

## 服務組合與驗證範圍

正常 create_local_app/LocalOwners 已接 actual intake/research/E6 registry、PaperStart/read、immutable fixture release reader、公開獨立 PaperOwnerWorker/PaperScheduler、owner feedback/outbox、private backup/restore。Loader/factory 為產品內部固定組合；公開入口沒有 factory／替換 executable／clock／PASS 參數。Native 流程走公開 CLI／API／UI，沒有 DB／lifecycle／Approval 灌入、test app、route mock 冒充產品。

一般 LOCAL_RESEARCH 保留 Paper read／未獲准入；software qualification receipt 或 native inventory 不發行 financial/runtime release。來源 synthetic TTY/minimal UI、historical native fixture 各有範圍，不替代本次 actual native TTY/browser，也不替代真實資料／forward。

Exact-clean source 33 commands／2101 execution instances PASS（phase1 247、phase2 1854），0 failures/errors/skips，636 pinned inputs 不變。2101 為執行實例，非 unique tests／產品驗收總數。Native baseline 6 stages／25 scoped scenarios／28 commands PASS；normal positive flow 另有22 owned commands（17 native CLI＋5 browser）、1 separate native TTY enrollment、3 separate control starts。Owned Windows Job trees 已回收、temporary awake 已還原。

[Disposition](normal-fixture-qualified-d3d8496-py312/disposition.json) 與 [hash manifest](normal-fixture-qualified-artifact-hashes-d3d8496.json) 留存329份 sanitized artifacts，明列 raw/published hashes。Private profile/dataset/stores/auth/session/backups/native archives 不入 Git。失敗666fdde legacy minimal restore、first Edge prelaunch harness failure、bounded RED/diagnostic 全保留且無 acceptance credit；修正後全新 clean source/native corpus 分開通過。早期部分 external driver 未留存，只列不完全 replay 的歷史。Bounded independent source/tool review0 Critical/Important，reviewer_execution NONE；沒有 whole-product approval。

## 平台與外部缺口

| 項目 | 狀態 |
|---|---|
| Windows11 x86-64 | 本報告 scoped source/native positive FIXTURE PASS；完整產品尚未驗收 |
| Ubuntu24.04 x86-64 | NOT_RUN；無已指定、獲准本機 host |
| Ubuntu26.04 x86-64 | NOT_RUN；無已指定、獲准本機 host |
| 真實 cloud／dataset | NOT_RUN |
| 真實時間 Paper／forward | NOT_RUN；合成時間0 credit |
| Provider／capital／LIVE | NOT_RUN；requests0、credentials NONE、capital NONE |
| GitHub compute／main merge | NOT_USED／NOT_PERFORMED |

Ubuntu 各 target 待提供獲准本機 x64 host，Python3.12 build environment、Node24及locked dependencies/offline cache、互不重疊的本機 SQLite/data/cloud/package roots、指定 service account/systemd。不安裝 OS、不改磁碟、不轉 hosted compute。下列變數須指向該 host 專案內全新輸出；是第一批待執行命令，smoke 不代替完整驗收：

~~~sh
python3.12 tools/run_credential_free_tests.py --focused --require-clean --expected-revision d3d849642f278ccd39723355367bf1030d8f0619 --output "$source_qualification_output"
python3.12 tools/build_product.py --output "$native_output" --expected-revision d3d849642f278ccd39723355367bf1030d8f0619
python3.12 tools/verify_native_product.py --package-root "$native_output/dist/r7" --output "$native_smoke_output"
~~~

完整 source policy、正常 UI/research/Paper/outbox/restore、native install/service/restart/reboot/SSH/capacity 仍須在各 host 留證。Cloud/dataset/forward 另待其實際 commissioning。

## PM/E6 裁定與下一步

[Decision bundle](PRODUCT_USABILITY_DEPENDENCIES_20261008.md) 保留普通 Paper 的四項決定：qualification check inventory/platform scope、initial native release/build mapping、config/risk/simulator/account generations、independent runtime generation/currentness。該文件逐項列最小方案／影響與被阻塞操作。S12 proposal 保持 PROPOSED_NOT_ACTIVE；FIXTURE 接通不接受 proposal，不放寬 E7 財務語意。

保存 checkpoint 後繼續 forward-seconds UI、native rejected/insufficient 及剩餘 Master；外部決定不阻止獨立工作。不以此報告或測試數承諾獲利日期。
