"""Rule-based validation. Every rule has an ID so QC checklists are traceable."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config as C
from .indicators import compute_indicators

T = C.THRESHOLDS
RULES = {
    "V01": ("error", "Required metadata missing"),
    "V02": ("error", "Non-numeric entry in a data cell"),
    "V03": ("error", "Negative value"),
    "V04": ("error", "Year block entirely empty"),
    "V05": ("warning", "Age spike: value far above neighbouring ages"),
    "V06": ("warning", "Age-cohort progression outside expected band"),
    "V07": ("warning", "GER above warning threshold"),
    "V08": ("error", "GER above plausible maximum"),
    "V09": ("error", "NER above 100%"),
    "V10": ("warning", "GPI outside plausible range"),
    "V11": ("warning", "Year-on-year change in level enrolment too large"),
    "V12": ("error", "Enrolment at an age exceeds population by too much"),
}


def _issue(country, rule, where, msg, year=None):
    sev = RULES[rule][0]
    return {"country": country, "rule": rule, "severity": sev, "year": year, "where": where, "message": msg}


def validate(sub: dict) -> pd.DataFrame:
    meta, enr, pop = sub["meta"], sub["enrolment"], sub["population"]
    country = meta.get("ISO3") or meta.get("Country") or meta["file"]
    out = []
    for fld in C.META_FIELDS[:3]:
        if not meta.get(fld):
            out.append(_issue(country, "V01", f"Metadata:{fld}", f"'{fld}' is missing"))
    for _, r in sub["non_numeric"].iterrows():
        out.append(_issue(country, "V02", r["cell"], f"Value '{r['value']}' is not numeric", r["year"]))
    for df in (enr, pop):
        for _, r in df[df.value < 0].iterrows():
            out.append(_issue(country, "V03", r["cell"], f"Negative value {r['value']:.0f}", r["year"]))
    for y, g in enr.groupby("year"):
        if g.value.isna().all():
            out.append(_issue(country, "V04", f"Enrolment:{y}", f"No enrolment data for {y}", y))
    ok = enr[enr.value.notna() & (enr.value >= 0)]
    # V05 age spike
    tot = ok.groupby(["level", "year", "age"])["value"].sum().reset_index()
    for (lvl, y), g in tot.groupby(["level", "year"]):
        s = g.set_index("age")["value"].reindex(C.AGES)
        a0, a1 = C.LEVELS[lvl]
        for a in range(a0 + 1, a1):  # interior official ages only; level edges legitimately step
            nb = [s.get(a - 1), s.get(a + 1)]
            nb = [v for v in nb if pd.notna(v)]
            v = s.get(a)
            if pd.notna(v) and nb and v > 100 and v > T["spike_ratio"] * max(np.mean(nb), 1):
                out.append(_issue(country, "V05", f"Enrolment:{lvl}:age{a}",
                                  f"{lvl} age {a}: {v:,.0f} vs neighbours' mean {np.mean(nb):,.0f}", y))
    # V06 cohort progression (all levels pooled): age a in t vs age a-1 in t-1
    byage = ok.groupby(["year", "age"])["value"].sum().unstack("age")
    for y in byage.index[1:]:
        py = y - 1
        if py not in byage.index:
            continue
        for a in range(7, 17):  # skip entry age 6 and exit ages (legitimately volatile)
            prev, cur = byage.loc[py].get(a - 1), byage.loc[y].get(a)
            if pd.notna(prev) and pd.notna(cur) and prev > 100:
                ratio = cur / prev
                if not (T["cohort_lo"] <= ratio <= T["cohort_hi"]):
                    out.append(_issue(country, "V06", f"Enrolment:age{a}",
                                      f"Cohort {py}->{y}, age {a-1}->{a}: ratio {ratio:.2f}", y))
    # indicators-based rules
    ind = compute_indicators(enr, pop)
    for _, r in ind[(ind.indicator == "GER") & (ind.sex == "T")].iterrows():
        if r.value > T["ger_error"]:
            out.append(_issue(country, "V08", f"Indicators:{r.level}", f"GER {r.value:.1f}%", r.year))
        elif r.value > T["ger_warn"]:
            out.append(_issue(country, "V07", f"Indicators:{r.level}", f"GER {r.value:.1f}%", r.year))
    for _, r in ind[(ind.indicator == "NER") & (ind.sex == "T") & (ind.value > T["ner_error"])].iterrows():
        out.append(_issue(country, "V09", f"Indicators:{r.level}", f"NER {r.value:.1f}%", r.year))
    for _, r in ind[ind.indicator == "GPI_GER"].iterrows():
        if not (T["gpi_low"] <= r.value <= T["gpi_high"]):
            out.append(_issue(country, "V10", f"Indicators:{r.level}", f"GPI {r.value:.2f}", r.year))
    # V11 yoy
    lt = ok.groupby(["level", "year"])["value"].sum().reset_index().sort_values("year")
    for lvl, g in lt.groupby("level"):
        g = g.set_index("year")["value"]
        for y in g.index[1:]:
            if y - 1 in g.index and g[y - 1] > 0:
                ch = g[y] / g[y - 1] - 1
                if abs(ch) > T["yoy_warn"]:
                    out.append(_issue(country, "V11", f"Enrolment:{lvl}", f"{lvl} total changed {ch:+.0%}", y))
    # V12 enrolment vs population by age
    ea = ok.groupby(["year", "age"])["value"].sum()
    pa = pop[pop.value.notna()].groupby(["year", "age"])["value"].sum()
    j = pd.concat([ea.rename("e"), pa.rename("p")], axis=1).dropna()
    for (y, a), r in j[j.e > T["enrol_pop_ratio"] * j.p.clip(lower=1)].iterrows():
        out.append(_issue(country, "V12", f"Enrolment:age{a}", f"Enrolment {r.e:,.0f} > {T['enrol_pop_ratio']}x population {r.p:,.0f}", y))
    cols = ["country", "rule", "severity", "year", "where", "message"]
    return pd.DataFrame(out, columns=cols)


def qc_checklist(issues: pd.DataFrame, country: str) -> dict:
    """Checklist summary: one pass/fail row per rule for a country."""
    sub = issues[issues.country == country] if len(issues) else issues
    rows = {}
    for rid, (sev, desc) in RULES.items():
        n = int((sub.rule == rid).sum()) if len(sub) else 0
        rows[rid] = {"description": desc, "severity": sev, "count": n, "status": "PASS" if n == 0 else "REVIEW"}
    return rows
