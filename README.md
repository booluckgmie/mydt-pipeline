# mydt-pipeline

A small, tested reference pipeline for **Excel-template-based data collection**: build a multi-year template with formulas, extend it with new years, validate country submissions against traceable rules, consolidate into one database, and produce per-country indicator review reports.

> All data here is **synthetic**. The workbook layout, indicators (GER, NER, GPI) and thresholds are illustrative stand-ins for a real data-collection template, not any official tool or methodology.

## Pipeline

```
template.py   build_template / add_year   -> multi-year workbook (input cells, formulas, built-in checks)
synthetic.py  make_submissions            -> 10 country files, 7 with a deliberate defect
read.py       read_workbook               -> tidy tables; non-numeric cells captured, not crashed on
indicators.py compute_indicators          -> independent Python GER / NER / GPI
validate.py   validate, qc_checklist      -> rules V01-V12, per-country PASS / REVIEW checklist
consolidate.py consolidate                -> CSV + SQLite database + run log (a corrupt file never stops a batch)
report.py     all_reports                 -> self-contained HTML review per country
cli.py / streamlit_app.py                         -> command line and Streamlit uploader
```

## Quick start

```bash
pip install -e .[dev,app]
mydt synth sample_data/submissions -n 10        # synthetic submissions
mydt run sample_data/submissions sample_data/run  # validate + consolidate + reports
mydt add-year sample_data/submissions/MYDT_XC01.xlsx 2027   # extend a template, data preserved
streamlit run streamlit_app.py
pytest
```

## Design choices

- **Two independent calculations of every indicator.** The workbook computes them with `SUMIFS` formulas; `indicators.py` recomputes them from raw inputs. `tests/test_pipeline.py` recalculates a workbook in LibreOffice and asserts the two agree for all 24 level/indicator/year cells. Disagreement means a formula bug or a tampered template.
- **Adding a year never touches existing data.** Year blocks are appended to the right; `add_year` is idempotent.
- **Every check has a rule ID** (`validate.RULES`) and thresholds live in `config.py`, so the QC checklist is auditable and changes are one-line diffs.
- **Level-edge awareness.** Age-spike and cohort checks skip ages where steps are legitimate (school entry/exit), which removed all false positives on clean synthetic countries.
- **Batch robustness.** Unreadable workbooks are logged as `FAILED` in `run_log` and the batch continues.

## Validation rules

| ID | Severity | Check |
|---|---|---|
| V01 | error | Required metadata missing |
| V02 | error | Non-numeric entry in a data cell |
| V03 | error | Negative value |
| V04 | error | Year block entirely empty |
| V05 | warning | Age spike vs neighbouring ages |
| V06 | warning | Age-cohort progression outside band |
| V07/V08 | warning/error | GER above warning / plausible maximum |
| V09 | error | NER above 100% |
| V10 | warning | GPI outside plausible range |
| V11 | warning | Large year-on-year change in level enrolment |
| V12 | error | Enrolment at an age far above population |

## Limitations

Synthetic data only; thresholds are not calibrated to real country data; one reference workbook layout (translated template variants would be produced by a language-parameterised build step, not yet implemented).
