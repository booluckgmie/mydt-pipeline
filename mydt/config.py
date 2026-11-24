"""Single source of truth for template structure and methodology parameters."""
from __future__ import annotations

# level -> (official entrance age, official last age)
LEVELS: dict[str, tuple[int, int]] = {
    "ISCED1": (6, 11),
    "ISCED2": (12, 14),
    "ISCED3": (15, 17),
}
AGES = list(range(5, 20))          # single ages captured in the template
SEXES = ("M", "F", "T")            # T is a formula (M+F) in the workbook
DATA_ROW0 = 5                      # first data row on data sheets
YEAR_ROW, SEX_ROW = 3, 4
FIRST_YEAR_COL = 3                 # column C
META_FIELDS = ["Country", "ISO3", "Survey year", "Contact name", "Contact email"]

# thresholds used by validation rules (kept here so they are auditable)
THRESHOLDS = {
    "ger_warn": 130.0, "ger_error": 200.0, "ner_error": 100.0,
    "gpi_low": 0.6, "gpi_high": 1.6,
    "yoy_warn": 0.30,             # >30% change in level total year on year
    "spike_ratio": 3.0,           # single-age value vs mean of neighbours
    "cohort_lo": 0.6, "cohort_hi": 1.4,  # cohort progression ratio band
    "enrol_pop_ratio": 1.5,
}
