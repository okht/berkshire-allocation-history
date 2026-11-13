"""Build individual issuer ranks and complete top-ten sums from public evidence."""
from __future__ import annotations

from decimal import Decimal, localcontext


# CUSIP-linked spellings repair split or carried-over words in early text tables.
# The retained quarterly evidence preserves each original label and security row.
ISSUER_LABELS = {
    "093671": "H&R Block Inc.",
    "20825C": "ConocoPhillips",
    "82028K": "Shaw Communications Inc.",
    "867914": "SunTrust Banks Inc.",
}


def quarterly_positions(portfolio: dict) -> list[dict]:
    eligible = sorted(
        (issuer for issuer in portfolio["rank_all"] if issuer["individual_company_ranking_eligible"]),
        key=lambda issuer: (-int(issuer["value_usd"]), issuer["company_id"]),
    )
    if len(eligible) < 10:
        raise ValueError(f"Fewer than ten eligible companies in the 13F portfolio at {portfolio['date']}")
    return [
        {
            "rank": rank, "company": ISSUER_LABELS.get(issuer["company_id"], issuer["name"]), "company_id": issuer["company_id"],
            "cusips": issuer["cusips"], "value_usd": issuer["value_usd"], "verified": True,
            "reason": "Ranked by the combined market value of this issuer's eligible securities in the amended 13F portfolio.",
            "sources": issuer["sources"],
        }
        for rank, issuer in enumerate(eligible[:10], 1)
    ]


def build_top_ten(observations: list[dict], annual_evidence: list[dict], quarterly_evidence: list[dict], precision: int):
    annual = {period["year"]: period for period in annual_evidence}
    quarterly = {period["date"]: period for period in quarterly_evidence}
    holdings, totals = [], []
    with localcontext() as context:
        context.prec = precision
        for observation in observations:
            base = {key: observation[key] for key in ("date", "period", "frequency")}
            if observation["frequency"] == "quarterly":
                portfolio = quarterly[observation["date"]]
                positions = quarterly_positions(portfolio)
            else:
                portfolio = annual[observation["year"]]
                positions = portfolio["ranks"]
            if [position["rank"] for position in positions] != list(range(1, 11)):
                raise ValueError(f"Expected ten numbered evidence records at {observation['date']}")
            stocks, total = (Decimal(observation[key]) for key in ("stock_usd", "total_usd"))
            values, period_sources = [], list(observation["sources"])
            for position in positions:
                verified = position["verified"]
                raw_value = position["value_usd"]
                company = position["company"]
                if not isinstance(verified, bool) or verified != (raw_value is not None) or verified != bool(company):
                    raise ValueError(f"Rank verification does not match the supplied identity and value: {base['date']}, rank {position['rank']}")
                value = Decimal(raw_value) if verified else None
                if value is not None:
                    values.append(value)
                sources = list(dict.fromkeys(position["sources"] + portfolio["sources"] + observation["sources"]))
                period_sources.extend(sources)
                holdings.append({
                    **base, "rank": position["rank"], "company": company,
                    "company_id": position.get("company_id"), "cusips": position.get("cusips", []),
                    "value_usd": raw_value, "share_of_total": str(value / total) if verified else None,
                    "share_of_stocks": str(value / stocks) if verified else None,
                    "verified": verified, "reason": position["reason"], "sources": sources,
                })
            complete = len(values) == 10
            combined = sum(values, Decimal(0)) if complete else None
            totals.append({
                **base, **{key: observation[key] for key in ("cash_usd", "stock_usd", "total_usd")},
                "verified_rank_count": len(values), "complete": complete,
                "top_ten_value_usd": str(combined) if complete else None,
                "top_ten_share_of_total": str(combined / total) if complete else None,
                "top_ten_share_of_stocks": str(combined / stocks) if complete else None,
                "sources": list(dict.fromkeys(period_sources)),
            })
    return holdings, totals


def top_ten_statistics(holdings: list[dict], totals: list[dict]) -> dict:
    latest = totals[-1]
    stats = {
        "observations": len(totals), "rank_records": len(holdings),
        "complete_observations": sum(row["complete"] for row in totals),
        "latest": {**latest, "holdings": [row for row in holdings if row["date"] == latest["date"]]},
        "segments": {},
    }
    for frequency in ("annual", "quarterly"):
        sample = [row for row in totals if row["frequency"] == frequency]
        complete = [row for row in sample if row["complete"]]
        segment = {
            "observations": len(sample), "complete_observations": len(complete),
            "verified_by_rank": {str(rank): sum(row["verified"] for row in holdings if row["frequency"] == frequency and row["rank"] == rank) for rank in range(1, 11)},
        }
        for label, comparator in (("maximum", max), ("minimum", min)):
            extreme = comparator(complete, key=lambda row: Decimal(row["top_ten_share_of_total"])) if complete else None
            segment[label] = {key: value for key, value in extreme.items() if key != "sources"} if extreme else None
        stats["segments"][frequency] = segment
    return stats
