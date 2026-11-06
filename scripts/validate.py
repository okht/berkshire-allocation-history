#!/usr/bin/env python3
"""Validate publication data, issuer grouping, provenance and deterministic output.

The checks are read-only and require only Python's standard library.
"""
from __future__ import annotations

from calendar import monthrange
import csv
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

from build import DATA, ROOT, POSITIONS, build_observations, build_sources, build_statistics, canonical_hash, load_json


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_observations(inputs: dict, rows: list[dict]) -> None:
    require(len(rows) == 141, "Expected 141 observations")
    require(len({row["date"] for row in rows}) == 141, "Duplicate observation dates")
    annual = [row for row in rows if row["frequency"] == "annual"]
    quarterly = [row for row in rows if row["frequency"] == "quarterly"]
    require(len(annual) == 30 and len(quarterly) == 111, "Annual/quarterly count mismatch")
    require([row["year"] for row in annual] == list(range(1968, 1998)), "Annual coverage must be FY1968-FY1997")
    expected_quarters = []
    for year in range(1998, 2027):
        for month in (3, 6, 9, 12):
            date = f"{year:04}-{month:02}-{monthrange(year, month)[1]:02}"
            if "1998-12-31" <= date <= "2026-06-30":
                expected_quarters.append(date)
    require([row["date"] for row in quarterly] == expected_quarters, "Quarterly dates are not consecutive")
    require(sum(row["second_value_usd"] is not None for row in rows) == 126, "Expected 126 verified second ranks")
    require(sum(row["third_value_usd"] is not None for row in rows) == 124, "Expected 124 verified third ranks")
    require(all(row["date"] != "1998-06-30" for row in rows), "Visual separator must not be a data observation")
    for row in rows:
        date = row["date"]
        for key in ("cash_usd", "stock_usd", "total_usd", "first_value_usd", "second_value_usd", "third_value_usd"):
            require(row[key] is None or isinstance(row[key], str) and re.fullmatch(r"[0-9]+", row[key]) is not None, f"Invalid exact-dollar field {date} {key}")
        cash, stocks, total = (Decimal(row[key]) for key in ("cash_usd", "stock_usd", "total_usd"))
        require(cash >= 0 and stocks > 0 and cash + stocks == total, f"Invalid denominator {date}")
        amounts = [Decimal(row[position + "_value_usd"]) for position in POSITIONS if row[position + "_value_usd"] is not None]
        names = [row[position + "_name"] for position in POSITIONS if row[position + "_value_usd"] is not None]
        require(amounts == sorted(amounts, reverse=True), f"Ranks not descending {date}")
        require(all(value > 0 for value in amounts) and sum(amounts) <= stocks, f"Ranks exceed stocks {date}")
        require(len(names) == len(set(names)), f"Repeated company in ranks {date}")
        for position in POSITIONS:
            value, name, share = (row[position + suffix] for suffix in ("_value_usd", "_name", "_share"))
            require((value is None) == (name is None) == (share is None), f"Missing-rank inconsistency {date} {position}")
        require(row["second_rank_verified"] == (row["second_value_usd"] is not None), f"Second-rank flag {date}")
        require(row["third_rank_verified"] == (row["third_value_usd"] is not None), f"Third-rank flag {date}")
        with localcontext() as context:
            context.prec = inputs["decimal_precision"]
            require(abs(Decimal(row["cash_share"]) + Decimal(row["stock_share"]) - 1) < Decimal("1e-30"), f"Allocation fractions do not sum to one {date}")
    baseline = inputs["numeric_baseline"]
    require(canonical_hash([{key: row[key] for key in baseline["fields"]} for row in rows]) == baseline["sha256"], "Original numeric snapshot changed")
    require(rows == build_observations(inputs), "Allocation JSON is not reproducible from curated inputs")


def validate_issuer_evidence(rows: list[dict]) -> int:
    quarterly = {row["date"]: row for row in rows if row["frequency"] == "quarterly"}
    evidence = load_json(DATA / "evidence" / "quarterly_company_holdings.json")["rows"]
    aliases = load_json(DATA / "evidence" / "issuer_aliases.json")
    require(len(evidence) == 111, "Expected 111 full 13F portfolios")
    securities_checked = 0
    for period in evidence:
        date = period["date"]
        row = quarterly[date]
        groups = period["rank_all"]
        require(sum(int(group["value_usd"]) for group in groups) == int(row["stock_usd"]) == int(period["stock_total_usd"]), f"Full holdings total {date}")
        unique_securities = set()
        for group in groups:
            component_sum = 0
            for security in group["securities"]:
                key = (security["cusip"], security.get("put_call", ""))
                require(key not in unique_securities, f"Duplicate manager-aggregated security {date} {key}")
                unique_securities.add(key)
                prefix = security["cusip"][:6]
                require(aliases["prefix_aliases"].get(prefix, prefix) == group["company_id"], f"Issuer alias mismatch {date} {key}")
                component_sum += int(security["value_usd"])
            require(component_sum == int(group["value_usd"]), f"Company-class sum {date}")
            require(sorted(security["cusip"] for security in group["securities"]) == group["cusips"], f"CUSIP membership {date}")
        ranked = sorted((group for group in groups if group["individual_company_ranking_eligible"]), key=lambda group: (-int(group["value_usd"]), group["company_id"]))
        require(len({group["company_id"] for group in ranked}) == len(ranked), f"Duplicate ranked issuer {date}")
        for position, group in zip(POSITIONS, ranked[:3]):
            require(group["instrument_kind"] == "company security" and not group["put_call"], f"Ineligible top holding {date}")
            require(group["value_usd"] == row[position + "_value_usd"] and group["name"] == row[position + "_name"], f"Company rank mismatch {date} {position}")
        securities_checked += len(unique_securities)
    annual_evidence = {row["year"]: row for row in load_json(DATA / "evidence" / "annual_rankings.json")["rows"]}
    for row in rows:
        if row["frequency"] != "annual":
            continue
        proof = annual_evidence[row["year"]]
        for position, flag in (("second", "rank2_verified"), ("third", "rank3_verified")):
            require(proof[flag] == (row[position + "_value_usd"] is not None), f"Annual proof flag {row['year']} {position}")
            if proof[flag]:
                require(proof[position + "_value_usd"] == row[position + "_value_usd"] and proof[position + "_name"] == row[position + "_name"], f"Annual proof mismatch {row['year']} {position}")
    require(not annual_evidence[1998]["included_in_main_series"], "1998 annual evidence must be excluded from the main series")
    return securities_checked


def validate_language_and_paths() -> int:
    disallowed_script = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")
    local_path = re.compile(r"(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\(?:localhost|Users|home)|/(?:Users|home|mnt|tmp)/)", re.IGNORECASE)
    count = 0
    for folder in (DATA, ROOT / "scripts"):
        for path in folder.rglob("*"):
            if not path.is_file() or path.suffix not in (".json", ".csv", ".py"):
                continue
            text = path.read_text(encoding="utf-8")
            require(disallowed_script.search(text) is None, f"Non-English script found in {path.name}")
            require(local_path.search(text) is None, f"Local path found in {path.name}")
            count += 1
    return count


def validate_outputs(rows: list[dict], inputs: dict) -> None:
    with (DATA / "allocation.csv").open(encoding="utf-8", newline="") as stream:
        exported = list(csv.DictReader(stream))
    require(len(exported) == len(rows), "CSV row count")
    for row, csv_row in zip(rows, exported):
        require(set(row) == set(csv_row), "CSV fields")
        for key, value in row.items():
            if value is None:
                expected = ""
            elif isinstance(value, (list, dict)):
                expected = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            else:
                expected = str(value)
            require(csv_row[key] == expected, f"CSV differs at {row['date']} {key}")
    require(load_json(DATA / "statistics.json") == build_statistics(rows, inputs), "Statistics are stale")
    require(load_json(DATA / "sources.json") == build_sources(rows), "Source index is stale")
    source_urls = {source["url"] for source in load_json(DATA / "sources.json")["sources"]}
    require(all(set(row["sources"]).issubset(source_urls) for row in rows), "Observation source missing from source index")
    for artifact in load_json(DATA / "manifest.json")["artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"Missing manifest artifact {artifact['path']}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], f"Manifest hash mismatch {artifact['path']}")


def main() -> None:
    inputs = load_json(DATA / "inputs.json")
    rows = load_json(DATA / "allocation.json")
    validate_observations(inputs, rows)
    security_count = validate_issuer_evidence(rows)
    text_files = validate_language_and_paths()
    validate_outputs(rows, inputs)
    print(f"PASS: 141 observations, 30 annual, 111 quarterly; 126 second ranks and 124 third ranks.")
    print(f"PASS: exact numeric baseline, common denominators, top-three subsets and {security_count} issuer-grouped securities.")
    print(f"PASS: English-only data/code, no local paths in {text_files} files, CSV parity, statistics, source index and hashes.")


if __name__ == "__main__":
    main()
