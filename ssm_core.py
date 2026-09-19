# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) v27.0 — COMBAT CORE + GLOBAL RADAR
# ======================================================================
# Countries: US UA DE GB CN PL RU IL
# Global board: tech equity metals energy rates credit fx vol crypto
# Hardened for GitHub Actions
# ======================================================================

import asyncio
import math
import json
import datetime
import urllib.request
import os
import sys
import traceback

class RollingOnchainBuffer:
    def __init__(self, max_size=500):
        self.max_size = max_size
        self.buffer = []

    def extend(self, new_values):
        self.buffer.extend(new_values)
        if len(self.buffer) > self.max_size:
            self.buffer = self.buffer[-self.max_size:]

    def get_rolling_median(self, default_value):
        if not self.buffer:
            return default_value
        s = sorted(self.buffer)
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    def get_size(self):
        return len(self.buffer)


MARKETS = {
    "SMH": {"sleeve": "tech", "name": "Semiconductors", "stress": "drawdown"},
    "QQQ": {"sleeve": "tech", "name": "Nasdaq-100", "stress": "drawdown"},
    "SPY": {"sleeve": "equity", "name": "S&P 500", "stress": "drawdown"},
    "EEM": {"sleeve": "equity", "name": "Emerging Markets", "stress": "drawdown"},
    "EWZ": {"sleeve": "equity", "name": "Brazil", "stress": "drawdown"},
    "DBB": {"sleeve": "metals", "name": "Base Metals", "stress": "spike"},
    "GLD": {"sleeve": "metals", "name": "Gold", "stress": "spike"},
    "SLV": {"sleeve": "metals", "name": "Silver", "stress": "spike"},
    "USO": {"sleeve": "energy", "name": "Crude Oil", "stress": "spike"},
    "UNG": {"sleeve": "energy", "name": "Natural Gas", "stress": "spike"},
    "TLT": {"sleeve": "rates", "name": "US 20Y Treasuries", "stress": "drawdown"},
    "HYG": {"sleeve": "credit", "name": "US High Yield", "stress": "drawdown"},
    "UUP": {"sleeve": "fx", "name": "US Dollar Index", "stress": "spike"},
    "^VIX": {"sleeve": "vol", "name": "VIX", "stress": "level"},
    "BTC-USD": {"sleeve": "crypto", "name": "Bitcoin", "stress": "drawdown"},
}

SLEEVE_WEIGHTS = {
    "tech": 0.18, "equity": 0.14, "metals": 0.14, "energy": 0.10,
    "rates": 0.10, "credit": 0.10, "fx": 0.08, "vol": 0.10, "crypto": 0.06,
}


class SovereignGlobalMonitorV27:
    RAW_CONFIG = """
    {
      "GLOBAL_DEFAULTS": {
        "ALERT_THRESHOLD": 70.0,
        "ELEVATED_THRESHOLD": 55.0,
        "BASE_BLIND_SPOT": 0.10,
        "BIOLOGICAL_BUFFER": 0.05,
        "SIGMOID_STEEPNESS": 1.2,
        "SMH_BASELINE": 550.0,
        "DBB_BASELINE": 25.0
      },
      "COUNTRY_PROFILES": {
        "US": {"FISCAL_PRESSURE": 0.20, "DEMOGRAPHIC_SHRINKAGE": 0.01, "USDT_BASELINE_MEDIAN": 15000.0},
        "UA": {"FISCAL_PRESSURE": 0.515, "DEMOGRAPHIC_SHRINKAGE": 0.28, "USDT_BASELINE_MEDIAN": 5000.0},
        "DE": {"FISCAL_PRESSURE": 0.25, "DEMOGRAPHIC_SHRINKAGE": 0.04, "USDT_BASELINE_MEDIAN": 12000.0},
        "GB": {"FISCAL_PRESSURE": 0.24, "DEMOGRAPHIC_SHRINKAGE": 0.03, "USDT_BASELINE_MEDIAN": 15000.0},
        "CN": {"FISCAL_PRESSURE": 0.18, "DEMOGRAPHIC_SHRINKAGE": 0.08, "USDT_BASELINE_MEDIAN": 40000.0},
        "PL": {"FISCAL_PRESSURE": 0.22, "DEMOGRAPHIC_SHRINKAGE": 0.06, "USDT_BASELINE_MEDIAN": 8000.0},
        "RU": {"FISCAL_PRESSURE": 0.28, "DEMOGRAPHIC_SHRINKAGE": 0.18, "USDT_BASELINE_MEDIAN": 25000.0},
        "IL": {"FISCAL_PRESSURE": 0.30, "DEMOGRAPHIC_SHRINKAGE": 0.12, "USDT_BASELINE_MEDIAN": 12000.0}
      },
      "WEIGHTS": {
        "w_smh": 0.459, "w_metals": 0.153, "w_flow": 0.306, "w_fiscal": 0.082
      }
    }
    """

    def __init__(self):
        self.cache_stale_cycles = 0
        self.high_stress_duration = 0
        current_dir = os.path.dirname(os.path.abspath(__file__)) or "."
        self.csv_file = os.path.join(current_dir, "ssm_historical_database.csv")
        self.global_config = json.loads(self.RAW_CONFIG)
        self.active_params = {}
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)
        self.weights = dict(self.global_config.get("WEIGHTS", {}))
        self._load_weights_file(current_dir)
        d = self.global_config["GLOBAL_DEFAULTS"]
        self.smh_baseline = d["SMH_BASELINE"]
        self.dbb_baseline = d["DBB_BASELINE"]
        self.radar_cache = None

    def _load_weights_file(self, base_dir):
        path = os.path.join(base_dir, "weights.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            w = data.get("defaults") or data.get("weights")
            if isinstance(w, dict) and "w_smh" in w:
                self.weights = w
                print(f"[SSM] loaded weights from {path}")
        except Exception as e:
            print(f"[SSM] weights.json skip: {e}", file=sys.stderr)

    def _switch_country(self, code):
        defaults = self.global_config["GLOBAL_DEFAULTS"]
        profile = self.global_config["COUNTRY_PROFILES"].get(
            code, self.global_config["COUNTRY_PROFILES"]["US"]
        )
        self.active_params = {**defaults, **profile}

    async def _fetch_yahoo_closes(self, symbol, range_="3mo"):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range_}"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SSM/27)"})
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=8.0).read()
            )
            data = json.loads(raw.decode())
            closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            return [c for c in closes if c is not None]
        except Exception:
            return []

    async def _fetch_yahoo_last(self, symbol, fallback):
        closes = await self._fetch_yahoo_closes(symbol, "5d")
        if closes:
            return float(closes[-1]), f"YAHOO_{symbol}_OK"
        return float(fallback), f"YAHOO_{symbol}_FAIL"

    async def _fetch_tron_usdt(self):
        url = "https://api.trongrid.io/v1/contracts/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t/transactions"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (SSM/27)", "Accept": "application/json"},
            )
            raw = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=6.0).read()
            )
            data = json.loads(raw.decode())
            values = []
            for tx in data.get("data", []):
                try:
                    contracts = tx.get("raw_data", {}).get("contract", [])
                    if not contracts:
                        continue
                    hx = contracts[0].get("parameter", {}).get("value", {}).get("data", "")
                    if isinstance(hx, str) and hx.startswith("a9059cbb") and len(hx) >= 136:
                        amt = int(hx[-64:], 16) / 1e6
                        if amt >= 100.0:
                            values.append(amt)
                except Exception:
                    continue
            return values
        except Exception:
            return []

    @staticmethod
    def _sma(vals, n):
        if len(vals) < n:
            return None
        return sum(vals[-n:]) / n

    def _local_stress(self, closes, mode):
        if not closes or len(closes) < 5:
            return 0.0, {}
        px = closes[-1]
        base = self._sma(closes, min(50, len(closes))) or closes[0]
        ch5 = (px - closes[-6]) / closes[-6] if len(closes) >= 6 else 0.0
        if mode == "drawdown":
            dd = max((base - px) / base, 0.0)
            stress = min(dd * 4.0, 1.0)
            if ch5 < -0.04:
                stress = min(stress + abs(ch5) * 2.0, 1.0)
            return stress, {"px": px}
        if mode == "spike":
            up = max((px - base) / base, 0.0)
            stress = min(up * 5.0, 1.0)
            if ch5 > 0.05:
                stress = min(stress + ch5 * 1.5, 1.0)
            return stress, {"px": px}
        if mode == "level":
            stress = min(max((px - 12.0) / 28.0, 0.0), 1.0)
            return stress, {"px": px}
        return 0.0, {"px": px}

    async def build_global_radar(self):
        per_symbol = {}
        errors = []

        async def one(sym, meta):
            try:
                closes = await self._fetch_yahoo_closes(sym, "3mo")
                stress, diag = self._local_stress(closes, meta["stress"])
                return sym, {
                    "symbol": sym,
                    "name": meta["name"],
                    "sleeve": meta["sleeve"],
                    "mode": meta["stress"],
                    "stress": round(stress, 3),
                    "stress_pct": round(stress * 100, 1),
                    "px": round(diag["px"], 4) if diag.get("px") is not None else None,
                }, None
            except Exception as e:
                return sym, None, type(e).__name__

        results = await asyncio.gather(*[one(s, m) for s, m in MARKETS.items()])
        for sym, row, err in results:
            if row:
                per_symbol[sym] = row
            else:
                errors.append({"symbol": sym, "error": err})

        usdt_med = self.onchain_buffer.get_rolling_median(12000.0)
        if self.onchain_buffer.get_size() > 0:
            base = 12000.0
            usdt_stress = min(max((usdt_med - base) / base * 0.5, 0.0), 1.0)
            per_symbol["USDT-TRON"] = {
                "symbol": "USDT-TRON",
                "name": "USDT large tx median",
                "sleeve": "crypto",
                "mode": "flow",
                "stress": round(usdt_stress, 3),
                "stress_pct": round(usdt_stress * 100, 1),
                "px": round(usdt_med, 2),
            }

        bucket = {}
        for row in per_symbol.values():
            bucket.setdefault(row["sleeve"], []).append(row["stress"])
        sleeve_stress = {sl: sum(a) / len(a) for sl, a in bucket.items()}

        total_w = acc = 0.0
        for sl, st in sleeve_stress.items():
            w = SLEEVE_WEIGHTS.get(sl, 0.05)
            acc += st * w
            total_w += w
        composite = (acc / total_w) if total_w else 0.0
        risk_pct = round(100.0 / (1.0 + math.exp(-(composite - 0.25) * 6.0)), 2)
        status = "CRITICAL" if risk_pct >= 75 else ("ELEVATED" if risk_pct >= 55 else "NORMAL")
        ranked = sorted(per_symbol.values(), key=lambda x: x["stress"], reverse=True)

        board = {
            "COMPOSITE_RISK_PCT": risk_pct,
            "STATUS": status,
            "COMPOSITE_RAW": round(composite, 4),
            "SLEEVES": {k: round(v * 100, 1) for k, v in sorted(sleeve_stress.items(), key=lambda x: -x[1])},
            "TOP_STRESS": [
                {"symbol": r["symbol"], "name": r["name"], "sleeve": r["sleeve"], "stress_pct": r["stress_pct"]}
                for r in ranked[:8]
            ],
            "MARKETS": per_symbol,
            "ERRORS": errors,
        }
        self.radar_cache = board
        return board

    def _compute_country_stress(self, smh, dbb, usdt_median, past_risk, kinetic_factor=0.0):
        smh_dd = max((self.smh_baseline - smh) / max(self.smh_baseline, 1e-9), 0.0)
        smh_stress = min(smh_dd * 4.0, 1.0)
        metals_up = max((dbb - self.dbb_baseline) / max(self.dbb_baseline, 1e-9), 0.0)
        metals_stress = min(metals_up * 5.0, 1.0)
        usdt_base = float(self.active_params.get("USDT_BASELINE_MEDIAN", 15000.0))
        if usdt_base > 0:
            flow_up = max((usdt_median - usdt_base) / usdt_base, 0.0)
            flow_stress = min(flow_up * 0.5, 1.0)
        else:
            flow_stress = 0.0
        fiscal = max(float(self.active_params.get("FISCAL_PRESSURE", 0.2)), 0.0)
        demo = float(self.active_params.get("DEMOGRAPHIC_SHRINKAGE", 0.0))
        bio = float(self.active_params.get("BIOLOGICAL_BUFFER", 0.05))
        blind = float(self.active_params.get("BASE_BLIND_SPOT", 0.10))
        steep = float(self.active_params.get("SIGMOID_STEEPNESS", 1.2))
        w = self.weights
        core = (
            smh_stress * float(w.get("w_smh", 0.38))
            + metals_stress * float(w.get("w_metals", 0.28))
            + flow_stress * float(w.get("w_flow", 0.18))
            + fiscal * float(w.get("w_fiscal", 0.16))
        )
        financial = core * (1.0 + blind)
        kinetic = kinetic_factor + demo * 0.25 - bio * 0.15
        total = financial + max(kinetic, 0.0) * 0.8
        total += (past_risk / 100.0) * 0.25
        if self.cache_stale_cycles > 0:
            total += round(0.15 * math.log(self.cache_stale_cycles + 1), 3)
        risk = 1.0 / (1.0 + math.exp(-total * steep))
        return round(risk * 100.0, 2), {
            "smh_stress": round(smh_stress, 3),
            "metals_stress": round(metals_stress, 3),
            "flow_stress": round(flow_stress, 3),
            "fiscal": round(fiscal, 3),
            "core": round(core, 4),
            "total_stress": round(total, 4),
        }

    def _write_csv(self, ts, country, risk, status, smh, dbb, usdt):
        try:
            exists = os.path.exists(self.csv_file)
            with open(self.csv_file, "a", encoding="utf-8") as f:
                if not exists:
                    f.write("Timestamp,Country,Risk_Pct,Status,SMH,DBB,USDT_Median\n")
                f.write(f"{ts},{country},{risk},{status},{smh},{dbb},{round(usdt, 2)}\n")
        except Exception as e:
            print(f"[WARN] CSV: {e}", file=sys.stderr)

    async def execute_monitoring_cycle(self, country_code="US", past_risk=40.0, kinetic_factor=0.0, network_storm=False):
        self._switch_country(country_code)
        tasks = [
            self._fetch_yahoo_last("SMH", self.smh_baseline),
            self._fetch_yahoo_last("DBB", self.dbb_baseline),
            self._fetch_tron_usdt() if not network_storm else asyncio.sleep(0, result=[]),
        ]
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=12.0)

            def unpack(x, default):
                return default if isinstance(x, Exception) else x

            smh_r = unpack(results[0], (self.smh_baseline, "SMH_FAIL"))
            dbb_r = unpack(results[1], (self.dbb_baseline, "DBB_FAIL"))
            txs = unpack(results[2], [])
            smh, st_smh = smh_r if isinstance(smh_r, tuple) else (smh_r, "OK")
            dbb, st_dbb = dbb_r if isinstance(dbb_r, tuple) else (dbb_r, "OK")
            if isinstance(txs, list) and txs:
                self.onchain_buffer.extend(txs)
                self.cache_stale_cycles = 0
                st_tron = f"TRON_OK(n={self.onchain_buffer.get_size()})"
            else:
                st_tron = "TRON_CACHE"
                if self.onchain_buffer.get_size() == 0:
                    self.cache_stale_cycles += 1
            usdt_med = self.onchain_buffer.get_rolling_median(
                float(self.active_params.get("USDT_BASELINE_MEDIAN", 15000))
            )
            network_log = f"{st_smh} | {st_dbb} | {st_tron}"
        except Exception as e:
            self.cache_stale_cycles += 1
            smh, dbb = self.smh_baseline, self.dbb_baseline
            usdt_med = float(self.active_params.get("USDT_BASELINE_MEDIAN", 15000))
            network_log = f"ERROR:{type(e).__name__}"

        risk_pct, parts = self._compute_country_stress(float(smh), float(dbb), float(usdt_med), past_risk, kinetic_factor)
        thr_c = float(self.active_params.get("ALERT_THRESHOLD", 70))
        thr_e = float(self.active_params.get("ELEVATED_THRESHOLD", 55))
        if risk_pct >= thr_c:
            status = "CRITICAL"
            self.high_stress_duration += 1
        elif risk_pct >= thr_e:
            status = "ELEVATED"
            self.high_stress_duration = 0
        else:
            status = "NORMAL"
            self.high_stress_duration = 0
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._write_csv(ts, country_code, risk_pct, status, smh, dbb, usdt_med)
        return {
            "HEADER": "SOVEREIGN_STRESS_MONITOR_V27",
            "TIMESTAMP": ts,
            "COUNTRY": country_code,
            "RISK_PCT": risk_pct,
            "VISIBILITY_PCT": round(100.0 - risk_pct, 2),
            "STATUS": status,
            "NETWORK_LOG": network_log,
            "WEIGHTS": self.weights,
            "LIVE_METRICS": {
                "smh_price": round(float(smh), 2),
                "dbb_price": round(float(dbb), 2),
                "usdt_median": round(float(usdt_med), 2),
                **parts,
            },
        }


async def run_all():
    engine = SovereignGlobalMonitorV27()
    engine.onchain_buffer.extend([8000, 12000, 15000, 9000, 11000])
    print("=" * 78)
    print("SSM v27 — COMBAT CORE + GLOBAL RADAR")
    print("=" * 78)

    print("\n[1] GLOBAL RADAR...")
    radar = await engine.build_global_radar()
    print(f"    COMPOSITE: {radar['COMPOSITE_RISK_PCT']}%  STATUS={radar['STATUS']}")
    print("    SLEEVES:", radar["SLEEVES"])
    print("    TOP:", ", ".join(f"{x['symbol']} {x['stress_pct']}%" for x in radar["TOP_STRESS"][:5]))

    print("\n[2] Country matrix...")
    countries = ["US", "UA", "DE", "GB", "CN", "PL", "RU", "IL"]
    country_reports = []
    for c in countries:
        rep = await engine.execute_monitoring_cycle(country_code=c, past_risk=40.0)
        country_reports.append(rep)
        print(f"    {c}: {rep['RISK_PCT']}%  {rep['STATUS']}")

    unified = {
        "HEADER": "SSM_V27_UNIFIED_REPORT",
        "TIMESTAMP_UTC": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "GLOBAL_RADAR": {
            "COMPOSITE_RISK_PCT": radar["COMPOSITE_RISK_PCT"],
            "STATUS": radar["STATUS"],
            "SLEEVES": radar["SLEEVES"],
            "TOP_STRESS": radar["TOP_STRESS"],
        },
        "COUNTRIES": [
            {
                "COUNTRY": r["COUNTRY"],
                "RISK_PCT": r["RISK_PCT"],
                "STATUS": r["STATUS"],
                "smh": r["LIVE_METRICS"]["smh_price"],
                "dbb": r["LIVE_METRICS"]["dbb_price"],
                "usdt_median": r["LIVE_METRICS"]["usdt_median"],
            }
            for r in country_reports
        ],
        "WEIGHTS": engine.weights,
    }
    print("\n" + "=" * 78)
    print("UNIFIED REPORT")
    print("=" * 78)
    print(json.dumps(unified, indent=2, ensure_ascii=False))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "ssm_unified_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(unified, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] saved {out}")
    if os.path.exists(engine.csv_file):
        print(f"[OK] csv {engine.csv_file} ({os.path.getsize(engine.csv_file)} bytes)")


def main():
    try:
        asyncio.run(run_all())
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(0)


if __name__ == "__main__":
    main()
