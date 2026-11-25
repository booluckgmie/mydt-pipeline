import pytest
from openpyxl import load_workbook
from mydt import config as C
from mydt.i18n import LANGS, labels
from mydt.template import build_template, add_year, prefill
from mydt.synthetic import make_submissions
from mydt.consolidate import consolidate
from mydt.read import read_workbook


def test_every_language_defines_every_label():
    base = set(labels("en"))
    for lg in LANGS:
        lab = labels(lg)
        assert set(lab) == base and all(lab[k] for k in base)
        assert len(lab["meta_fields"]) == len(C.META_FIELDS)


def test_unknown_language_rejected():
    with pytest.raises(ValueError):
        labels("de")


@pytest.mark.parametrize("lang", [lg for lg in LANGS if lg != "en"])
def test_translated_template_is_processed_identically(tmp_path, lang):
    """Same seed, different label language -> identical consolidated numbers and issues."""
    en = make_submissions(tmp_path / "en", n=4, lang="en")
    tr = make_submissions(tmp_path / lang, n=4, lang=lang)
    a, b = consolidate(en, tmp_path / "o1"), consolidate(tr, tmp_path / "o2")
    for k in ("enrolment", "population", "indicators", "issues"):
        x, y = a[k].drop(columns=["file"], errors="ignore"), b[k].drop(columns=["file"], errors="ignore")
        assert x.reset_index(drop=True).equals(y.reset_index(drop=True)), k
    assert load_workbook(tr[0])["Enrolment"]["A4"].value == labels(lang)["level"]
    assert load_workbook(tr[0]).properties.language == lang


def test_add_year_works_on_translated_template(tmp_path):
    p = build_template(tmp_path / "t.xlsx", [2024], lang="fr")
    add_year(p, 2025)
    assert load_workbook(p)["Indicators"].cell(C.YEAR_ROW, 6).value == 2025


def test_prefill_sets_metadata_and_keeps_others(tmp_path):
    p = build_template(tmp_path / "t.xlsx", [2025], lang="es")
    prefill(p, country="Chile", iso3="CHL", survey_year=2027)
    prefill(p, contact_email="focal@example.org")
    meta = read_workbook(p)["meta"]
    assert (meta["Country"], meta["ISO3"], meta["Survey year"], meta["Contact email"]) == ("Chile", "CHL", 2027, "focal@example.org")
    assert meta["Contact name"] is None
