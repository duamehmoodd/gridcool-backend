#  GridCool

**Predicting power grid failure before it happens — using real weather data and a real electrical engineering simulation.**

> We built a system that predicts which parts of the electricity grid are at risk of failing during extreme heat, using real live weather data and a real physics simulation — not guesses.

---

## The Problem

When it gets extremely hot, everyone runs their AC at once. All that extra electricity has to flow through **transformers** — the devices that step power down from big transmission lines into something safe for homes. Push too much current through a transformer and it can overheat, get damaged, or knock out power to an entire neighborhood. This happens during real heat waves.

**The question GridCool answers:** *Given how hot it is right now (or was on a specific day), which transformers are about to be overloaded — and by how much?*

---

## What's Inside

GridCool is a full working system with two halves:

| | |
|---|---|
|  **Backend** | Python. Fetches real weather data, runs an actual electrical engineering simulation, and identifies at-risk transformers. |
|  **Frontend** | React. A live "mission control" dashboard with maps, charts, and alerts. |

It currently covers **5 real U.S. cities**, each with its own climate and grid operator:

- Phoenix, AZ
- Dallas, TX
- Las Vegas, NV
- Atlanta, GA
- Sacramento, CA

---

## How It Works — The Pipeline

Each stage below feeds the next, like an assembly line:

1. **Live heat data (FortyGuard)** — pulls the real-time heat index (temperature + humidity) for each city.
2. **Demand modeling** — converts heat index into a demand multiplier (e.g. `1.5x` = 50% more electricity use than a mild day), calibrated on real historical data.
3. **Electrical simulation (OpenDSS)** — runs that demand through a real, industry-standard grid model (1,305 transformers, thousands of homes) using OpenDSS, the same class of software real utility engineers use. Output: each transformer's load as a % of rated capacity.
4. **Historical backup (ResStock)** — a real U.S. government dataset of hourly AC usage from a genuinely hot day (July 25, 2018), used both as a reliable fallback and to calibrate the live demand model.
5. **Decision agent** — a deliberately rule-based (non-ML, fully explainable) system that turns raw numbers into readable alerts, e.g.:
   > *"Transformer t226192762b reached 145% of rated capacity — critical risk of thermal damage or localized outage if this heat pattern continues."*
6. **Extra real-world context** — pulls in official NOAA Extreme Heat Warnings and EIA regional demand data.
7. **Auto re-evaluation** — re-runs the entire pipeline every few minutes for all 5 cities automatically, logging every check to a full audit trail.
8. **Graceful fallback** — if the live weather API is down, the system falls back to real historical data instead of crashing or showing an error.

---

## Honesty Note

The grid model (1,305 transformers) is a **public, standard test model** used by engineers everywhere — it is *not* the actual wiring of Phoenix, Dallas, or any specific city, since real utility wiring diagrams aren't public. Think of it as: *a realistic, industry-standard grid, stressed by that city's real weather.* This is stated openly throughout the project.

---

## The Dashboard

A dark, mission-control-style interface with 5 pages:

- **Dashboard** — map of all 5 cities, live at-risk transformer list, click-through detail panel
- **Heat Intel** — live temperature, humidity, air quality, and heat map overlay per city
- **Risk Timeline** — hour-by-hour interactive chart of a transformer's stress level
- **Grid Demand** — regional electricity demand plotted against transformer stress
- **Alerts & Audit** — real NOAA warnings plus the full automated check history

---

## Repo Structure

```
gridcool-backend/
├── data/                        # Grid model & datasets
├── src/                         # Core backend pipeline
├── gcool/                       # React frontend ("the face")
├── temperature-api-quickstart/  # FortyGuard API integration
├── test_heatmap_dates.py
├── requirements.txt
├── .env.example
└── README.md
```


## One-Line Summary

> We built a system that uses real live weather data and a real electrical engineering simulation to predict, city by city, exactly which power grid transformers are about to overload during extreme heat — and it keeps checking itself automatically, forever, with a full audit trail, even if the weather service goes down.

---

## License

MIT — see [LICENSE](./LICENSE)
