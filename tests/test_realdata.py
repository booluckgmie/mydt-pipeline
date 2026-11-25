import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.index import app  # noqa: E402
from mydt import realdata as R  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_snapshot_shape_and_years():
    d = R.load()
    assert set(d.columns) >= {"country", "country_name", "level", "sex", "measure", "year", "value", "indicator"}
    assert d.year.min() >= 2015 and d.year.max() <= 2025          # nothing from 2026 on
    assert d.country.nunique() == 14 and "MYS" in set(d.country)
    assert set(d.level) == {"ISCED1", "ISCED2", "ISCED3"} and set(d.sex) == {"T", "F", "M"}
    assert set(d.measure) == set(R.MEASURES)
    assert (d.value > 0).all() and d.value.notna().all()


def test_both_sexes_equal_female_plus_male_enrolment():
    e = R.load().query("measure == 'enrolment'").pivot_table(index=["country", "level", "year"],
                                                              columns="sex", values="value").dropna()
    assert len(e) > 300
    assert (((e["T"] - e["F"] - e["M"]).abs() / e["T"]) < 0.001).all()


def test_computed_ger_reproduces_published_ger():
    a = R.agreement()
    assert a["compared"] > 1000 and a["within"] / a["compared"] > 0.98
    assert a["max_abs_diff"] < 10


def test_ger_arithmetic_on_a_tiny_fixture():
    rows = [("AAA", "Aland", "ISCED1", "T", m, 2020, v, "x") for m, v in
            (("enrolment", 90.0), ("school_age_pop", 100.0), ("ger_published", 89.5))]
    w = R.wide(pd.DataFrame(rows, columns=["country", "country_name", "level", "sex", "measure", "year", "value",
                                           "indicator"]))
    r = w.iloc[0]
    assert r.ger_computed == pytest.approx(90.0) and r["diff"] == pytest.approx(0.5)
    a = R.agreement(pd.DataFrame(rows, columns=["country", "country_name", "level", "sex", "measure", "year",
                                                "value", "indicator"]), tol=0.1)
    assert a["compared"] == 1 and a["within"] == 0 and a["outliers"][0]["diff"] == 0.5


def test_payload_is_json_safe_and_complete():
    p = R.payload()
    blob = json.dumps(p)
    assert "NaN" not in blob and len(p) == 14
    assert sum(len(v["rows"]) for v in p.values()) == len(R.wide())


def test_fetch_script_matches_the_snapshot():
    spec = importlib.util.spec_from_file_location("fetch_uis", ROOT / "scripts" / "fetch_uis.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                        # importing must not download anything
    assert m.END < 2026 and set(m.COUNTRIES) == set(R.load().country)
    assert m.OUT == R.CSV and "Source: UNESCO Institute for Statistics" in R.source_note()


def test_vercel_ships_the_snapshot():
    cfg = json.loads((ROOT / "vercel.json").read_text())
    assert cfg["functions"]["api/index.py"]["includeFiles"] == "mydt/**" and R.CSV.exists()
    assert 'data/*' in (ROOT / "pyproject.toml").read_text()


def test_real_data_tab_in_the_page():
    html = app.test_client().get("/").data.decode()
    assert "data-tab=realdata" in html and "id=tab-realdata" in html
    blob = re.search(r'<script id=real-data type=application/json>(.*?)</script>', html, re.S).group(1)
    assert len(json.loads(blob)) == 14 and "NaN" not in blob
    assert "Credit: UIS" in html and "Independent check" in html
    assert "SYNTHETIC DEMO" not in html and "Sample files are synthetic" in html


def test_latest_year_differs_by_country_and_stops_before_2026():
    ly = R.latest_years()
    assert set(ly) == set(R.load().country)
    assert min(ly.values()) == 2023 and max(ly.values()) <= 2025
    assert ly["MYS"] == 2025 and ly["KEN"] == 2023


def test_banner_states_the_real_year_range():
    html = app.test_client().get("/").data.decode()
    assert "to the latest year each country has (between 2023 and 2025; none from 2026)" in html
    assert "2015 to 2025." not in html and "id=r-range" in html
