# ======================================================================
# SSM — Optional AI Advisory + Narrative Lag decompile (v32.4)
# OpenAI-compatible: OpenRouter (default), Groq, OpenAI
# NEVER overrides G / S / Ground / LAND / Gap scores.
# ======================================================================
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

PROVIDER_PRESETS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "env_keys": ("OPENAI_API_KEY", "SSM_OPENAI_API_KEY"),
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "env_keys": ("GROQ_API_KEY", "OPENAI_API_KEY", "SSM_OPENAI_API_KEY"),
    },
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openrouter/free",
        "env_keys": ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "SSM_OPENAI_API_KEY"),
    },
}


def _slim_feeds(passport: dict) -> List[dict]:
    out = []
    for f in passport.get("DATA_DYNAMIC_FEEDS") or []:
        out.append(
            {
                "COUNTRY": f.get("COUNTRY"),
                "R": f.get("DISPLAY_SCORE"),
                "STATUS": f.get("STATUS"),
                "G": (f.get("OFFICIAL") or {}).get("GLOBAL_REGIME_SCORE"),
                "S": (f.get("STRUCTURAL") or {}).get("LOCAL_STRUCTURAL_SCORE"),
                "GROUND": (f.get("GROUND") or {}).get("GROUND_INDEX"),
                "LAND": (f.get("LAND") or {}).get("LAND_STRESS"),
                "GAP": (f.get("COMPARISON") or {}).get("GAP_SCORE"),
                "ALARMS": (f.get("COMPARISON") or {}).get("ALARM_CODES"),
            }
        )
    return out


def detect_narrative_pressure(passport: dict, gap_threshold: float = 15.0) -> Tuple[bool, float, List[str]]:
    """Return (triggered, max_gap, countries_with_pressure)."""
    max_gap = 0.0
    hot: List[str] = []
    for f in passport.get("DATA_DYNAMIC_FEEDS") or []:
        comp = f.get("COMPARISON") or {}
        gap = float(comp.get("GAP_SCORE") or 0)
        alarms = list(comp.get("ALARM_CODES") or [])
        max_gap = max(max_gap, gap)
        if gap >= gap_threshold or "NARRATIVE_LAG" in alarms or "GROUND_DIVERGENCE" in alarms or "LAND_WATCH" in alarms or "LAND_CRITICAL" in alarms:
            hot.append(str(f.get("COUNTRY") or "?"))
    return (len(hot) > 0 or max_gap >= gap_threshold), max_gap, hot


class SovereignAIAdvisory:
    def __init__(self, config: dict):
        self.config = config or {}
        self.ai = dict(self.config.get("AI_ADVISORY") or {})
        provider = str(self.ai.get("provider") or "openrouter").lower().strip()
        if provider not in PROVIDER_PRESETS:
            provider = "openrouter"
        self.provider = provider
        preset = PROVIDER_PRESETS[provider]
        self.endpoint = str(self.ai.get("endpoint") or preset["endpoint"])
        self.model = str(self.ai.get("model") or preset["model"])
        self.gap_threshold = float(
            self.ai.get("narrative_gap_threshold")
            or (self.config.get("GLOBAL_DEFAULTS") or {}).get("NARRATIVE_GAP_AI_THRESHOLD")
            or 15.0
        )

        vault = (
            (self.config.get("ENTERPRISE_DATA_GATEWAYS") or {}).get("API_KEYS_VAULT") or {}
        )
        self.api_key = ""
        for env_name in preset["env_keys"]:
            val = (os.environ.get(env_name) or "").strip()
            if val and not val.upper().startswith("PASTE") and "YOUR_" not in val.upper():
                self.api_key = val
                break
        if not self.api_key:
            for k in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
                val = str(vault.get(k) or "").strip()
                if val and not val.upper().startswith("PASTE"):
                    self.api_key = val
                    break

    def generate_brief(self, passport: dict) -> Optional[dict]:
        if not self.ai.get("enabled"):
            return None
        if not self.api_key:
            return {
                "role": "advisory_not_authoritative",
                "status": "SKIPPED_NO_API_KEY",
                "provider": self.provider,
                "hint": "Set OPENROUTER_API_KEY (or GROQ/OPENAI) in environment.",
            }

        triggered, max_gap, hot = detect_narrative_pressure(passport, self.gap_threshold)
        feeds = _slim_feeds(passport)

        if triggered:
            system_prompt = (
                "You are an independent macro analyst. The JSON is a deterministic SSM radar passport. "
                "You are NOT authoritative and MUST NOT invent or replace numeric scores. "
                "NARRATIVE_LAG / elevated GAP means official/market layer G is calmer than LAND/structure/ground. "
                f"Trigger: max GAP={max_gap:.1f}, threshold={self.gap_threshold}, countries={hot}. "
                "Respond in Russian with sections:\n"
                "1) INTERPRETATION OF GAP — plain language why G can look calm while S/Ground/LAND are high.\n"
                "2) NARRATIVE DECOMPILATION — hypotheses about media/official framing vs these layers "
                "(hypotheses only; do not claim proven fraud).\n"
                "3) 7-DAY QUALITATIVE OUTLOOK — may Gap widen/narrow; uncertainty required.\n"
                "4) DATA GAPS — what live signals are missing (ACLED, migration, informal economy).\n"
                "5) DISCLAIMER — not investment advice; math layers remain the source of truth.\n"
                "Be concise and professional. No portfolio buy/sell orders."
            )
            status = "NARRATIVE_LAG_DECOMPILED"
        else:
            system_prompt = (
                "You are an independent macro analyst. JSON is a deterministic SSM passport. "
                "You are NOT authoritative; do not replace scores. "
                "GAP is not above the decompile threshold for most countries. "
                "Respond in Russian briefly: (1) overall reading of G vs LAND (2) any mild divergences "
                "(3) missing data (4) disclaimer: not investment advice."
            )
            status = "ROUTINE_BRIEF"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "LIVE_PASSPORT:\n"
                    + json.dumps(
                        {
                            "VERSION": passport.get("VERSION"),
                            "MAX_GAP": max_gap,
                            "HOT_COUNTRIES": hot,
                            "FEEDS": feeds,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "max_tokens": int(self.ai.get("max_tokens") or 1000),
            "temperature": float(self.ai.get("temperature") or 0.25),
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "SSM-Advisory/32.3",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/BubuRR/sovereign-stress-monitor"
            headers["X-Title"] = "SSM Narrative Advisory"

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            text = data["choices"][0]["message"]["content"]
            return {
                "role": "advisory_not_authoritative",
                "status": status,
                "narrative_lag_triggered": triggered,
                "max_gap_observed": round(max_gap, 2),
                "gap_threshold": self.gap_threshold,
                "hot_countries": hot,
                "provider": self.provider,
                "model": self.model,
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "ai_narrative_brief": text,
                "never_override_scores": True,
                "disclaimer": "Advisory text only. G/S/Ground/LAND/Gap remain mathematical.",
            }
        except Exception as e:
            return {
                "role": "advisory_not_authoritative",
                "status": "AI_ADVISORY_DEGRADED",
                "narrative_lag_triggered": triggered,
                "max_gap_observed": round(max_gap, 2),
                "provider": self.provider,
                "error": str(e)[:400],
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            }
