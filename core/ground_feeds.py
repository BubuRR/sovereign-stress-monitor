# ======================================================================
# SSM v30.5 — Five ground ("земли") signal feeds
# ======================================================================
# 1 conflict  2 food  3 migration  4 mortality  5 physical
# Free path: prior baselines + optional public endpoints
# Paid path: ACLED / Polygon / FRED keys from API_KEYS_VAULT
# Each signal returns score in [0, 1] + meta (source, quality)
# ======================================================================

import asyncio
import json
import math
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional, Tuple


def _vault(config: dict) -> dict:
    return (
        config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {}) or {}
    )


def _is_live_key(val: Optional[str]) -> bool:
    if not val or not isinstance(val, str):
        return False
    u = val.upper()
    return "PASTE" not in u and len(val.strip()) > 8


async def _http_json(url: str, timeout: float = 8.0, headers: Optional[dict] = None) -> Any:
    loop = asyncio.get_running_loop()
    hdrs = {"User-Agent": "SSM/30.5", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)

    def _get():
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))

    return await loop.run_in_executor(None, _get)


def _blend(prior: float, live: Optional[float], live_weight: float = 0.6) -> Tuple[float, str]:
    """Blend prior baseline with live observation when available."""
    prior = float(min(max(prior, 0.0), 1.0))
    if live is None:
        return prior, "prior_only"
    live = float(min(max(live, 0.0), 1.0))
    w = min(max(live_weight, 0.0), 1.0)
    score = w * live + (1.0 - w) * prior
    return float(min(max(score, 0.0), 1.0)), "hybrid"


class GroundSignalEngine:
    """Collect five ground signals for a country profile."""

    def __init__(self, config: dict):
        self.config = config
        self.vault = _vault(config)
        self.spec = config.get("GROUND_SIGNALS", {})

    async def fetch_all(self, country: str, prior: dict) -> Dict[str, Any]:
        country = country.upper().strip()
        results = {}
        # parallel-ish sequential await (simple, robust)
        results["conflict"] = await self._conflict(country, prior)
        results["food"] = await self._food(country, prior)
        results["migration"] = await self._migration(country, prior)
        results["mortality"] = await self._mortality(country, prior)
        results["physical"] = await self._physical(country, prior)

        # composite ground intensity
        total_w = 0.0
        acc = 0.0
        for name, row in results.items():
            if not self.spec.get(name, {}).get("enabled", True):
                continue
            w = float(self.spec.get(name, {}).get("weight", 0.2))
            acc += w * float(row["score"])
            total_w += w
        ground_index = acc / total_w if total_w > 0 else 0.0

        return {
            "signals": results,
            "GROUND_INDEX": round(ground_index, 4),
            "coverage_note": (
                "Ground layer blends LOCAL_PRIORS baselines with live feeds when keys/APIs work; "
                "otherwise prior_only. Not a full shadow-economy census."
            ),
        }

    async def _conflict(self, country: str, prior: dict) -> dict:
        base = float(prior.get("conflict_base", 0.1))
        live = None
        source = "prior"
        quality = "baseline"

        email = self.vault.get("ACLED_EMAIL", "")
        key = self.vault.get("ACLED_KEY", "")
        if _is_live_key(email) and _is_live_key(key):
            try:
                # ACLED requires registration; if keys present attempt a light query
                q = urllib.parse.urlencode(
                    {
                        "email": email,
                        "key": key,
                        "event_type": "Battles|Explosions/Remote violence|Violence against civilians",
                        "limit": 1,
                    }
                )
                url = f"https://api.acleddata.com/acled/read?{q}"
                data = await _http_json(url, timeout=10.0)
                # Presence of data → elevated; count if available
                cnt = 0
                if isinstance(data, dict):
                    cnt = int(data.get("count") or len(data.get("data") or []))
                live = min(0.3 + math.log1p(cnt) / 8.0, 1.0)
                source = "acled"
                quality = "paid_api"
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
        source = "prior"
        quality = "baseline"

        # Public FAO food price index (CSV-ish endpoint variants change; try JSON world bank style proxy)
        try:
            # World Bank API: Food production index or CPI food where available — soft probe
            url = (
                "https://api.worldbank.org/v2/country/WLD/indicator/"
                "CPTOTSAXN?format=json&per_page=3&mrnev=1"
            )
            data = await _http_json(url, timeout=8.0)
            # Very soft signal: if API responds, slight lift from prior using last value anomaly
            if isinstance(data, list) and len(data) > 1:
                rows = data[1] or []
                if rows and rows[0].get("value") is not None:
                    # normalize roughly: high index → more stress (crude)
                    val = float(rows[0]["value"])
                    live = min(max((val - 100.0) / 80.0, 0.0), 1.0)
                    source = "worldbank_proxy"
                    quality = "public_api"
        except Exception:
            live = None

        score, mode = _blend(base, live, 0.4 if live is not None else 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality if live is not None else "prior_only",
            "mode": mode,
            "label": "food",
        }

    async def _migration(self, country: str, prior: dict) -> dict:
        base = float(prior.get("migration_base", 0.1))
        # No universal free real-time displacement API without keys —
        # prior carries wartime/refugee structural load; live stub for paid later
        live = None
        source = "prior"
        quality = "prior_only"
        # Optional: UNHCR-like placeholders would go here with keys
        score, mode = _blend(base, live, 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality,
            "mode": mode,
            "label": "migration",
        }

    async def _mortality(self, country: str, prior: dict) -> dict:
        base = float(prior.get("mortality_base", 0.1))
        live = None
        score, mode = _blend(base, live, 0.0)
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
        source = "prior"
        quality = "prior_only"
        try:
            # GDACS RSS/JSON style public events (best-effort)
            url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?from=20240101"
            data = await _http_json(url, timeout=8.0)
            if data:
                # any parseable payload → mild live confirmation of monitoring path
                live = min(base + 0.05, 1.0)
                source = "gdacs_probe"
                quality = "public_api"
        except Exception:
            live = None
        score, mode = _blend(base, live, 0.25 if live is not None else 0.0)
        return {
            "score": round(score, 4),
            "source": source,
            "quality": quality if live is not None else "prior_only",
            "mode": mode,
            "label": "physical",
        }
