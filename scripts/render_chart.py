"""Build the saved Data chart and a portable HTML period-by-period holdings explorer."""

import csv
import json
from collections import defaultdict
from decimal import Decimal
from html import escape
from pathlib import Path
from build import write_manifest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CASH, EQUITY, TOTAL = "Cash / short-term pool", "Disclosed equities", "Top 10 combined"
RANKS = [f"Rank {i}" for i in range(1, 11)]
PALETTE = ["#0D887D", "#505DCD", "#BD730F", "#B34D75", "#347CA5", "#697E28",
           "#873E9C", "#B45234", "#247161", "#6D65A3", "#83623F", "#476578"]
COLORS = dict(zip([CASH, EQUITY, *RANKS], PALETTE))
COLORS[TOTAL] = "#A75819"
BREAK = "1998-06-30"
RUNTIME = "https://persistent.oaistatic.com/plugins/visualize/charts/data-analytics-plugin/1.2.1/charts/element.js"
LABELS = {"OCCIDENTAL PETE CORP": "Occidental Petroleum Corp.", "CHUBB LIMITED": "Chubb Ltd."}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write(path, content):
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def js(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")


def display(value, is_money=False):
    if value is None:
        return None
    d = Decimal(value)
    return f"${d:,.0f}" if is_money else f"{d * 100:.2f}%"


def number(value):
    return None if value is None else float(value)


def range_rows():
    with (DATA / "percentage-ranges.csv").open(encoding="utf-8-sig", newline="") as handle:
        ranges = {(r["series"], r["sample"]): r for r in csv.DictReader(handle)}
    rows = []
    for series in ["Cash", *RANKS]:
        cells = [f'<th scope="row">{escape(series)}</th>']
        for sample in ("all", "quarterly"):
            row = ranges[series, sample]
            for bound in ("minimum", "maximum"):
                share = display(row[f"{bound}_share"])
                period = escape(row[f"{bound}_period"])
                date = escape(row[f"{bound}_date"])
                company = row[f"{bound}_company"]
                details = f'<time datetime="{date}">{period}</time>'
                if company:
                    details += " &middot; " + escape(LABELS.get(company, company))
                cells.append(f"<td><strong>{share}</strong><small>{details}</small></td>")
            cells.append(f'<td class="count">{int(row["verified_observations"])}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(rows)


def main():
    allocations = load("allocation.json")
    ranks = defaultdict(list)
    for r in load("top-ten-holdings.json"):
        ranks[r["date"]].append(r)
    totals = {r["date"]: r for r in load("top-ten-totals.json")}
    rows, panels = [], []
    for a in allocations:
        day = a["date"]
        ordered = sorted(ranks[day], key=lambda r: r["rank"])
        assert [r["rank"] for r in ordered] == list(range(1, 11))
        t = totals[day]
        rows.append({"date": day, CASH: number(a["cash_share"]), EQUITY: number(a["stock_share"]),
                     **{label: number(r["share_of_total"]) for label, r in zip(RANKS, ordered)},
                     TOTAL: number(t["top_ten_share_of_total"])})
        period = a["period"] if a["frequency"] == "annual" else f"{day[:4]} Q{int(day[5:7])//3}"
        gaps = defaultdict(list)
        for r in ordered:
            if not r["verified"]:
                gaps[r["reason"]].append(r["rank"])
        panels.append({"date": day, "period": period, "verified": t["verified_rank_count"],
                       "gaps": [[indices, reason] for reason, indices in gaps.items()],
                       "rows": [[LABELS.get(r["company"], r["company"]), display(r["value_usd"], True),
                                 display(r["share_of_total"])] for r in ordered],
                       "total": [display(t["top_ten_value_usd"], True), display(t["top_ten_share_of_total"])],
                       "denominator": display(a["total_usd"], True),
                       "sources": list(dict.fromkeys([*a["sources"], *(u for r in ordered for u in r["sources"])]))})
    rows.append({"date": BREAK, **dict.fromkeys([CASH, EQUITY, *RANKS, TOTAL])})
    rows.sort(key=lambda r: r["date"])
    facts = {"source": "Share of cash plus disclosed equities", "complete": sum(t["complete"] for t in totals.values())}
    spec = {"type": "line", "x": "date", "y": [CASH, EQUITY, *RANKS], "showLegend": True,
            "yLabel": facts["source"], "yDomain": [0, 1], "colors": COLORS,
            "valueFormat": {"style": "percent", "maximumFractionDigits": 2},
            "referenceLines": [{"axis": "x", "value": "1998-12-31", "label": "1998 Q4: quarterly 13F scope"}]}
    config = {"id": "berkshire-allocation-history", "title": "Berkshire Hathaway: cash, equities and ranks 1-10",
              "height": 505, "spec": spec, "rows": rows,
              "description": "Ranks track the company at each position on each date. All individual shares use cash plus disclosed equities. Blank ranks lack sufficient evidence. Fiscal annual reports and the quarterly 13F series are separated by a gap.",
              "summary": f"{len(allocations)} dates, 1968-2026 Q2. At June 30, 2026 the top ten account for {panels[-1]['total'][1]} of cash plus disclosed equities."}
    write(DATA / "chart.json", json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    latest = panels[-1]
    def cells(values, tag="td"):
        return "".join(f"<{tag}>{escape(str(x)) if x is not None else '&mdash;'}</{tag}>" for x in values)
    replacements = {
        "__RANGE_ROWS__": range_rows(),
        "__CONFIG__": js(config), "__PANELS__": js(panels), "__RUNTIME__": RUNTIME,
        "__OPTIONS__": "".join(f'<option value="{i}"{" selected" if i==len(panels)-1 else ""}>{escape(p["period"])}</option>' for i,p in reversed(list(enumerate(panels)))),
        "__LATEST_ROWS__": "".join("<tr>"+cells([i,*row])+"</tr>" for i,row in enumerate(latest["rows"],1)),
        "__LATEST_SUM__": cells(["", "Top ten combined", *latest["total"]]),
        "__LATEST_DENOM__": latest["denominator"], "__LATEST_WEIGHT__":latest["total"][1],
        "__COVERAGE__": str(facts["complete"]), "__LATEST_LABEL__": latest["period"],
    }
    html = Path(__file__).with_name("chart_template.html").read_text(encoding="utf-8")
    for token, value in replacements.items():
        html = html.replace(token, value)
    write(ROOT / "docs/index.html", html)
    write_manifest()
    print(f"Built chart and interactive explorer for {len(allocations)} dates and {len(allocations)*10} rank slots.")


if __name__ == "__main__":
    main()
