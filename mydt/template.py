"""Build a MYDT-style workbook and extend it with new years of data entry."""
from __future__ import annotations
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from . import config as C
from .i18n import labels

INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
CALC_FILL = PatternFill("solid", fgColor="E7E6E6")
HEAD = Font(bold=True)
N_AGES = len(C.AGES)


def _year_cols(first_col: int, k: int) -> tuple[int, int, int]:
    c = first_col + 3 * k
    return c, c + 1, c + 2


def _data_range(sheet: str, col: int) -> str:
    r0, r1 = C.DATA_ROW0, _last_row(sheet)
    return f"{sheet}!${L(col)}${r0}:${L(col)}${r1}"


def _last_row(sheet: str) -> int:
    n = N_AGES * len(C.LEVELS) if sheet == "Enrolment" else N_AGES
    return C.DATA_ROW0 + n - 1


def _write_year_block(ws, k: int, year: int, data_sheet: str) -> None:
    m, f, t = _year_cols(C.FIRST_YEAR_COL, k)
    for col, sx in zip((m, f, t), C.SEXES):
        ws.cell(C.YEAR_ROW, col, year).font = HEAD
        ws.cell(C.SEX_ROW, col, sx).font = HEAD
        ws.column_dimensions[L(col)].width = 10
    last = _last_row(data_sheet)
    dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0",
                        allow_blank=True, showErrorMessage=True,
                        errorTitle="Invalid", error="Enter a non-negative number")
    ws.add_data_validation(dv)
    dv.add(f"{L(m)}{C.DATA_ROW0}:{L(f)}{last}")
    for r in range(C.DATA_ROW0, last + 1):
        ws.cell(r, m).fill = ws.cell(r, f).fill = INPUT_FILL
        c = ws.cell(r, t, f'=IF(AND({L(m)}{r}="",{L(f)}{r}=""),"",SUM({L(m)}{r}:{L(f)}{r}))')
        c.fill = CALC_FILL


def _indicator_formulas(ws, k: int, year: int) -> None:
    m, f, t = _year_cols(C.FIRST_YEAR_COL, k)
    for col in (m, f, t):
        ws.cell(C.YEAR_ROW, col, year).font = HEAD
    for col, sx in zip((m, f, t), C.SEXES):
        ws.cell(C.SEX_ROW, col, sx).font = HEAD
        ws.column_dimensions[L(col)].width = 10
    for i, (lvl, (a0, a1)) in enumerate(C.LEVELS.items()):
        for j, ind in enumerate(("GER", "NER")):
            r = C.DATA_ROW0 + i * 2 + j
            for col in (m, f, t):
                enr_lvl = f'Enrolment!$A${C.DATA_ROW0}:$A${_last_row("Enrolment")}'
                enr_age = f'Enrolment!$B${C.DATA_ROW0}:$B${_last_row("Enrolment")}'
                e = _data_range("Enrolment", col)
                p = _data_range("Population", col)
                pa = f'Population!$B${C.DATA_ROW0}:$B${_last_row("Population")}'
                pop = f'SUMIFS({p},{pa},">={a0}",{pa},"<={a1}")'
                if ind == "GER":
                    num = f'SUMIFS({e},{enr_lvl},"{lvl}")'
                else:
                    num = f'SUMIFS({e},{enr_lvl},"{lvl}",{enr_age},">={a0}",{enr_age},"<={a1}")'
                ws.cell(r, col, f'=IFERROR(100*{num}/{pop},"")').number_format = "0.0"
    # GPI rows
    base = C.DATA_ROW0 + len(C.LEVELS) * 2
    for i, lvl in enumerate(C.LEVELS):
        r = base + i
        ger_m = f"{L(m)}{C.DATA_ROW0 + i * 2}"
        ger_f = f"{L(f)}{C.DATA_ROW0 + i * 2}"
        ws.cell(r, t, f'=IFERROR({ger_f}/{ger_m},"")').number_format = "0.00"


def build_template(path: str | Path, years: list[int], lang: str = "en") -> Path:
    """Build a template. `lang` (en/fr/es/pt/ru) changes visible labels only; structure is identical."""
    T = labels(lang)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.properties.language = lang
    rd = wb.active
    rd.title = "README"
    rd["A1"] = T["title"]
    rd["A1"].font = Font(bold=True, size=13)
    rd["A3"] = T["fill_note"]
    rd["A4"] = T["sheets_note"]
    md = wb.create_sheet("Metadata")
    for i, fld in enumerate(T["meta_fields"], start=2):
        md.cell(i, 1, fld).font = HEAD
        md.cell(i, 2).fill = INPUT_FILL
    md.column_dimensions["A"].width = 18
    md.column_dimensions["B"].width = 34

    en = wb.create_sheet("Enrolment")
    en["A1"] = T["enrol_title"]; en["A1"].font = HEAD
    en.cell(C.SEX_ROW, 1, T["level"]).font = HEAD
    en.cell(C.SEX_ROW, 2, T["age"]).font = HEAD
    r = C.DATA_ROW0
    for lvl in C.LEVELS:
        for a in C.AGES:
            en.cell(r, 1, lvl); en.cell(r, 2, a); r += 1
    po = wb.create_sheet("Population")
    po["A1"] = T["pop_title"]; po["A1"].font = HEAD
    po.cell(C.SEX_ROW, 1, T["all"]).font = HEAD
    po.cell(C.SEX_ROW, 2, T["age"]).font = HEAD
    for i, a in enumerate(C.AGES):
        po.cell(C.DATA_ROW0 + i, 1, "All"); po.cell(C.DATA_ROW0 + i, 2, a)  # "All" is a data key: keep it language-neutral

    ind = wb.create_sheet("Indicators")
    ind["A1"] = T["ind_title"]; ind["A1"].font = HEAD
    for i, lvl in enumerate(C.LEVELS):
        for j, nm in enumerate(("GER", "NER")):
            ind.cell(C.DATA_ROW0 + i * 2 + j, 1, lvl); ind.cell(C.DATA_ROW0 + i * 2 + j, 2, nm)
        ind.cell(C.DATA_ROW0 + len(C.LEVELS) * 2 + i, 1, lvl)
        ind.cell(C.DATA_ROW0 + len(C.LEVELS) * 2 + i, 2, "GPI(GER)")
    ck = wb.create_sheet("Checks")
    ck["A1"] = T["check_title"]; ck["A1"].font = HEAD
    ck.cell(C.SEX_ROW, 1, T["year"]).font = HEAD
    ck.cell(C.SEX_ROW, 2, T["negative_cells"]).font = HEAD
    ck.cell(C.SEX_ROW, 3, T["status"]).font = HEAD
    wb.save(path)
    for y in years:
        add_year(path, y)
    return Path(path)


def existing_years(ws) -> list[int]:
    ys = []
    for col in range(C.FIRST_YEAR_COL, ws.max_column + 1, 3):
        v = ws.cell(C.YEAR_ROW, col).value
        if isinstance(v, int):
            ys.append(v)
    return ys


def add_year(path: str | Path, year: int) -> Path:
    """Append a new year block to every sheet (idempotent). Existing data is untouched."""
    wb = load_workbook(path)
    en = wb["Enrolment"]
    ys = existing_years(en)
    if year in ys:
        return Path(path)
    k = len(ys)
    _write_year_block(en, k, year, "Enrolment")
    _write_year_block(wb["Population"], k, year, "Population")
    _indicator_formulas(wb["Indicators"], k, year)
    ck = wb["Checks"]
    m, f, _ = _year_cols(C.FIRST_YEAR_COL, k)
    r = C.DATA_ROW0 + k
    ck.cell(r, 1, year)
    rng = f"Enrolment!${L(m)}${C.DATA_ROW0}:${L(f)}${_last_row('Enrolment')}"
    ck.cell(r, 2, f'=COUNTIF({rng},"<0")')
    ck.cell(r, 3, f'=IF(B{r}=0,"OK","CHECK")')
    wb.save(path)
    return Path(path)


def prefill(path: str | Path, country: str | None = None, iso3: str | None = None,
            survey_year: int | None = None, contact_name: str | None = None,
            contact_email: str | None = None) -> Path:
    """Pre-fill the Metadata sheet (column B, same order as config.META_FIELDS). None leaves a cell as is."""
    wb = load_workbook(path)
    md = wb["Metadata"]
    for i, v in enumerate((country, iso3, survey_year, contact_name, contact_email), start=2):
        if v is not None:
            md.cell(i, 2, v)
    wb.save(path)
    return Path(path)
