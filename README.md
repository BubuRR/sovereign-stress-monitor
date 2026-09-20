# Sovereign Stress Monitor (SSM) v30.5.2

**Hybrid early-warning radar for economic and structural stress**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **What this is:** an open research monitor that shows **official/market data beside structural priors and five ground-level proxies**, then highlights the **gap** when the visible layer looks calm and the land/structural layer does not.
>
> **What this is not:** a classified intel system, a calibrated default-probability model, or a replacement for national statistics / institutional risk platforms.
>
> **Not investment advice.**

### 30-second picture

| Layer | Meaning |
|-------|---------|
| **G — Official** | Listed-market regime (SMH, DBB, USDT flows) |
| **S — Structural** | Fiscal / demographic / buffer priors (versioned, do not self-erase) |
| **Ground ×5** | conflict · food · migration · mortality · physical |
| **GAP + alarms** | When alternative intensity exceeds official calm |

```bash
pip install -r requirements.txt
pytest -q
python ssm_core.py          # expect: [SSM FEED] SMH: LIVE ...
streamlit run interface/app.py --server.port 8501
```

---

## 1. Problem statement

Institutional and media narratives often lean on **what is easy to measure**: listed markets, formal payrolls, tax cash registers, quarterly filings. Large parts of real activity—cash, informal labor, wartime disruption, demographic drain, parallel FX—leave weaker or delayed traces in those feeds.

When the visible slice looks stable while physical and social stress accumulates, conventional dashboards can stay green. Operators on the ground experience the opposite.

SSM does not claim to “see the whole informal economy.” It claims something narrower and testable:

1. **Always show the official/market layer and the alternative layer side by side.**
2. **Treat chronic structural load as first-class**, not something that should be washed out by a calm equity tape.
3. **Raise named alarms when the gap is large**, instead of collapsing everything into a single vanity percentage.

---

## 2. Architecture (three layers + comparison)

```text
┌─────────────────────────────────────────────────────────────┐
│  DISPLAY R  ≈  max(G, S)  +  small lift from ground excess  │
├──────────────────┬──────────────────┬───────────────────────┤
│  OFFICIAL  G     │  STRUCTURAL  S   │  GROUND  (5 signals)  │
│  market regime   │  fiscal/demo/    │  conflict · food ·    │
│  SMH / DBB /     │  buffer priors   │  migration · mortality│
│  USDT flows      │  (versioned)     │  · physical           │
├──────────────────┴──────────────────┴───────────────────────┤
│  GAP = max(S, GROUND) − G                                   │
│  ALARMS = named codes when official calm ≠ land/structural  │
└─────────────────────────────────────────────────────────────┘
```

| Layer | Symbol | Role | Updates |
|-------|--------|------|---------|
| Official / market | **G** ∈ [0,1] | Risk-on/off and listed-market stress from public (or paid) feeds | Every cycle |
| Structural | **S** ∈ [0,1] | Declared chronic load from country priors | Only when you change config (does not “normalize” with markets) |
| Ground | **5 scores → index** | Proxies for conflict, food, migration, mortality, physical disruption | Priors always; live APIs when keys exist |
| Gap | **GAP** | How much alternative intensity exceeds official regime | Every cycle |
| Alarms | **codes** | Machine-readable sirens, not a single opaque score | Every cycle |

### Structural intensity (transparent formula)

\[
S = 1 - \exp\bigl(-\lambda (\alpha F + \beta D + \gamma B)\bigr)
\]

- \(F\) — fiscal pressure prior  
- \(D\) — demographic / labor squeeze prior  
- \(B\) — buffer / “garage” gap prior  
- \(\alpha,\beta,\gamma\) — weights in `STRUCTURAL_MIX` (sum normalized to 1)  
- \(\lambda\) — `STRUCTURAL_LAMBDA` in config  

**S is not P(default).** It is a bounded, monotone transform of declared priors so auditors can see every input.

### Display rule (default)

\[
R = \max(G, S) + 0.15 \cdot \max(\mathrm{GROUND} - \max(G,S),\ 0)
\]

Optional `COMPOSITE_MODE: soft_or` uses \(G + S - G\cdot S\) before the ground lift.  
**Intent:** a calm global tech/materials tape cannot force a “green” display while structural or ground load remains extreme.

### Gap and alarms

```text
GAP = max(S, GROUND_INDEX) − G
```

Example alarm codes:

| Code | Meaning |
|------|---------|
| `SILENT_STRESS` | Structural load elevated while market regime is subdued |
| `GROUND_DIVERGENCE` | Ground index hot while official regime is not |
| `NARRATIVE_LAG` | Gap above configured threshold |
| `CHRONIC_CRITICAL` | Structural intensity above chronic critical floor |
| `HUMANITARIAN_STRESS` | Ground index at humanitarian-level threshold |
| `LOW_DIGITAL_COVERAGE_WARNING` | Config assumes incomplete digital coverage and alternative layer is hot |

---

## 3. Five ground signals (“земли”)

| Signal | Intent | Free path | Paid / richer path |
|--------|--------|-----------|--------------------|
| **conflict** | Violence / war intensity | Country prior | ACLED credentials in vault |
| **food** | Food price / access stress | Prior + public macro probe | Extend with FAO/national series |
| **migration** | Displacement / labor flight | Country prior | Wire UNHCR / national APIs when you have access |
| **mortality** | Health / excess death stress | Country prior | Research mortality feeds |
| **physical** | Disasters / infrastructure shock | Prior + GDACS-style probe | Commercial hazard APIs |

Each signal returns `{score, source, quality}` with `quality ∈ {prior_only, public_api, paid_api, hybrid}`.  
That makes **data pedigree visible**—critical when half the value of the product is knowing *what you are not seeing live*.

---

## 4. Repository layout

```text
ssm_core.py              # CLI entry → asyncio.run(run_all())
core/
  quant_engine.py        # G, S, ground blend, gap, alarms, run_all
  ground_feeds.py        # five ground connectors
  database.py            # SQLite at repo root (WAL)
api/main.py              # FastAPI: health, composite passport, history
interface/app.py         # Streamlit: G vs Ground, GAP, per-country signals
config/parameters.json    # priors, weights, thresholds, API_KEYS_VAULT
tests/test_smoke.py
Dockerfile / docker-compose.yml
.github/workflows/main.yml
```

Database file: `ssm_intelligence.db` (project root, not under `core/`).  
Artifact: `ssm_unified_report.json` after each successful cycle.

---

## 5. Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
python ssm_core.py
```

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
streamlit run interface/app.py --server.port 8501
```

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Health + layer list |
| `GET /api/v1/radar/composite` | Full hybrid passport |
| `GET /api/v1/risk/{CC}` | SQLite history for country code |

### Optional paid feeds

Edit `config/parameters.json` → `ENTERPRISE_DATA_GATEWAYS.API_KEYS_VAULT`:

- `POLYGON_IO_KEY` — equity/macro bars  
- `QUICKNODE_TRON_KEY` — denser chain access  
- `ACLED_EMAIL` / `ACLED_KEY` — conflict events  
- `FRED_API_KEY` — reserved for macro extensions  

If a value still contains `PASTE`, SSM stays on the free path. **No key is required to run.**

---

## 6. What a cycle prints (example semantics)

```text
[SSM] UA: R=61.5% ELEVATED G=59.7 S=61.1 Ground=63.8 Gap=4.0
      alarms=[LOW_DIGITAL_COVERAGE_WARNING]
```

Read as:

- **G** — listed-market composite is elevated but not extreme.  
- **S** — structural priors remain high (fiscal/demographic/buffer).  
- **Ground** — conflict/migration-class load dominates the ground index.  
- **Gap / alarms** — coverage and divergence flags fire even when G is not in crisis territory.

That is the intended behavior: **not silent just because SMH is firm.**

---

## 7. Strengths

| Strength | Why it matters to an engineering lead |
|----------|----------------------------------------|
| **Explicit dual (triple) accounting** | Official vs structural vs ground are separate objects in the schema, not a blended mystery meat score |
| **Chronic load cannot self-erase** | S is config-versioned; it does not adapt away a multi-year squeeze the way rolling z-scores do |
| **Gap is a first-class output** | The product’s thesis is measurable: divergence, not vibes |
| **Named alarms** | Operable in logs, CI, and on-call style reviews |
| **Degraded-mode design** | Runs without vendor keys; upgrades quality when keys appear |
| **Auditable structural formula** | Closed form, bounded, monotone in priors |
| **Anti-drift for market breaks** | Change-point (ruptures PELT or fallback) freezes pre-break baseline |
| **Thin, readable stack** | FastAPI + Streamlit + SQLite; one process cycle is understandable in one sitting |
| **Tests on the critical path** | Smoke tests for syntax, S, gap logic, DB round-trip |

---

## 8. Limitations and honest risks

| Limitation | Implication |
|------------|-------------|
| **Ground live coverage is incomplete** | Without ACLED/FAO/displacement APIs, several signals stay on priors—sensitive to author judgment |
| **Priors can encode bias** | High UA conflict prior is intentional; it is still an expert assumption, not a measurement |
| **G uses broad US-listed ETFs (SMH/DBB)** | Useful global regime proxy; poor as a pure local GDP nowcast |
| **USDT TRC-20 is a narrow capital-flight slice** | Informative when it moves; easy to over-interpret |
| **No claim of shadow-GDP estimation** | Digital-coverage parameter is a *hypothesis weight*, not an empirical census |
| **Alarms are rule-based** | Transparent, but not trained on a labeled crisis dataset |
| **Public Yahoo / TronGrid / probe APIs are brittle** | Production deployments should prefer paid, contracted feeds |
| **Not a portfolio or compliance system** | No holdings, no mandate rules, no SOC2 story |

If you need a single sentence for stakeholders:

> SSM is a **hybrid divergence radar**, not a replacement for national statistics or institutional risk platforms.

---

## 9. Design principles (non-negotiables)

1. **Never show only the comfortable layer.** Official and alternative outputs ship together.  
2. **Label pedigree.** `prior_only` vs `paid_api` is part of the product.  
3. **No synthetic “AI probability of crash” without labels.** ML stays out until there is a real event study.  
4. **Prefer a loud, named alarm over a quiet, precise-looking wrong number.**  
5. **Config is policy.** Changing fiscal/demographic priors is a deliberate act, not a silent online update.

---

## 10. Roadmap (engineering order)

1. **Stabilize free probes** — pin endpoints, cache, offline fixtures for CI.  
2. **Wire real ground series** — ACLED, food indices, displacement—behind the same signal interface.  
3. **Version priors** — date stamps / git tags when country assumptions change.  
4. **Event journal** — store alarm onsets; review against known stress episodes.  
5. **Only then** — supervised models on *labeled* gaps, not on synthetic targets.

---

## 11. License / continuity

Research and operational prototype. Original project token retained for lineage: `TOKEN_F5B2C8E4A1D7396F`.

---

## 12. Bottom line for a principal engineer

SSM v30.5 is a **deliberately opinionated** monitor: it assumes official digital visibility is partial, encodes that assumption in structure (layers, gap, alarms), and refuses to let a single market composite narrate “all clear” when structural and ground loads disagree.

It is strongest as an **internal radar and argument surface**—a place to see *which* layer is driving the story.  
It is weakest if sold as a calibrated sovereign default oracle or a full map of the informal economy.

Use it where that honesty is a feature.
