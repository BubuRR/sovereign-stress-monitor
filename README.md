# SSM v30.5 — Hybrid Official + Ground Radar

**See official and ground side by side. See the gap. Hear the alarm.**

| Layer | What |
|-------|------|
| **OFFICIAL (G)** | Market regime — SMH, DBB, USDT flows |
| **STRUCTURAL (S)** | Fiscal / demographic / buffer priors (versioned) |
| **GROUND (5)** | conflict · food · migration · mortality · physical |
| **GAP** | `max(S, ground) − G` — calm markets vs hot land |
| **ALARMS** | `SILENT_STRESS`, `GROUND_DIVERGENCE`, `NARRATIVE_LAG`, … |

Ground feeds use **LOCAL_PRIORS baselines** always; when you paste keys in `config/parameters.json` → `API_KEYS_VAULT` (Polygon, QuickNode, ACLED, …) live quality upgrades automatically.

```bash
pip install -r requirements.txt
pytest -q
python ssm_core.py
uvicorn api.main:app --port 8000
streamlit run interface/app.py --server.port 8501
```

Not investment advice. Proxies ≠ full informal-economy census.
