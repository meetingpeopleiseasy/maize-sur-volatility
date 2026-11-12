# Research Design Implications

Query date: 2026-11-03. With escalated network permission, Databento's official documentation was reached (DOCUMENTED); its API access, historical coverage, and pricing remain UNKNOWN. CME Group, Barchart, and Nasdaq Data Link were blocked or timed out (details in data_availability_report.md). Documented Databento facts are used below; all other vendor claims remain unverified.

## 1. Prefer individual contract data as the unit of analysis

The old corn inventory-price-volatility study is retired, and its assumptions must not carry over. For any new study that needs delivery month/year, expiration, settlement, volume, or open interest, the unit of observation should be the individual listed contract, not a continuous or front-contract series.

Consequences:

- Use CME DataMine Daily Settlements, Bloomberg Terminal, LSEG Workspace, or Barchart individual-contract data as the primary candidate routes.
- Treat CME CPS and Nasdaq Data Link continuous series only as descriptive long-horizon price series, never as contract-level data.
- If only a continuous series is available, record the exact roll convention (roll date, expiry used, back-adjustment or ratio-adjustment) and explicitly document the limitations.

## 2. Build the contract calendar independently

Settlement files usually lack expiration / last trading date. Even where a vendor exposes an `expiration` field (Databento defines it as "last eligible trade time"), it is not automatically the last trading date and must be cross-checked against a separate product calendar. The design must join an independent contract calendar that maps each contract month to its expiration and last trading date. This is essential for:

- computing time-to-maturity,
- defining roll timing,
- avoiding look-ahead bias in roll-based variables,
- aligning volume and open interest across contracts.

Do not infer expiration from the contract month alone (e.g., "Dec" is not an expiration date).

## 3. Do not let "40+ years" drive coverage assumptions

Vendor marketing about long history refers to the program or to selected flagship products, not to every field and every dataset. The design should specify the required coverage explicitly and verify the earliest available year, the field completeness, and the frequency over that window for each candidate source. A source that advertises 40 years of prices may still lack open interest or OHLC for part of the window.

## 4. Do not treat free daily files as free archives

The CME Daily Bulletin and recent settlement files are free only for a narrow recent window. They are useful for validating field definitions and pipeline logic, but they are not a historical archive. The research plan should not budget a long backtest against free current-day files.

## 5. Field-completeness gate before data selection

The required fields are: trade date, exchange/product, individual contract identifier, delivery month and year, expiration/LTD, settlement, OHLC, volume, open interest. A source is only a primary source if it provides contract-level settlement, OHLC, volume, and open interest. Databento now satisfies this via the definition schema (expiration) plus statistics schema (settlement, cleared volume, open interest) and OHLCV schemas (open/high/low/close/volume). Nasdaq continuous and raw settlement-only files still require a join and should be documented as secondary.

## 6. Volume and open interest interpretation

- Same-day vs prior-day OI matters for event studies and for measures like roll activity. CME settlement files carry prior-day OI, and Databento statistics carry the trading session in `ts_ref`; in both cases confirm the as-of date and never join T-day prices to T-1-day OI without an explicit alignment step.
- Traded volume and cleared volume are different quantities: OHLCV volume is electronic-session traded volume, while cleared volume is the venue's official cleared figure for the previous trading date. Pick one definition and document it.
- In continuous series, volume/OI can be single-contract or roll-aggregated; the design must know which before using them.
- For "active contract" definitions, the study needs per-contract volume/OI to select the most active contract at each date; continuous files cannot reconstruct this reliably.

## 7. Time alignment and look-ahead risk

Use trade date (or settlement date) as the canonical time key. Publication timestamps and data-source dates are not the same as trade date. Any real-time or vintage analysis must use as-of data; final revised files cannot measure what was knowable at the time. This is the same vintage-data principle that applied to the retired study and remains binding.

## 8. Sourcing and budget decision tree

Recommended order of evaluation:

1. Confirm existing university subscriptions first (WRDS, Bloomberg, LSEG Workspace) through the library or finance lab; this is usually the lowest incremental cost and often provides native contract-level fields.
2. For intraday or raw message-level work, evaluate Databento: it provides both OHLCV and the statistics schema for settlement, cleared volume, and open interest, so no external CME join is required for those fields. This is DOCUMENTED; GLBX.MDP3 history depth and academic pricing remain UNKNOWN until an API key is available.
3. For a fast, long, but continuous-only price picture, use Nasdaq Data Link free tier or CME CPS, while documenting roll methodology.
4. For a fully contract-level daily archive with settlement + OHLC + volume + OI, compare CME DataMine Daily Settlements against Barchart and the terminal routes on coverage, export limits, and academic pricing.

## 9. Documentation requirement

For whichever route is chosen, capture in the project's data dictionary: source name and access date, product page URL, field dictionary URL, contract-calendar source, roll rule (for continuous), whether OI is same-day or prior-day, whether settlement is final or preliminary, and the earliest/latest available trade date. Every coverage and price claim should carry a query date, because terms change.

## 10. Immediate unknowns to resolve with vendors

- CME CPS methodology and per-product roll rules.
- Earliest corn history and field completeness in each paid dataset.
- Academic pricing and bulk-export limits for DataMine, Barchart, Databento, Nasdaq Data Link.
- Whether WRDS at this institution includes a commodity-futures database.
- Bloomberg/LSEG field mnemonics and export quotas at the local terminal.

