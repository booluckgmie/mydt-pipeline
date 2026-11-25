"""Vercel serverless entrypoint: upload country workbooks -> validation issues + indicators.
Streamlit can't run on Vercel, so this is a small Flask equivalent of the Streamlit app
(synthetic demo). Vercel caps request bodies at ~4.5 MB.

vercel.json rewrites every path to /api/index, so Flask only ever sees that path:
all actions are POST fields on one URL rather than separate routes.
"""
import io
import sys
import tempfile
import zipfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
from flask import Flask, request, send_file  # noqa: E402
from mydt.consolidate import consolidate  # noqa: E402
from mydt.read import read_workbook  # noqa: E402
from mydt.synthetic import DEFECTS, make_submissions  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

DEFECT_TEXT = {
    None: "None (clean file)",
    "negative": "Negative enrolment value (rule V03)",
    "text": "Text 'n/a' typed into a data cell (V02)",
    "spike": "One age 12x its neighbours (V05)",
    "missing_year": "Latest year block left empty (V04)",
    "no_iso": "ISO3 metadata missing (V01)",
    "ger_high": "Enrolment 2.4x too high, GER above max (V07/V08)",
    "cohort": "One age cut to 40%, cohort break (V06)",
}

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>MYDT submission checker</title>
<style>body{{font:14px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#222}}
table{{border-collapse:collapse;width:100%;margin:.6rem 0}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}
th{{background:#f0f0f0}}small,.muted{{color:#666}}.box{{border:1px solid #ddd;border-radius:8px;padding:.6rem 1rem;margin:1rem 0}}
button{{padding:4px 10px;cursor:pointer}}h2{{margin-top:1.6rem}}form.inline{{display:inline}}</style>
<h1>MYDT submission checker</h1><small>SYNTHETIC demo - illustrative format only. Max 4 MB per upload.</small>
<div class=box><h3>Upload your own workbooks</h3>
<form method=post enctype=multipart/form-data><input type=hidden name=action value=upload>
<input type=file name=files accept=.xlsx multiple required> <button>Check</button></form></div>
{samples}{body}"""

_sample_dir = None


def sample_files():
    """Generate the synthetic sample workbooks once per warm instance (in /tmp)."""
    global _sample_dir
    if _sample_dir is None or not any(Path(_sample_dir).glob("*.xlsx")):
        _sample_dir = tempfile.mkdtemp()
        make_submissions(_sample_dir, n=10)
    return sorted(Path(_sample_dir).glob("*.xlsx"))


def samples_panel(selected=None):
    rows = []
    for i, p in enumerate(sample_files(), start=1):
        rows.append(
            f"<tr><td>{escape(p.name)}</td><td>{escape(DEFECT_TEXT[DEFECTS.get(i)])}</td><td>"
            f"<form class=inline method=post><input type=hidden name=action value=preview>"
            f"<input type=hidden name=name value='{escape(p.name)}'><button>Preview input</button></form></td></tr>")
    return ("<div class=box><h3>Sample data</h3>"
            "<p class=muted>10 synthetic country workbooks; 7 carry one deliberate defect so you can see "
            "what the checker flags.</p>"
            "<form class=inline method=post><input type=hidden name=action value=run_sample>"
            "<button><b>Run checker on all 10 samples</b></button></form> "
            "<form class=inline method=post><input type=hidden name=action value=zip>"
            "<button>Download samples (.zip)</button></form>"
            "<table><tr><th>File</th><th>Injected defect</th><th></th></tr>" + "".join(rows) + "</table></div>")


def preview_html(path: Path) -> str:
    sub = read_workbook(path)
    meta = pd.DataFrame({"field": list(sub["meta"].keys()),
                         "value": [("" if v is None else str(v)) for v in sub["meta"].values()]})
    en = sub["enrolment"]
    total = (en.groupby(["level", "year"]).value.sum(min_count=1).unstack("year").round(0))
    head = en.head(12)[["level", "age", "year", "sex", "value", "cell"]]
    return (f"<div class=box><h3>Input preview: {escape(path.name)}</h3>"
            f"<h4>Metadata</h4>{meta.to_html(index=False)}"
            f"<h4>Total enrolment by level and year</h4>{total.to_html(na_rep='')}"
            f"<h4>First 12 enrolment cells (tidy view)</h4>{head.to_html(index=False)}</div>")


def results_html(paths):
    tmp = Path(tempfile.mkdtemp())
    res = consolidate(paths, tmp / "out")
    iss, ind, log = res["issues"], res["indicators"], res["run_log"]
    ok = int((log.status == "OK").sum())
    ind_t = ind[ind.sex == "T"].round(1) if len(ind) else ind
    by_rule = ("" if not len(iss) else
               "<h4>Issues by country</h4>" + iss.groupby(["country", "severity"]).size()
               .unstack(fill_value=0).to_html())
    return (f"<h2>Output: {ok} of {len(paths)} files processed</h2>"
            f"<h3>Run log</h3>{log.to_html(index=False)}"
            f"<h3>Issues ({len(iss)})</h3>{by_rule}{iss.to_html(index=False) if len(iss) else '<p>None.</p>'}"
            f"<h3>Indicators (total)</h3>{ind_t.to_html(index=False) if len(ind_t) else '<p>None.</p>'}")


# Both paths: browsers request "/", Flask receives the rewritten "/api/index".
@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    action = request.form.get("action") if request.method == "POST" else None
    if action is None:
        return PAGE.format(samples=samples_panel(), body="")
    if action == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sample_files():
                z.write(p, p.name)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True,
                         download_name="mydt_sample_submissions.zip")
    if action == "preview":
        match = [p for p in sample_files() if p.name == request.form.get("name")]
        if not match:
            return PAGE.format(samples=samples_panel(), body="<p>Unknown sample.</p>"), 400
        return PAGE.format(samples=samples_panel(), body=preview_html(match[0]))
    if action == "run_sample":
        paths = sample_files()
        return PAGE.format(samples=samples_panel(), body=results_html(paths))
    # upload
    files = [f for f in request.files.getlist("files") if f.filename]
    if not files:
        return PAGE.format(samples=samples_panel(), body="<p>No files uploaded.</p>"), 400
    tmp = Path(tempfile.mkdtemp())  # /tmp is the only writable path on Vercel
    paths = []
    for f in files:
        p = tmp / Path(f.filename).name
        f.save(p)
        paths.append(p)
    previews = ""
    for p in paths:
        try:
            previews += preview_html(p)
        except Exception as e:  # unreadable workbook: consolidate() will log it as FAILED
            previews += f"<div class=box><b>{escape(p.name)}</b>: could not be read ({escape(repr(e))})</div>"
    return PAGE.format(samples=samples_panel(), body=previews + results_html(paths))
