"""American Exit Index — data collection.

Single-page fetch of Numbeo's rankings_by_country table. ONE request gets
all 155+ countries; we filter down to the 20 in countries.yaml by exact
country-name match. Old per-country approach used 20 requests and hit a
URL pattern Numbeo doesn't actually support (country=PT vs country=Portugal).

Sources today:
  - Numbeo rankings_by_country.jsp (HTML scrape, attribution-required)
  - exchangerate.host (free JSON, USD reference rates)

Sources to add (TODO):
  - State Dept consulate appointment wait times (Architect)
  - Wikipedia residency-permit summaries (Architect)
  - r/AmerExit weekly question volume per country (Scout)
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
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

NUMBEO_RANKINGS_URL = "https://www.numbeo.com/cost-of-living/rankings_by_country.jsp"
FX_URL = "https://api.exchangerate.host/latest?base=USD"

# Numbeo table row: country name, then six index columns in fixed order.
# Tolerant whitespace; relies on the cityOrCountryInIndicesTable class for
# the country cell, which has been stable since at least 2019.
NUMBEO_ROW_RE = re.compile(
    r'<td\s+class="cityOrCountryInIndicesTable">([^<]+)</td>\s*'
    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*'      # cost of living index
    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*'      # rent index
    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*'      # cost of living + rent index
    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*'      # groceries index
    r'<td[^>]*>\s*([\d.]+)\s*</td>\s*'      # restaurant price index
    r'<td[^>]*>\s*([\d.]+)\s*</td>',        # local purchasing power index
    re.IGNORECASE,
)


def fetch_numbeo_table() -> dict[str, dict[str, float]]:
    """Fetch the country rankings page once. Returns {country_name: indices}."""
    resp = requests.get(NUMBEO_RANKINGS_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    rows = NUMBEO_ROW_RE.findall(resp.text)
    if not rows:
        raise RuntimeError(
            "numbeo: zero rows parsed from rankings table — selector likely "
            "broke, inspect rankings_by_country.jsp markup"
        )
    return {
        name.strip(): {
            "cost_of_living_index": float(col),
            "rent_index": float(rent),
            "cost_of_living_plus_rent_index": float(col_rent),
            "groceries_index": float(grocer),
            "restaurant_price_index": float(rest),
            "local_purchasing_power_index": float(lpp),
        }
        for name, col, rent, col_rent, grocer, rest, lpp in rows
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

    print("Fetching Numbeo country rankings (single request)...")
    try:
        numbeo_table = fetch_numbeo_table()
        numbeo_error = None
        print(f"  parsed {len(numbeo_table)} countries from Numbeo")
    except Exception as e:
        numbeo_table = {}
        numbeo_error = str(e)
        print(f"  ERROR: {e}")

    print("Fetching FX rates...")
    fx = fetch_fx()

    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
    result: dict[str, Any] = {
        "_meta": {
            "fetched_at": fetched_at,
            "numbeo_error": numbeo_error,
            "fx": fx,
        }
    }

    matched = 0
    for country in config["countries"]:
        slug = country["slug"]
        numbeo_name = country.get("numbeo_country_name")
        indices = numbeo_table.get(numbeo_name) if numbeo_name else None
        if indices is not None:
            matched += 1
            result[slug] = {
                "numbeo": {
                    **indices,
                    "fetched_at": fetched_at,
                    "source": "numbeo.com/cost-of-living/rankings_by_country.jsp",
                    "attribution_required": True,
                }
            }
        else:
            result[slug] = {
                "numbeo": {
                    "error": (
                        f"country name '{numbeo_name}' not found in rankings table"
                        if numbeo_name
                        else "no numbeo_country_name set in countries.yaml"
                    )
                }
            }

    with (DATA / "raw_data.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nWrote raw data: {matched}/{len(config['countries'])} countries matched.")
    if matched < len(config["countries"]):
        unmatched = [c["slug"] for c in config["countries"] if "error" in result[c["slug"]]["numbeo"]]
        print("  unmatched:")
        for s in unmatched:
            print(f"    - {s}: {result[s]['numbeo']['error']}")


if __name__ == "__main__":
    main()
