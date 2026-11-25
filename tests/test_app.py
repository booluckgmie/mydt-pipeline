import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.index import app, chart_html  # noqa: E402


def _chart_data(html: str) -> dict:
    m = re.search(r'<script id=chart-data type=application/json>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_sample_run_embeds_chart_data_for_every_country():
    html = app.test_client().post("/", data={"action": "run_sample"}).data.decode()
    d = _chart_data(html)
    assert len(d) == 10
    assert {r["i"] for r in d["XC01"]} == {"GER", "NER"}
    assert {r["l"] for r in d["XC01"]} == {"ISCED1", "ISCED2", "ISCED3"}
    assert "c-country" in html


def test_chart_data_keeps_country_codes_inert_in_script_tag():
    ind = pd.DataFrame({"level": ["ISCED1"], "indicator": ["GER"], "year": [2026], "sex": ["T"],
                        "value": [90.0], "country": ["</script><b>x"]})
    html = chart_html(ind)
    assert "</script><b>" not in html.split("application/json>")[1].split("</script>")[0]
    assert _chart_data(html)["</script><b>x"][0]["v"] == 90.0


def test_chart_omitted_when_no_indicators():
    assert chart_html(pd.DataFrame()) == ""
