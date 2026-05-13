"""American Exit Index — scoring.

Reads raw_data.json (produced by scrape.py) and countries.yaml, emits
data/latest.json plus a dated snapshot under data/history/.

Three-axis composite, weights below. Each axis is independently 0-100 so
weekly delta posts can call out movers on a single axis ("Spain's
purchasing-power score dropped 8 points this week because the euro
strengthened against the dollar").
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).parent
DATA = ROOT / "data"
HISTORY = DATA / "history"

# Composite weights — sum to 1.0.
W_VISA = 0.40
W_DOLLAR = 0.35
W_SPEED = 0.25

# US baseline for purchasing-power normalization. Numbeo's cost-of-living
# index is itself anchored to NYC=100; we re-anchor to USA-nation=100 by
# scaling against the national index in raw_data.json.
US_COL_BASELINE = 68.8   # USA nation-level cost-of-living index, Numbeo May 2026
US_RENT_BASELINE = 40.7  # USA nation-level rent index, used as cross-check


def score_visa(country: dict[str, Any]) -> int:
    """Visa accessibility, 0-100.

    Three components:
      - has US-friendly residency pathway: binary, 40pts
      - processing time inverse: 30pts max
      - financial requirement reasonableness: 30pts max

    Pathway points are 40 because countries without a viable US-citizen
    residency path (e.g. somewhere requiring marriage or refugee status)
    should sit near zero on this axis regardless of the other components.
    """
    o = country.get("overrides", {})

    pathway_pts = 40 if country.get("primary_visa") else 0

    days = o.get("visa_processing_days", 365)
    if days <= 30:
        time_pts = 30
    elif days <= 60:
        time_pts = 25
    elif days <= 90:
        time_pts = 20
    elif days <= 180:
        time_pts = 12
    elif days <= 365:
        time_pts = 5
    else:
        time_pts = 0

    money = o.get("visa_financial_requirement_usd", 50000)
    if money == 0:
        fin_pts = 25  # points-tested, not financial — solid but not perfect
    elif money <= 10000:
        fin_pts = 30
    elif money <= 25000:
        fin_pts = 22
    elif money <= 40000:
        fin_pts = 15
    elif money <= 60000:
        fin_pts = 8
    elif money <= 100000:
        fin_pts = 3
    else:
        fin_pts = 0

    return min(100, pathway_pts + time_pts + fin_pts)


def score_dollar(country: dict[str, Any], raw: dict[str, Any]) -> int:
    """Dollar purchasing power, 0-100.

    Inverse of local cost-of-living index, anchored such that USA-baseline =
    50. A country at half USA's COL scores ~83; double USA scores ~17.
    """
    col = raw.get("numbeo", {}).get("cost_of_living_index")
    if col is None:
        # Fall back to manual override if scrape failed.
        col = country.get("overrides", {}).get("cost_of_living_index_fallback")
    if col is None:
        return 50  # honest "we don't know" middle

    # ratio < 1 means cheaper than USA → higher score
    ratio = col / US_COL_BASELINE
    # Map ratio 0.3 → 100, 0.5 → 83, 1.0 → 50, 1.5 → 17, 2.0 → 0
    score = round(100 - ((ratio - 0.3) / 1.7) * 100)
    return max(0, min(100, score))


def score_speed(country: dict[str, Any]) -> int:
    """Speed to permanent residency, 0-100.

    Permanent residency, NOT citizenship — citizenship adds 2-5 years on
    top in most countries and isn't what most people researching emigration
    actually optimize for in year one.
    """
    months = country.get("overrides", {}).get("months_to_permanent_residency", 120)
    if months <= 12:
        return 100
    if months <= 24:
        return 80
    if months <= 36:
        return 60
    if months <= 60:
        return 40
    if months <= 120:
        return 20
    return 0


def tier(composite: int) -> str:
    if composite >= 80:
        return "Easy mode"
    if composite >= 60:
        return "Workable"
    if composite >= 40:
        return "Doable with paperwork"
    if composite >= 20:
        return "Real commitment required"
    return "Lottery or marry-in"


def score_country(country: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    visa = score_visa(country)
    dollar = score_dollar(country, raw)
    speed = score_speed(country)
    composite = round(visa * W_VISA + dollar * W_DOLLAR + speed * W_SPEED)
    return {
        "slug": country["slug"],
        "name": country["name"],
        "region": country["region"],
        "primary_visa": country.get("primary_visa"),
        "scores": {
            "visa_accessibility": visa,
            "dollar_purchasing_power": dollar,
            "speed_to_residency": speed,
            "composite": composite,
        },
        "tier": tier(composite),
        "data": {
            "processing_days": country.get("overrides", {}).get("visa_processing_days"),
            "financial_requirement_usd": country.get("overrides", {}).get(
                "visa_financial_requirement_usd"
            ),
            "months_to_permanent_residency": country.get("overrides", {}).get(
                "months_to_permanent_residency"
            ),
            "cost_of_living_index": raw.get("numbeo", {}).get("cost_of_living_index"),
            "cost_of_living_vs_usa": (
                round(raw["numbeo"]["cost_of_living_index"] / US_COL_BASELINE, 2)
                if raw.get("numbeo", {}).get("cost_of_living_index")
                else None
            ),
        },
    }


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: pathlib.Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    config = load_yaml(ROOT / "countries.yaml")
    raw_all = load_json(DATA / "raw_data.json", default={})

    today = dt.date.today().isoformat()

    rankings = []
    for country in config["countries"]:
        raw = raw_all.get(country["slug"], {})
        rankings.append(score_country(country, raw))

    rankings.sort(key=lambda c: c["scores"]["composite"], reverse=True)
    for i, c in enumerate(rankings, 1):
        c["rank"] = i

    # Delta vs yesterday — for "biggest mover" weekly post copy.
    prev_path = HISTORY / f"{(dt.date.today() - dt.timedelta(days=1)).isoformat()}.json"
    prev = load_json(prev_path, default={"rankings": []})
    prev_ranks = {c["slug"]: c["rank"] for c in prev.get("rankings", [])}
    prev_composites = {c["slug"]: c["scores"]["composite"] for c in prev.get("rankings", [])}
    for c in rankings:
        c["delta"] = {
            "rank_change": (prev_ranks.get(c["slug"], c["rank"]) - c["rank"])
            if c["slug"] in prev_ranks
            else 0,
            "composite_change": c["scores"]["composite"]
            - prev_composites.get(c["slug"], c["scores"]["composite"]),
        }

    output = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "date": today,
        "weights": {"visa": W_VISA, "dollar": W_DOLLAR, "speed": W_SPEED},
        "us_baseline_col_index": US_COL_BASELINE,
        "rankings": rankings,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    HISTORY.mkdir(parents=True, exist_ok=True)
    with (DATA / "latest.json").open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    with (HISTORY / f"{today}.json").open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(rankings)} country rankings to data/latest.json")
    print("Top 5:")
    for c in rankings[:5]:
        print(f"  {c['rank']}. {c['name']:<20} {c['scores']['composite']:>3}  [{c['tier']}]")


if __name__ == "__main__":
    main()
