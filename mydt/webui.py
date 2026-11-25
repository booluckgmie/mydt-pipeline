"""HTML for the web demo (served by api/index.py on Vercel). Pure functions: data in, HTML string out.

The app is one page with tabs (Overview, Samples, Check my files, Results, Rules, Templates, About).
Tabs are plain JavaScript; without JavaScript every section is shown one after another.
Everything user-derived (country codes, file names, messages) goes through html.escape.
"""
from __future__ import annotations
import json
from html import escape as esc

import pandas as pd

from . import config as C
from .i18n import LANGS
from .read import read_workbook
from .synthetic import DEFECTS
from .validate import RULES

REPO = "https://github.com/booluckgmie/mydt-pipeline"

DEFECT_TEXT = {
    None: "Clean file",
    "negative": "Negative enrolment value (V03)",
    "text": "Text 'n/a' typed into a data cell (V02)",
    "spike": "One age 12x its neighbours (V05)",
    "missing_year": "Latest year block left empty (V04)",
    "no_iso": "ISO3 metadata missing (V01)",
    "ger_high": "Enrolment 2.4x too high, GER above max (V07/V08)",
    "cohort": "One age cut to 40%, cohort break (V06)",
}

LANG_NAMES = {"en": "English", "fr": "Français", "es": "Español", "pt": "Português", "ru": "Русский"}

TABS = [("overview", "Overview"), ("samples", "Samples"), ("check", "Check my files"),
        ("results", "Results"), ("rules", "Rules"), ("templates", "Templates"), ("about", "About")]

DARK = ("color-scheme:dark;--bg:#0e131a;--surface:#161d27;--text:#e8edf3;--muted:#98a5b5;--line:#283240;"
        "--brand:#6b9aff;--brand-ink:#0a1220;--brand-soft:#1a2740;--ok:#5fd39a;--ok-bg:#12301f;--warn:#f0b35a;--warn-bg:#35260f;"
        "--err:#ff9088;--err-bg:#3a1a18;--shadow:0 1px 2px rgba(0,0,0,.4);--c1:#6b9aff;--c2:#fb923c;--c3:#34d399")

CSS = """
:root{color-scheme:light;--bg:#f5f6f8;--surface:#fff;--text:#1b2430;--muted:#5b6777;--line:#e2e6ec;--brand:#1d5cff;--brand-ink:#fff;
--brand-soft:#e8efff;--ok:#0b7a43;--ok-bg:#e1f4ea;--warn:#8a5200;--warn-bg:#fcefd6;--err:#b3261e;--err-bg:#fae6e4;
--shadow:0 1px 2px rgba(16,24,40,.06),0 6px 18px rgba(16,24,40,.06);--c1:#2563eb;--c2:#ea580c;--c3:#059669}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){__DARK__}}
:root[data-theme=dark]{__DARK__}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text)}
a{color:var(--brand)}h1,h2,h3,h4{line-height:1.2;margin:0 0 .5rem}h2{font-size:1.5rem}h3{font-size:1.1rem}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
header.top{background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.bar{display:flex;align-items:center;gap:14px;padding:10px 0;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.05rem;white-space:nowrap}
.mark{width:30px;height:30px;border-radius:8px;background:var(--brand);color:var(--brand-ink);display:grid;place-items:center;font-weight:800}
.pill{font-size:.72rem;font-weight:700;letter-spacing:.04em;padding:2px 8px;border-radius:99px;background:var(--warn-bg);color:var(--warn)}
nav.tabs{display:flex;gap:4px;overflow-x:auto;flex:1;min-width:0;scrollbar-width:none}
nav.tabs button{border:0;background:none;color:var(--muted);font:inherit;font-weight:600;padding:8px 12px;border-radius:8px;cursor:pointer;white-space:nowrap}
nav.tabs button:hover{background:var(--brand-soft);color:var(--text)}
nav.tabs button[aria-selected=true]{background:var(--brand-soft);color:var(--brand)}
nav.tabs button.hidden{display:none}
main{padding:22px 0 40px}
.panel{display:block}.js .panel[hidden]{display:none}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:var(--shadow);margin-bottom:16px}
.hero{background:linear-gradient(135deg,var(--brand-soft),var(--surface));padding:30px 24px}
.hero h1{font-size:clamp(1.6rem,4vw,2.3rem);margin-bottom:.6rem}.hero p{color:var(--muted);max-width:60ch;margin:0 0 1.2rem}
.cta{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-block;border:1px solid var(--line);background:var(--surface);color:var(--text);font:inherit;font-weight:600;
padding:9px 16px;border-radius:10px;cursor:pointer;text-decoration:none}
.btn:hover{border-color:var(--brand)}.btn.primary{background:var(--brand);color:var(--brand-ink);border-color:var(--brand)}
.btn.small{padding:5px 10px;font-size:.85rem}.btn[disabled]{opacity:.6;cursor:wait}
form.inline{display:inline}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}
.grid.wide{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card.step{position:relative;padding-top:36px}.step .n{position:absolute;top:14px;left:20px;font-weight:800;color:var(--brand)}
.muted{color:var(--muted)}small,.small{font-size:.85rem}
.chip{display:inline-block;padding:2px 9px;border-radius:99px;font-size:.78rem;font-weight:700}
.chip.ok{background:var(--ok-bg);color:var(--ok)}.chip.warn{background:var(--warn-bg);color:var(--warn)}.chip.err{background:var(--err-bg);color:var(--err)}
.chip.info{background:var(--brand-soft);color:var(--brand)}
.kpis{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:16px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi b{display:block;font-size:1.9rem;line-height:1.1}.kpi span{color:var(--muted);font-size:.85rem}
.kpi.err b{color:var(--err)}.kpi.warn b{color:var(--warn)}.kpi.ok b{color:var(--ok)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:.6rem 0}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--brand-soft);font-weight:700;position:sticky;top:0}tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.drop{display:block;border:2px dashed var(--line);border-radius:14px;padding:34px 16px;text-align:center;cursor:pointer;background:var(--bg)}
.drop:hover,.drop.over{border-color:var(--brand);background:var(--brand-soft)}.drop b{display:block;font-size:1.05rem}
.drop input{position:absolute;opacity:0;width:1px;height:1px}
.files{list-style:none;padding:0;margin:.8rem 0;display:flex;gap:6px;flex-wrap:wrap}.files li{background:var(--brand-soft);border-radius:8px;padding:3px 9px;font-size:.85rem}
label.f{display:block;font-weight:600;font-size:.88rem;margin-bottom:10px}
select,input[type=text],input[type=number]{font:inherit;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 9px;width:100%;margin-top:4px}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin-bottom:6px}.filters label{font-size:.82rem;font-weight:600;min-width:130px}
.alert{border-radius:12px;padding:12px 16px;margin-bottom:16px;font-weight:600}.alert.err{background:var(--err-bg);color:var(--err)}
.alert.info{background:var(--brand-soft);color:var(--text);font-weight:500}
details{margin:.6rem 0}summary{cursor:pointer;font-weight:700}
.empty{text-align:center;padding:40px 16px;color:var(--muted)}
footer{border-top:1px solid var(--line);padding:18px 0 30px;color:var(--muted);font-size:.85rem}
svg .ax{fill:var(--muted);font-size:11px}svg .gl{stroke:var(--line)}svg .ref{stroke:var(--muted)}
@media (max-width:560px){.card{padding:14px}.hero{padding:22px 16px}}
@media (max-width:720px){nav.tabs{order:3;flex-basis:100%;margin:0 -4px}.bar{gap:8px 12px}}
"""

CSS += """
.theme{display:none;margin-left:auto;align-items:center;gap:7px;border:1px solid var(--line);background:var(--surface);color:var(--muted);
padding:5px 10px;border-radius:99px;cursor:pointer;font:inherit}
.js .theme{display:inline-flex}.theme:hover{border-color:var(--brand)}
.theme svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.theme .track{position:relative;width:34px;height:18px;border-radius:99px;background:var(--line);transition:background .15s}
.theme .knob{position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:var(--surface);
box-shadow:0 1px 2px rgba(0,0,0,.35);transition:transform .15s}
.theme[aria-checked=true] .track{background:var(--brand)}.theme[aria-checked=true] .knob{transform:translateX(16px)}
.theme:focus-visible,nav.tabs button:focus-visible,.btn:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
@media (prefers-reduced-motion:reduce){.theme .track,.theme .knob{transition:none}}
"""
CSS = CSS.replace("__DARK__", DARK)

JS = """
(function(){
document.documentElement.classList.add('js');
var tg=document.getElementById('theme-toggle'),mq=window.matchMedia('(prefers-color-scheme: dark)'),root=document.documentElement;
function isDark(){var t=root.getAttribute('data-theme');return t?t==='dark':mq.matches;}
function sync(){if(tg)tg.setAttribute('aria-checked',isDark()?'true':'false');}
if(tg){tg.addEventListener('click',function(){var next=isDark()?'light':'dark';root.setAttribute('data-theme',next);
  try{localStorage.setItem('mydt-theme',next);}catch(e){}sync();});
  if(mq.addEventListener)mq.addEventListener('change',sync);sync();}
var body=document.body,tabs=[].slice.call(document.querySelectorAll('nav.tabs button')),
    panels=[].slice.call(document.querySelectorAll('.panel'));
function show(id){
  var ok=panels.some(function(p){return p.id==='tab-'+id;}); if(!ok)id='overview';
  panels.forEach(function(p){p.hidden=p.id!=='tab-'+id;});
  tabs.forEach(function(t){t.setAttribute('aria-selected',t.dataset.tab===id?'true':'false');});
  try{history.replaceState(null,'','#'+id);}catch(e){}
  window.scrollTo({top:0});
}
tabs.forEach(function(t){t.addEventListener('click',function(){show(t.dataset.tab);});});
[].forEach.call(document.querySelectorAll('[data-goto]'),function(b){b.addEventListener('click',function(e){e.preventDefault();show(b.dataset.goto);});});
show(body.dataset.force==='1'?body.dataset.active:(location.hash.slice(1)||body.dataset.active));
/* busy state on submit */
[].forEach.call(document.querySelectorAll('form'),function(f){f.addEventListener('submit',function(){
  var b=f.querySelector('button[type=submit],button:not([type])');
  if(b&&f.dataset.busy){setTimeout(function(){b.disabled=true;b.textContent=f.dataset.busy;},0);}});});
/* drop zone */
var dz=document.getElementById('drop'),inp=document.getElementById('files'),list=document.getElementById('filelist');
if(dz&&inp){
  function names(){list.innerHTML='';[].forEach.call(inp.files,function(f){var li=document.createElement('li');li.textContent=f.name+' ('+Math.round(f.size/1024)+' KB)';list.appendChild(li);});}
  inp.addEventListener('change',names);
  ['dragenter','dragover'].forEach(function(ev){dz.addEventListener(ev,function(e){e.preventDefault();dz.classList.add('over');});});
  ['dragleave','drop'].forEach(function(ev){dz.addEventListener(ev,function(e){e.preventDefault();dz.classList.remove('over');});});
  dz.addEventListener('drop',function(e){if(e.dataTransfer&&e.dataTransfer.files.length){inp.files=e.dataTransfer.files;names();}});
}
/* issue filters */
var fs=document.getElementById('f-sev'),fc=document.getElementById('f-country'),fr=document.getElementById('f-rule'),cnt=document.getElementById('f-count');
if(fs){var rows=[].slice.call(document.querySelectorAll('#issues-body tr'));
  function apply(){var n=0;rows.forEach(function(tr){var ok=(!fs.value||tr.dataset.sev===fs.value)&&(!fc.value||tr.dataset.country===fc.value)&&(!fr.value||tr.dataset.rule===fr.value);tr.hidden=!ok;if(ok)n++;});cnt.textContent=n;}
  fs.onchange=fc.onchange=fr.onchange=apply;}
/* CSV downloads built in the browser from embedded data */
var cd=document.getElementById('csv-data');
if(cd){var CSV=JSON.parse(cd.textContent);
  [].forEach.call(document.querySelectorAll('[data-csv]'),function(b){b.addEventListener('click',function(){
    var blob=new Blob([CSV[b.dataset.csv]],{type:'text/csv'}),a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download='mydt_'+b.dataset.csv+'.csv';document.body.appendChild(a);a.click();a.remove();});});}
})();
"""

CHART_JS = """
(function(){
var D=JSON.parse(document.getElementById('chart-data').textContent);
var cs=document.getElementById('c-country'),is=document.getElementById('c-ind'),box=document.getElementById('c-svg');
var COL={ISCED1:'var(--c1)',ISCED2:'var(--c2)',ISCED3:'var(--c3)'};
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
  for(var t=mn;t<=mx;t+=step){svg.appendChild(el('line',{x1:L,x2:L+pw,y1:Y(t),y2:Y(t),class:'gl'}));
    svg.appendChild(el('text',{x:L-6,y:Y(t)+4,'text-anchor':'end',class:'ax'},t));}
  svg.appendChild(el('line',{x1:L,x2:L+pw,y1:Y(100),y2:Y(100),class:'ref','stroke-dasharray':'4 3'}));
  svg.appendChild(el('text',{x:L+pw+4,y:Y(100)+4,class:'ax'},'100%'));
  yrs.forEach(function(y){svg.appendChild(el('text',{x:X(y),y:H-B+16,'text-anchor':'middle',class:'ax'},y));});
  svg.appendChild(el('text',{x:L+pw/2,y:H-6,'text-anchor':'middle',class:'ax'},'Year'));
  var levels=[...new Set(rows.map(function(r){return r.l;}))].sort(),ends=[];
  levels.forEach(function(l){
    var pts=rows.filter(function(r){return r.l===l;}).sort(function(a,b){return a.y-b.y;});
    svg.appendChild(el('polyline',{points:pts.map(function(r){return X(r.y)+','+Y(r.v);}).join(' '),fill:'none',stroke:COL[l]||'#888','stroke-width':2.4}));
    pts.forEach(function(r){var m=el('circle',{cx:X(r.y),cy:Y(r.v),r:3.8,fill:COL[l]||'#888'});m.appendChild(el('title',{},l+' '+r.y+': '+r.v.toFixed(1)+'%'));svg.appendChild(m);});
    var last=pts[pts.length-1];if(last)ends.push({l:l,x:X(last.y)+8,y:Y(last.v)+4});
  });
  ends.sort(function(a,b){return a.y-b.y;});
  for(var k=1;k<ends.length;k++){if(ends[k].y-ends[k-1].y<15)ends[k].y=ends[k-1].y+15;}
  ends.forEach(function(e){svg.appendChild(el('text',{x:e.x,y:e.y,'font-size':12,'font-weight':700,fill:COL[e.l]||'#888'},e.l));});
  box.innerHTML='';box.appendChild(svg);
}
cs.onchange=is.onchange=draw;draw();
})();
"""


def _safe_json(obj) -> str:
    """JSON for a <script type=application/json> block: '<' escaped so nothing can close the tag."""
    return json.dumps(obj).replace("<", "\\u003c")


def chart_html(ind: pd.DataFrame) -> str:
    """Interactive line chart (inline SVG, no libraries): total GER or NER by level and year, per country."""
    t = ind[(ind.sex == "T") & ind.indicator.isin(["GER", "NER"]) & ind.value.notna()] if len(ind) else ind
    if not len(t):
        return ""
    data = {c: [{"l": r.level, "i": r.indicator, "y": int(r.year), "v": round(float(r.value), 2)}
                for r in g.itertuples()] for c, g in t.groupby("country")}
    return ("<div class=card><h3>Indicators by level and year</h3>"
            "<div class=filters><label>Country <select id=c-country></select></label>"
            "<label>Indicator <select id=c-ind><option value=GER>GER</option><option value=NER>NER</option></select></label></div>"
            "<div id=c-svg></div><p class='muted small'>Total (both sexes), %. Dashed line = 100%; the vertical axis "
            "does not start at 0. Hover a point for its value.</p></div>"
            f"<script id=chart-data type=application/json>{_safe_json(data)}</script><script>{CHART_JS}</script>")


# ---------- sections ----------

def overview_html() -> str:
    steps = [("1", "Preview", "Open a sample or your own workbook and see exactly what will be checked."),
             ("2", "Run the checker", "Every workbook is read and tested against 12 traceable rules."),
             ("3", "Review", "See issues by country, indicator charts and a PASS / REVIEW status per country."),
             ("4", "Fix and resubmit", "Countries correct the flagged cells in Excel and upload again.")]
    feats = [("12 traceable rules", "Every issue carries a rule ID (V01 to V12), so the QC checklist is auditable."),
             ("Indicators double-checked", "GER, NER and GPI are recomputed in code and compared with the workbook formulas."),
             ("One bad file never stops a batch", "Unreadable workbooks are logged as FAILED and the rest carry on."),
             ("Five languages", "Templates can be built with English, French, Spanish, Portuguese or Russian labels.")]
    return (
        "<div class='card hero'><h1>Check country submissions in seconds</h1>"
        "<p>Upload Excel data-collection templates, validate them against clear rules, and see the indicators and "
        "problems per country. Built on synthetic data to show the approach.</p><div class=cta>"
        "<form class=inline method=post data-busy='Running…'><input type=hidden name=action value=run_sample>"
        "<button class='btn primary' type=submit>Run the 10 sample files</button></form>"
        "<button class=btn data-goto=check type=button>Upload your files</button>"
        "<button class=btn data-goto=templates type=button>Get a template</button></div></div>"
        "<h2>How it works</h2><div class=grid>"
        + "".join(f"<div class='card step'><span class=n>{n}</span><h3>{esc(t)}</h3><p class=muted>{esc(d)}</p></div>"
                  for n, t, d in steps)
        + "</div><h2>What you get</h2><div class=grid>"
        + "".join(f"<div class=card><h3>{esc(t)}</h3><p class=muted>{esc(d)}</p></div>" for t, d in feats)
        + "</div>")


def samples_html(files, preview: str = "") -> str:
    cards = []
    for i, p in enumerate(files, start=1):
        defect = DEFECTS.get(i)
        chip = "<span class='chip ok'>Clean</span>" if defect is None else "<span class='chip warn'>Has a defect</span>"
        name = esc(p.name)
        cards.append(
            f"<div class=card><div style='display:flex;justify-content:space-between;gap:8px;align-items:center'>"
            f"<h3 style='margin:0'>{esc(p.stem.replace('MYDT_', ''))}</h3>{chip}</div>"
            f"<p class='muted small'>{esc(DEFECT_TEXT[defect])}</p>"
            f"<form class=inline method=post><input type=hidden name=action value=preview><input type=hidden name=name value='{name}'>"
            f"<button class='btn small' type=submit>Preview input</button></form> "
            f"<form class=inline method=post><input type=hidden name=action value=download><input type=hidden name=name value='{name}'>"
            f"<button class='btn small' type=submit>Download .xlsx</button></form></div>")
    return (
        "<h2>Sample data</h2><p class=muted>Ten synthetic country workbooks. Seven carry one deliberate defect so you can see "
        "what the checker flags.</p><div class=cta style='margin-bottom:16px'>"
        "<form class=inline method=post data-busy='Running…'><input type=hidden name=action value=run_sample>"
        "<button class='btn primary' type=submit>Run checker on all 10</button></form>"
        "<form class=inline method=post><input type=hidden name=action value=zip>"
        "<button class=btn type=submit>Download all (.zip)</button></form></div>"
        + preview + "<div class='grid'>" + "".join(cards) + "</div>")


def check_html() -> str:
    return (
        "<h2>Check my files</h2><div class=card>"
        "<form method=post enctype=multipart/form-data data-busy='Checking…'><input type=hidden name=action value=upload>"
        "<label class=drop id=drop for=files><b>Drop .xlsx workbooks here, or click to choose</b>"
        "<span class=muted>One file per country. Up to 4 MB in total.</span>"
        "<input id=files type=file name=files accept='.xlsx' multiple required></label>"
        "<ul class=files id=filelist></ul>"
        "<button class='btn primary' type=submit>Check files</button></form></div>"
        "<div class='alert info'>The checker expects the demo template layout (sheets Metadata, Enrolment, Population). "
        "No template yet? Build one on the <b>Templates</b> tab, or try the <b>Samples</b>. "
        "Files are checked in memory and not stored.</div>")


def rules_html() -> str:
    from . import config as _c
    rows = "".join(
        f"<tr><td><b>{rid}</b></td><td><span class='chip {'err' if sev == 'error' else 'warn'}'>{sev}</span></td>"
        f"<td>{esc(desc)}</td></tr>" for rid, (sev, desc) in RULES.items())
    th = _c.THRESHOLDS
    thr = [("GER warning above", f"{th['ger_warn']:.0f}%"), ("GER error above", f"{th['ger_error']:.0f}%"),
           ("NER error above", f"{th['ner_error']:.0f}%"), ("GPI plausible range", f"{th['gpi_low']} to {th['gpi_high']}"),
           ("Year-on-year level change", f"{th['yoy_warn']*100:.0f}%"), ("Age spike ratio", f"{th['spike_ratio']}x neighbours"),
           ("Cohort progression band", f"{th['cohort_lo']} to {th['cohort_hi']}"),
           ("Enrolment / population at one age", f"{th['enrol_pop_ratio']}x")]
    thr_rows = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in thr)
    return (
        "<h2>Validation rules</h2><p class=muted>Errors must be fixed. Warnings need a human look. "
        "Thresholds live in <code>config.py</code>, so a change is a one-line diff.</p>"
        f"<div class=tablewrap><table><tr><th>Rule</th><th>Severity</th><th>What it checks</th></tr>{rows}</table></div>"
        f"<h3>Thresholds</h3><div class=tablewrap><table><tr><th>Setting</th><th>Value</th></tr>{thr_rows}</table></div>"
        "<p class='muted small'>Synthetic demo thresholds, not calibrated to real country data.</p>")


def templates_html(default_years=(2023, 2027)) -> str:
    opts = "".join(f"<option value={k}>{esc(v)}</option>" for k, v in LANG_NAMES.items() if k in LANGS)
    return (
        "<h2>Get a template</h2><div class=card>"
        "<p class=muted>Build a blank multi-year workbook with formulas and built-in checks. Labels are translated; "
        "the structure is identical in every language, so any version is processed the same way.</p>"
        "<form method=post data-busy='Building…'><input type=hidden name=action value=template>"
        "<div class=grid><label class=f>Language<select name=lang>" + opts + "</select></label>"
        f"<label class=f>First year<input type=number name=y0 min=2015 max=2035 value={default_years[0]}></label>"
        f"<label class=f>Last year<input type=number name=y1 min=2015 max=2035 value={default_years[1]}></label></div>"
        "<h3>Pre-fill (optional)</h3><div class=grid>"
        "<label class=f>Country<input type=text name=country maxlength=80 placeholder='e.g. Chile'></label>"
        "<label class=f>ISO3 code<input type=text name=iso3 maxlength=3 placeholder='e.g. CHL'></label>"
        "<label class=f>Survey year<input type=number name=survey_year min=2015 max=2035 placeholder='2027'></label></div>"
        "<button class='btn primary' type=submit>Download template (.xlsx)</button></form>"
        "<p class='muted small'>Draft translations: a native speaker should review them before real use. "
        "Adding a year to an existing file is available in the command line: <code>mydt add-year</code>.</p></div>")


def about_html() -> str:
    return (
        "<h2>About</h2><div class=card><p>This is a reference pipeline for Excel-template-based data collection. "
        "It builds a multi-year template, validates country submissions against traceable rules, consolidates them into one "
        "database and produces per-country indicator reviews.</p>"
        "<p><b>All data is synthetic.</b> The layout, the indicators (GER, NER, GPI) and the thresholds are illustrative "
        "stand-ins, not any official tool or methodology.</p>"
        f"<p>Source code, tests and the command-line version: <a href='{REPO}'>{REPO.replace('https://', '')}</a>.</p></div>"
        "<div class=card><h3>Limits of this web version</h3><ul>"
        "<li>Uploads are limited to about 4 MB per request.</li>"
        "<li>Nothing is stored: results exist only in the page you are looking at.</li>"
        "<li>HTML review reports and the SQLite database come from the command line (<code>mydt run</code>).</li></ul></div>")


# ---------- previews and results ----------

def preview_html(path) -> str:
    sub = read_workbook(path)
    meta = pd.DataFrame({"field": list(sub["meta"].keys()),
                         "value": [("" if v is None else str(v)) for v in sub["meta"].values()]})
    en = sub["enrolment"]
    total = en.groupby(["level", "year"]).value.sum(min_count=1).unstack("year")
    total.index.name, total.columns.name = "Level", None
    head = en.head(12)[["level", "age", "year", "sex", "value", "cell"]]
    return (f"<div class=card><h3>Input preview: {esc(path.name)}</h3>"
            f"<h4>Metadata</h4><div class=tablewrap>{meta.to_html(index=False, border=0)}</div>"
            f"<h4>Total enrolment by level and year</h4><div class=tablewrap>{total.to_html(na_rep='', border=0, float_format=lambda v: f'{v:,.0f}')}</div>"
            f"<details><summary>First 12 enrolment cells (tidy view)</summary><div class=tablewrap>"
            f"{head.to_html(index=False, border=0)}</div></details></div>")


def _country_status(iss: pd.DataFrame, countries) -> str:
    rows = []
    for c in sorted(countries):
        sub = iss[iss.country == c] if len(iss) else iss
        e = int((sub.severity == "error").sum()) if len(sub) else 0
        w = int((sub.severity == "warning").sum()) if len(sub) else 0
        chip = ("<span class='chip err'>Needs fixes</span>" if e else
                "<span class='chip warn'>Review warnings</span>" if w else "<span class='chip ok'>Clean</span>")
        rows.append(f"<tr><td><b>{esc(str(c))}</b></td><td class=num>{e}</td><td class=num>{w}</td><td>{chip}</td></tr>")
    return ("<div class=tablewrap><table><tr><th>Country</th><th class=num>Errors</th><th class=num>Warnings</th>"
            "<th>Status</th></tr>" + "".join(rows) + "</table></div>")


def _issues_table(iss: pd.DataFrame) -> str:
    if not len(iss):
        return "<p class=muted>No issues found.</p>"
    body = []
    for r in iss.itertuples():
        sev_chip = f"<span class='chip {'err' if r.severity == 'error' else 'warn'}'>{esc(r.severity)}</span>"
        yr = "" if pd.isna(r.year) else str(int(r.year))
        body.append(f"<tr data-sev='{esc(r.severity)}' data-country='{esc(str(r.country))}' data-rule='{esc(r.rule)}'>"
                    f"<td>{esc(str(r.country))}</td><td>{esc(r.rule)}</td><td>{sev_chip}</td><td>{yr}</td>"
                    f"<td>{esc(str(r.where))}</td><td>{esc(str(r.message))}</td></tr>")
    countries = sorted(iss.country.astype(str).unique())
    rules = sorted(iss.rule.unique())
    opt = lambda vals: "<option value=''>All</option>" + "".join(f"<option>{esc(v)}</option>" for v in vals)
    return (f"<div class=filters><label>Severity<select id=f-sev><option value=''>All</option><option>error</option>"
            f"<option>warning</option></select></label><label>Country<select id=f-country>{opt(countries)}</select></label>"
            f"<label>Rule<select id=f-rule>{opt(rules)}</select></label>"
            f"<span class='muted small'>Showing <b id=f-count>{len(iss)}</b> of {len(iss)}</span></div>"
            "<div class=tablewrap><table><tr><th>Country</th><th>Rule</th><th>Severity</th><th>Year</th><th>Where</th>"
            f"<th>Message</th></tr><tbody id=issues-body>{''.join(body)}</tbody></table></div>")


def results_html(res: dict, n_files: int) -> str:
    iss, ind, log = res["issues"], res["indicators"], res["run_log"]
    ok = int((log.status == "OK").sum())
    failed = log[log.status == "FAILED"]
    countries = sorted(ind.country.unique()) if len(ind) else []
    n_err = int((iss.severity == "error").sum()) if len(iss) else 0
    n_warn = int((iss.severity == "warning").sum()) if len(iss) else 0
    clean = sum(1 for c in countries if not (len(iss) and (iss.country == c).any()))
    kpis = (f"<div class=kpis><div class=kpi><b>{ok}/{n_files}</b><span>files processed</span></div>"
            f"<div class='kpi ok'><b>{clean}</b><span>clean countries</span></div>"
            f"<div class='kpi err'><b>{n_err}</b><span>errors</span></div>"
            f"<div class='kpi warn'><b>{n_warn}</b><span>warnings</span></div></div>")
    alert = ""
    if len(failed):
        names = ", ".join(esc(str(n)) for n in failed.file)
        alert = (f"<div class='alert err'>{len(failed)} file(s) could not be read and were skipped: {names}. "
                 "Check that they are .xlsx files that use the template layout.</div>")
    ind_t = ind[ind.sex == "T"].round(1) if len(ind) else ind
    csvs = {"issues": iss.to_csv(index=False), "indicators": ind.to_csv(index=False), "run_log": log.to_csv(index=False)}
    ind_html = ind_t.to_html(index=False, border=0) if len(ind_t) else "<p class=muted>None.</p>"
    return (
        "<h2>Results</h2>" + alert + kpis
        + "<div class=card><h3>Status by country</h3>" + _country_status(iss, countries) + "</div>"
        + chart_html(ind)
        + f"<div class=card><h3>Issues ({len(iss)})</h3>{_issues_table(iss)}"
        "<div class=cta><button class='btn small' type=button data-csv=issues>Download issues (.csv)</button>"
        "<button class='btn small' type=button data-csv=indicators>Download indicators (.csv)</button>"
        "<button class='btn small' type=button data-csv=run_log>Download run log (.csv)</button></div></div>"
        f"<div class=card><details><summary>Indicators (total, both sexes)</summary><div class=tablewrap>{ind_html}</div></details>"
        f"<details><summary>Run log</summary><div class=tablewrap>{log.to_html(index=False, border=0)}</div></details></div>"
        f"<script id=csv-data type=application/json>{_safe_json(csvs)}</script>")


# ---------- page shell ----------

def page(active: str = "overview", *, samples=(), preview: str = "", results: str = "", force: bool = False) -> str:
    nav = "".join(
        f"<button type=button data-tab={k} aria-selected={'true' if k == active else 'false'}"
        f"{' class=hidden' if k == 'results' and not results else ''}>{esc(label)}</button>" for k, label in TABS)
    res_panel = results or ("<div class='card empty'><h3>No results yet</h3>"
                            "<p>Run the samples or check your own files to see results here.</p></div>")
    panels = {"overview": overview_html(), "samples": samples_html(samples, preview), "check": check_html(),
              "results": res_panel, "rules": rules_html(), "templates": templates_html(), "about": about_html()}
    sections = "".join(f"<section class=panel id=tab-{k} {'hidden' if k != active else ''}>{panels[k]}</section>"
                       for k, _ in TABS)
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>MYDT Checker</title>"
        "<script>try{var t=localStorage.getItem('mydt-theme');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);}catch(e){}</script>"
        "<style>" + CSS + "</style></head>"
        f"<body data-active={active} data-force={'1' if force else '0'}>"
        "<header class=top><div class=wrap><div class=bar><div class=logo><span class=mark>M</span>MYDT Checker"
        "<span class=pill>SYNTHETIC DEMO</span></div><nav class=tabs aria-label=Sections>" + nav + "</nav>"
        "<button class=theme id=theme-toggle type=button role=switch aria-checked=false aria-label='Dark mode' title='Switch light / dark'>"
        "<svg viewBox='0 0 24 24' aria-hidden=true><circle cx=12 cy=12 r=4 /><path d='M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'/></svg>"
        "<span class=track><span class=knob></span></span>"
        "<svg viewBox='0 0 24 24' aria-hidden=true><path d='M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'/></svg></button>"
        "</div></div></header>"
        "<main><div class=wrap>" + sections + "</div></main>"
        f"<footer><div class=wrap>Synthetic data, illustrative only. <a href='{REPO}'>Source code</a></div></footer>"
        "<script>" + JS + "</script></body></html>")
