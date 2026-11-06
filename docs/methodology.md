# Methodology

This dataset reconstructs five allocation and concentration series from public Berkshire Hathaway financial reports and SEC holdings disclosures. Its audit cutoff is **2026-11-06**; the publication date is **2026-11-07**. The final observation is **2026-06-30**. Publication does not imply a later holdings refresh.

## Observation dates and coverage

| Segment | Observations | Stock measure | Cash measure |
| --- | ---: | --- | --- |
| Fiscal 1968–1997 | 30 annual | Disclosed equity market/fair value in the documented annual-report scope | Cash plus separately disclosed short-term investments, subject to each report's scope |
| 1998Q4–2026Q2 | 111 quarterly | Berkshire Hathaway Inc.'s main 13F portfolio, reconstructed with amendments | Documented Insurance and Other cash/Treasury pool, with historical Finance adjustments |

The annual and quarterly segments are separated in the chart. A 1998 annual-report observation exists in the research audit but is excluded from the published series, which uses the 1998Q4 13F observation. No annual values are interpolated into missing quarters, and connecting lines do not describe daily holdings.

Some early fiscal years end a few days before or after December 31. Cash at the parent fiscal year-end may be paired with insurer equities valued at calendar year-end; row notes preserve this mismatch. `year` identifies the fiscal observation, so it can differ from the calendar year in `date`. Reports for 1965–1967 were examined but excluded because mixed securities categories could not be separated sufficiently for the chosen ratio.

## Common denominator

For each date:

```text
T = C + S
cash_share   = C / T
stock_share  = S / T
first_share  = M1 / T
second_share = M2 / T
third_share  = M3 / T
```

`M1` through `M3` are holdings within `S`; adding their shares to the cash and stock shares would double count them. Cash and stock shares sum to one. Concentration is measured against cash plus stocks, not against stocks alone, Berkshire's market capitalization, or its total assets.

## Cash construction

Where separately disclosed, the quarterly calculation is:

```text
C = cash and cash equivalents
  + separately reported short-term U.S. Treasury bills
  - disclosed payables for unsettled Treasury purchases
```

Treasury bills already inside cash equivalents are not added again. Historical Insurance and Other balances are combined with the separately presented Finance and Financial Products balances where needed to maintain the documented scope. Railway, utility, and energy cash is excluded from this quarterly pool. Reporting reorganizations and comparisons to later restated amounts are recorded in the observation notes; this is not a uniformly restated business perimeter across all years.

A missing Treasury-purchase payable is **unknown**, not a confirmed zero. When no separate amount was identified, the dataset retains the reported cash/Treasury sum without inventing an extra deduction. Such periods cannot be described as precisely reconstructed net-Treasury balances. [Quarterly component records](../data/evidence/quarterly_cash_components.json) retain these nullable fields and the deduction status.

For 2026Q2, the disclosed calculation is $35.096 billion cash and equivalents + $324.905 billion Treasury bills − $0.771 billion unsettled Treasury purchases = **$359.230 billion**. See the [quarterly report](https://www.berkshirehathaway.com/qtrly/2ndqtr26.pdf), balance sheet and related payable disclosure.

Early annual cash is a broader historical proxy. Short-term captions can include commercial paper and other instruments, and insurance, banking, finance, and affiliated-company consolidation changes over time. The data do not claim to isolate net U.S. Treasury bills for every early year. In particular, 1985–1986 use original-report cash matched to the original equity scope; 1987 uses the 1988 report's restated comparative scope.

## Stock construction

### Annual reports

The annual segment uses explicitly disclosed market or fair values, not cost or carrying value when those differ. Separately reported common-stock investments are included where their market value belongs within the selected equity scope. Redeemable preferred shares classified with fixed-maturity securities are excluded; nonredeemable preferred shares can be included in the equity category. Affiliates, subsidiaries, and Finance assets require period-specific treatment, documented in row notes.

Some early financial groups were unconsolidated, and later reports do not always provide matching restated equity fair values. Some cash and equity captions have different coverage: Finance cash is retained where documented, including 1995–1997, while an undisclosed Finance equity value is not inferred or assigned to zero. The series is not a uniformly matched portfolio covering the whole group. Row notes preserve these limitations.

### Quarterly 13F filings

The quarterly segment uses Berkshire Hathaway Inc.'s main 13F filing series. Separately filed portfolios such as NEAM are not added. Non-13F investments, including many foreign-listed stocks, and wholly owned operating businesses are outside this stock denominator. Index funds and other reported securities remain in the 13F total; funds and options are ineligible for individual-company rankings.

Original filings and amendments are reconciled at security level. A complete restatement replaces its earlier table; newly disclosed holdings are added without counting prior holdings again. Partial corrections replace only the affected securities. Cover-only corrections do not create a second portfolio. For a few legacy filings, the explanatory text and security overlap determine treatment because the amendment checkbox alone is misleading.

Later releases of confidential holdings are assigned to their original reporting quarters. This produces a **retrospectively completed public record**, not a dataset of information available on each original filing date. A backtest of what investors could have known at the time would need a separate reconstruction of disclosure timing.

Source amounts are converted using the filing's stated units. Legacy tables usually report thousands of dollars; modern information tables report dollars from 2022Q4. Integer-dollar output preserves the conversion, not extra precision. Where a filing's cover total disagrees with its security rows, the audited series retains the security-row sum and records the discrepancy. It introduces no balancing adjustment.

## Company rankings

Manager rows for the same security are aggregated once. Included share classes of the same issuer are then combined into a company total, and the ranking is recalculated for each period. For example, Alphabet's GOOG and GOOGL classes are combined. Related but separately constituted issuers are not automatically merged merely because their names share a brand.

For annual reports, a partial list of large holdings establishes a rank only when the remaining evidence bounds every possible omitted company below it. `Other` is a group, never an individual holding. A known company name is insufficient if its complete value across included security classes remains unverified.

### Ranking gaps

| Rank | Verified observations | Gaps |
| --- | ---: | --- |
| Largest | 128 / 141 | Fiscal 1968–1976 and 1978–1981 |
| Second-largest | 126 / 141 | Fiscal 1968–1982 |
| Third-largest | 124 / 141 | Fiscal 1968–1982, 1985, and 1993 |

All 111 quarterly observations have three verified company rankings. An annual gap means that available evidence does not establish the required complete company value; it does not mean that Berkshire held no such investment.

**1977 illustrates why issuer aggregation matters.** GEICO common stock of $10.516 million and convertible preferred stock of $33.033 million combine to $43.549 million, establishing first place. Washington Post common stock is $33.401 million, but approximately $4.038 million of other preferred securities lacks issuer identification. Washington Post's second-place identity can be bounded, while its complete same-company value cannot; the plotted second value therefore remains null. For third place, Capital Cities common stock plus that preferred residual could reach about $17.266 million, above Interpublic's disclosed $17.187 million. The third rank also remains null. The [original 1977 report](https://theoraclesclassroom.com/wp-content/uploads/2019/09/1977-Berkshire-AR.pdf) supports the components but does not resolve the missing issuer identities.

For 1985, a minority-interest adjustment prevents a precise comparison between ABC and Beatrice in the original consolidation scope. For 1993, remaining preferred-stock and Other categories are sufficiently bounded to establish second place, but not third. The relevant rows retain the details.

## Statistics and reproducibility

Peaks are computed only over verified observations and separately for the annual and quarterly segments. They are observed-sample maxima, not daily historical records. Missing ranks are excluded, never converted to zero. No overall mean is computed by pooling unequal annual and quarterly sampling frequencies.

The published inputs reproduce the derived tables, ratios, statistics, and chart. [Retained evidence](../data/evidence/) includes annual ranking proofs, cash components, complete quarterly company portfolios, and issuer mappings. It does not replace the original filings or provide an automatic source-to-dataset refresh pipeline. [The source catalog](../data/sources.json) links the underlying reports and filings; original third-party PDFs are not bundled.

From the repository root:

```sh
python scripts/build.py
python scripts/render_chart.py
python scripts/validate.py
```

The validation checks observation coverage, arithmetic, ranking order, missing-value treatment, and consistency between generated artifacts. Monetary calculations use decimal/integer arithmetic; chart rendering may use floating-point display values. The README's PNG preview is a checked export using the same pinned Data charts 1.2.1 component; these commands regenerate the data and HTML, but do not regenerate the PNG. See the [data dictionary](data-dictionary.md) for storage conventions.
