"""Build the published chart from the reviewed allocation data (standard library only)."""

from decimal import Decimal
from html import escape
from pathlib import Path
import json
from build import write_manifest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = "https://persistent.oaistatic.com/plugins/visualize/charts/data-analytics-plugin/1.2.1/charts/element.js"
SERIES = {
    "cash_share": "Cash + net T-bills / early cash proxy",
    "stock_share": "Disclosed equities",
    "first_share": "Largest holding",
    "second_share": "Second-largest holding",
    "third_share": "Third-largest holding",
}


def main():
    observations = json.loads((ROOT / "data/allocation.json").read_text(encoding="utf-8"))
    rows = [{"date": row["date"], **{
        label: None if row[field] is None else float(row[field])
        for field, label in SERIES.items()
    }} for row in observations]
    rows.append({"date": "1998-06-30", **{label: None for label in SERIES.values()}})
    rows.sort(key=lambda row: row["date"])
    latest = observations[-1]
    config = {
        "id": "berkshire-allocation-history",
        "title": "Cash, equities and the top three holdings | 1968-2026 Q2",
        "description": (
            "All five series use cash plus disclosed equities as the denominator. "
            "The top three company holdings are subsets of equities, ranked separately at each observation; "
            "share classes of the same issuer are combined. There are 141 observations: 30 annual points "
            "for 1968-1997 and 111 quarterly points for 1998 Q4-2026 Q2. Early cash includes other "
            "reported short-term investments; historical consolidation and equity coverage vary. "
            "The later stock series uses Form 13F securities, excluding non-13F foreign holdings and "
            "operating subsidiaries. Unverified rankings remain null. The scope transition is broken "
            "with an empty separator, which is not an observation. This is a disclosure snapshot, "
            "not daily holdings or a real-time portfolio."
        ),
        "summary": (
            f"Five historical allocation lines. At {latest['date']}, cash is "
            f"{Decimal(latest['cash_share']) * 100:.2f}% and equities are "
            f"{Decimal(latest['stock_share']) * 100:.2f}% of cash plus disclosed equities. "
            + "; ".join(
                f"{latest[prefix + '_name']}: {Decimal(latest[prefix + '_share']) * 100:.2f}%"
                for prefix in ["first", "second", "third"]
            ) + "."
        ),
        "height": 540,
        "spec": {
            "type": "line", "x": "date", "y": list(SERIES.values()),
            "yLabel": "Share of cash + disclosed equities", "yDomain": [0, 1], "showLegend": True,
            "colors": dict(zip(SERIES.values(), ["#0D9488", "#5965D9", "#D58A26", "#C45678", "#427FA5"])),
            "valueFormat": {"style": "percent", "maximumFractionDigits": 2},
            "referenceLines": [{"axis": "x", "value": "1998-12-31", "label": "1998 Q4: quarterly 13F scope"}],
        },
        "rows": rows,
    }
    encoded = json.dumps(config, ensure_ascii=False, indent=2)
    with (ROOT / "data/chart.json").open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(encoded + "\n")
    fields = [("Cash and net T-bills", "cash_usd", "cash_share"),
              ("Disclosed equities", "stock_usd", "stock_share")]
    for prefix in ["first", "second", "third"]:
        fields.append((latest[f"{prefix}_name"], f"{prefix}_value_usd", f"{prefix}_share"))
    table_rows = "\n".join(
        f"<tr><td>{escape(name)}</td><td>${Decimal(latest[value]) / Decimal(10**9):,.3f}B</td>"
        f"<td>{Decimal(latest[share]) * 100:.2f}%</td></tr>"
        for name, value, share in fields
    )
    template = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Source-backed Berkshire Hathaway cash, disclosed equities and top-three holding allocation history, 1968-2026 Q2.">
<title>Berkshire Hathaway Allocation History</title>
<style>
*,*::before,*::after { box-sizing:border-box; }
:root { color-scheme:light; font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; color:#24323c; background:#fafbfc; }
body { margin:0; } main { max-width:1440px; margin:auto; padding:32px 24px 48px; }
h1 { font-size:clamp(24px,3vw,36px); line-height:1.2; margin:0 0 12px; }
h2 { font-size:21px; margin:30px 0 10px; } p { max-width:1100px; }
a { color:#146493; text-underline-offset:3px; } .muted { color:#596772; }
.chart-card { background:white; padding:20px 12px 8px; border:1px solid #e4e9ed; border-radius:10px; margin:24px 0; }
[data-data-chart] { color-scheme:light; font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; color:#242424; min-width:0; width:100%;
 --foreground:#242424; --muted-foreground:#6b6b6b; --card:#fff; --muted:#f3f3f3; --popover:#fff;
 --popover-foreground:#242424; --border:#e7e7e7; --ring:#176bb8; --green:#22794d; --red:#bc4760; }
table { border-collapse:collapse; width:min(100%,780px); font-variant-numeric:tabular-nums; }
th,td { padding:9px 12px; border-bottom:1px solid #dfe5e9; text-align:right; } th:first-child,td:first-child { text-align:left; }
.note { border-left:3px solid #0d9488; padding-left:16px; } footer { margin-top:32px; font-size:14px; }
@media(max-width:600px) { main { padding:22px 12px; } .chart-card { padding:12px 0; } th,td { padding:8px 5px; font-size:14px; } }
</style>
</head>
<body><main>
<h1>Berkshire Hathaway allocation history</h1>
<p class="muted">1968-2026 Q2 &middot; 141 disclosed observations &middot; Evidence reviewed November 6, 2026</p>
<p>Each line is divided by <strong>cash plus disclosed equities</strong>. The top three companies are ranked anew at each date, with share classes combined. Their values are already included in equities.</p>
<section class="chart-card" id="berkshire-chart" data-data-chart data-viz-composition>
<div data-viz-container style="min-height:610px"></div>
</section>
<p class="muted">Click a legend item to show or hide a line. Double-click an item to isolate it. Hover over a date for exact percentages.</p>
<p class="note"><strong>Read the scope break:</strong> 1968-1997 uses annual reports and an early cash proxy that may include other short-term instruments. From 1998 Q4, the series uses quarterly 13F equities and the specified cash/T-bill pool. These scopes differ. Unverified ranks are blank, and connecting segments do not describe daily holdings.</p>
<h2>Latest paired disclosure: June 30, 2026</h2>
<table><thead><tr><th scope="col">Component / company</th><th scope="col">Value (USD)</th><th scope="col">Share of total</th></tr></thead><tbody>
__TABLE_ROWS__
</tbody></table>
<p class="muted">This is a fixed research snapshot. The denominator excludes operating businesses and non-13F equities in the quarterly section; it is not Berkshire's total assets.</p>
<p><a href="https://github.com/okht/berkshire-allocation-history/blob/main/data/allocation.csv">Download data (CSV)</a> &middot;
<a href="https://github.com/okht/berkshire-allocation-history/blob/main/docs/methodology.md">Methodology and limitations</a> &middot;
<a href="https://github.com/okht/berkshire-allocation-history/blob/main/data/sources.json">Source URLs</a></p>
<footer><a href="https://github.com/okht/berkshire-allocation-history">View the repository and reproduction scripts</a>. Amounts and ratios are computed from public filings. Chart module: Data charts 1.2.1 (loaded from its pinned CDN; internet access required).</footer>
<noscript><p>JavaScript is required for the interactive chart. The full numerical data and methodology are available through the links above.</p></noscript>
</main>
<script type="module">
const { mountChart } = await import("__RUNTIME__");
const root = document.getElementById("berkshire-chart");
const config = __CONFIG__;
mountChart(root.querySelector("[data-viz-container]"), config);
</script>
</body></html>
'''
    output = template.replace("__TABLE_ROWS__", table_rows).replace("__RUNTIME__", RUNTIME)
    output = output.replace("__CONFIG__", encoded.replace("</", "<\\/"))
    (ROOT / "docs").mkdir(exist_ok=True)
    with (ROOT / "docs/index.html").open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(output)
    write_manifest()
    print(f"Built data/chart.json and docs/index.html from {len(observations)} observations.")


if __name__ == "__main__":
    main()
