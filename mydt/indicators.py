"""Independent Python implementation of the indicator methodology (mirrors workbook formulas)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config as C


def compute_indicators(enrol: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    """GER, NER (%) by level/year/sex (M, F, T) and GPI of GER. Returns long table."""
    def with_total(df):
        t = df.groupby(["level", "age", "year"], dropna=False)["value"].sum(min_count=1).reset_index()
        t["sex"] = "T"
        return pd.concat([df[["level", "age", "year", "sex", "value"]], t], ignore_index=True)

    e = with_total(enrol)
    p = with_total(pop.assign(level="All"))
    out = []
    for lvl, (a0, a1) in C.LEVELS.items():
        pp = p[p.age.between(a0, a1)].groupby(["year", "sex"])["value"].sum(min_count=1)
        el = e[e.level == lvl]
        ger = el.groupby(["year", "sex"])["value"].sum(min_count=1)
        ner = el[el.age.between(a0, a1)].groupby(["year", "sex"])["value"].sum(min_count=1)
        for name, num in (("GER", ger), ("NER", ner)):
            s = (100 * num / pp.replace(0, np.nan)).dropna().reset_index(name="value")
            s["level"], s["indicator"] = lvl, name
            out.append(s)
    res = pd.concat(out, ignore_index=True)
    g = res[res.indicator == "GER"].pivot_table(index=["level", "year"], columns="sex", values="value")
    if {"M", "F"} <= set(g.columns):
        gpi = (g["F"] / g["M"]).dropna().reset_index(name="value")
        gpi["sex"], gpi["indicator"] = "T", "GPI_GER"
        res = pd.concat([res, gpi], ignore_index=True)
    return res[["level", "indicator", "year", "sex", "value"]]
