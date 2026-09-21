# ======================================================================
# SSM v31.1 — Ground layer (SovereignGroundAutomator)
# ======================================================================
# Five signals: conflict · food · migration · mortality · physical
# DEFAULT: works WITHOUT API keys (LOCAL_PRIORS baselines)
# OPTIONAL: ACLED / public probes when keys present in API_KEYS_VAULT
# Never returns silent 0.0 for high-stress countries when keys missing —
# priors carry chronic load (that is the product thesis).
# ======================================================================

from __future__ import annotations

import asyncio
import json
import math
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional, Tuple


def _vault(config: dict) -> dict:
    return config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {}) or {}


def _is_live_key(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return False
    u = val.upper().strip()
    if not u or "PASTE" in u or u.startswith("YOUR_"):
        return False
    return len(u) > 6


def _acled_creds(vault: dict) -> Tuple[str, str]:
    """Accept several key names used across versions."""
    email = (
        vault.get("ACLED_EMAIL")
        or vault.get("ACLED_REGISTERED_EMAIL")
        or ""
    )
    key = (
        vault.get("ACLED_KEY")
        or vault.get("ACLED_API_KEY")
        or vault.get("ACLED_PASSWORD")
        or ""
    )
    return str(email).strip(), str(key).strip()


async def _http_json(url: str, timeout: float = 10.0, headers: Optional[dict] = None) -> Any:
    loop = asyncio.get_running_loop()
    hdrs = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; SSM/31.1; +https://github.com/BubuRR/sovereign-stress-monitor)"
        ),
        "Accept": "application/json",
    }
    if headers:
        hdrs.update(headers)

    def _get():
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))

    return await loop.run_in_executor(None, _get)


def _blend(prior: float, live: Optional[float], live_weight: float = 0.55) -> Tuple[float, str]:
    prior = float(min(max(prior, 0.0), 1.0))
    if live is None:
        return prior, "prior_only"
    live = float(min(max(live, 0.0), 1.0))
    w = min(max(live_weight, 0.0), 1.0)
    score = w * live + (1.0 - w) * prior
    return float(min(max(score, 0.0), 1.0)), "hybrid"


# ISO2 → ACLED-ish country name hints (best-effort)
_ACLED_COUNTRY = {
    "UA": "Ukraine",
    "RU": "Russia",
    "IL": "Israel",
    "PS": "Palestine",
    "SY": "Syria",
    "SD": "Sudan",
    "YE": "Yemen",
    "US": "United States",
    "DE": "Germany",
    "GB": "United Kingdom",
    "CN": "China",
    "PL": "Poland",
}


class SovereignGroundAutomator:
    """
    Automated ground-layer collector.
    - No keys: prior baselines from LOCAL_PRIORS (recommended default).
    - With ACLED email+key: conflict channel upgrades toward live.
    - Public probes (World Bank / GDACS) used opportunistically; failures → prior.
    """

    def __init__(self, config: dict):
        self.config = config
        self.vault = _vault(config)
        self.spec = config.get("GROUND_SIGNALS", {})

    async def fetch_all(self, country: str, prior: dict) -> Dict[str, Any]:
        code = country.upper().strip()
        results = {
            "conflict": await self._conflict(code, prior),
            "food": await self._food(code, prior),
            "migration": await self._migration(code, prior),
            "mortality": await self._mortality(code, prior),
            "physical": await self._physical(code, prior),
        }
        total_w, acc = 0.0, 0.0
        for name, row in results.items():
            if not self.spec.get(name, {}).get("enabled", True):
                continue
            w = float(self.spec.get(name, {}).get("weight", 0.2))
            acc += w * float(row["score"])
            total_w += w
        ground_index = acc / total_w if total_w > 0 else 0.0
        live_n = sum(1 for r in results.values() if r.get("quality") not in ("prior_only",))
        return {
            "signals": results,
            "GROUND_INDEX": round(ground_index, 4),
            "LIVE_CHANNELS": live_n,
            "MODE": "hybrid" if live_n else "prior_baseline",
            "coverage_note": (
                "Ground layer defaults to LOCAL_PRIORS. "
                "Paste ACLED_EMAIL + ACLED_KEY (or ACLED_API_KEY) in API_KEYS_VAULT for live conflict. "
                "Missing keys do NOT zero-out high-stress countries — priors preserve chronic load."
            ),
        }

    async def _conflict(self, country: str, prior: dict) -> dict:
        base = float(prior.get("conflict_base", 0.1))
        live = None
        source, quality = "prior", "prior_only"
        email, key = _acled_creds(self.vault)
        if _is_live_key(email) and _is_live_key(key):
            try:
                cname = _ACLED_COUNTRY.get(country, country)
                q = urllib.parse.urlencode(
                    {
                        "email": email,
                        "key": key,
                        "country": cname,
                        "event_type": "Battles|Explosions/Remote violence|Violence against civilians",
                        "limit": 50,
                        "fields": "event_id_cnty|event_type|country",
                    }
                )
                url = f"https://api.acleddata.com/acled/read?{q}"
                data = await _http_json(url, timeout=12.0)
                cnt = 0
                if isinstance(data, dict):
                    cnt = int(data.get("count") or 0)
                    if not cnt and isinstance(data.get("data"), list):
                        cnt = len(data["data"])
                # Map event count → [0,1] softly; blend with prior
                live = min(0.25 + math.log1p(max(cnt, 0)) / 6.0, 1.0)
                source, quality = "acled", "paid_api"
            except Exception:
                live = None
        score, mode = _blend(base, live, 0.55 if live is not None else 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality if live is not None else "prior_only",
            "mode": mode,
            "label": "conflict",
        }

    async def _food(self, country: str, prior: dict) -> dict:
        base = float(prior.get("food_base", 0.15))
        live = None
        source, quality = "prior", "prior_only"
        try:
            url = (
                "https://api.worldbank.org/v2/country/WLD/indicator/"
                "CPTOTSAXN?format=json&per_page=3&mrnev=1"
            )
            data = await _http_json(url, timeout=8.0)
            if isinstance(data, list) and len(data) > 1:
                rows = data[1] or []
                if rows and rows[0].get("value") is not None:
                    val = float(rows[0]["value"])
                    live = min(max((val - 100.0) / 80.0, 0.0), 1.0)
                    source, quality = "worldbank_proxy", "public_api"
        except Exception:
            live = None
        score, mode = _blend(base, live, 0.35 if live is not None else 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality if live is not None else "prior_only",
            "mode": mode,
            "label": "food",
        }

    async def _migration(self, country: str, prior: dict) -> dict:
        # No reliable free real-time UNHCR JSON without registration noise —
        # keep structural prior; live slot reserved for future key-backed feed.
        base = float(prior.get("migration_base", 0.1))
        score, mode = _blend(base, None, 0.0)
        return {
            "score": round(score, 4),
            "source": "prior",
            "quality": "prior_only",
            "mode": mode,
            "label": "migration",
        }

    async def _mortality(self, country: str, prior: dict) -> dict:
        base = float(prior.get("mortality_base", 0.1))
        score, mode = _blend(base, None, 0.0)
        return {
            "score": round(score, 4),
            "source": "prior",
            "quality": "prior_only",
            "mode": mode,
            "label": "mortality",
        }

    async def _physical(self, country: str, prior: dict) -> dict:
        base = float(prior.get("physical_base", 0.1))
        live = None
        source, quality = "prior", "prior_only"
        try:
            url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?from=20240101"
            data = await _http_json(url, timeout=8.0)
            if data:
                live = min(base + 0.05, 1.0)
                source, quality = "gdacs_probe", "public_api"
        except Exception:
            live = None
        score, mode = _blend(base, live, 0.2 if live is not None else 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality if live is not None else "prior_only",
            "mode": mode,
            "label": "physical",
        }


# Backward-compatible name used by quant_engine
GroundSignalEngine = SovereignGroundAutomator
