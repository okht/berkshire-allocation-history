#!/usr/bin/env python3
"""Rebuild the published allocation data using only Python's standard library.

Run from any working directory: python path/to/scripts/build.py
No network requests, environment configuration or third-party packages are used.
"""
from __future__ import annotations

import csv
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EVIDENCE = DATA / "evidence"
POSITIONS = ("first", "second", "third")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value) -> None:
    # Fixed LF bytes keep manifest hashes stable across Windows and Git checkouts.
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def canonical_hash(value) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_observations(inputs: dict) -> list[dict]:
    rows = []
    with localcontext() as context:
        context.prec = inputs["decimal_precision"]
        for original in inputs["rows"]:
            row = dict(original)
            cash = Decimal(row["cash_usd"])
            stocks = Decimal(row["stock_usd"])
            total = cash + stocks
            if cash < 0 or stocks <= 0:
                raise ValueError(f"Invalid denominator at {row['date']}")
            row.update(total_usd=str(total), cash_share=str(cash / total), stock_share=str(stocks / total))
            for position in POSITIONS:
                amount = row[position + "_value_usd"]
                row[position + "_share"] = None if amount is None else str(Decimal(amount) / total)
            rows.append(row)
    rows.sort(key=lambda row: row["date"])
    baseline = inputs["numeric_baseline"]
    projection = [{key: row[key] for key in baseline["fields"]} for row in rows]
    if canonical_hash(projection) != baseline["sha256"]:
        raise ValueError("Rebuilt numeric values differ from the reviewed publication baseline")
    return rows


def point(row: dict, metric: str) -> dict:
    result = {key: row[key] for key in ("date", "period", "year", "frequency", "scope", "total_usd")}
    result["share_of_total"] = row[metric]
    if metric in ("cash_share", "stock_share"):
        result["value_usd"] = row["cash_usd" if metric == "cash_share" else "stock_usd"]
    else:
        position = metric.split("_", 1)[0]
        result["company"] = row[position + "_name"]
        result["value_usd"] = row[position + "_value_usd"]
    return result


def build_statistics(rows: list[dict], inputs: dict) -> dict:
    stats = {
        "snapshot_date": inputs["snapshot_date"],
        "currency": "USD",
        "ratio_unit": "Fraction of cash plus securities; multiply by 100 for percent",
        "observations": len(rows),
        "annual_observations": sum(row["frequency"] == "annual" for row in rows),
        "quarterly_observations": sum(row["frequency"] == "quarterly" for row in rows),
        "first_observation": rows[0]["date"],
        "last_observation": rows[-1]["date"],
        "verified_ranks": {position: sum(row[position + "_value_usd"] is not None for row in rows) for position in POSITIONS},
        "missing_ranks": {position: [row["period"] for row in rows if row[position + "_value_usd"] is None] for position in POSITIONS},
        "latest": rows[-1],
        "segments": {},
        "limitation": "Extrema are sampled observations, not daily historical extrema. Annual-report and quarterly-13F scopes are summarized separately.",
    }
    for frequency in ("annual", "quarterly"):
        sample = [row for row in rows if row["frequency"] == frequency]
        segment = {"observations": len(sample), "first_date": sample[0]["date"], "last_date": sample[-1]["date"], "series": {}}
        for metric in ("cash_share", "stock_share", "first_share", "second_share", "third_share"):
            available = [row for row in sample if row[metric] is not None]
            segment["series"][metric] = {
                "verified_observations": len(available),
                "maximum": point(max(available, key=lambda row: Decimal(row[metric])), metric) if available else None,
                "minimum": point(min(available, key=lambda row: Decimal(row[metric])), metric) if available else None,
            }
        stats["segments"][frequency] = segment
    return stats


def build_sources(rows: list[dict]) -> dict:
    entries = {}

    def ensure(url: str) -> dict:
        if url not in entries:
            host = urlparse(url).hostname or ""
            if host.endswith("sec.gov"):
                kind = "SEC filing"
            elif host.endswith("berkshirehathaway.com"):
                kind = "Company report or shareholder letter"
            else:
                kind = "Archived original company report hosted by a third party"
            entries[url] = {"url": url, "source_kind": kind, "observation_dates": set(), "evidence_files": set(), "locators": []}
        return entries[url]

    for row in rows:
        for url in row["sources"]:
            ensure(url)["observation_dates"].add(row["date"])

    locator_keys = {
        "report_year", "year", "pdf_page", "printed_page", "pdf_pages_1based", "printed_pages",
        "source_pdf_page", "source_printed_page", "pages", "locator", "location", "subject",
        "purpose", "source_kind", "sha256", "visual_verified", "visually_checked",
    }

    def visit(value, evidence_path: str) -> None:
        if isinstance(value, dict):
            url = value.get("source_url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                entry = ensure(url)
                entry["evidence_files"].add(evidence_path)
                locator = {key: value[key] for key in sorted(locator_keys) if key in value}
                if locator and locator not in entry["locators"]:
                    entry["locators"].append(locator)
            for item in value.values():
                visit(item, evidence_path)
        elif isinstance(value, list):
            for item in value:
                visit(item, evidence_path)
        elif isinstance(value, str) and value.startswith(("https://", "http://")):
            ensure(value)["evidence_files"].add(evidence_path)

    for path in sorted(EVIDENCE.glob("*.json")):
        visit(load_json(path), path.relative_to(ROOT).as_posix())
    output = []
    for url, entry in sorted(entries.items()):
        entry["observation_dates"] = sorted(entry["observation_dates"])
        entry["evidence_files"] = sorted(entry["evidence_files"])
        output.append(entry)
    return {
        "description": "Original disclosure URLs and retained evidence locations. Sources used only for comparative or ranking evidence may have no main-series observation date.",
        "source_count": len(output),
        "sources": output,
    }


def csv_field(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def write_manifest() -> None:
    manifest = {
        "schema_version": 1,
        "description": "SHA-256 of curated inputs, retained evidence, portable scripts and generated analytical data. This manifest does not hash itself.",
        "artifacts": [],
    }
    files = sorted(path for folder in (DATA, ROOT / "scripts") for path in folder.rglob("*") if path.is_file() and path.suffix in (".json", ".csv", ".py") and path.name != "manifest.json")
    for path in files:
        manifest["artifacts"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    save_json(DATA / "manifest.json", manifest)


def main() -> None:
    inputs = load_json(DATA / "inputs.json")
    rows = build_observations(inputs)
    save_json(DATA / "allocation.json", rows)
    with (DATA / "allocation.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: csv_field(value) for key, value in row.items()} for row in rows)
    save_json(DATA / "statistics.json", build_statistics(rows, inputs))
    save_json(DATA / "sources.json", build_sources(rows))
    write_manifest()
    print(f"Rebuilt {len(rows)} observations: allocation.json, allocation.csv, statistics.json, sources.json and manifest.json")


if __name__ == "__main__":
    main()
