# How to raise evaluation scores

## Architecture 7 → 9
- Keep hybrid isolation (done).
- Add explicit FORECAST block (EWMA on Gap/Land from SQLite) separate from AI text.
- Version single source: config VERSION only; report/API read it.
- Document "is / is not" matrix in README (done in spirit — keep strict).

## Code maturity 6 → 8–9
- One VERSION string everywhere (32.4+).
- pytest for gap alarm thresholds + narrative detect.
- CI green on every push; pin requirements.
- No silent except; log feed LIVE/FALLBACK always in report.
- Optional: typed report schema (pydantic) for JSON passport.

## Ground reality 4 → 7+
- ACLED research key → live conflict channel.
- 1–2 more free public series (e.g. commodity, migration proxy) with soft fail.
- Recalibrate LOCAL_PRIORS on a fixed calendar (monthly), with PRIOR_VERSION field.
- Lower false "all ELEVATED from metals only": split MARKET_ELEVATED vs LAND_ELEVATED in STATUS.
- Scenario module (what-if) without LLM.

## AI narrative (OpenRouter free)
- Keep advisory-only (done).
- Gap threshold 5 + NARRATIVE_LAG/LAND_WATCH triggers (32.4).
- Cache last brief; rate-limit to 1 call per cycle.
- Never paste keys to git/chat.
