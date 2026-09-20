# Realistic development vector (90 days)

Chosen path: **Research regime terminal** — not “sovereign AI Aladdin clone”.

## Why this path

- Public data + CPD + transparent drivers can be useful as a *second opinion*.
- Fake country AI probabilities and Aladdin comparisons destroy credibility.
- Narrow scope is shippable; wide scope is not.

## Days 1–30 — Hardening (done in v30 baseline)

- [x] Complete `run_all` / no truncated modules
- [x] Correct Yahoo + TronGrid endpoints
- [x] Single DB path (repo root)
- [x] `pytest` smoke tests
- [x] Honest README / disclaimer
- [ ] Pin CI green on every push
- [ ] Snapshot fixtures for offline tests (no live network in unit tests)

## Days 31–60 — Methodology

1. **Define events** (pick one): e.g. 5-day SMH drawdown ≤ −8%, or VIX spike, or DXY jump.
2. **Log features + labels** offline; walk-forward; report precision/recall — or drop claims.
3. Replace fixed fiscal/demographic constants with **documented priors** or remove from composite.
4. Country layer: either real local instruments (FX, local equity) or **one global regime** only.

## Days 61–90 — Product

1. UI: regime state + **driver breakdown** (already partially in JSON `DRIVERS`).
2. Data freshness badge (stale cycles already tracked).
3. Optional: paid Polygon path only; deprecate brittle Yahoo for production deploys.
4. One-page methodology PDF for users.

## Explicit non-goals (next 90 days)

- Multi-asset portfolio construction  
- Smart-contract “success fee” automation  
- Marketing claims vs BlackRock/Palantir  
- Synthetic RandomForest “crash probability” without real labels  

## Success metric

A user can answer: *“Did the global risk regime shift in the last week, and which inputs drove the flag?”*  
— with reproducible logs — not *“Country X is 62.03% stressed.”*
