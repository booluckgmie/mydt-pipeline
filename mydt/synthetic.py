"""Generate SYNTHETIC country submissions (with deliberate errors) to exercise the pipeline."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from openpyxl import load_workbook
from . import config as C
from .template import build_template, existing_years, _year_cols

# country index -> injected defect
DEFECTS = {2: "negative", 3: "text", 4: "spike", 5: "missing_year", 6: "no_iso", 7: "ger_high", 8: "cohort"}


def _fill(path, code, name, rng, defect):
    wb = load_workbook(path)
    en, po, md = wb["Enrolment"], wb["Population"], wb["Metadata"]
    years = existing_years(en)
    scale = rng.uniform(5e4, 4e5)
    for i, v in enumerate([name, None if defect == "no_iso" else code, years[-1] + 1,
                           "Focal Point", "focal@example.org"], start=2):
        md.cell(i, 2, v)
    pop_age = {}
    for k, y in enumerate(years):
        m, f, _ = _year_cols(C.FIRST_YEAR_COL, k)
        for i, a in enumerate(C.AGES):
            base = scale * (1 + 0.01 * k) * (1 - 0.02 * abs(a - 11))
            pm = round(base * 0.51); pf = round(base * 0.49)
            pop_age[(k, a)] = (pm, pf)
            po.cell(C.DATA_ROW0 + i, m, pm); po.cell(C.DATA_ROW0 + i, f, pf)
        r = C.DATA_ROW0
        for lvl, (a0, a1) in C.LEVELS.items():
            for a in C.AGES:
                pm, pf = pop_age[(k, a)]
                if a0 <= a <= a1:
                    rate = rng.uniform(0.85, 1.0)
                elif a0 - 1 <= a <= a1 + 3:
                    rate = rng.uniform(0.02, 0.08)
                else:
                    rate = 0.0
                # age-cohort smoothness: enrolment in each level only counts at its own ages
                gfac = 0.97 if lvl == "ISCED3" else 1.0
                en.cell(r, m, round(pm * rate * gfac)); en.cell(r, f, round(pf * rate * gfac * rng.uniform(0.97, 1.03)))
                r += 1
    last_k = len(years) - 1
    m, f, _ = _year_cols(C.FIRST_YEAR_COL, last_k)
    if defect == "negative":
        en.cell(C.DATA_ROW0 + 6, m, -1200)
    elif defect == "text":
        en.cell(C.DATA_ROW0 + 7, f, "n/a")
    elif defect == "spike":
        en.cell(C.DATA_ROW0 + 4, m, en.cell(C.DATA_ROW0 + 4, m).value * 12)
    elif defect == "missing_year":
        for r in range(C.DATA_ROW0, C.DATA_ROW0 + len(C.AGES) * len(C.LEVELS)):
            en.cell(r, m).value = None; en.cell(r, f).value = None
    elif defect == "ger_high":
        for r in range(C.DATA_ROW0, C.DATA_ROW0 + len(C.AGES)):
            for c in (m, f):
                en.cell(r, c, round((en.cell(r, c).value or 0) * 2.4))
    elif defect == "cohort":  # halve one age across the last year -> cohort break
        for lvl_i in range(len(C.LEVELS)):
            r = C.DATA_ROW0 + lvl_i * len(C.AGES) + C.AGES.index(9)
            for c in (m, f):
                en.cell(r, c, round(en.cell(r, c).value * 0.4))
    wb.save(path)


def make_submissions(outdir: str | Path, n: int = 10, years=(2023, 2024, 2025, 2026), seed: int = 7) -> list[Path]:
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    paths = []
    for i in range(1, n + 1):
        code = f"XC{i:02d}"
        p = outdir / f"MYDT_{code}.xlsx"
        build_template(p, list(years))
        _fill(p, code, f"Synthetic Country {i:02d}", rng, DEFECTS.get(i))
        paths.append(p)
    return paths
