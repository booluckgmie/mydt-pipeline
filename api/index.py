"""Vercel serverless entrypoint for the web demo (Flask). The page itself is built in mydt/webui.py.

vercel.json rewrites every path to /api/index, so Flask only ever sees that path:
every action is a POST field (`action`) on one URL rather than a separate route.
Vercel caps request bodies at ~4.5 MB; /tmp is the only writable path.
"""
import io
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, request, send_file  # noqa: E402
from mydt.consolidate import consolidate  # noqa: E402
from mydt.i18n import LANGS  # noqa: E402
from mydt.synthetic import make_submissions  # noqa: E402
from mydt.template import build_template, prefill  # noqa: E402
from mydt import webui  # noqa: E402
from mydt.webui import chart_html, preview_html  # noqa: E402,F401  (re-exported for tests)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_sample_dir = None


def sample_files():
    """Generate the synthetic sample workbooks once per warm instance (in /tmp)."""
    global _sample_dir
    if _sample_dir is None or not any(Path(_sample_dir).glob("*.xlsx")):
        _sample_dir = tempfile.mkdtemp()
        make_submissions(_sample_dir, n=10)
    return sorted(Path(_sample_dir).glob("*.xlsx"))


def _render(active="overview", **kw):
    return webui.page(active, samples=sample_files(), **kw)


def _run(paths):
    res = consolidate(paths, Path(tempfile.mkdtemp()) / "out")
    return _render("results", results=webui.results_html(res, len(paths)), force=True)


def _int(name, default, lo, hi):
    try:
        return min(max(int(request.form.get(name, default)), lo), hi)
    except (TypeError, ValueError):
        return default


def _cell_text(value, limit=80):
    """User text written into a workbook cell: never let it start a formula."""
    v = (value or "").strip()[:limit].lstrip("=+-@\t\r ")
    return v or None


@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    action = request.form.get("action") if request.method == "POST" else None
    if action is None:
        return _render()
    if action == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sample_files():
                z.write(p, p.name)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True,
                         download_name="mydt_sample_submissions.zip")
    if action in ("preview", "download"):
        match = [p for p in sample_files() if p.name == request.form.get("name")]
        if not match:
            return _render("samples", preview="<div class='alert err'>Unknown sample.</div>", force=True), 400
        if action == "download":
            return send_file(match[0], as_attachment=True, download_name=match[0].name, mimetype=XLSX)
        return _render("samples", preview=preview_html(match[0]), force=True)
    if action == "run_sample":
        return _run(sample_files())
    if action == "template":
        lang = request.form.get("lang", "en")
        if lang not in LANGS:
            return _render("templates", force=True), 400
        y0 = _int("y0", 2023, 2015, 2035)
        y1 = min(max(_int("y1", 2027, 2015, 2035), y0), y0 + 9)
        out = Path(tempfile.mkdtemp()) / f"MYDT_{lang}_{y0}-{y1}.xlsx"
        build_template(out, list(range(y0, y1 + 1)), lang=lang)
        iso = _cell_text(request.form.get("iso3"), 3)
        sy = request.form.get("survey_year", "").strip()
        prefill(out, country=_cell_text(request.form.get("country")), iso3=iso.upper() if iso else None,
                survey_year=_int("survey_year", None, 2015, 2035) if sy else None)
        return send_file(out, as_attachment=True, download_name=out.name, mimetype=XLSX)
    # upload
    files = [f for f in request.files.getlist("files") if f.filename]
    if not files:
        return _render("check", preview="", force=True), 400
    tmp = Path(tempfile.mkdtemp())
    paths = []
    for f in files:
        p = tmp / Path(f.filename).name
        f.save(p)
        paths.append(p)
    return _run(paths)
