"""Streamlit front-end: upload country workbooks -> issues, indicators, downloadable CSVs.
Run:  pip install -e .[app] && streamlit run app.py
"""
import tempfile
from pathlib import Path
import streamlit as st
from mydt.consolidate import consolidate

st.title("MYDT submission checker (synthetic demo)")
files = st.file_uploader("Country workbooks (.xlsx)", type="xlsx", accept_multiple_files=True)
if files:
    tmp = Path(tempfile.mkdtemp())
    paths = []
    for f in files:
        p = tmp / f.name; p.write_bytes(f.getbuffer()); paths.append(p)
    res = consolidate(paths, tmp / "out")
    st.metric("Files processed", int((res["run_log"].status == "OK").sum()))
    st.subheader("Issues"); iss = res["issues"]
    sev = st.multiselect("Severity", ["error", "warning"], default=["error", "warning"])
    st.dataframe(iss[iss.severity.isin(sev)] if len(iss) else iss)
    st.subheader("Indicators (total)")
    st.dataframe(res["indicators"].query("sex == 'T'"))
    for k, df in res.items():
        st.download_button(f"Download {k}.csv", df.to_csv(index=False), f"{k}.csv")
