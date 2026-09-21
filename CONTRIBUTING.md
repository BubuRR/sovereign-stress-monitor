# Contributing

## Useful directions

1. **Live ground feeds** — conflict (ACLED), food indices, displacement — same interface as `core/ground_feeds.py`.
2. **Tests** — offline fixtures so CI does not depend on Yahoo/Tron.
3. **Alarm journal** — persist alarm onset times for later review.

## Rules

- Keep **pedigree** visible (`prior_only` / `LIVE` / `paid_api`).
- Do not market scores as default probabilities.
- Official and alternative layers must remain **side by side** in outputs.
- Open a GitHub Issue before large architectural changes.

```bash
pytest -q
python ssm_core.py
```
