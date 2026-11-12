# Data Availability Report — Commodity Futures Data Routes

Query date: 2026-11-03 (Asia/Shanghai).

Important evidence-status note: this environment has no outbound internet access (DNS resolution fails for cmegroup.com, databento.com, data.nasdaq.com, and barchart.com), and no web-search tool is available. I could not open any official product page, data dictionary, or price list during this turn. Everything below is compiled from prior public documentation knowledge and is marked as unverified. Every item that could not be confirmed against a live source is marked UNKNOWN. Before purchase or download, each claim must be re-checked against the vendor's current documentation.

## 2026-11-03 retry results (with escalated network permission)

With escalated network permission, a subset of pages became reachable. Actual outcomes:

- Databento: reachable and verified via the official markdown documentation. See the Databento section below for verified facts.
- Nasdaq Data Link: homepage returned 200, but the metadata API returned HTTP 403 from Incapsula, and a guessed CHRIS/CME corn dataset URL returned 404. Nasdaq Data Link remains unverified beyond the homepage.
- Barchart: www.barchart.com returned HTTP 202 with 0 bytes on multiple pages (Cloudflare protection). Unverified.
- CME Group: www.cmegroup.com, cmegroup.com, and datamine.cmegroup.com all timed out or were reset. Unverified.
- WRDS, Bloomberg, LSEG Workspace: not attempted beyond noting they require institutional login.

Verified facts carry their source URL and a 2026-11-03 date. Everything else remains UNKNOWN and must be re-checked when access is available.

Status terminology: each source is now assessed on four independent dimensions — documentation status, API access status, historical coverage status, and pricing status — in source_comparison.csv. A vendor can be documentation-level verified while its actual historical coverage and pricing remain unknown.

## Scope and required fields

Required fields: trade date, exchange/product, individual contract identifier, delivery month and year, expiration / last trading date, settlement, open/high/low/close, volume, open interest.

The critical design distinction is between:

- individual contract data: one row per listed contract (e.g., CZ2024 = Dec 2024 corn), with its own volume and open interest;
- front contract: the single nearest-to-delivery contract at each point in time;
- active contract: the contract with the highest volume/open interest at each point in time;
- continuous series: a synthetic back-adjusted or ratio-adjusted series stitched across contracts, which is not tradable and must not be treated as one contract's prices.

## 1. CME Group Continuous Price Series (CPS)

- Product family: CME Group Continuous Price Series, sold through CME DataMine.
- Granularity: continuous. It is a derived series built from individual contracts according to a documented methodology.
- Known/expected attributes: the methodology defines the underlying contract mapping, the roll date, the expiry date used in the roll, and whether volume/open interest are single-contract values or aggregated across the two contracts involved in the roll. These details are per product and must be read from the official methodology document. Exact current rules are UNKNOWN and unverified here.
- Coverage: UNKNOWN. CME marketing may reference "40+ years" for the overall program or for selected flagship products; this does not mean every agricultural product has 40 years, and it does not mean the continuous series has full OHLC + volume + OI over that whole span.
- Pricing/licensing: PAID via DataMine. Academic pricing UNKNOWN.
- Use for research: useful for a quick long-horizon price picture, but not sufficient for contract-level work. Do not use CPS as a substitute for individual contract data when delivery month, expiration, or contract-level volume/OI matter.

## 2. CME DataMine Daily Settlements

- Granularity: individual contract.
- Known/expected fields in settlement files: contract month/year, open, high, low, last, change, settle, estimated volume, and prior-day open interest. Trade date is implied by the file date.
- Missing from typical settlement files: expiration / last trading date, and same-day final open interest (settlement files carry prior-day OI). LTD/expiration must be joined from a product calendar.
- Coverage: UNKNOWN per product. Historical depth differs across products; confirm the earliest available year for corn before assuming long history.
- Pricing/licensing: PAID via DataMine; recent-day settlement files and the Daily Bulletin are free. A free current-day file is not a free historical archive.

## 3. CME Daily Bulletin

- Granularity: individual contract.
- Contains daily settlement, volume, and open interest by contract (and product summaries). OHLC coverage may be partial depending on the bulletin format; UNKNOWN.
- Archive: current day plus a limited recent window on cmegroup.com. It is not a free substitute for a historical archive. Deep history requires DataMine.
- Pricing: free for the recent window.

## 4. Barchart

- Granularity: mixed. Barchart offers both continuous series and individual contract quotes/history through its web products and APIs (cmdty).
- Known/expected fields: OHLC, volume, open interest, and settlement are generally available for individual contracts; expiration/LTD is UNKNOWN without confirming the product dictionary.
- Coverage: UNKNOWN. Free web/API access is typically limited to a recent history window; deeper history requires a paid plan.
- Pricing/licensing: free tier plus paid subscriptions. Academic pricing UNKNOWN.

## 5. Databento

Status: DOCUMENTED (official docs fetched 2026-11-03). API access, historical coverage, and pricing remain UNKNOWN until an API key is configured.

- Granularity: individual instrument symbols via `raw_symbol` or numeric `instrument_id`; parent symbol `ZC.FUT` returns all corn futures (and futures spreads). Continuous symbology exists but is not a substitute for individual contracts.
- Contract mapping: the definition schema provides `raw_symbol`, `instrument_id`, `maturity_year`, `maturity_month`, `maturity_day`, and `expiration`. Definitions are point-in-time (timestamped), which is useful for expired-contract and lookahead work.
- Expiration vs last trading date: the documented `expiration` field is "the last eligible trade time" and may only have date precision. It is not independently the last trading date; an external CME contract calendar is still required to confirm LTD for CBOT corn.
- Settlement vs close: `statistics` provides the venue's official settlement price with `stat_flags` marking preliminary vs final and actual vs theoretical. `ohlcv-1d.close` is Databento's UTC-day close from the electronic session and can differ from official settlement (e.g., block/OTC effects).
- Volume: `ohlcv-1d.volume` is electronic-session traded volume; `statistics` `CLEARED_VOLUME` is official cleared volume for the previous trading date. These are different concepts and must not be conflated.
- Open interest: `statistics` `OPEN_INTEREST` is the venue's official outstanding-contracts figure; its as-of trading session is carried in `ts_ref`, so T-day price vs T-1-day OI alignment must be handled explicitly.
- Coverage: `GLBX.MDP3` documents full coverage of all CME/CBOT/NYMEX/COMEX futures and options on futures from June 2010; before May 2017 the source is legacy MDP 2 (FIX/FAST). Per-schema start dates are returned by `metadata.get_dataset_range`, which requires an API key and was not run.
- Pricing: metered per uncompressed GB; metadata, symbology, and account management are free; batch download is billed once and re-downloadable for 30 days. Exact `GLBX.MDP3` unit prices and any minimums or academic discounts are UNKNOWN without an API key.

Use for research: contract-level fields are recoverable in principle (DOCUMENTED), but the decision rule cannot pass until per-schema corn coverage, settlement/OI overlap, and pricing are confirmed with an API key (API-VERIFIED).

## 6. Nasdaq Data Link (formerly Quandl)

- Granularity: primarily continuous futures (e.g., CHRIS/CME family), with some raw/individual datasets available; availability varies.
- Known/expected fields for continuous futures: open, high, low, settle/last, change, volume, previous-day open interest.
- Missing: individual contract identifier, delivery month/year, expiration/LTD, and same-day OI on the continuous series. Continuous roll conventions vary by dataset.
- Coverage: UNKNOWN per dataset. Front-month continuous corn may have long history, but do not assume every dataset has the same depth.
- Pricing/licensing: free tier with API key plus paid premium for more history/datasets; academic terms UNKNOWN.

## 7. WRDS, Bloomberg, LSEG Workspace (university-subscription routes)

- WRDS: availability of commodity futures depends entirely on the institution's subscribed databases. Whether a CME/commodity-futures product is present is UNKNOWN and must be checked with the local WRDS administrator.
- Bloomberg Terminal: native individual-contract futures history with trade date, contract ID, delivery month/year, expiration/LTD, settlement, OHLC, volume, and open interest. Coverage is generally deep but product-specific. Bulk export is limited on the terminal; a Data License is needed for large-scale download.
- LSEG Workspace / DataScope Select: analogous contract-level coverage. Bulk access via DataScope or Tick History; institutional licensing applies.
- All three are paid institutional resources; academic access exists only where the university holds a subscription. Exact field dictionaries and per-product history are UNKNOWN here.

## Field coverage summary

| Source | Individual contract | Delivery M/Y | Expiration/LTD | Settlement | OHLC | Volume | Open interest |
|---|---|---|---|---|---|---|---|
| CME CPS | No (continuous) | No | UNKNOWN | Yes | Partial | Partial | Partial |
| CME DataMine Daily Settlements | Yes | Yes | No | Yes | Yes | Yes | Prior-day OI |
| CME Daily Bulletin | Yes | Yes | No | Yes | Partial | Yes | Yes |
| Barchart | Yes | Yes | UNKNOWN | Yes | Yes | Yes | Yes |
| Databento | Yes | Yes | Yes | Yes | Yes (bars) | Yes | Yes |
| Nasdaq Data Link (continuous) | No | No | No | Yes | Yes | Yes | Prior-day OI |
| WRDS | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Bloomberg Terminal | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| LSEG Workspace | Yes | Yes | Yes | Yes | Yes | Yes | Yes |

## Free sample / trial / academic / low-cost options

- CME: recent-day settlement files and the Daily Bulletin are free, but only for a narrow recent window; they can be used for pipeline validation, not history.
- Databento: free credits/trial; academic credits may be available (terms UNKNOWN).
- Nasdaq Data Link: free API tier with a limited number of continuous futures datasets; enough for prototyping, not necessarily for full contract-level history.
- Barchart: limited free end-of-day history; deeper data is paid.
- University: WRDS, Bloomberg, and LSEG access should be confirmed through the library/finance lab; this is usually the cheapest route for deep history because the subscription already exists.

## UNKNOWN items that must be verified before commitment

1. CME CPS current methodology: roll date, expiry date, underlying contract mapping, and whether volume/OI are single-contract or aggregated.
2. Earliest available year for corn in CME DataMine Daily Settlements, CPS, Nasdaq Data Link, Databento, and Barchart.
3. Whether CME Daily Bulletin includes full OHLC or only settle/volume/OI.
4. Databento's exact futures coverage window for GLBX.MDP3 (settlement/OI/expiration availability is now verified via statistics/definition schemas).
5. WRDS commodity-futures database availability at this institution.
6. Bloomberg/LSEG field mnemonics and per-product history depth at the local terminal.
7. All academic-pricing and bulk-download terms (DataMine, Barchart, Databento, Nasdaq Data Link).

