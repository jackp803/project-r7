# 一般 Paper 政策選擇紀錄 — 2026-10-21

同一 task `CODEX-R7-PRODUCTIZATION-MASTER-20261002`、同一 branch `codex/r7-productization-master-20261002`。政策審閱基準是 commit `729f19372202332839c06a0569ea74e363d6eef8` 的完整草案；原草案及所有驗證紀錄保留。

使用者已明確選擇：

1. 採用整套草案數值與明確標示的工程基準策略。
2. **先完成實際資金費率模型及驗證，再開始觀察**。未接受零資金費率 Paper 模型。
3. 若未來可以調整，這一輪選擇既有風控。這項條件成立，因此本輪接受現有控制；未授權把它永久固定。

政策可以在未來改版。修改必須保留版本、hash、選擇 generation 及稽核紀錄，重新執行受影響的研究／准入／運作檢查。舊證據保留原政策身分，不能直接轉成新政策 PASS。已存在的持倉保持原 E5 風控／保護綁定，不因改設定而默默重綁或平倉。既有 immutable research selection 不能原地覆寫；必要時以新 run／profile 及它自身的資格繼續。這些限制保護證據，不剝奪使用者日後改政策的選擇。

本輪風控仍是：模擬資金 1,000 USDT、0.001 BTC、1 倍、每筆名目額／margin 各上限 200 USDT、單一持倉、每日最多 6 次進場、已平倉回撤達 50 USDT 或連虧 5 筆時鎖新進場。沒有另增每筆／每日 USDT 損失硬上限，也不宣稱此鎖包含浮動損失。其餘成本、研究、robustness 與 forward 數值仍依原草案。

**已選定數值協議，不等於產品已安裝這組選擇或通過准入。** 原 `simulation.proposed.json` 內的零 funding_model 未選定；未修改原檔來冒稱使用者已接受零模型。新模型的 exact version/hash 與正式可執行 selection 尚待實作／驗證。

## 本輪實際完成

- 用既有 bffc558 Windows `R7.exe init-profile`，在專案內建立全新 `profiles/ordinary-paper-recorded-funding-20261021`。沒有複製另一個 store 的登入、receipt、資料庫或運行權限；未啟動任何服務／Paper run。
- 用既有 `acquire-public-data`，取得 2026-07-24 00:00 UTC～2026-10-20 00:00 UTC 的 OKX 公開唯讀 BTC 4H 資料：528 根已收盤 K 線、264 個已結算 funding 記錄、缺口／重複清單皆空。本輪實際公開請求／回應 **9/9**，累計 **17/17**；私人請求 0、credentials NONE、provider mutation 0、資金 NONE。
- 現有 capture inventory validator 已接受全部 31 個擷取檔案，逐檔 byte hash 核對一致。核對只讀公開原始擷取與 manifest／檔案 bytes，沒有將 sealed OOS 的價格／費率 rows 解碼給策略選擇或調參流程。
- 用既有 `author-package`，產生工程基準 `authoring-example-four-hour` **0.2.2** 的實際套件。content hash `sha256:501a3384efab8aa3697f9f126b1ed1715cb3392c3c6ac446e3f85a0e7b2e391f`；manifest hash `sha256:d13d93b5c6823b925db12572dee5f1ddfcf5feb7e37db26e5a86d6abd874bf1c`。兩個 payload 經既有 parser／hash validator 核對。沒有 GPT 身分、回測、CANDIDATE 或 Paper 成果宣稱。
- 第一次 author-package 呼叫把 `--notes` 誤當成文字參數；正式 CLI 要求檔案路徑。失敗屬呼叫方式錯誤，已保留，改用本機 notes 檔後成功，沒有修改產品程式或降低檢查。

資料 manifest hash：`sha256:3a10fc2a5cf21ca1b9a1fa21ed613d616e3c984612dcf589ad169e118f98b937`。來源、完整 byte inventory、公開原始回應、資料容器、authoring package 與獨立靜態 source maps 在本 checkpoint 分別保存。

## 未完成與下一步

實際費率模型、延後結算／崩潰恢復、正常入口與報告整合尚未實作驗證。既有契約 `funding-allocation-v0.1` §9.2 已允許非零 Paper model，E5／E6 可沿用既有 signed funding／exact interval／immutable evidence 規則；沒有泛稱等待已裁定的四項 PM mapping。具體設計見 [FUNDING_MODEL_DESIGN.md](FUNDING_MODEL_DESIGN.md)。

新 owning store 的實際固定 qualification 尚未執行；不得搬入舊 receipt。資料取得不等於獨立 OOS，仍須核對全部 prior family／trial／holdout，不能用新 profile／family 抹掉已看過的期間。正式 intake／development／robustness／final OOS、實際 CANDIDATE、容量留存／恢復與原生准入尚未完成。Paper、真實時間觀察均 NOT_STARTED。

原 bffc558 軟體／安裝包資格保持原範圍；這次沒有新 executable。原目標機、Ubuntu 24.04／26.04、雲端／SSH 及實際觀察樣本仍未被取代。Master IN_PROGRESS，沒有 main merge、GitHub compute、私人帳戶或資金使用。
