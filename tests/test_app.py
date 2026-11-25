import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.index import app, chart_html  # noqa: E402


def _chart_data(html: str) -> dict:
    m = re.search(r'<script id=chart-data type=application/json>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_sample_run_embeds_chart_data_for_every_country():
    html = app.test_client().post("/", data={"action": "run_sample"}).data.decode()
    d = _chart_data(html)
    assert len(d) == 10
    assert {r["i"] for r in d["XC01"]} == {"GER", "NER"}
    assert {r["l"] for r in d["XC01"]} == {"ISCED1", "ISCED2", "ISCED3"}
    assert "c-country" in html


def test_chart_data_keeps_country_codes_inert_in_script_tag():
    ind = pd.DataFrame({"level": ["ISCED1"], "indicator": ["GER"], "year": [2026], "sex": ["T"],
                        "value": [90.0], "country": ["</script><b>x"]})
    html = chart_html(ind)
    assert "</script><b>" not in html.split("application/json>")[1].split("</script>")[0]
    assert _chart_data(html)["</script><b>x"][0]["v"] == 90.0


def test_chart_omitted_when_no_indicators():
    assert chart_html(pd.DataFrame()) == ""


# ---- multi-section UI ----
import io
import zipfile  # noqa: E402,F401

from openpyxl import load_workbook  # noqa: E402

from mydt.i18n import labels  # noqa: E402


def _post(**data):
    return app.test_client().post("/", data=data)


def test_home_has_all_sections_and_hides_results_tab_until_a_run():
    html = app.test_client().get("/").data.decode()
    for tab in ("overview", "samples", "check", "results", "rules", "templates", "about"):
        assert f'id=tab-{tab}' in html and f'data-tab={tab}' in html
    assert "<button type=button data-tab=results aria-selected=false class=hidden>" in html
    assert "No results yet" in html


def test_run_shows_results_tab_status_kpis_and_csv_data():
    r = _post(action="run_sample")
    html = r.data.decode()
    assert r.status_code == 200 and 'data-active=results' in html and 'data-force=1' in html
    assert "Status by country" in html and "files processed" in html and "Needs fixes" in html
    csv = json.loads(re.search(r'<script id=csv-data type=application/json>(.*?)</script>', html, re.S).group(1))
    assert set(csv) == {"issues", "indicators", "run_log"} and csv["issues"].startswith("country,rule")


def test_every_country_with_issues_is_not_shown_clean():
    """Status table must agree with the issues table (regression: ISO3-less file showed as Clean)."""
    html = _post(action="run_sample").data.decode()
    row = re.search(r"<tr><td><b>MYDT_XC06</b></td><td class=num>(\d+)</td>", html)
    assert row and int(row.group(1)) >= 1


def test_rules_tab_lists_all_twelve_rules():
    html = app.test_client().get("/").data.decode()
    assert all(f"<b>V{i:02d}</b>" in html for i in range(1, 13))


def test_template_download_in_every_language_with_prefill():
    for lang in ("en", "fr", "es", "pt", "ru"):
        r = _post(action="template", lang=lang, y0="2026", y1="2027", country="Chile", iso3="chl", survey_year="2027")
        assert r.status_code == 200
        wb = load_workbook(io.BytesIO(r.data))
        assert wb["Metadata"]["A2"].value == labels(lang)["meta_fields"][0]
        assert (wb["Metadata"]["B2"].value, wb["Metadata"]["B3"].value, wb["Metadata"]["B4"].value) == ("Chile", "CHL", 2027)
        assert wb["Enrolment"]["C3"].value == 2026


def test_template_rejects_unknown_language_and_neutralises_formulas():
    assert _post(action="template", lang="de").status_code == 400
    r = _post(action="template", lang="en", country='=HYPERLINK("http://x")')
    assert load_workbook(io.BytesIO(r.data))["Metadata"]["B2"].value == 'HYPERLINK("http://x")'


def test_template_year_span_is_capped():
    r = _post(action="template", lang="en", y0="2015", y1="2035")
    from mydt.template import existing_years
    assert len(existing_years(load_workbook(io.BytesIO(r.data))["Enrolment"])) == 10


def test_upload_without_files_returns_400_on_the_check_tab():
    r = _post(action="upload")
    assert r.status_code == 400 and 'data-active=check' in r.data.decode()


def test_user_controlled_text_is_escaped(tmp_path):
    from mydt.webui import results_html
    iss = pd.DataFrame([{"country": "<img src=x>", "rule": "V01", "severity": "error", "year": 2026,
                         "where": "<b>w</b>", "message": "<script>alert(1)</script>"}])
    res = {"issues": iss, "indicators": pd.DataFrame(columns=["level", "indicator", "year", "sex", "value", "country"]),
           "run_log": pd.DataFrame([{"file": "<x>.xlsx", "status": "FAILED", "detail": ""}])}
    html = results_html(res, 1)
    assert "<img src=x>" not in html and "<script>alert(1)" not in html and "&lt;img src=x&gt;" in html


def test_theme_switch_markup_and_no_flash_script():
    html = app.test_client().get("/").data.decode()
    assert 'id=theme-toggle' in html and 'role=switch' in html and "aria-label='Dark mode'" in html
    head = html.split("</head>")[0]
    assert "localStorage.getItem('mydt-theme')" in head and "setAttribute('data-theme'" in head  # applied before paint
    assert ":root[data-theme=dark]" in html and ":root:not([data-theme=light])" in html
    assert "__DARK__" not in html


def test_dark_tokens_are_identical_for_system_and_manual_dark():
    html = app.test_client().get("/").data.decode()
    sys_dark = re.search(r"prefers-color-scheme:dark\)\{:root:not\(\[data-theme=light\]\)\{(.*?)\}\}", html).group(1)
    manual = re.search(r":root\[data-theme=dark\]\{(.*?)\}", html).group(1)
    assert sys_dark == manual and "--bg:#0e131a" in manual
