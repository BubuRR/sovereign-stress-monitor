# ======================================================================
# SSM v30.5 — Hybrid dual-layer + 5 ground signals + gap / alarm
# ======================================================================
# OFFICIAL / MARKET  → G
# STRUCTURAL PRIORS  → S
# GROUND (земли)     → five signals → GROUND_INDEX
# GAP                → when official calm but ground/structural hot
# ALARM_CODES        → named sirens (radar + signaling)
# Paid keys in config → richer feeds; free path always works via priors
# ======================================================================

import asyncio
import math
import json
import datetime
import urllib.request
import os
import sys
import traceback
import numpy as np

try:
    import ruptures as rpt
    HAS_RUPTURES = True
except ImportError:
    rpt = None
    HAS_RUPTURES = False

import scipy.stats as stats
from core.database import SovereignStressDB
from core.ground_feeds import GroundSignalEngine


class RollingOnchainBuffer:
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.buffer = []

    def extend(self, values):
        self.buffer.extend(values)
        if len(self.buffer) > self.max_size:
            self.buffer = self.buffer[-self.max_size :]

    def trimmed_median(self, default):
        if not self.buffer:
            return default
        s = sorted(self.buffer)
        c = max(1, int(len(s) * 0.05))
        if len(s) > 20:
            s = s[c:-c]
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0

    def size(self):
        return len(self.buffer)


class SovereignGlobalMonitorCore:
    def __init__(self, config_path="config/parameters.json"):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(self.root, config_path)
        with open(path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.defaults = self.config["GLOBAL_DEFAULTS"]
        self.weights = self.config.get("WEIGHTS", {})
        self.mix = self.config.get(
            "STRUCTURAL_MIX",
            {"alpha_fiscal": 0.5, "beta_demographic": 0.35, "gamma_buffer": 0.15},
        )
        self.composite_mode = self.config.get("COMPOSITE_MODE", "max")
        self.priors = self.config.get("LOCAL_PRIORS", {})
        self.db = SovereignStressDB()
        self.onchain = RollingOnchainBuffer(500)
        self.ground = GroundSignalEngine(self.config)
        self.cache_stale = 0
        self.high_stress_dur = {}
        self.pre_crisis_smh = float(self.defaults.get("SMH_50D_AVERAGE_NORM", 550))
        self.pre_crisis_dbb = float(self.defaults.get("DBB_50D_AVERAGE_NORM", 25))
        self.reference_mode = "normal"

    def _yahoo_chart_urls(self, symbol: str):
        # Multiple hosts — Yahoo intermittently blocks single endpoint/UA
        q = f"{symbol}?interval=1d&range=3mo"
        return [
            f"https://query1.finance.yahoo.com/v8/finance/chart/{q}",
            f"https://query2.finance.yahoo.com/v8/finance/chart/{q}",
        ]

    def _http_get_sync(self, url: str, timeout: float = 15.0) -> bytes:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    async def _fetch_prices(self, symbol, fallback):
        """Return list of closes. Prefer live Yahoo/Polygon; never silently fake a flat series without log."""
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        key = vault.get("POLYGON_IO_KEY", "")
        urls = []
        if key and "PASTE" not in key.upper():
            base = self.config["ENTERPRISE_DATA_GATEWAYS"]["POLYGON_IO_MACRO_FEED"].rstrip("/")
            urls.append(
                f"{base}/v2/aggs/ticker/{symbol}/range/1/day/2024-01-01/2030-01-01"
                f"?adjusted=true&limit=120&apiKey={key}"
            )
        urls.extend(self._yahoo_chart_urls(symbol))

        loop = asyncio.get_running_loop()
        last_err = None
        for url in urls:
            try:
                raw = await loop.run_in_executor(None, lambda u=url: self._http_get_sync(u))
                data = json.loads(raw.decode())
                if "results" in data and data["results"]:
                    closes = [float(x["c"]) for x in data["results"] if x.get("c") is not None]
                    if closes:
                        print(f"[SSM FEED] {symbol}: LIVE n={len(closes)} last={closes[-1]:.2f}", flush=True)
                        return closes
                res = data.get("chart", {}).get("result") or []
                if res:
                    closes = res[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                    closes = [float(c) for c in closes if c is not None]
                    if closes:
                        print(f"[SSM FEED] {symbol}: LIVE n={len(closes)} last={closes[-1]:.2f}", flush=True)
                        return closes
            except Exception as e:
                last_err = e
                continue
        print(
            f"[SSM FEED] {symbol}: FALLBACK {fallback} ({type(last_err).__name__ if last_err else 'empty'})",
            file=sys.stderr,
            flush=True,
        )
        return [float(fallback)] * 50

    async def _fetch_usdt(self):
        vault = self.config.get("ENTERPRISE_DATA_GATEWAYS", {}).get("API_KEYS_VAULT", {})
        qn = vault.get("QUICKNODE_TRON_KEY", "")
        usdt = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        if qn and "PASTE" not in qn.upper():
            base = self.config["ENTERPRISE_DATA_GATEWAYS"]["QUICKNODE_TRON_RPC"].rstrip("/")
            url = f"{base}/{qn}"
        else:
            url = (
                f"https://api.trongrid.io/v1/contracts/{usdt}/events"
                f"?event_name=Transfer&only_confirmed=true&limit=50"
            )
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url, headers={"User-Agent": "SSM/30.5.1", "Accept": "application/json"}
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            data = json.loads(raw.decode())
            values = []
            for ev in data.get("data", []):
                try:
                    r = ev.get("result", {})
                    v = r.get("value") or r.get("_value") or r.get("amount")
                    if v is None:
                        continue
                    amt = float(v) / 1e6
                    if amt >= 100:
                        values.append(amt)
                except Exception:
                    continue
            return values
        except Exception:
            return []

    def _change_point(self, series):
        if len(series) < 24:
            return False
        try:
            signal = np.array(series, dtype=float)
            if HAS_RUPTURES:
                br = rpt.Pelt(model="rbf").fit(signal).predict(pen=3.0)
                return len(br) > 1 and (len(series) - br[-2]) <= 5
            mid = len(signal) // 2
            mu, sd = float(np.mean(signal[:mid])), float(np.std(signal[:mid])) + 1e-9
            return abs(float(np.mean(signal[-5:])) - mu) / sd > 2.5
        except Exception:
            return False

    def _z_stress(self, current, history, mode):
        if len(history) < 15:
            base = sum(history) / len(history) if history else current
            if mode == "dd":
                return min(max((base - current) / max(base, 1e-9) * 4.0, 0.0), 1.0)
            return min(max((current - base) / max(base, 1e-9) * 5.0, 0.0), 1.0)
        mu, sd = float(np.mean(history)), float(np.std(history)) + 1e-9
        cdf = float(stats.norm.cdf((current - mu) / sd))
        return round(1.0 - cdf, 4) if mode == "dd" else round(cdf, 4)

    def _structural_S(self, prior: dict) -> float:
        F = float(prior.get("fiscal_pressure", 0))
        D = float(prior.get("demographic_squeeze", 0))
        B = float(prior.get("buffer_gap", 0))
        a = float(self.mix["alpha_fiscal"])
        b = float(self.mix["beta_demographic"])
        g = float(self.mix["gamma_buffer"])
        s = a + b + g
        a, b, g = (a / s, b / s, g / s) if s > 0 else (0.5, 0.35, 0.15)
        lam = float(self.defaults.get("STRUCTURAL_LAMBDA", 2.5))
        return float(min(max(1.0 - math.exp(-lam * (a * F + b * D + g * B)), 0.0), 1.0))

    def _combine(self, G: float, S: float, ground: float) -> float:
        # R primary = max(G,S); ground can lift display slightly when hot
        mode = (self.composite_mode or "max").lower()
        if mode == "soft_or":
            base = G + S - G * S
        else:
            base = max(G, S)
        lift = 0.15 * max(ground - base, 0.0)
        return float(min(max(base + lift, 0.0), 1.0))

    def _gap_and_alarms(self, G: float, S: float, ground: float) -> dict:
        """Official-calm vs ground/structural-hot → the product's core insight."""
        official = G
        alternative = max(S, ground)
        gap = float(max(alternative - official, 0.0))
        gap_thr = float(self.defaults.get("GAP_ALARM_THRESHOLD", 0.25))
        coverage = float(self.defaults.get("ASSUMED_DIGITAL_COVERAGE", 0.45))

        alarms = []
        if S >= float(self.defaults.get("CHRONIC_CRITICAL_S", 0.75)):
            alarms.append("CHRONIC_CRITICAL")
        if S >= float(self.defaults.get("CHRONIC_WATCH_S", 0.45)) and G < 0.50:
            alarms.append("SILENT_STRESS")
        if gap >= gap_thr:
            alarms.append("NARRATIVE_LAG")
        if ground >= 0.60 and G < 0.55:
            alarms.append("GROUND_DIVERGENCE")
        if ground >= 0.70:
            alarms.append("HUMANITARIAN_STRESS")
        if coverage < 0.50 and alternative >= 0.55:
            alarms.append("LOW_DIGITAL_COVERAGE_WARNING")

        return {
            "OFFICIAL_LAYER": round(official * 100, 2),
            "ALTERNATIVE_LAYER": round(alternative * 100, 2),
            "GAP_SCORE": round(gap * 100, 2),
            "ASSUMED_DIGITAL_COVERAGE": coverage,
            "ALARM_CODES": alarms,
            "ALARM_ACTIVE": len(alarms) > 0,
            "WHY": (
                "Gap = max(structural, ground) − market regime. "
                "Positive gap means official/market calm while land/structural load is higher."
            ),
        }

    async def execute_monitoring_cycle(self, country_code="US", past_risk=50.0):
        code = country_code.upper().strip()
        prior = self.priors.get(code, self.priors.get("US", {}))
        d = self.defaults

        if getattr(self, "_shared_smh", None):
            smh_hist = list(self._shared_smh)
        else:
            smh_hist = await self._fetch_prices("SMH", d["SMH_50D_AVERAGE_NORM"])
        if getattr(self, "_shared_dbb", None):
            dbb_hist = list(self._shared_dbb)
        else:
            dbb_hist = await self._fetch_prices("DBB", d["DBB_50D_AVERAGE_NORM"])
        txs = await self._fetch_usdt()
        ground_pack = await self.ground.fetch_all(code, prior)

        if txs:
            self.onchain.extend(txs)
            self.cache_stale = 0
            network = "FEED_OK"
        else:
            network = "FEED_DEGRADED"
            if self.onchain.size() == 0:
                self.cache_stale += 1

        smh = smh_hist[-1] if smh_hist else d["SMH_50D_AVERAGE_NORM"]
        dbb = dbb_hist[-1] if dbb_hist else d["DBB_50D_AVERAGE_NORM"]
        usdt_med = self.onchain.trimmed_median(
            float(prior.get("historical_median_usdt", 10000))
        )

        smh_break = self._change_point(smh_hist)
        dbb_break = self._change_point(dbb_hist)
        hs = self.high_stress_dur.get(code, 0)
        if smh_break or dbb_break or hs >= 3:
            if hs == 0:
                self.pre_crisis_smh = (
                    float(np.mean(smh_hist[-50:])) if len(smh_hist) >= 50 else smh
                )
                self.pre_crisis_dbb = (
                    float(np.mean(dbb_hist[-50:])) if len(dbb_hist) >= 50 else dbb
                )
            self.reference_mode = "pre_crisis"
        else:
            self.reference_mode = "normal"

        act_smh = (
            [self.pre_crisis_smh] * 50
            if self.reference_mode == "pre_crisis"
            else smh_hist
        )
        act_dbb = (
            [self.pre_crisis_dbb] * 50
            if self.reference_mode == "pre_crisis"
            else dbb_hist
        )

        tech = self._z_stress(smh, act_smh, "dd")
        mat_raw = self._z_stress(dbb, act_dbb, "spike")
        mat_def = max((1.0 - mat_raw) - float(prior.get("buffer_gap", 0)), 0.0)
        if mat_def > 0.6:
            mat_def *= 2.0
        base_usdt = max(float(prior.get("historical_median_usdt", 1)), 1e-9)
        flow = min(max(0.12 + ((usdt_med - base_usdt) / base_usdt) * 0.25, 0.0), 0.40)

        w = self.weights
        market_linear = (
            tech * float(w.get("w_smh", 0.35))
            + mat_def * float(w.get("w_metals", 0.25))
            + flow * float(w.get("w_flow", 0.20))
        )
        market_linear *= 1.0 + float(d.get("BASE_BLIND_SPOT", 0.1))
        market_linear += (past_risk / 100.0) * 0.08
        if self.cache_stale:
            market_linear += float(w.get("w_stale", 0.1)) * math.log(self.cache_stale + 1)

        steep = float(d.get("SIGMOID_STEEPNESS", 1.2))
        G = float(min(max(1.0 / (1.0 + math.exp(-market_linear * steep)), 0.0), 1.0))
        S = self._structural_S(prior)
        ground = float(ground_pack["GROUND_INDEX"])
        R = self._combine(G, S, ground)
        risk_pct = round(R * 100.0, 2)

        gap_block = self._gap_and_alarms(G, S, ground)

        alert, elev = float(d["ALERT_THRESHOLD"]), float(d["ELEVATED_THRESHOLD"])
        chronic_crit = float(d.get("CHRONIC_CRITICAL_S", 0.75))
        chronic_watch = float(d.get("CHRONIC_WATCH_S", 0.45))

        if risk_pct >= alert or S >= chronic_crit or ground >= 0.75:
            status = "CRITICAL"
            self.high_stress_dur[code] = hs + 1
        elif risk_pct >= elev or S >= chronic_watch or ground >= 0.45:
            status = "ELEVATED"
            self.high_stress_dur[code] = 0
        else:
            status = "NORMAL"
            self.high_stress_dur[code] = 0

        local_overlay = (
            "STRESS"
            if S >= chronic_crit
            else ("WATCH" if S >= chronic_watch else "NONE")
        )

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.db.write_triage_log(
            country=code,
            risk_pct=risk_pct,
            status_level=status,
            smh_price=float(smh),
            dbb_price=float(dbb),
            usdt_median=float(usdt_med),
            global_score=G,
            structural_score=S,
            ground_score=ground,
            gap_score=gap_block["GAP_SCORE"] / 100.0,
        )

        return {
            "COUNTRY": code,
            "TIMESTAMP_UTC": ts,
            "DISPLAY_SCORE": risk_pct,
            "STATUS": status,
            "OFFICIAL": {
                "GLOBAL_REGIME_SCORE": round(G * 100, 2),
                "SMH": round(float(smh), 2),
                "DBB": round(float(dbb), 2),
                "SMH_SOURCE": "LIVE" if abs(float(smh) - float(d["SMH_50D_AVERAGE_NORM"])) > 0.5 else "FALLBACK",
                "DBB_SOURCE": "LIVE" if abs(float(dbb) - float(d["DBB_50D_AVERAGE_NORM"])) > 0.5 else "FALLBACK",
                "USDT_MEDIAN": round(float(usdt_med), 2),
                "NETWORK": network,
                "REGIME_MARKET": self.reference_mode,
                "STRUCTURAL_BREAK_SMH": bool(smh_break),
                "STRUCTURAL_BREAK_DBB": bool(dbb_break),
            },
            "STRUCTURAL": {
                "LOCAL_STRUCTURAL_SCORE": round(S * 100, 2),
                "LOCAL_OVERLAY": local_overlay,
                "PRIOR_NOTE": prior.get("note", ""),
            },
            "GROUND": {
                "GROUND_INDEX": round(ground * 100, 2),
                "SIGNALS": {
                    k: {
                        "score": round(v["score"] * 100, 2),
                        "source": v["source"],
                        "quality": v["quality"],
                    }
                    for k, v in ground_pack["signals"].items()
                },
                "NOTE": ground_pack["coverage_note"],
            },
            "COMPARISON": gap_block,
            "DRIVERS": {
                "tech_stress": round(tech, 4),
                "materials_deficit": round(mat_def, 4),
                "stablecoin_flow": round(flow, 4),
                "fiscal_prior": round(float(prior.get("fiscal_pressure", 0)), 4),
                "demographic_prior": round(
                    float(prior.get("demographic_squeeze", 0)), 4
                ),
            },
            "COMPOSITE_MODE": self.composite_mode,
        }


async def run_all():
    core = SovereignGlobalMonitorCore()
    countries = list(core.priors.keys()) or ["US", "UA", "DE", "GB", "CN", "PL", "RU", "IL"]
    # Fetch global market series ONCE (shared across countries) — avoids Yahoo rate limits
    d = core.defaults
    print("[SSM] Fetching shared market feeds (SMH/DBB)...", flush=True)
    core._shared_smh = await core._fetch_prices("SMH", d["SMH_50D_AVERAGE_NORM"])
    core._shared_dbb = await core._fetch_prices("DBB", d["DBB_50D_AVERAGE_NORM"])
    feeds = []
    for code in countries:
        try:
            hist = core.db.fetch_historical_matrix(code, limit=1)
            past = hist[0]["risk_pct"] if hist else 50.0
            row = await core.execute_monitoring_cycle(code, past_risk=past)
            feeds.append(row)
            alarms = ",".join(row["COMPARISON"]["ALARM_CODES"]) or "—"
            print(
                f"[SSM] {code}: R={row['DISPLAY_SCORE']}% {row['STATUS']} "
                f"G={row['OFFICIAL']['GLOBAL_REGIME_SCORE']} "
                f"S={row['STRUCTURAL']['LOCAL_STRUCTURAL_SCORE']} "
                f"Ground={row['GROUND']['GROUND_INDEX']} "
                f"Gap={row['COMPARISON']['GAP_SCORE']} "
                f"alarms=[{alarms}]",
                flush=True,
            )
        except Exception as e:
            print(f"[SSM ERROR] {code}: {e}", file=sys.stderr)
            traceback.print_exc()

    report = {
        "HEADER": "SSM_HYBRID_GROUND_PASSPORT",
        "VERSION": "30.5.1",
        "DISCLAIMER": (
            "Hybrid radar: official/market (G) beside structural priors (S) and five ground "
            "signals. Gap highlights when markets look calm while land/structural load is high. "
            "Not investment advice. Ground scores are proxies + priors, not a full informal-economy census."
        ),
        "METHODOLOGY": {
            "OFFICIAL_G": "Market regime from SMH/DBB/USDT + change-point anti-drift",
            "STRUCTURAL_S": "S=1-exp(-λ(αF+βD+γB)) versioned LOCAL_PRIORS",
            "GROUND": "conflict, food, migration, mortality, physical — prior baselines + live APIs when keys exist",
            "GAP": "max(S, ground) − G; alarms when official calm and alternative hot",
            "DISPLAY_R": "max(G,S) plus small lift from ground excess",
        },
        "TIMESTAMP_UTC": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "WEIGHTS": core.weights,
        "STRUCTURAL_MIX": core.mix,
        "COMPOSITE_MODE": core.composite_mode,
        "ASSUMED_DIGITAL_COVERAGE": core.defaults.get("ASSUMED_DIGITAL_COVERAGE"),
        "DATA_DYNAMIC_FEEDS": feeds,
        "COUNTRIES_PROCESSED": len(feeds),
    }
    path = os.path.join(core.root, "ssm_unified_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[SSM] Report → {path}", flush=True)
    return report
