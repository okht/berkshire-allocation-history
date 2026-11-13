"""Optional: export the README figure from data/chart.json. Requires Matplotlib."""

import json
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
chart = json.loads((ROOT / "data/chart.json").read_text(encoding="utf-8"))
rows, spec = chart["rows"], chart["spec"]
dates = [date.fromisoformat(r["date"]) for r in rows]
cash, equities, *ranks = spec["y"]
total = "Top 10 combined"
groups = [
    ("Allocation and concentration", [cash, equities, total]),
    ("The three largest positions", ranks[:3]),
    ("Positions four through ten", ranks[3:]),
]
fig, axes = plt.subplots(3, 1, figsize=(15.2, 10.5), sharex=True)
fig.subplots_adjust(left=.067, right=.80, bottom=.097, top=.875, hspace=.39)
fig.text(.065, .958, "Berkshire Hathaway allocation history", fontsize=25, weight="bold", color="#192f2a")
fig.text(.067, .918, "Share of cash + disclosed equities    |    Fiscal 1968 to 2026 Q2", fontsize=13, color="#445c54")
for i, (ax, (title, fields)) in enumerate(zip(axes, groups)):
    ax.set_title(title, loc="left", fontsize=13, weight="bold", pad=6, color="#213b32")
    for key in fields:
        values = [r[key] for r in rows]
        c = spec["colors"][key]
        ax.plot(dates, [float("nan") if v is None else v for v in values], lw=1.9, c=c, label=key)
        isolated = [j for j,v in enumerate(values) if v is not None and (j==0 or values[j-1] is None) and (j==len(values)-1 or values[j+1] is None)]
        ax.scatter([dates[j] for j in isolated],[values[j] for j in isolated],s=20,color=c,zorder=4)
    ax.axvline(date(1998,12,31), color="#818c84", lw=.9, ls="--")
    if i==0:
        ax.annotate("Quarterly 13F scope", (date(1998,12,31),.96), xytext=(5,0), textcoords="offset points", fontsize=9, color="#545f58")
    ax.set_ylim(bottom=0)
    if i==0: ax.set_ylim(0,1.02)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5)); ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.grid(axis="y", color="#e3e9e5", lw=.8)
    ax.spines[["top","right","left"]].set_visible(False); ax.spines["bottom"].set_color("#cbd6cf")
    ax.tick_params(length=0, colors="#526059", labelsize=10, pad=5)
    ax.legend(loc="center left", bbox_to_anchor=(1.005,.5), frameon=False, fontsize=10, handlelength=2)
axes[-1].xaxis.set_major_locator(mdates.YearLocator(5)); axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axes[-1].set_xlim(dates[0],dates[-1])
fig.text(.067,.032,"Annual-report and quarterly filing scopes differ. Gaps mark unverified ranks; a combined total requires all ten. The three panels use different vertical scales.",fontsize=10,color="#495e53")
fig.savefig(ROOT/"assets/allocation-history.png",dpi=145,facecolor="white",metadata={"Software":"Matplotlib"})
plt.close(fig)
