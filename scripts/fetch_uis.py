"""Download a small snapshot of real, public UIS data into mydt/data/uis_public.csv.

Source: UNESCO Institute for Statistics (UIS) public data API, https://api.uis.unesco.org
Measures per country, level (ISCED1-3), sex (T/F/M) and year:
  enrolment        number enrolled (UIS indicators 20062.. / 40035..)
  school_age_pop   population of official school age (SAP.1 .. SAP.3)
  ger_published    gross enrolment ratio as published by UIS (GER.1 .. GER.3)

The public API has level totals only (no single-age enrolment), so this snapshot feeds the "Real data" tab,
not the age-by-age template checks. Run:  python scripts/fetch_uis.py   (needs internet; stdlib only)
"""
from __future__ import annotations
import csv
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.uis.unesco.org/api/public"
START, END = 2015, 2025          # nothing from 2026 on
COUNTRIES = {"MYS": "Malaysia", "IDN": "Indonesia", "PHL": "Philippines", "VNM": "Viet Nam", "IND": "India",
             "BGD": "Bangladesh", "KEN": "Kenya", "NGA": "Nigeria", "ETH": "Ethiopia", "EGY": "Egypt",
             "BRA": "Brazil", "MEX": "Mexico", "PER": "Peru", "FRA": "France"}
LEVELS = {1: "ISCED1", 2: "ISCED2", 3: "ISCED3"}
ENROLMENT = {  # (level, sex) -> indicator
    (1, "T"): "20062", (1, "F"): "20063", (1, "M"): "40035",
    (2, "T"): "20064", (2, "F"): "20065", (2, "M"): "40038",
    (3, "T"): "20070", (3, "F"): "20071", (3, "M"): "40041"}
SUFFIX = {"T": "", "F": ".F", "M": ".M"}
OUT = Path(__file__).resolve().parent.parent / "mydt" / "data" / "uis_public.csv"


def get(path: str, params: list[tuple[str, str]]):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main() -> int:
    version = get("versions", [])[0]
    vid = version["version"]
    wanted = {}  # indicator -> (measure, level, sex)
    for (lvl, sx), code in ENROLMENT.items():
        wanted[code] = ("enrolment", LEVELS[lvl], sx)
    for lvl in LEVELS:
        for sx, suf in SUFFIX.items():
            wanted[f"SAP.{lvl}{suf}"] = ("school_age_pop", LEVELS[lvl], sx)
            wanted[f"GER.{lvl}{suf}"] = ("ger_published", LEVELS[lvl], sx)
    rows = []
    for code, (measure, level, sex) in wanted.items():
        params = [("indicator", code), ("start", str(START)), ("end", str(END)), ("version", vid)]
        params += [("geoUnit", c) for c in COUNTRIES]
        for rec in get("data/indicators", params)["records"]:
            if rec["value"] is None or not (START <= rec["year"] <= END):
                continue
            rows.append({"country": rec["geoUnit"], "country_name": COUNTRIES[rec["geoUnit"]], "level": level,
                         "sex": sex, "measure": measure, "year": rec["year"], "value": rec["value"],
                         "indicator": code})
    rows.sort(key=lambda r: (r["country"], r["measure"], r["level"], r["sex"], r["year"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    OUT.with_name("uis_public.SOURCE.txt").write_text(
        "Source: UNESCO Institute for Statistics (UIS), public data API https://api.uis.unesco.org\n"
        f"Data release: {version['themeDataStatus'][0]['description']} (API version {vid})\n"
        f"Retrieved: {date.today().isoformat()}\n"
        f"Years: {START}-{END}. Countries: {', '.join(COUNTRIES)}.\n"
        "Check the UIS terms of use and licence before reuse, and keep this credit with the data.\n"
        "Rebuild with: python scripts/fetch_uis.py\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {OUT} (release: {version['themeDataStatus'][0]['description']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
