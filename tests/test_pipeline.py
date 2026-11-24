import shutil, subprocess
from pathlib import Path
import pandas as pd
import pytest
from openpyxl import load_workbook
from mydt import config as C
from mydt.template import build_template, add_year, existing_years
from mydt.synthetic import make_submissions
from mydt.consolidate import consolidate
from mydt.read import read_workbook
from mydt.indicators import compute_indicators


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    d = tmp_path_factory.mktemp("w")
    files = make_submissions(d / "sub", n=10)
    return files, consolidate(files, d / "out"), d


def test_add_year_is_idempotent_and_preserves_data(tmp_path):
    p = build_template(tmp_path / "t.xlsx", [2024, 2025])
    wb = load_workbook(p); wb["Enrolment"]["C5"] = 123; wb.save(p)
    add_year(p, 2026); add_year(p, 2026)
    wb = load_workbook(p)
    assert existing_years(wb["Enrolment"]) == [2024, 2025, 2026]
    assert wb["Enrolment"]["C5"].value == 123
    assert wb["Indicators"].cell(C.YEAR_ROW, 9).value == 2026


@pytest.mark.parametrize("code,rule", [("XC02", "V03"), ("XC03", "V02"), ("XC04", "V05"),
                                       ("XC05", "V04"), ("XC07", "V08"), ("XC08", "V06")])
def test_injected_defect_is_detected(run, code, rule):
    iss = run[1]["issues"]
    assert ((iss.country == code) & (iss.rule == rule)).any()


def test_missing_iso_detected(run):
    assert (run[1]["issues"].rule == "V01").sum() == 1


def test_clean_countries_have_no_errors(run):
    iss = run[1]["issues"]
    for c in ("XC01", "XC09", "XC10"):
        assert not ((iss.country == c) & (iss.severity == "error")).any()


def test_consolidation_row_counts(run):
    res = run[1]
    per = len(C.AGES) * len(C.LEVELS) * 2 * 4  # ages*levels*sexes*years
    assert len(res["enrolment"]) == 10 * per
    assert (res["run_log"].status == "OK").all()


def test_corrupt_file_does_not_stop_batch(run, tmp_path):
    files = list(run[0][:2]); bad = tmp_path / "bad.xlsx"; bad.write_bytes(b"not a workbook")
    res = consolidate(files + [bad], tmp_path / "o")
    assert (res["run_log"].status == "FAILED").sum() == 1 and (res["run_log"].status == "OK").sum() == 2


def test_python_indicator_matches_excel_formulas(run, tmp_path):
    """Recalculate a workbook with LibreOffice and compare Excel-formula GER/NER to Python."""
    if not shutil.which("soffice"):
        pytest.skip("LibreOffice not installed")
    src = run[0][0]  # clean country
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", str(tmp_path), str(src)],
                   check=True, capture_output=True)
    wb = load_workbook(tmp_path / src.name, data_only=True)["Indicators"]
    py = compute_indicators(**{k: v for k, v in zip(("enrol", "pop"), (read_workbook(src)["enrolment"], read_workbook(src)["population"]))})
    checked = 0
    for i, lvl in enumerate(C.LEVELS):
        for j, ind in enumerate(("GER", "NER")):
            row = C.DATA_ROW0 + i * 2 + j
            for k, y in enumerate((2023, 2024, 2025, 2026)):
                excel = wb.cell(row, C.FIRST_YEAR_COL + 3 * k + 2).value
                ref = py[(py.level == lvl) & (py.indicator == ind) & (py.year == y) & (py.sex == "T")].value.iloc[0]
                assert excel == pytest.approx(ref, rel=1e-6); checked += 1
    assert checked == 24
