# Data dictionary

The published snapshot contains 141 observations: 30 annual records for fiscal 1968–1997 and 111 quarterly records from 1998Q4 through 2026Q2. Its audit cutoff is 2026-11-06. All monetary values are U.S. dollars.

## Files

| File | Purpose |
| --- | --- |
| [`data/inputs.json`](../data/inputs.json) | Audited inputs used to rebuild the published allocation series. This is a fixed input snapshot, not a live filing feed. |
| [`data/allocation.json`](../data/allocation.json) | Full observation records, including amounts, calculated shares, evidence notes, and source links. |
| [`data/allocation.csv`](../data/allocation.csv) | Tabular export of the allocation records. |
| [`data/statistics.json`](../data/statistics.json) | Snapshot summary, verified-observation counts, and segment-specific concentration statistics. |
| [`data/sources.json`](../data/sources.json) | Public source catalog for the underlying reports and filings. |
| [`data/manifest.json`](../data/manifest.json) | SHA-256 hashes of the included inputs, evidence, scripts, and generated analytical files. |
| [`data/evidence/`](../data/evidence/) | Annual ranking proofs, quarterly cash components, full quarterly company portfolios, issuer aliases, and ranking audits. |
| [`data/chart.json`](../data/chart.json) | Rendering specification and chart data derived from the allocation records. |
| [`docs/index.html`](index.html) | Interactive chart with embedded data; requires internet access to load its pinned chart component. |
| [`assets/allocation-history.png`](../assets/allocation-history.png) | Checked static preview exported with Data charts 1.2.1. The documented Python commands do not regenerate this image. |

`allocation.json` is an array of records. `inputs.json` contains a `rows` array plus snapshot/publication dates, expected counts, a decimal precision of 36 significant digits, and a `numeric_baseline` hash that locks the reviewed numerical output. The build recomputes totals and shares from the input amounts.

In `statistics.json`, `segments.annual` and `segments.quarterly` contain a `series` object for each of the five share fields. Each series records its verified count, maximum, and minimum. An extremum includes the date, amount, denominator, and `share_of_total`; company concentration points also identify the company. `latest`, `verified_ranks`, and `missing_ranks` summarize the full snapshot.

In `sources.json`, each entry has a public `url`, `source_kind`, supporting `observation_dates`, repository-relative `evidence_files`, and any retained page or other `locators`. A source used only for comparative or ranking evidence can have no main-series observation date.

## Allocation record

| Field | JSON type | Meaning |
| --- | --- | --- |
| `date` | string | ISO `YYYY-MM-DD` observation date. Early records can use a fiscal year-end other than December 31. |
| `period` | string | Display label: `FY 1968`, for example, or an ISO quarterly date. |
| `year` | integer | Fiscal observation year for annual records; calendar year for quarterly records. It need not equal the year in an early fiscal `date`. |
| `frequency` | string | `annual` or `quarterly`. |
| `scope` | string | `annual_report_disclosed_equities` or `cash_plus_13f_securities`. These identify different coverage regimes, not interchangeable portfolio definitions. |
| `cash_usd` | string | Cash-like pool `C`, constructed under the period's documented scope and disclosure limits. |
| `stock_usd` | string | Disclosed stock/securities value `S`: annual-report equity fair value or reconstructed main-filer 13F total. |
| `total_usd` | string | Common denominator `C + S`. |
| `first_name` | string or null | Largest verified company holding in this observation's stock scope. |
| `second_name` | string or null | Second-largest verified company holding. |
| `third_name` | string or null | Third-largest verified company holding. |
| `first_value_usd` | string or null | Complete verified value `M1` of included securities belonging to the largest company. |
| `second_value_usd` | string or null | Complete verified value `M2` of the second-largest company. |
| `third_value_usd` | string or null | Complete verified value `M3` of the third-largest company. |
| `cash_share` | string | Decimal fraction `C / (C + S)`. |
| `stock_share` | string | Decimal fraction `S / (C + S)`. |
| `first_share` | string or null | Decimal fraction `M1 / (C + S)`. |
| `second_share` | string or null | Decimal fraction `M2 / (C + S)`. |
| `third_share` | string or null | Decimal fraction `M3 / (C + S)`. |
| `second_rank_verified` | boolean | Whether both second-place rank and the required complete company value are established. |
| `third_rank_verified` | boolean | Whether both third-place rank and the required complete company value are established. |
| `notes` | array of strings | Source-specific accounting scope, amendments, corrections, reconciliation decisions, and evidence gaps. |
| `sources` | array of strings | Public URLs supporting the observation. Multiple URLs can represent cash reports, original holdings, amendments, and supplementary ranking evidence. |

## Numeric and missing-value conventions

Amounts and calculated shares are serialized as strings to preserve integer and decimal precision across software. Parse them with a decimal-aware library before calculation. A value such as `"0.0778794227867"` means approximately **7.78794%**, not 0.077879%. Multiply shares by 100 only for percentage display.

An integer-dollar amount can originate from a report rounded to thousands or millions of dollars. The storage format does not imply dollar-level measurement accuracy. Display values in the README are rounded; calculations use the unrounded stored values.

`null` means unavailable or not established under the documented scope. It is never a zero holding. A rank's name, value, and share remain null when its complete value cannot be verified, even if a likely company is known. In CSV, nulls are empty cells; array fields are JSON-encoded text.

The flat allocation table stores the resulting cash pool. It does not expose every historical cash component as a separate column. Quarterly components are retained in [`quarterly_cash_components.json`](../data/evidence/quarterly_cash_components.json): `cash_equivalents_usd`, `separately_reported_treasury_bills_usd`, `unsettled_treasury_payable_usd`, and `payable_status`. A missing Treasury-purchase payable must not be inferred to be zero from the presence of `cash_usd`; consult the component record, `notes`, and the linked report.

## Relationships and chart-only data

```text
total_usd = cash_usd + stock_usd
cash_share + stock_share = 1
first_value_usd >= second_value_usd >= third_value_usd  [when verified]
first_value_usd + second_value_usd + third_value_usd <= stock_usd
```

The top-three values are subsets of the stock total. Companies can move between ranks over time; `second_share` tracks each period's second-largest company, not a fixed stock.

Chart data may contain an all-null separator between the annual and quarterly regimes. It is a rendering instruction, not a 142nd observation. Chart display values can be floating-point numbers; use `allocation.json` for exact calculations. Dates, missing rankings, and the regime break should be preserved when making another chart.

For the inclusion rules behind these fields, see [Methodology](methodology.md).
