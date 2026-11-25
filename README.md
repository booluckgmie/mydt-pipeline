# mydt-pipeline

A small, tested reference pipeline for **Excel-template-based data collection**: build a multi-year template with formulas, extend it with new years, validate country submissions against traceable rules, consolidate into one database, and produce per-country indicator review reports.

> The sample workbooks are **synthetic**; the *Real data* tab of the web demo uses a snapshot of public UNESCO Institute for Statistics (UIS) data, credited to UIS. The workbook layout, indicators (GER, NER, GPI) and thresholds are illustrative stand-ins for a real data-collection template, not any official tool or methodology.

## Pipeline

```
template.py   build_template / add_year   -> multi-year workbook (input cells, formulas, built-in checks)
i18n.py       labels(lang)                -> en / fr / es / pt / ru visible labels (structure identical)
              prefill                     -> write country metadata into a template (template.py)
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
mydt template out/MYDT_fr.xlsx --years 2026 2027 --lang fr   # fr | es | pt | ru | en
mydt prefill out/MYDT_fr.xlsx --country France --iso3 FRA --survey-year 2027
streamlit run streamlit_app.py
pytest
```

## Workflow

How a data-collection round runs, end to end. Every step has a command and, for steps 3-5, a place in the web UI.

```
1 Build template  ->  2 Countries fill it  ->  3 Upload & read  ->  4 Validate  ->  5 Review  ->  6 Consolidate
   mydt build            (Excel, offline)        UI / mydt run        rules V01-V12     HTML reports     CSV + SQLite
```

1. **Build the template.** `build_template` writes a multi-year workbook: yellow cells are data entry, grey cells are formulas. `mydt add-year <file> 2027` appends a year block to the right and never touches existing data.
2. **Countries fill it in** offline in Excel and send the file back.
3. **Upload and read.** Drop the `.xlsx` files into the web UI (or run `mydt run <dir> <out>`). Each workbook is read into tidy tables; cells that are not numbers are captured, not crashed on.
4. **Validate.** Rules V01-V12 run per country (see the table below). Errors block acceptance, warnings need a human look. Indicators (GER, NER, GPI) are recomputed in Python independently of the workbook's own formulas.
5. **Review.** The UI shows the run log, issues by country and severity, and total indicators. The CLI also writes one self-contained HTML review report per country.
6. **Consolidate.** All accepted submissions go into one database (`consolidated.sqlite` plus CSVs). An unreadable file is logged as `FAILED` and the batch continues.

### Using the web UI

The same demo runs locally (`streamlit run streamlit_app.py`) and on Vercel (`api/index.py`, a Flask app whose HTML is built in `mydt/webui.py`). The Vercel version is one page with tabs:

| Tab | What you do there |
|---|---|
| **Overview** | See the four steps and start with *Run the 10 sample files*, *Upload your files* or *Get a template*. |
| **Samples** | Ten synthetic workbooks, seven with a deliberate defect (shown on each card). *Preview input* shows metadata, total enrolment by level and year and the first data cells; *Download .xlsx* or the zip gives you the files. |
| **Check my files** | Drag and drop your `.xlsx` workbooks (4 MB in total) and press *Check files*. |
| **Results** | Appears after a run: file, clean-country, error and warning counts; a PASS-style status per country; an indicator chart (GER or NER by level and year, per country); an issues table you can filter by severity, country and rule; CSV downloads of issues, indicators and the run log. |
| **Real data** | Public statistics from the UNESCO Institute for Statistics (UIS), 14 countries, 2015 to 2025: pick a country and see enrolment by level, GER computed from the counts against the ratio UIS publishes, or the gender parity of GER, plus a latest-year table and an independent agreement check. Level totals only (the public data has no single-age enrolment), so the age-by-age rules still run on the synthetic files. |
| **Rules** | All twelve rules (V01-V12) with severity, plus the thresholds from `config.py`. |
| **Templates** | Build a blank multi-year template in English, French, Spanish, Portuguese or Russian, for the years you choose, optionally pre-filled with country, ISO3 and survey year. |
| **About** | What the demo is, its limits and the source code. |

Nothing is stored: results exist only in the page you are looking at. The Vercel version does not produce the HTML review reports or the SQLite database (they need matplotlib and a writable disk); use the CLI (`mydt run`) for those. The page uses no JavaScript libraries. It follows the visitor's system light or dark setting until they flip the switch in the header; the choice is remembered in the browser (`localStorage`) and applied before the page paints, so there is no flash.

## Deploying to Vercel

`api/index.py` is the entrypoint and `vercel.json` rewrites every path to it, so Flask only sees `/api/index`; every UI action (preview, download, run, template) is a POST with an `action` field on one URL. Vercel installs dependencies from `pyproject.toml` (not `requirements.txt`), so anything the app imports, including `flask`, must be listed there. The Streamlit script is `streamlit_app.py`, not `app.py`, so Vercel does not mistake it for the entrypoint.

## Real data snapshot

`mydt/data/uis_public.csv` is a snapshot of public UIS data (enrolment, school-age population and the published GER for ISCED levels 1 to 3, by sex, 14 countries, 2015 to 2025), with its release, retrieval date and credit in `mydt/data/uis_public.SOURCE.txt`. Rebuild it with `python scripts/fetch_uis.py` (stdlib only, needs internet); edit `COUNTRIES` or the year range at the top of that script to change what is fetched. It is stored in the repo so the demo works offline and shows the same numbers every time. Check the UIS terms of use before reusing the data, and keep the credit.

## Design choices

- **Two independent calculations of every indicator.** The workbook computes them with `SUMIFS` formulas; `indicators.py` recomputes them from raw inputs. `tests/test_pipeline.py` recalculates a workbook in LibreOffice and asserts the two agree for all 24 level/indicator/year cells. Disagreement means a formula bug or a tampered template.
- **One structure, many languages.** `--lang` changes labels only. A test builds the same submissions in every language and asserts the consolidated numbers and issues are identical to the English ones.
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

Synthetic data only; thresholds are not calibrated to real country data; one reference workbook layout. Translations (fr/es/pt/ru) are drafts for a build step that changes visible labels only; sheet names, level codes and sex codes stay language-neutral so every language version is processed by identical code. A native speaker should review them before use. Stata and R ports of the processing scripts are not included.
