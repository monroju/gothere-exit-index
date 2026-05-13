# American Exit Index

Daily-updated ranking of the top 20 destinations for Americans leaving the US.
Three-axis composite score: visa accessibility, dollar purchasing power,
speed-to-residency. Designed as a citable resource for journalists writing
"Americans moving abroad" coverage — every citation is a backlink to GoThere.

## Pipeline

```
countries.yaml ──► scrape.py ──► raw_data.json ──► score.py ──► data/latest.json
                       │                                              │
                       └─► (Numbeo, State Dept, Wikipedia,             ├─► site/ static dashboard
                            consulate pages, FX feeds)                 ├─► data/history/YYYY-MM-DD.json (daily snapshot)
                                                                       └─► newsletter weekly delta (top 3 movers)
```

## Run

```bash
cd ~/Projects/GoThere/exit_index
python scrape.py                  # refresh raw_data.json
python score.py                   # produce data/latest.json + snapshot
git add data/ && git commit -m "exit_index: $(date +%F)" && git push
```

Daily cron on Mac Mini handles all three in one shot via `cron.sh`.

## Scoring formula

Each axis 0-100, composite = weighted average:

| Axis | Weight | Components |
|---|---|---|
| Visa accessibility | 40% | US-friendly residency pathway exists (40pts) + processing time inverse (30pts) + financial requirement reasonableness (30pts) |
| Dollar purchasing power | 35% | Numbeo cost-of-living index relative to US baseline (USA=100). Lower local index = higher score, capped at 100. |
| Speed to residency | 25% | Months to permanent residency: <12mo=100, 12-24=80, 24-36=60, 36-60=40, 60-120=20, >120=0 |

Composite tiers:
- 80-100: **Easy mode** (Portugal, Mexico, Panama tier)
- 60-79: **Workable** (Spain, Costa Rica, Greece tier)
- 40-59: **Doable with paperwork** (Germany, France, Ireland tier)
- 20-39: **Real commitment required** (UK, NL tier)
- 0-19: **Lottery or marry-in** (Australia tier for most paths)

## Data sources (free)

- **Numbeo** — cost-of-living index, free with attribution
- **State Dept travel.state.gov** — visa categories per country (HTML scrape)
- **Wikipedia** — country residency requirement summaries (stable, citable)
- **Consulate appointment pages** — wait time signals (where public)
- **OECD / Big Mac index** — purchasing power cross-check
- **exchangerate.host** — free FX feed, daily

Each data point in `raw_data.json` carries `source`, `fetched_at`, and a
confidence tier. Manual overrides live in `countries.yaml` under each
country's `overrides:` block.

## Hosting

Live at https://monroju.github.io/gothere-exit-index/ — GitHub Pages serves
the repo root. `index.html`, `style.css`, `script.js`, and `data/` are all
at the repo root for a zero-build, zero-config deploy. Daily commit by the
Mac Mini cron → automatic deploy.

To re-deploy locally for testing: just open `index.html` in a browser, the
JS reads `./data/latest.json` from the same directory.

## Mac Mini cron setup (one-time, run from the Mac Mini terminal)

```bash
# 1. Clone the repo
cd ~/projects && git clone git@github.com:monroju/gothere-exit-index.git
cd gothere-exit-index
pip3 install -r requirements.txt

# 2. Verify it runs
python3 scrape.py && python3 score.py

# 3. Wire the cron (06:00 Madrid daily)
(crontab -l 2>/dev/null; echo '0 6 * * * cd ~/projects/gothere-exit-index && bash cron.sh >> cron.log 2>&1') | crontab -

# 4. (Optional) wire Telegram alerts: edit cron.sh env or export
# TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in ~/.bashrc
```

## Press positioning

The Index is published as **GoThere's American Exit Index**. Public, free,
no signup wall. Every chart screenshot ends with the GoThere URL in the
corner. The press kit hook is "1,200+ data points, daily updated, the only
free public tracker of US emigration friction."

Journalists writing the "X% of Americans say they'd leave" story need a
data anchor. We are that anchor.
