"""Vercel serverless entrypoint: upload country workbooks -> validation issues + indicators.
Streamlit can't run on Vercel, so this is a small Flask equivalent of app.py
(synthetic demo). Vercel caps request bodies at ~4.5 MB.
"""
import sys
import tempfile
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, request  # noqa: E402
from mydt.consolidate import consolidate  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>MYDT submission checker</title>
<style>body{{font:14px system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;color:#222}}
table{{border-collapse:collapse;width:100%;margin:.6rem 0}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}
th{{background:#f0f0f0}}small{{color:#666}}</style>
<h1>MYDT submission checker</h1><small>SYNTHETIC demo - illustrative format only. Max 4 MB per upload.</small>
<form method=post enctype=multipart/form-data><p><input type=file name=files accept=.xlsx multiple required>
<button>Check</button></p></form>{body}"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return PAGE.format(body="")
    files = [f for f in request.files.getlist("files") if f.filename]
    if not files:
        return PAGE.format(body="<p>No files uploaded.</p>"), 400
    tmp = Path(tempfile.mkdtemp())  # /tmp is the only writable path on Vercel
    paths = []
    for f in files:
        p = tmp / Path(f.filename).name
        f.save(p)
        paths.append(p)
    res = consolidate(paths, tmp / "out")
    iss, ind = res["issues"], res["indicators"]
    ok = int((res["run_log"].status == "OK").sum())
    body = (f"<h2>{ok} of {len(paths)} files processed</h2>"
            f"<h2>Run log</h2>{res['run_log'].to_html(index=False)}"
            f"<h2>Issues ({len(iss)})</h2>{iss.to_html(index=False) if len(iss) else '<p>None.</p>'}"
            f"<h2>Indicators (total)</h2>"
            f"{ind[ind.sex == 'T'].to_html(index=False) if len(ind) else '<p>None.</p>'}")
    return PAGE.format(body=body)
