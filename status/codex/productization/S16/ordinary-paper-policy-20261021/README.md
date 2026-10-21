# 一般 Paper 正式政策完整草案 — 2026-10-21

狀態：**DRAFT_NOT_SELECTED，尚未套用，尚未啟動一般 Paper 或真實時間觀察。**

這是應使用者「先給我完整草案」準備的審閱文件。所有金額都是本機模擬 USDT，沒有真實帳戶或資金。數值是建議的研究協議，並非已證明能獲利或普遍足夠的統計標準。結果不合格或證據不足時保留原結果，不為升級候選而調低門檻。

同一任務 `CODEX-R7-PRODUCTIZATION-MASTER-20261002`、同一實作分支 `codex/r7-productization-master-20261002`。本次核對的 authoritative main 是 `7d1f447c8a9e8b46dc5ecc7bf0a78e1d63680812`，準備前 HEAD 是 `f456195d4f6db8c42027468552339b26eeceaf88`。

既有合格 Windows executable 保持 `bffc558b9652dc41c0804896436ac7ad8744f7f8`；實作 hash `sha256:387238c130af7b96f59578fdfec3b1fa76fc9443daa8a174be00d79ba166c666`、build hash `sha256:639a0390b56f904c62eb375b5c0e483f8e34c9faffb906e7f60ba6e67fc3b37e`。本政策文件與資料形狀檢查不發出新軟體資格，也不替新 owning store 發 receipt。原資格證據見 [current Windows disposition](../../S12/current-windows-bffc558/disposition.json)。Master 仍 IN_PROGRESS。

## 你需要決定的三組項目

1. **數值與研究輸入**：採用下列整套數值及明確標示的工程基準策略，或列出要改的項目。沒有找到已合格的 GPT BTC 4H 策略包；工程策略不能冒充 GPT 研究成果。
2. **Paper 資金費率模型**：接受目前產品支援的「資金費率固定為零」模型，僅用於明確揭露模型的 Paper 觀察；或要求先補足實際資金費率模型，完成相應設計與驗證後才觀察。這個選擇不改變歷史研究必須用實際資金費率的要求。
3. **損失上限的意義**：接受現有名目部位、已平倉回撤、連虧與進場頻率限制；或要求新增獨立的「每筆／每日最多虧損 USDT」控制後才允許進場。現有欄位不能保證每筆最多虧某個金額。

明確選定後才會產生正式本機選擇紀錄。文件內的 proposed JSON 是審閱輸入，沒有放入啟用中的產品資料根目錄；`draft.json` 的 workflow 授權保持 false，receipt、submission、dataset refs 保持未綁定。個別 policy 的 `workflow_authorized: true` 是待審閱的預定內容，並非已執行授權。

## 模擬帳戶、進場與保護

| 項目 | 建議值 | 實際意義與限制 |
|---|---:|---|
| 市場／節奏 | BTC_USDT_PERP／4h 收盤 | 僅此商品；不使用未收盤或未來資料 |
| 模擬帳戶起始資金 | 1,000 USDT | 每個策略 run 隔離的模擬會計基準 |
| 固定下單數量 | 0.001 BTC | BASE 單位；不自動加碼、不複利調整 |
| 槓桿／margin mode | 1 倍／ISOLATED | Paper 模型設定，不會改交易所帳戶 |
| 每筆名目額／margin 上限 | 各 200 USDT | 在 1 倍下兩者相等；價格使 0.001 BTC 超過上限時拒絕進場 |
| 同時持倉 | 1 | 本草案只選一個策略／隔離 run；不是跨多策略投資組合總限額 |
| 每日最多進場 | 6 次 | UTC 日計數；不是每日虧損金額限制 |
| 已平倉回撤鎖 | 50 USDT | 依本 run 已平倉 PnL 的歷史資產峰值計算，等於起始資金的 5%，不含浮動虧損 |
| 連續虧損鎖 | 5 筆 | 新進場檢查達門檻即拒絕；不是取消持倉保護或關閉電腦 |
| 最低預估 reward/risk | 1.5 | E5 依現有成本與停損／目標提案檢查；工程策略目標是 2R |
| 每筆預估來回成本／允許上限 | 各 1 USDT | 進場風控使用的保守預算；實際模型成交成本另算，不是費用或損失的硬上限 |
| 停損／目標／持倉時間 | ATR(2) × 2／2R／4 小時 | 工程策略原規則；沒有移動停損。E5 執行保護與時間出場 |
| 意圖有效／計畫 TTL／action TTL | 各 15 秒 | 超時須走既有失效檢查，不能重放過期授權 |
| 模擬首次成交比例／餘量 | 100%／首次成交後取消餘量 | 明確模型假設；不代表真實流動性或保證成交 |

風控鎖限制新進場。持倉仍須走既有保護、平倉、查詢及恢復流程；跳價、資料延遲或停止程序時不能承諾在停損價格成交。**沒有獨立單筆 USDT 最大損失欄位、沒有獨立每日 USDT 虧損欄位，也沒有浮動損失即時硬上限。**

歷史研究 replay 不會套用即時 E5 的帳戶／槓桿／日次數／持倉限額。相同數量與成本有助對照，但不能宣稱歷史成交已符合全部 Paper 帳戶限制。

## 成本、行情與時間

| 項目 | 建議值 |
|---|---|
| 研究與 Paper 手續費 | 每次成交名目額的 5 bps（0.05%）；研究 maker／taker 都取 5 bps |
| 研究與 Paper 滑價 | 進場 5 bps、出場 5 bps，計入成交價；報表不重複扣除 |
| 歷史資金費率 | 必須為資料集實際記錄；缺漏即拒絕／證據不足，不補零 |
| 即時 Paper 資金費率 | 現行唯一支援 `EXPLICIT_REGISTERED_PAPER_ZERO`，待你選擇是否接受此範圍 |
| OKX 公開行情輪詢 | 每 5 秒排程一次；實際 API 請求／回應逐次記錄 |
| 新鮮度 | 最多 5 秒，且仍受原生 quote 的 5,000 ms 檢查約束 |
| 保護檢查排程 | 1 秒；不是每秒必有新行情或每秒保證成交 |
| 每時間框架快取 | 256 根，受既有暖機／收盤／時間對齊檢查 |

5 bps 是本草案的模型假設，不是你的真實帳戶費率。OKX 官方的示例列有 0.05% taker；實際費用另依等級／地區等條件而異：[OKX 費用計算說明](https://www.okx.com/en-eu/help/how-to-calculate-the-contract-transaction-fee)。全程不查私人費率或帳戶。

現行普通 Paper 以明確零資金費率 evidence 結算，既有 forward assessment 可以據此通過門檻；它沒有額外「已包含真實資金費率」的升級檢查。報告會帶出模型、PAPER_ONLY、LIVE NOT_RUN 及 financial authority NONE。即使得到 READY_FOR_APPROVAL，也不能稱為完整實際成本證據、真實交易許可或獲利保證。要求實際資金費率時，這是具體的新模型需求，不能套另一個 JSON 值繞過 parser。

## 真實資料研究協議

預定透過既有 `acquire-public-data`，唯讀取得 OKX BTC 4H、**2026-07-24 00:00 UTC 至 2026-10-20 00:00 UTC，88 天**。此入口上限 89 天及 64 個有紀錄請求，因此不宣稱多年或完整市場週期研究。理論完整量為 528 根 4h K 線、264 個 8h funding 時點；實際量、截止時間、缺口、重複、原始回應與 logical／byte／manifest hashes 必須由實際取得結果填入，現在均未取得。API 可用歷史範圍不足或 funding 頻率不符合當前 decoder 時保留拒絕，不合成補齊。

| 區間（UTC，左含右不含） | 用途 | 最低已平倉樣本 |
|---|---|---:|
| 07-24～07-30 | 暖機／來源前段，不計入評分 | — |
| 07-30～08-13 | 初始執行相容性／訓練區間 | 不冒稱獨立驗證 |
| 08-13～09-30 | development、鄰域與 walk-forward | development 100 筆 |
| 09-30～10-20 | 預定 sealed final OOS | 50 筆 |

32 根 feature-only 暖機；最大持倉及 label horizon 各 4 小時，右邊界去除該 horizon，後續評分區間起點加 4 小時 embargo。**日期是提案，不代表尚未觀察過**：先核對所有既有 family／trial／holdout 與診斷資料紀錄；已看過的區間不能換 family 名字冒充獨立 OOS。若不再獨立，保留診斷身分，另等真正未觀察資料，不重新命名洗掉歷史。

每個 development／walk-forward／sealed OOS 的評分要求：net PnL ≥ 1 USDT、每筆 expectancy ≥ 0.01 USDT、最大回撤 ≤ 50 USDT、最大連虧 ≤ 5、profit factor ≥ 1.2；profit factor 無法定義則 BLOCK。walk-forward 每個訓練／評估窗口及合併結果至少 30 筆已平倉；樣本不足保持證據不足，日期較長也不算自動補足。

這些是預先凍結的研究條件。50 USDT 在評估中是「不超過」；E5 新進場在回撤已達 50 時就鎖住，兩個 owner 的邊界行為保持原樣。

## 策略及 robustness

現有 authoring kit 工程策略 `authoring-example-four-hour` 0.2.1 的 `fast_window` 未被規則引用，不能假稱對它做有效鄰域測試。

草案另附 **0.2.2 proposed definition**：只把雙向規則內的固定 ADX > 20 改成實際引用整數參數 `adx_threshold=20`，移除未使用參數；EMA(2)、ADX(2)、ATR(2)、ATR×2 停損、2R 目標及 4h max-hold 保持。這是工程輸入提案，尚未 author-package／收件／回測，沒有 GPT 身分，也沒有宣稱新舊完整數值結果已驗證相同。

| 項目 | 建議協議 |
|---|---|
| 鄰域 | ADX threshold = 15、20、25、30、35，5 組全部計入分母 |
| 鄰域通過率 | ≥ 80%（至少 4/5）；無效變體不刪除 |
| WF1 | train 08-13～08-27；evaluate 08-28～09-11 |
| WF2 | train 08-13～09-11；evaluate 09-12～09-30 |
| WF 通過率 | 兩個窗口全部通過，且合併結果通過；訓練依 net PnL，再以 variant hash 決定同分 |
| 壓力 1 | 基礎成本上再加 fee 5 bps、entry／exit 各 5 bps、絕對 recorded funding 成本 ×2 |
| 壓力 2 | 基礎成本上再加 fee 10 bps、entry／exit 各 10 bps、絕對 recorded funding 成本 ×3 |
| 壓力底線 | 每個情境 net PnL ≥ 0 USDT |
| Monte Carlo | trade permutation 與 moving-block bootstrap 都執行，各 200 次，固定 seed 20261021 |
| 樣本／block | 至少 100 筆 development closed trades；bootstrap block=5、至少 20 effective blocks；permutation block=1 |
| MC 門檻 | drawdown q95 ≤ 50 USDT；bootstrap expectancy q05 ≥ 0 USDT／筆 |
| 計算界限 | trials 5、replays 64、evaluations 200,000；每個 MC path observations 上限 500,000；一般 replay 上限 2,000 |

預定最多 20 次 robustness replay（base、5 鄰域、2 壓力、2×[5 訓練＋1 評估]），低於 64；實際 bars、樣本與預算仍由 owner 檢查。有限重抽樣只描述所選序列／依賴模型的敏感性，不排除選擇偏差或沒觀察到的市場狀態。只有 development／robustness 合格後凍結 finalist，再由隔離入口評估 sealed OOS；不以 OOS 結果回頭選參數。

## 自動調度與真實時間觀察

正常產品入口使用一個 `run-product` coordinator，管理 control／research／runtime：每 30 秒掃描本機 inbox、對明確選定的 research policy 排程並 queue 報告；子程序重啟預算 3 次、backoff 5 秒。這是產品啟動後的調度，不會新增 OS 開機啟動項、休眠或安全設定，也不要求 Chat／Codex／瀏覽器維持開啟。cloud_root_id 保持 null，沒有實際雲端收件／ACK 宣稱。

選定政策且下列准入全部合格後，先以 **48 小時為第一段運作觀察目標**；沒有足夠成交就保留未完成。48 小時不是 forward 升級 PASS，也不保證 48 小時內一定出現交易。

最終 Paper 評估草案：至少 **30 天實際時間、30 筆已平倉、29.7 天（2,566,080 秒）健康觀察、最大觀察缺口 60 秒**，並同時滿足 net PnL ≥ 1、expectancy ≥ 0.01、回撤 ≤ 50、連虧 ≤ 5、PF ≥ 1.2（未定義即 BLOCK）。重啟不能抹去歷史最大缺口或當成補足缺失時間。

**長時間留存能力尚未完成這次政策的容量驗證。** 目前每個 runtime token 的公開擷取上限是 86,400 批或 1 GiB；5 秒輪詢按批數最快約 5 天達限，位元組上限可能更早。程式會拒絕，不能靜默刪 evidence 或靠重啟規避限制。必須先量測實際增長、完成合適的留存／歸檔與停止恢復處理，才能宣稱無人值守 30 天可行；第一段觀察也要通過實測容量准入。這是需繼續完成的技術項目，不是請你批准刪檔或放寬門檻。

## 選定後的正式設定順序與尚未完成項目

1. 記錄你對三組項目的明確選擇，凍結政策版本、hash、策略輸入與研究協議；不是先執行再挑合意門檻。
2. 以既有 `init-profile` 建全新 owning instance／config／data root，放在專案內；原 qualified diagnostic store 的 immutable research selection、auth、receipt、資料庫和 evidence 全部保留。**不複製它們來授權新 root。**
3. 新 store 由既有 `tools/qualify_paper_product.py --config <fresh config> --package-root <exact native package>` 實際完成固定 qualification，取得自身 receipt。需 exact-clean bffc source 與 exact native package；先前其他 store 的 PASS 不可轉移。
4. 既有公開唯讀取得入口產生實際 data/funding refs、完整 hash 與逐請求帳；核對 trial／holdout 歷史後確定是否能作為獨立 OOS。若缺資料只保留診斷。
5. 用 `author-package`、正式 intake 與 capability negotiation 建立實際 0.2.2 工程包。manifest 的 requested profiles 與本機 research selection 必須一致；family 保留既有可追溯歷史。
6. 用 `configure-research` 選定正式 inputs，再跑既有完整研究流程。只有實際 CANDIDATE 且綁定相同 selected risk policy hash，才可進入 Paper；REJECTED／BLOCKED 就停止該候選，不用 FIXTURE 或展示政策補 PASS。
7. 在 fresh native instance 走正式 owner enrollment（密碼只在本機互動輸入）、`configure-market-data`、`configure-paper` 與本機 workflow selection，核對當前 native subject／generation／store receipt。此文件不提供密碼或可重用登入。
8. 完成容量／行情／保護／停止／恢復及資源隔離准入後，以既有 `run-product` 啟動服務。**它不會自動執行 PaperStart，`configure-paper` 也只選政策、不建立 run。** 在正常 Control Center 登入後，經正式 UI／API 的 PaperStart 提交精確選定的 strategy_id、strategy_version、policy_id、當前 expected_revision 及穩定 command_id；重試保留同一個命令身分。
9. 讀回真正 accepted 的原始 run_id，確認既有 runtime owner 已接管同一 run、行情／保護／健康／時間證據開始產生，再宣稱觀察已啟動。查看 `product-status` 與正式 run 狀態；服務程序存在本身不算 run 已運作或已累積樣本。透過既有暫停／停止入口收尾，保留持倉保護及實際結果。

CLI 概念順序不是可直接執行腳本；`draft.json` 故意保留真實 refs／receipt 未綁定。正式命令必須使用實際建成的 config／selection 路徑與當時 CLI help。若改動風控或 funding 的 canonical 語義，先明確列設計衝突與審閱要求，不把它稱成尚待已通過的四項 PM mapping。

本次準備 **新增 market API calls 0**，既有累計 public requests/responses **8/8**；私人請求 0、credentials NONE、provider mutation 0、資金 NONE、GitHub compute NOT_USED。查閱官方公開文件與離線 parser 檢查分別記錄，不當成行情 API 呼叫。後續實際取資料會增加公開呼叫帳，不再申報全部 provider calls=0。

原目標機、Ubuntu 24.04／26.04、雲端／SSH、真實時間及成交樣本仍是獨立未完成項目。此草案不取消它們、不啟動 LIVE、不 merge main。

## 附件與檢查範圍

`draft.json` 是完整狀態／依賴／未選定綁定；九個 `*.proposed.json` 是各政策完整欄位，另有 proposed strategy。`verify_draft.py` 僅呼叫現有 parser、驗證規則引用與日期／單位／hash／理論預算一致性，不初始化 store、不發 API、不回測、不測 native，也不授予 CANDIDATE 或 Paper 資格。檢查結果、每檔 SHA256、有限 source map 與獨立靜態審閱分開保存。
