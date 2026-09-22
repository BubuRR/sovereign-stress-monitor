# Sovereign Stress Monitor (SSM) v32.4

**Release line: v32.4** — hybrid G/S/Ground/LAND + Gap; optional OpenRouter advisory (env `OPENROUTER_API_KEY`). Sample report is regenerated with this version tag.
Open hybrid **macro stress radar**: official market layer vs structural priors vs ground proxies, with an explicit **gap**.

Not investment advice. Not a substitute for BlackRock Aladdin or Palantir.

---

## What it is

SSM estimates, per country profile:

| Layer | Meaning |
|-------|---------|
| **G** | Global/official market regime (SMH, DBB, USDT proxies) |
| **S** | Structural local pressure from **versioned priors** (fiscal, demographic, buffer) |
| **Ground** | Five “ground” signal slots (conflict, food, migration, mortality, physical) — priors by default |
| **LAND** | `max(S, Ground)` — land intensity even if markets look calm |
| **Gap** | How far land/structure sits above official G |
| **R** | Display composite (max-based + small ground lift) |

Optional **AI Advisory**: LLM narrative **after** the math. It does **not** write G/S/Land/Gap.

---

## What it is not

- Not a default-probability model or credit rating  
- Not a full census of informal economy  
- Not “cheat-proof” or immune to bad inputs  
- Not a generative model inventing the index  

Garbage in (feeds/priors) → garbage out (scores).

---

## Quick start (Windows)

1. Install [Python 3.10+](https://www.python.org/downloads/) with **Add to PATH**.  
2. Download ZIP or clone this repo.  
3. Double-click **`install.bat`**, then **`start-simple.bat`**.  
4. Browser: **http://localhost:8501**

Manual:

```text
python -m pip install -r requirements.txt
python ssm_core.py
python -m streamlit run interface/app.py --server.port 8501
```

No paid API keys required for core radar (Yahoo/public paths + local priors).

---

## Optional AI Advisory (your key only)

**Recommended free path: [Groq](https://console.groq.com)** — see `HOWTO-OPENROUTER.md` (default) or `HOWTO-GROQ.md`.

Also supported: OpenRouter, OpenAI (OpenAI-compatible endpoints).

## Optional AI Advisory (your key only)

1. Get **your own** key from a provider (e.g. OpenAI platform — free trial/credits vary by account; we do **not** ship keys).  
2. Set environment variable:

```text
set OPENAI_API_KEY=sk-...
```

3. In `config/parameters.json`:

```json
"AI_ADVISORY": { "enabled": true, "provider": "openai", "model": "gpt-4o-mini", ... }
```

4. Run `python ssm_core.py` — report gains `AI_ADVISORY` text or soft error.  
5. If key missing or `enabled: false` → `AI_ADVISORY: null`, radar unchanged.

**Legal:** only keys you own. Do not commit secrets to GitHub.

---

## Optional ground upgrade (ACLED etc.)

Same pattern: put **your** research key in vault/env. Without it, Ground stays prior-based (`prior_only`).

---

## Hard baseline (anti rolling-window habituation)

`HARD_BASELINE_SMH` / `HARD_BASELINE_DBB` in `GLOBAL_DEFAULTS` anchor physical deficit vs a policy “peace” level, not only the last 3 months. Edit anchors when you recalibrate.

---

## Project layout

```text
ssm_core.py            entry
core/quant_engine.py   hybrid math
core/ground_feeds.py   ground automator
core/ai_advisory.py    optional LLM narrative
core/database.py       SQLite history
config/parameters.json  priors + flags
interface/app.py       Streamlit dashboard
api/main.py            optional FastAPI
```

---

## Tests

```text
pytest -q
```

---

## Methodology (honest)

- **Official G** tracks market proxies; calm equities ≠ calm society.  
- **S / Ground / LAND** encode chronic pressure the market may ignore.  
- **Gap** is the product’s point: divergence, not a single Wall Street number.  
- **AI** is a second opinion on the passport, never the judge of scores.

---

## License

See `LICENSE`.

