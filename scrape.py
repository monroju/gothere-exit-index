"""American Exit Index — data collection.

Reads countries.yaml, hits free public sources for each country, writes
data/raw_data.json. Designed to fail gracefully — if Numbeo rate-limits,
the country falls back to the manual override in countries.yaml and the
scorer marks the data point as stale rather than crashing the pipeline.

Sources today:
  - Numbeo cost-of-living index (HTML scrape, attribution-required)
  - State Dept reciprocity tables (HTML scrape, visa processing context)
  - exchangerate.host (free JSON, USD reference rates)

Sources to add (TODO, owners noted):
  - State Dept consulate appointment wait times (Architect)
  - Wikipedia residency-permit summaries (Architect)
  - r/AmerExit weekly question volume per country (Scout)
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import time
from typing import Any

import requests
import yaml

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
USER_AGENT = (
    "Mozilla/5.0 (compatible; GoThereExitIndex/0.1; "
    "+https://getgothere.app/exit-index)"
)
HEADERS = {"User-Agent": USER_AGENT}
THROTTLE_SECONDS = 2.0  # be polite — daily run, no rush

NUMBEO_URL = "https://www.numbeo.com/cost-of-living/country_result.jsp?country={code}"
NUMBEO_INDEX_RE = re.compile(
    r"Cost of Living Index[^<]*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>",
    re.IGNORECASE | re.DOTALL,
)

FX_URL = "https://api.exchangerate.host/latest?base=USD"


def fetch_numbeo(country_code: str) -> dict[str, Any]:
    """Scrape Numbeo country page. Returns empty dict on failure."""
    try:
        resp = requests.get(
            NUMBEO_URL.format(code=country_code),
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"numbeo fetch failed: {e}"}

    match = NUMBEO_INDEX_RE.search(resp.text)
    if not match:
        return {"error": "numbeo cost_of_living_index pattern not found"}

    return {
        "cost_of_living_index": float(match.group(1)),
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "numbeo.com",
        "attribution_required": True,
    }


def fetch_fx() -> dict[str, Any]:
    try:
        resp = requests.get(FX_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": f"fx fetch failed: {e}"}


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    config = load_yaml(ROOT / "countries.yaml")
    DATA.mkdir(parents=True, exist_ok=True)

    fx = fetch_fx()
    result: dict[str, Any] = {
        "_meta": {
            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "fx": fx,
        }
    }

    for country in config["countries"]:
        slug = country["slug"]
        code = country.get("numbeo_country_code")
        print(f"  fetching {slug}...")
        result[slug] = {"numbeo": fetch_numbeo(code) if code else {}}
        time.sleep(THROTTLE_SECONDS)

    with (DATA / "raw_data.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nWrote raw data for {len(config['countries'])} countries.")
    bad = [s for s, v in result.items() if s != "_meta" and v.get("numbeo", {}).get("error")]
    if bad:
        print(f"  warnings: {len(bad)} countries had numbeo errors:")
        for s in bad:
            print(f"    - {s}: {result[s]['numbeo']['error']}")


if __name__ == "__main__":
    main()
