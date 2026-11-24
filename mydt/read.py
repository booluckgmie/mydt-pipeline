"""Read a country workbook into tidy tables (inputs only; formulas are recomputed in Python)."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter as L
from . import config as C


def _is_formula(v) -> bool:
    return isinstance(v, str) and v.startswith("=")


def read_workbook(path: str | Path) -> dict:
    wb = load_workbook(path, data_only=False)
    meta = {}
    for i, fld in enumerate(C.META_FIELDS, start=2):
        v = wb["Metadata"].cell(i, 2).value
        meta[fld] = None if v in (None, "") else v
    meta["file"] = Path(path).name
    tables, bad = {}, []
    for sheet, lvl_fixed in (("Enrolment", False), ("Population", True)):
        ws = wb[sheet]
        rows = []
        for col in range(C.FIRST_YEAR_COL, ws.max_column + 1, 3):
            year = ws.cell(C.YEAR_ROW, col).value
            if not isinstance(year, int):
                continue
            for off, sx in ((0, "M"), (1, "F")):
                c = col + off
                for r in range(C.DATA_ROW0, ws.max_row + 1):
                    lvl, age = ws.cell(r, 1).value, ws.cell(r, 2).value
                    if age is None:
                        continue
                    v = ws.cell(r, c).value
                    cell = f"{sheet}!{L(c)}{r}"
                    if v in (None, ""):
                        val = float("nan")
                    elif isinstance(v, (int, float)) and not isinstance(v, bool):
                        val = float(v)
                    else:
                        val = float("nan")
                        bad.append({"sheet": sheet, "cell": cell, "year": year, "value": str(v)})
                    rows.append({"sheet": sheet, "level": lvl, "age": int(age), "year": year,
                                 "sex": sx, "value": val, "cell": cell})
        tables[sheet] = pd.DataFrame(rows)
    return {"meta": meta, "enrolment": tables["Enrolment"], "population": tables["Population"],
            "non_numeric": pd.DataFrame(bad, columns=["sheet", "cell", "year", "value"])}
