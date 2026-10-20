# 離線作者封裝

先以 `R7.exe export-capabilities --destination <全新本機 capabilities.json>` 匯出當前 implementation availability，再產生符合 E2 的實際 strategy JSON。Capability snapshot 中的 IMPLEMENTED 與 NOT_RUN／provider availability 是不同事實；不能用套件欄位自證相容、研究、PAPER 或 LIVE。

```text
R7.exe author-package --definition <實際 strategy JSON> --destination <全新本機套件資料夾> --submission-id <唯一 id> --dataset-profile <本機已選 profile> --validation-profile <本機已選 profile> --robustness-profile <本機已選 profile>
```

Ubuntu 使用相同參數的 `r7`。工具透過實際 E2 parser 計算 semantic content hash，再寫出 payload byte hash／長度、當前 capability snapshot hash 及嚴格 manifest。先寫 strategy／optional notes，最後寫 manifest；拒絕既有目的資料夾與被識別出的 secret notes。預設 requested profiles 為 `unselected`，不代表可執行的本機研究或金融設定。

`--package-version 0.1` 保留 legacy0.1／runtime0.1.0；0.2 包含 runtime、capability、intent class 及 validity。4h evaluation 仍與 expiry／max hold／exit monitoring 分開。Tactical 使用 `--valid-from <UTC Z> --valid-until <UTC Z>`；兩者必須存在且形成有限有效區間。既有 v0.2 策略支持1m／15m／1h／4h及 as-of multi-timeframe；helper 不把未知 indicator、semantic version 或 grammar 自動替換成可用功能。

輸出是可交付的 `strategy.json`／`manifest.json`，可選 `--notes <UTF-8 markdown 檔案>`。Chat 裡看似 JSON 的文件並不等於 JSON 檔案。Connector 是否能將檔案上傳指定資料夾，必須由該工具的實際成功結果證明；R7 本機 copy bridge 成功不代表 Chat connector 已具備或使用上傳能力。

套件放入指定 R7 root 的 `inbox/strategies/<submission_id>/` 後，仍需實際 local intake、private seal、E2 identity、E6 DRAFT，以及原本的 compatibility／研究／approval gates。雜湊是完整性與身分綁定，不是作者簽章或交易授權。開發 roundtrip 已涵蓋 legacy、4h、multi-timeframe、tactical、missing feature 與 E6 repeated scan；真實雲端 smoke 本次維持 `NOT_RUN`。
