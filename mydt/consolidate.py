"""Consolidate many workbooks into one tidy database (CSV + SQLite) and log failures."""
from __future__ import annotations
import sqlite3
from pathlib import Path
import pandas as pd
from .read import read_workbook
from .validate import validate
from .indicators import compute_indicators


def consolidate(files: list[Path], outdir: str | Path) -> dict[str, pd.DataFrame]:
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    enr, pop, ind, iss, log = [], [], [], [], []
    for f in sorted(files):
        try:
            sub = read_workbook(f)
        except Exception as e:  # corrupt/renamed sheets must not stop a batch run
            log.append({"file": Path(f).name, "status": "FAILED", "detail": repr(e)})
            continue
        code = sub["meta"].get("ISO3") or Path(f).stem
        for df, bucket in ((sub["enrolment"], enr), (sub["population"], pop)):
            bucket.append(df.assign(country=code, file=Path(f).name))
        i = compute_indicators(sub["enrolment"], sub["population"]).assign(country=code)
        ind.append(i)
        iss.append(validate(sub).assign(country=code))  # same label as the data, even when ISO3 is missing
        log.append({"file": Path(f).name, "status": "OK", "detail": ""})
    res = {
        "enrolment": pd.concat(enr, ignore_index=True) if enr else pd.DataFrame(),
        "population": pd.concat(pop, ignore_index=True) if pop else pd.DataFrame(),
        "indicators": pd.concat(ind, ignore_index=True) if ind else pd.DataFrame(),
        "issues": pd.concat(iss, ignore_index=True) if iss else pd.DataFrame(),
        "run_log": pd.DataFrame(log),
    }
    with sqlite3.connect(outdir / "consolidated.sqlite") as con:
        for k, df in res.items():
            df.to_sql(k, con, if_exists="replace", index=False)
    for k, df in res.items():
        df.to_csv(outdir / f"{k}.csv", index=False)
    return res
