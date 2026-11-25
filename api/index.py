"""Vercel serverless entrypoint: upload country workbooks -> validation issues + indicators.
Streamlit can't run on Vercel, so this is a small Flask equivalent of the Streamlit app
(synthetic demo). Vercel caps request bodies at ~4.5 MB.

vercel.json rewrites every path to /api/index, so Flask only ever sees that path:
all actions are POST fields on one URL rather than separate routes.
"""
import io
import json
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
<div class=box><h3>How it works</h3><ol>
<li><b>Preview</b> a sample (or your own file) to see what is being checked.</li>
<li><b>Run</b> the checker: every workbook is read, then validated against rules V01-V12.</li>
<li><b>Review</b> the output: run log, issues by country and severity, total indicators.</li>
<li><b>Fix and re-upload</b>: countries correct the flagged cells in Excel and submit again.</li></ol>
<small>Try it with the sample data below; 7 of the 10 files carry a deliberate defect.</small></div>
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
            f"<input type=hidden name=name value='{escape(p.name)}'><button>Preview input</button></form> "
            f"<form class=inline method=post><input type=hidden name=action value=download>"
            f"<input type=hidden name=name value='{escape(p.name)}'><button>Download .xlsx</button></form></td></tr>")
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


CHART_JS = """
(function(){
var D=JSON.parse(document.getElementById('chart-data').textContent);
var cs=document.getElementById('c-country'),is=document.getElementById('c-ind'),box=document.getElementById('c-svg');
var COL={ISCED1:'#1f77b4',ISCED2:'#d95f02',ISCED3:'#1b9e77'};
Object.keys(D).sort().forEach(function(c){var o=document.createElement('option');o.textContent=c;cs.appendChild(o);});
function el(n,a,t){var e=document.createElementNS('http://www.w3.org/2000/svg',n);for(var k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;return e;}
function draw(){
  var c=cs.value,ind=is.value,rows=D[c].filter(function(r){return r.i===ind;});
  var W=640,H=330,L=48,R=70,T=16,B=40,pw=W-L-R,ph=H-T-B;
  var yrs=[...new Set(rows.map(function(r){return r.y;}))].sort(),
      vals=rows.map(function(r){return r.v;}),
      mx=Math.max(100,Math.ceil(Math.max.apply(null,vals)/10)*10),
      mn=Math.max(0,Math.floor((Math.min.apply(null,vals)-5)/10)*10),
      step=(mx-mn)>60?20:10;
  var X=function(y){return L+(yrs.length>1?(y-yrs[0])/(yrs[yrs.length-1]-yrs[0]):0.5)*pw;},
      Y=function(v){return T+ph-((v-mn)/(mx-mn))*ph;};
  var svg=el('svg',{viewBox:'0 0 '+W+' '+H,width:'100%',role:'img','aria-label':'Total '+ind+' by level and year for '+c});
  for(var t=mn;t<=mx;t+=step){svg.appendChild(el('line',{x1:L,x2:L+pw,y1:Y(t),y2:Y(t),stroke:'#e3e3e3'}));
    svg.appendChild(el('text',{x:L-6,y:Y(t)+4,'text-anchor':'end','font-size':11,fill:'#666'},t));}
  svg.appendChild(el('line',{x1:L,x2:L+pw,y1:Y(100),y2:Y(100),stroke:'#999','stroke-dasharray':'4 3'}));
  svg.appendChild(el('text',{x:L+pw+4,y:Y(100)+4,'font-size':11,fill:'#666'},'100%'));
  yrs.forEach(function(y){svg.appendChild(el('text',{x:X(y),y:H-B+16,'text-anchor':'middle','font-size':11,fill:'#666'},y));});
  svg.appendChild(el('text',{x:L+pw/2,y:H-6,'text-anchor':'middle','font-size':11,fill:'#666'},'Year'));
  var levels=[...new Set(rows.map(function(r){return r.l;}))].sort(),ends=[];
  levels.forEach(function(l){
    var pts=rows.filter(function(r){return r.l===l;}).sort(function(a,b){return a.y-b.y;});
    svg.appendChild(el('polyline',{points:pts.map(function(r){return X(r.y)+','+Y(r.v);}).join(' '),fill:'none',stroke:COL[l]||'#444','stroke-width':2.2}));
    pts.forEach(function(r){var m=el('circle',{cx:X(r.y),cy:Y(r.v),r:3.6,fill:COL[l]||'#444'});m.appendChild(el('title',{},l+' '+r.y+': '+r.v.toFixed(1)+'%'));svg.appendChild(m);});
    var last=pts[pts.length-1];if(last)ends.push({l:l,x:X(last.y)+8,y:Y(last.v)+4});
  });
  ends.sort(function(a,b){return a.y-b.y;});
  for(var k=1;k<ends.length;k++){if(ends[k].y-ends[k-1].y<15)ends[k].y=ends[k-1].y+15;}
  ends.forEach(function(e){svg.appendChild(el('text',{x:e.x,y:e.y,'font-size':12,'font-weight':600,fill:COL[e.l]||'#444'},e.l));});
  box.innerHTML='';box.appendChild(svg);
}
cs.onchange=is.onchange=draw;draw();
})();
"""


def chart_html(ind: pd.DataFrame) -> str:
    """Interactive line chart (inline SVG, no libraries): total GER or NER by level and year, per country."""
    t = ind[(ind.sex == "T") & ind.indicator.isin(["GER", "NER"]) & ind.value.notna()] if len(ind) else ind
    if not len(t):
        return ""
    data = {c: [{"l": r.level, "i": r.indicator, "y": int(r.year), "v": round(float(r.value), 2)}
                for r in g.itertuples()] for c, g in t.groupby("country")}
    blob = json.dumps(data).replace("<", "\\u003c")  # keep user-controlled country codes inert in <script>
    return ("<h3>Chart: indicators by level and year</h3>"
            "<div class=box><label>Country <select id=c-country></select></label> "
            "<label>Indicator <select id=c-ind><option value=GER>GER</option><option value=NER>NER</option></select></label>"
            "<div id=c-svg></div><small>Total (both sexes), %. Dashed line = 100%; the vertical axis does not start at 0. Hover a point for its value.</small></div>"
            f"<script id=chart-data type=application/json>{blob}</script><script>{CHART_JS}</script>")


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
            f"{chart_html(ind)}"
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
    if action == "download":
        match = [p for p in sample_files() if p.name == request.form.get("name")]
        if not match:
            return PAGE.format(samples=samples_panel(), body="<p>Unknown sample.</p>"), 400
        return send_file(match[0], as_attachment=True, download_name=match[0].name,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
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
