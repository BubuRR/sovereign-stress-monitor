# Sovereign Stress Monitor (SSM) v30.0

**Experimental research tool** for regime / stress monitoring using public market series and optional on-chain stablecoin flow signals.

> Not investment advice. Not a substitute for institutional risk platforms.  
> Composite scores are **heuristic** and must be validated before any decision use.

## What it does

1. Pulls multi-month price history for **SMH** (semiconductors) and **DBB** (base metals) via Yahoo Finance (or Polygon if you add a key).
2. Optionally samples recent **USDT TRC-20** transfer sizes (TronGrid public API or QuickNode).
3. Detects **structural breaks** (ruptures PELT) to reduce baseline drift.
4. Builds a transparent composite → `NORMAL` / `ELEVATED` / `CRITICAL`.
5. Stores ticks in **SQLite** and exposes **FastAPI** + **Streamlit** views.

## What it does *not* do

- Predict sovereign defaults with institutional accuracy  
- Replace Bloomberg / Aladdin / CDS desks  
- Provide calibrated probabilities without your own event study  

## Quick start

```bash
pip install -r requirements.txt
pytest -q
python ssm_core.py

# API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Dashboard
streamlit run interface/app.py --server.port 8501
```

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health |
| `GET /api/v1/radar/composite` | Latest JSON passport |
| `GET /api/v1/risk/{CC}` | History for country code |

## Layout

```
ssm_core.py          # CLI entry → run_all()
core/quant_engine.py # signals + CPD + composite
core/database.py     # SQLite (project-root ssm_intelligence.db)
api/main.py          # FastAPI
interface/app.py     # Streamlit
config/parameters.json
tests/test_smoke.py
```

## Optional paid feeds

Edit `config/parameters.json` → `API_KEYS_VAULT` (Polygon / QuickNode).  
If keys contain `PASTE`, free public endpoints are used.

## License / token

Architect note: original project token `TOKEN_F5B2C8E4A1D7396F` retained for continuity.
