# ======================================================================
# SSM — Optional AI Advisory (v32.4.2 bilingual EN+RU)
# OpenAI-compatible: OpenRouter / Groq / OpenAI
# NEVER overrides G / S / Ground / LAND / Gap.
# ======================================================================
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import List, Optional, Tuple

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


def detect_narrative_pressure(
    passport: dict, gap_threshold: float = 15.0
) -> Tuple[bool, float, List[str]]:
    max_gap = 0.0
    hot: List[str] = []
    for f in passport.get("DATA_DYNAMIC_FEEDS") or []:
        comp = f.get("COMPARISON") or {}
        gap = float(comp.get("GAP_SCORE") or 0)
        alarms = list(comp.get("ALARM_CODES") or [])
        max_gap = max(max_gap, gap)
        if (
            gap >= gap_threshold
            or "NARRATIVE_LAG" in alarms
            or "GROUND_DIVERGENCE" in alarms
            or "LAND_WATCH" in alarms
            or "LAND_CRITICAL" in alarms
        ):
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
            or 5.0
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
                "You are an independent macro analyst for SSM (Sovereign Stress Monitor). "
                "Passport numbers are already computed by math. NEVER invent or change "
                "G, S, Ground, LAND, Gap, or R. "
                "Write a clear, longer briefing for a global audience: meaning of the numbers, "
                "land stress vs market/official facade, and a cautious qualitative forecast. "
                "No buy/sell advice.\n\n"
                f"NARRATIVE_LAG mode: max Gap={max_gap:.1f} (threshold {self.gap_threshold}), "
                f"focus countries: {hot}.\n"
                "Gap means LAND is above G. G is often a shared global market layer; "
                "country differences usually appear in S, Ground, LAND, Gap — not always in R.\n\n"
                "LANGUAGE RULE (mandatory):\n"
                "1) Write the COMPLETE briefing in clear English.\n"
                "2) Then write the COMPLETE briefing again in clear Russian (same meaning).\n"
                "Both parts must be understandable to non-specialists.\n\n"
                "Use these section headings in EACH language:\n"
                "### 1. In plain words\n"
                "### 2. Country focus\n"
                "### 3. vs market / official tone (hypotheses only)\n"
                "### 4. Outlook 7 and 30 days (base / worse / better)\n"
                "### 5. Missing data\n"
                "### 6. Disclaimer\n\n"
                "Target length: about 800–1500 words total (English + Russian). "
                "Short paragraphs. Phone-readable."
            )
            status = "NARRATIVE_LAG_DECOMPILED"
        else:
            system_prompt = (
                "You are an independent macro analyst for SSM. Do not change passport numbers. "
                "Clear longer briefing for a global audience. No buy/sell advice.\n\n"
                f"ROUTINE mode: max Gap={max_gap:.1f}, threshold {self.gap_threshold}.\n\n"
                "LANGUAGE RULE: full answer in clear English, then the same structure in clear Russian.\n\n"
                "Headings in each language:\n"
                "### 1. Overall picture\n"
                "### 2. Residual stress\n"
                "### 3. Outlook 7–30 days\n"
                "### 4. Limits and disclaimer\n\n"
                "About 500–1000 words total for both languages."
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
            "max_tokens": int(self.ai.get("max_tokens") or 2000),
            "temperature": float(self.ai.get("temperature") or 0.35),
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "SSM-Advisory/32.4.2",
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
            with urllib.request.urlopen(req, timeout=90.0) as resp:
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
                "output_languages": ["en", "ru"],
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
