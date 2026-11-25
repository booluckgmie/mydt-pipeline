"""Real, public UIS data snapshot (levels ISCED1-3, 2015-2025) for the web demo's "Real data" tab.

The snapshot is mydt/data/uis_public.csv, built by scripts/fetch_uis.py from the UIS public API.
It has level totals only (no single-age enrolment), so it is used for exploration and for an independent
check (enrolment / school-age population vs the ratio UIS publishes), not for the age-by-age template rules.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
CSV = DATA / "uis_public.csv"
SOURCE = DATA / "uis_public.SOURCE.txt"
MEASURES = ("enrolment", "school_age_pop", "ger_published")


@lru_cache(maxsize=1)
def load() -> pd.DataFrame:
    """The snapshot in long form (country, country_name, level, sex, measure, year, value, indicator)."""
    return pd.read_csv(CSV)


def source_note() -> str:
    return SOURCE.read_text(encoding="utf-8") if SOURCE.exists() else ""


def latest_years(df: pd.DataFrame | None = None) -> dict:
    """Latest year with any enrolment or published-GER value, per country (it differs: 2023 to 2025)."""
    df = load() if df is None else df
    d = df[df.measure.isin(["enrolment", "ger_published"])]
    return {c: int(y) for c, y in d.groupby("country").year.max().items()}


def wide(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per country, level, sex, year with enrolment, school_age_pop, ger_published, ger_computed, diff."""
    df = load() if df is None else df
    w = df.pivot_table(index=["country", "country_name", "level", "sex", "year"], columns="measure",
                       values="value").reset_index()
    for m in MEASURES:
        if m not in w:
            w[m] = float("nan")
    w["ger_computed"] = 100 * w.enrolment / w.school_age_pop
    w["diff"] = w.ger_computed - w.ger_published
    return w


def agreement(df: pd.DataFrame | None = None, tol: float = 0.1) -> dict:
    """How closely enrolment / school-age population reproduces the published GER."""
    c = wide(df).dropna(subset=["ger_computed", "ger_published"])
    bad = c[c["diff"].abs() > tol].sort_values("diff", key=abs, ascending=False)
    return {"compared": int(len(c)), "within": int((c["diff"].abs() <= tol).sum()), "tol": tol,
            "max_abs_diff": float(c["diff"].abs().max()) if len(c) else 0.0,
            "outliers": [{"country": r.country, "level": r.level, "sex": r.sex, "year": int(r.year),
                          "diff": round(float(r.diff), 2)} for r in bad.itertuples()]}


def payload(df: pd.DataFrame | None = None) -> dict:
    """Compact JSON for the browser: {ISO3: {name, rows: [[level, sex, year, enrolment, pop, published GER], ...]}}."""
    w = wide(df)
    out = {}
    for (c, name), g in w.groupby(["country", "country_name"]):
        rows = [[r.level, r.sex, int(r.year),
                 None if pd.isna(r.enrolment) else float(r.enrolment),
                 None if pd.isna(r.school_age_pop) else float(r.school_age_pop),
                 None if pd.isna(r.ger_published) else round(float(r.ger_published), 3)]
                for r in g.sort_values(["level", "sex", "year"]).itertuples()]
        out[c] = {"name": name, "rows": rows}
    return out
