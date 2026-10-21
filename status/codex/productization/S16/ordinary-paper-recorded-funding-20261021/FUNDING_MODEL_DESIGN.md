# Ordinary Paper 公開實際費率模型設計 — 2026-10-21

狀態：**DESIGN_FOR_REVIEW，未實作、未發新資格、未啟動觀察。**

使用者已選定數值／工程輸入，要求先完成實際資金費率模型與驗證。本文件把計價、來源完整性與延後結算的行為寫明，供跨模組設計審閱；沒有要求再次決定原四項 PM mapping，也不提出私人 API、實盤或資金授權。

## 1. 意圖、相容邊界與取捨

目標：普通 LOCAL_RESEARCH／REAL_TIME Paper 使用 OKX 公開**已結算 realizedRate**，不把預測費率、缺失或失敗查詢當成零。仍是模擬持倉的本機 Paper 模型，不是私人帳戶 funding ledger。

沿用既有 `funding-allocation-v0.1`，source_kind=PAPER_MODEL；E5 的正數成本／負數收入及 `net_pnl = gross_pnl - fees - funding_cost`、E6 的 immutable evidence／exact lineage／半開區間規則保持。

現有契約 §9.2 允許 deterministic simulated funding events；§6 要求 authoritative completeness，§6.2／§9.1 不准用來源缺失補零。現有 E4 zero producer 不能改標籤冒充新模型，FIXTURE ledger 也不能冒充公開資料來源。

比較過的方案：

- **公開已結算費率 × 既有 entry-fill notional（推薦本版）**：符合已選歷史研究的 ENTRY_FILL_PRICE_X_BASE_QUANTITY 口徑，模型可重放，資料需求有界。實際的是費率；notional 與持倉仍是模擬模型。
- **公開已結算費率 × 結算瞬間 mark-price notional**：更接近交易所計價，但需另定結算 mark 的時間對齊、可用性／延遲與 exposure 快照；不能拿稍後 ticker 或歷史 candle close 冒充精確 mark。這將是另一版模型與額外來源驗證。
- **私人帳戶帳單**：不在授權範圍，不實作或呼叫。

OKX 官方說明以 mark price 計算 USDT perpetual 的 position value，且實際 fee assessment 可能延後。因此推薦方案不能稱為交易所實際帳單或完整實際成本複製；名目 fundingTime 的半開區間屬此 Paper 模型的明確約定：[OKX perpetual funding fee mechanism](https://www.okx.com/en-ae/help/perps-funding-fee-mechanism)。

## 2. 明確版本與計價

預定新註冊 E4 source_version：`paper-public-recorded-entry-notional-v0.1`；普通 simulation policy 新 profile 預定 `r7-paper-simulation-policy-v0.5`，funding_model=`OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1`。實作前核對名稱尚未占用。舊 v0.2／零模型及 v0.3／v0.4 FIXTURE fault profiles 保持原義，既有 evidence 不重寫。

全部金融數值為有界、有限 Decimal，無 binary float。單一固定 exposure、首次實際成交後取消剩餘數量，沒有加碼／分批減倉模型。quantity 與 entry notional 必須由實際 Paper entry fills／Position lineage 證明，不取 approved quantity 代替 actual fill。無法證明 exposure 恆定時不發最終 funding evidence；保護與實際平倉仍照常處理。

本 source_version 的算術規則固定如下，不能受 ambient Decimal context 影響：

- 正規化輸入為無 exponent 的固定小數字串，最長 64 字元；整數位與小數位各最多 18 位，significant digits 最多 34 位；禁止浮點、非有限值、非標準前導零。quantity／price 必須正，rate 可正負且絕對值 < 1；所有正負零正規化為 `0`。
- entry fills 與適用 events 各最多 1,000 筆，排序鍵固定，重複／矛盾 identity 拒絕。entry basis 用 `sum(actual_fill_quantity × actual_fill_price)`，不經可能無限循環的加權均價除法。模型還須證明同一固定 exposure，數量變動不因此自動獲得支援。
- 乘法與排序後加總一律在獨立 Context(prec=128, Emin=-256, Emax=256) 內；Inexact、Rounded、InvalidOperation、Overflow、Underflow、Clamped、Subnormal 全部 trap。三個最多 18 整數／18 小數位的因子，兩層最多 1,000 筆加總，最多需要 114 位精度；128 足夠。遇 trap 拒絕最終化，不默默截位。
- 不捏造交易所帳單量化／捨入。輸出用固定小數 canonical text 去除無意義尾零、零一律 `0`；還須可由既有 downstream `r7-decimal34-v1` 無輸入捨入地表示，否則回報模型數值能力不足。source material hash 綁定上述算術版本與正規化後輸入。

對每個實際公開 settled event：

```
event applies iff opened_at <= fundingTime < flat_observed_at
event_cost = actual_entry_fill_notional × realizedRate × side_sign
side_sign = +1 for LONG; -1 for SHORT
funding_cost = sum(event_cost)
```

有適用事件，即使費率為零或總成本互相抵銷，也使用 INCLUDED、正確 source_record_count，不改成 ZERO_CONFIRMED。只有模型與完整來源共同證明 exact interval 沒有適用事件時才可 ZERO_CONFIRMED。

完整 normalized source material 包含註冊模型版本、exact plan／position／symbol／interval、actual fill basis、排序事件與公開 raw capture hash／query coverage 證明。用既有 canonical identity convention 產生 source_material_hash 與 fundev identity；calculated_at 改變不能製造第二個相同 allocation。

## 3. 公開唯讀擷取與 completeness

沿用有 request budget／deadline／bytes limits 的獨立 owned child、固定 OKX GET allowlist、原始 request／response／失敗紀錄與逐次 API 計數。新增 funding acquisition 不在 E5 保護 tick 內同步等網路，不存 API key 或 account ref。來源是 `/api/v5/public/funding-rate-history` 的 realizedRate，禁止用預測 fundingRate 替代。

第一版僅支援已驗證的 UTC 8h settlement grid；拒絕無法辨識的間隔變更、額外／重複／缺漏 event、錯 instrument、未結算值、分頁不完整或無進展。這是明示能力限制，不把其他時段資料硬改成 8h。所有頁面及正規化內容 hash 可追溯。當前 history 的上限與完整性不能由空列表、HTTP 200 或本機時間猜出。

推薦用**已公布 settled event 的上下界與連續來源**建立保守 completeness watermark：必須取得涵蓋 exact opened interval、且最新已結算事件時間 T ≥ flat_observed_at 的完整連續 source coverage，才可將 source_complete_through 設為 T。若結束在兩次 settlement 之間，可能要等下一次公開 settled event；不能因已過固定秒數就聲稱完整。固定 8h 模型遇變更或無法證明 coverage 仍 BLOCK。

此取捨可能讓財務結算等待約一個 settlement 週期，若 API 發布更晚則更久；不承諾 8h 一定取得。市場 ticker／candle 擷取與持倉保護不因 funding source PENDING 而停住。對尚無可靠 funding source 的新 run，先完成明確來源健康檢查，再允許新進場與健康 forward 計時。

### 3.1 開始／持續來源健康的可執行條件

這是工程來源有效性，與上一節 final allocation 的 upper-bracket completeness 不同，不能互相替代：

1. qualified native runtime owner 在 idle 也能啟動有限公開 funding preflight；capture 綁定當前 config／selected model hash／namespace／實際 runtime generation。preflight 不是 Paper run／financial evidence，不製造 run_id 或 caller PASS。正式 PaperStart 與每個新進場均讀回同一 current subject 的真實來源健康觀察。
2. HEALTHY 要求成功的 immutable 原始 capture、完整 pagination／request accounting、已驗證至少兩個連續 UTC 8h settled records；最新 settled event 必須等於 `floor(actual_observed_at, 8h)`，且所需更早 coverage 無缺口／額外時點。actual response receipt／owner observed 時間必須一致、非未來。僅 HTTP 成功或預測值不足。
3. capture 的有效期最多 60 秒；以 source actual observed UTC 與本機單調排程共同檢查。觀察／clock 反轉或後續讀回為未來即失效。排程每 5 秒嘗試更新，共用相同 BTC facts；同一類最多一個 owned child，無重疊。保留既有 transport 的每 response 2 MiB、165 requests／120 秒 deadline，以及 owned child 125 秒外層 deadline；所需歷史最多 89 天、normalize events 最多 1,000 筆。超限不擴充任意 endpoint 或無界查詢。
4. 起始是 UNAVAILABLE。成功且滿足上述條件才 HEALTHY；超過 60 秒是 STALE；失敗／timeout／grid 變更是 RETRYING 或拒絕，容量達限是 REFUSED_CAPACITY。不能因舊 capture 尚在磁碟就維持 HEALTHY。排程有界重試但不洗掉失敗紀錄；新 capture 通過全部條件才恢復。系統睡眠／關閉時間不補作健康秒數。
5. 新進場與 forward healthy time 都要求當前 source HEALTHY，並同時滿足原本 quote freshness、owner／reconciliation／protection／publication gates。尚未完成此條件，不開始健康觀察計時。來源失效只停新進場與健康累積；不阻擋現有 exposure 的保護／減倉／平倉，報告明示原因；沿用原最大觀察缺口 60 秒，不放寬來取得 PASS。
6. 已 flat、等待下一個 published upper bracket 的財務 PENDING，在 capture 本身仍 HEALTHY 且 flat／pending 已可靠持久化時可以繼續記錄運作健康秒數，但不能產生 closed financial sample／允許下一筆進場，forward assessment 也必須保持 BLOCKED。這樣不把正常等待來源結算冒充故障，也不把健康程序冒充已完成財務證據。

既有公開行情 capture 的 86,400 batches／1 GiB 限制仍保留；同一 runtime generation 的 market、funding 與 idle preflight 合計採此上限，所有 attempt 都計入，不能透過新增子目錄避開計數。另須跨 generation 核對實際 disk admission 與持續累積量，重啟不作為歸檔策略。新增 funding 紀錄的容量／歸檔／停止恢復必須一併評估；不靠重啟重設容量或刪 evidence。任何額外實際 API 呼叫納入公共帳，本 checkpoint 累計目前 17/17。

## 4. Flat 已證明但 funding 仍 pending

平倉與資金費率取得解耦：正常 E4／E5 程序執行 close、實際 flat observation 及允許的保護收尾；先持久化原本 fills、flat observation、exit authority 與 funding-pending intent，再等待來源完整。

PENDING 是 application-local 財務工作狀態，不新增 canonical lifecycle 或把 UNKNOWN funding 包成最終 evidence。既有 Position／TradeResult contract 保持原樣。此時不能將該筆當成 finalized closed-trade sample／PnL，不能宣稱 flat=0 cost，也不重複發 close／fill。此版在同一隔離 run 等待財務結算期間拒絕下一筆進場，避免未計 funding 的 equity 支持新進場。

後繼程序透過相同 durable key／lineage／generation 回復既有 flat/fills，重新驗證 captured source，再發布一筆 canonical funding evidence 與一筆 E5 TradeResult。相同內容重試返回原 identity；同一 allocation 的矛盾內容拒絕並保留診斷。不得修改已發布 TradeResult 來修 funding；遵守既有 profile 的後續 correction 邊界。

關閉／暫停／退休不取消仍有 exposure 的保護；funding unavailable 不阻止減倉、平倉或保護。持久化失敗、來源缺口或未 reaped child 不能被標成成功。重啟不得把 pending 交易遺漏、重新開倉或從統計帳抹掉。

## 5. 正式選擇、報告與升級

數值採原選定草案。只替換使用者未接受的零 funding model，建立實際新版本／hash，經既有 ordinary configure-paper／protected operational generation／native current-release 檢查；禁止從外部 JSON 注入 caller PASS 或計算結果。

報告採明確版本的 additive cost-convention profile（版本名稱實作時固定），必須揭露：public settled rates、entry-fill notional、PAPER_MODEL、pending funding count／coverage、source／model hashes、PAPER_ONLY、LIVE NOT_RUN、financial authority NONE。舊零模型報告 validator 與舊 immutable reports 保持原義，不把新 model 字串塞進舊固定 convention。

Forward assessment 只使用 E6 真正發布且 E5 驗證的 final funding／TradeResult。source pending／coverage unsupported 時不能 PASS；相同數量與實際費率不等於真實帳戶績效。原 30 天／30 筆等門檻保留；有程式、有資料或已開服務均不能代替時間／成交樣本。

軟體變更必須產生新的 exact-clean executable／implementation／build identities，更新受影響的固定測試登錄並跑適用完整 qualification。舊 bffc558 receipt 只證明其原本軟體與 store，不對新模型提供資格。新 owning store 要由正式 producer 實際建立它自己的 receipt。原 FIXTURE regression、風控與 LF／FP fail-closed checks 不刪減。

## 6. 設計驗收條件

1. 正／負／零 realized rate、LONG／SHORT、抵銷事件及 Decimal repeatability；INCLUDED 與 ZERO_CONFIRMED 區分正確。
2. exact opened／flat half-open 邊界、相鄰 positions 不重複分攤；實際 fill quantity／basis 與 plan／position lineage 不可替換。
3. 缺漏、延遲、預測值、錯 symbol、重複／亂序／矛盾頁、未結算事件、未知版本／8h grid 變更、timeout／資源拒絕均不補零或完成 financial sample。
4. 空回應不能證明 complete；沒有 published upper bracket 不能推進 watermark；費率尚未公布仍保護／平倉，並拒絕新進場。
5. close ACK／fill／flat 後、funding capture／publish 前後每個 crash boundary 的真實重啟，原 flat／fill／allocation 不重複；pending 工作不可丟失。
6. E5 PnL 正確包含費率成本／收入；E6 evidence conflict／replay／generation fence、backup／restore inhibition 正確；沒有手改 DB。
7. 正式 CLI／Control Center／authenticated PaperStart 到獨立 owner 的正常路徑；政策版本錯、舊 receipt、錯 owning store、新選擇 generation 變更均 fail closed。
8. 新報告正確顯示模型與 pending，舊零模型報告保持；不將 source code／FIXTURE／加速時鐘當新原生或真實觀察證據。
9. source／browser／native impacted checks 與新 exact-clean full qualification，測試與真實公開擷取分開執行、分開記錄。正常 shutdown、重啟、有限容量與 resource isolation 仍驗證。

## 7. 尚未作出的宣稱

此文件不宣稱模型已實作、資料已通過研究／獨立 OOS、原生套件已包含新功能，或 Paper／真實時間觀察已啟動。沒有新增資產、私人 API、真實交易金鑰、真實帳戶、10U／LIVE、GitHub compute 或 main merge。

設計涉及 E4 source、application close/recovery、公開 capture 及報告的配合。依本次使用的 brainstorming architectural 流程，需先審閱這份具體書面設計，再完成實作計畫與產品修改；既有公開取得／工程 authoring／政策選擇紀錄工作不受此設計步驟阻擋。
