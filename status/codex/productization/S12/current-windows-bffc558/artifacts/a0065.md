# Chat authoring kit: BTC 4H, current executable capabilities

This kit supplies author inputs, not a profitable strategy or a financial
approval. The tracked `authoring-v0.2/examples/four-hour/strategy.json` is an
engineering example, strategy `authoring-example-four-hour@0.2.0`, semantic hash
`sha256:034645d0279cbff987828f59d7ba9a7791f2c9dc4774d1a76b91587bab87bcc7`.
It is not a verified GPT strategy. Its name says SMA but its actual definition
uses EMA(2); use the definition, not the display name, as the source of truth.

## Give Chat these inputs

Export the actual installed executable's snapshot:

```powershell
R7.exe export-capabilities --destination C:\R7-authoring\capabilities.json
```

Include that file, `authoring-v0.2/README.md`, the four-hour example, and this
request (replace the strategy hypothesis with your own):

> Author one BTC_USDT_PERP strategy with a 4h evaluation timeframe using only
> the attached capability snapshot and R7 v0.2 JSON DSL. Explain the hypothesis,
> required warmup, entry conditions and bounded exit policy. Do not invent
> indicators, broker capabilities, observed results, approval, account access
> or profitability. Return strategy.json and research_notes.md. Identify
> unsupported requirements explicitly. Keep independent validation data sealed;
> do not optimize parameters against it. Distinguish your original proposal
> from the engineering example and identify the model/date in the notes.

Author with the actual installed parser, using explicit requested profile IDs:

```powershell
R7.exe author-package --definition C:\R7-authoring\strategy.json --notes C:\R7-authoring\research_notes.md --destination C:\R7-staging\new-submission --submission-id new-submission --dataset-profile okx-btc-4h --validation-profile diagnostic --robustness-profile diagnostic
```

Do not edit an emitted manifest or substitute a stale capability snapshot.
The recipient still validates every payload hash, compatibility and validity.
Place the complete emitted folder into the explicitly selected inbox staging
layout described in the authoring README. Successful authoring is not execution.

## Keyless public research inputs

`acquire-public-data` accepts an explicit LOCAL_RESEARCH config, a fresh dataset
ID, UTC start/end; it has no key, account, endpoint or order arguments:

```powershell
R7.exe acquire-public-data --config C:\R7\config.json --dataset-id btc-4h-research --start 2026-08-01T00:00:00Z --end 2026-10-18T00:00:00Z
```

It retains raw public responses and prepared request receipts, counts actual
transport invocations and HTTP responses, and emits success OR rejection.
Requests use only fixed OKX public historical candles and funding-rate history.
The dataset uses documented base BTC volume (`volCcy`); raw contract volume is
retained separately. Settled `realizedRate` must cover the whole range. Current
fixed-interval funding input requires an uninterrupted 8h sequence; a different
interval or a gap is rejected rather than filled with zero. These rules follow
the existing dataset contract. Official reference:
[OKX public data documentation](https://app.okx.com/docs-v5/en/).

## Diagnostic setup without a formal review policy

The existing `r7-owner-selections-v0.2` profile accepts a disjoint research
selection containing exactly:

```json
{
  "selection_mode": "DIAGNOSTIC_DEVELOPMENT_ONLY",
  "dataset_ref": "datasets/btc-4h-research/dataset.json",
  "split_policy_ref": "engineering-split.json",
  "cost_policy_ref": "engineering-cost.json",
  "requested_dataset_profile": "okx-btc-4h",
  "requested_validation_profile": "diagnostic",
  "requested_robustness_profile": "diagnostic"
}
```

Wrap this in `research_policies` under an explicit local selection ID and select
the local staging root identity through the normal `configure-research` command.
Select costs and chronological split inputs explicitly. Engineering fee,
slippage and quantity assumptions are research scenarios, not account fee facts,
production defaults or a Paper risk policy. Funding replay uses recorded rates
with entry-price times base-quantity notional: an estimate, not account billing.

This mode rejects promotion, robustness, risk, family and adaptive seed inputs.
Normal intake, queue and the independent worker perform development replay;
robustness and sealed OOS stay NOT_RUN, and the missing formal review policy
keeps the result BLOCKED with lifecycle BACKTESTING. Positive development PnL
does not authorize candidate promotion, Paper entry or real-time observation.
Keep ingestion hashes/ranges separate from the research-visible development
partition; acquisition and integrity checks do not license research on holdout.
