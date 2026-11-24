"""Per-country indicator review reports (HTML, self-contained) + QC checklist."""
from __future__ import annotations
import base64, io
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import Template
from .validate import qc_checklist

TPL = Template("""<!doctype html><meta charset=utf-8><title>{{c}} review</title>
<style>body{font:14px system-ui;max-width:900px;margin:2rem auto;color:#222}
table{border-collapse:collapse;width:100%;margin:.6rem 0}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}
th{background:#f0f0f0}.error{color:#b00020;font-weight:600}.warning{color:#9a6700}.PASS{color:#1a7f37}.REVIEW{color:#b00020}
small{color:#666}</style>
<h1>Indicator review: {{c}}</h1><small>SYNTHETIC demo data - illustrative format only.</small>
<h2>Indicators (total, %)</h2>{{ind|safe}}<img src="data:image/png;base64,{{img}}" style="max-width:100%">
<h2>Validation issues ({{n}})</h2>{{iss|safe}}
<h2>QC checklist</h2><table><tr><th>Rule</th><th>Check</th><th>Severity</th><th>Hits</th><th>Status</th></tr>
{% for k,v in chk.items() %}<tr><td>{{k}}</td><td>{{v.description}}</td><td>{{v.severity}}</td><td>{{v.count}}</td><td class="{{v.status}}">{{v.status}}</td></tr>{% endfor %}</table>""")


def country_report(country: str, ind: pd.DataFrame, issues: pd.DataFrame, outdir: Path) -> Path:
    d = ind[(ind.country == country) & (ind.sex == "T") & (ind.indicator.isin(["GER", "NER"]))]
    piv = d.pivot_table(index=["level", "indicator"], columns="year", values="value").round(1)
    fig, ax = plt.subplots(figsize=(7, 3))
    for (lvl, nm), row in piv.iterrows():
        if nm == "GER":
            ax.plot(row.index, row.values, marker="o", label=f"{lvl} GER")
    ax.set_ylabel("GER %"); ax.set_xticks(sorted(d.year.unique())); ax.legend(fontsize=8); ax.grid(alpha=.3)
    buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format="png", dpi=110); plt.close(fig)
    iss = issues[issues.country == country].copy()
    iss_html = ("<p>No issues.</p>" if iss.empty else
                iss.drop(columns="country").assign(severity=lambda x: x.severity.map(lambda s: f'<span class="{s}">{s}</span>'))
                .to_html(index=False, escape=False))
    html = TPL.render(c=country, ind=piv.to_html(), img=base64.b64encode(buf.getvalue()).decode(),
                      iss=iss_html, n=len(iss), chk=qc_checklist(issues, country))
    p = Path(outdir) / f"review_{country}.html"
    p.write_text(html, encoding="utf-8")
    return p


def all_reports(res: dict, outdir: str | Path) -> list[Path]:
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    return [country_report(c, res["indicators"], res["issues"], outdir) for c in sorted(res["indicators"].country.unique())]
