# Sovereign Stress Monitor (SSM) v30.5

**Hybrid early-warning radar for economic and structural stress**

SSM is a research-grade monitoring stack that places **official/market observables** next to **structural priors** and **five ground-level proxies**, then surfaces the **gap** between them. It is built for environments where reported digital/cash-register activity is an incomplete picture of real conditions on the ground.

> **Not investment advice.** Scores are intensities and regime labels, not calibrated default probabilities or forecasts of asset returns.

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
