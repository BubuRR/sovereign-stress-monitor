# Sovereign Stress Monitor (SSM) v31.1

**Hybrid early-warning radar: official markets next to structural priors and ground proxies.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/BubuRR/sovereign-stress-monitor/actions/workflows/main.yml/badge.svg)](https://github.com/BubuRR/sovereign-stress-monitor/actions/workflows/main.yml)

> **Not investment advice.** Scores are intensities and regime labels — not calibrated default probabilities, not forecasts of asset returns, not a substitute for national statistics or institutional risk platforms.

---

## What this is (and is not)

| This **is** | This is **not** |
|-------------|-----------------|
| A research monitor that shows **three layers side by side** | A classified intel system |
| A way to see **GAP** when markets look calm and land/structural load does not | An estimate of shadow GDP or “true” informal market size |
| Runnable offline-ish with **no API keys** (priors + public feeds) | A production SLA service with guaranteed live ground data |
| Optional upgrade path (ACLED, Polygon, QuickNode) when you add keys | Automatic “absolute” sensing of physical pressure everywhere |

**Product thesis:** official digital visibility is incomplete. SSM does not claim to fill that gap completely. It **refuses to hide** structural and ground stress behind a single green market number.

---

## Architecture

```text
DISPLAY R  ≈  max(G, S)  +  small lift when ground exceeds that max
────────────────────────────────────────────────────────────────
 OFFICIAL G          STRUCTURAL S         GROUND (×5)
 market regime       fiscal / demo /      conflict · food ·
 SMH · DBB · USDT    buffer priors        migration · mortality ·
                                          physical
────────────────────────────────────────────────────────────────
 GAP = max(S, GROUND) − G
 ALARMS = named codes (SILENT_STRESS, GROUND_DIVERGENCE, …)
```

| Layer | Source of truth | Updates |
|-------|-----------------|---------|
| **G** | Yahoo (or Polygon) SMH/DBB + TronGrid USDT events | Each cycle |
| **S** | `LOCAL_PRIORS` in `config/parameters.json` | Only when you edit config |
| **Ground** | Same priors as baseline; ACLED/public probes if available | Each cycle |
| **GAP / alarms** | Derived from G, S, ground | Each cycle |

### Structural formula (explicit, auditable)

\[
S = 1 - \exp\bigl(-\lambda (\alpha F + \beta D + \gamma B)\bigr)
\]

\(F, D, B\) are declared priors (fiscal, demographic, buffer). **S is not P(default).**

### Ground module (`SovereignGroundAutomator`)

- **Default (no keys):** scores from country priors — high-stress countries **do not** collapse to zero.
- **Optional:** `ACLED_EMAIL` + `ACLED_KEY` (or `ACLED_API_KEY`) in `API_KEYS_VAULT` upgrades **conflict**.
- Each signal reports `quality`: `prior_only` | `public_api` | `paid_api` | `hybrid`.

### Market feeds

- Shared SMH/DBB fetch once per cycle (avoids rate limits).
- Browser-like User-Agent; query1/query2 fallback.
- Report fields `SMH_SOURCE` / `DBB_SOURCE` = `LIVE` or `FALLBACK`.

---

## What a run actually produces

```bash
pip install -r requirements.txt
pytest -q
python ssm_core.py
```

Typical log:

```text
[SSM FEED] SMH: LIVE n=64 last=591.xx
[SSM FEED] DBB: LIVE n=64 last=25.xx
[SSM] UA: R=61.5% ELEVATED G=54.7 S=61.1 Ground=63.7 Gap=9.0
      alarms=[GROUND_DIVERGENCE,LOW_DIGITAL_COVERAGE_WARNING]
```

JSON passport: `ssm_unified_report.json`  
SQLite history: `ssm_intelligence.db` (project root)

| Interface | Command |
|-----------|---------|
| API | `uvicorn api.main:app --port 8000` |
| Dashboard | `streamlit run interface/app.py --server.port 8501` |

Endpoints: `GET /`, `/api/v1/radar/composite`, `/api/v1/risk/{CC}`

---

## Capabilities matrix (honest)

| Capability | Status |
|------------|--------|
| Side-by-side G / S / Ground | **Yes** |
| GAP + named alarms | **Yes** |
| Live SMH/DBB (public) | **Yes** (when Yahoo reachable) |
| USDT flow sample (TronGrid) | **Yes** (best-effort) |
| Structural priors per country | **Yes** (config) |
| Ground without keys | **Yes** (priors) |
| Live ACLED conflict | **Optional** (research key) |
| Live migration / mortality series | **Mostly prior** (slots ready) |
| Calibrated sovereign default model | **No** |
| Full informal-economy measurement | **No** |
| 24/7 production ops guarantee | **No** |

---

## Configuration

- Weights, thresholds, priors: `config/parameters.json`
- Optional keys: `ENTERPRISE_DATA_GATEWAYS.API_KEYS_VAULT`
  - `POLYGON_IO_KEY`, `QUICKNODE_TRON_KEY`
  - `ACLED_EMAIL` / `ACLED_KEY` (aliases: `ACLED_REGISTERED_EMAIL`, `ACLED_API_KEY`)

If a value still contains `PASTE`, that channel stays on the free path.

---

## Repository layout

```text
ssm_core.py                 # CLI entry
core/quant_engine.py        # G, S, combine, gap, run_all
core/ground_feeds.py        # SovereignGroundAutomator
core/database.py            # SQLite WAL
api/main.py                 # FastAPI
interface/app.py            # Streamlit (G vs Ground, GAP)
config/parameters.json
tests/test_smoke.py
.github/workflows/main.yml  # CI
.github/workflows/release.yml  # tag v* → Release
```

---

## GitHub About (paste into UI)

See `GITHUB_ABOUT.txt`. Short description:

```text
Hybrid early-warning radar: official market (G) next to structural priors (S) and five ground proxies. Surfaces GAP when markets look calm but land/structural load does not. Research tool — not investment advice.
```

Suggested topics: `osint` `python` `early-warning` `risk-monitoring` `open-source` `macro` `streamlit` `fastapi`

---

## Releases

```bash
git tag v31.1
git push origin v31.1
```

Triggers `.github/workflows/release.yml` (tests + GitHub Release).

---

## Limitations (read before citing)

1. Ground live coverage is incomplete without vendor keys.  
2. Priors encode expert judgment (e.g. high UA conflict baseline) — intentional, still not a measurement.  
3. G uses global ETFs (SMH/DBB), not local GDP.  
4. USDT TRC-20 is a narrow capital-flow slice.  
5. Alarms are rule-based, not trained on labeled crises.  
6. Public APIs (Yahoo, TronGrid, probes) can fail; report marks FALLBACK.

---

## Design principles

1. Never show only the comfortable layer.  
2. Label data pedigree (`prior_only` vs `LIVE`).  
3. No synthetic “AI probability of crash” without labels.  
4. Prefer a named alarm over a quiet, precise-looking wrong number.  
5. Config is policy — changing priors is a deliberate act.

---

## License

MIT — see [LICENSE](LICENSE).

Research prototype. Lineage token retained for continuity: `TOKEN_F5B2C8E4A1D7396F`.
