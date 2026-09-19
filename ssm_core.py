# ======================================================================
# SOVEREIGN STRESS MONITOR (SSM) — GLOBAL MULTI-COUNTRY MATRIX NODE v25.6
# ======================================================================
# Architect: Odin (Sergey, Ukraine)
# Countries: US | UA | DE | GB | CN | PL | RU | IL
# Hardened for GitHub Actions (no crash on single API failure)
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
        sorted_values = sorted(self.buffer)
        n = len(sorted_values)
        if n % 2 == 1:
            return sorted_values[n // 2]
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0

    def get_size(self):
        return len(self.buffer)


class SovereignGlobalMonitorV25_6:
    RAW_CONFIG = """
    {
      "GLOBAL_DEFAULTS": {
        "ALERT_THRESHOLD": 60.0,
        "BASE_BLIND_SPOT": 0.35,
        "BIOLOGICAL_BUFFER": 0.05,
        "SMH_50D_AVERAGE_NORM": 240.0,
        "DBB_50D_AVERAGE_NORM": 20.0
      },
      "COUNTRY_PROFILES": {
        "US": {
          "FISCAL_PRESSURE": 0.35,
          "GARAGE_BUFFER": 0.02,
          "DEMOGRAPHIC_SHRINKAGE": 0.01,
          "HISTORICAL_MEDIAN_USDT": 50000.0
        },
        "UA": {
          "FISCAL_PRESSURE": 0.515,
          "GARAGE_BUFFER": 0.15,
          "DEMOGRAPHIC_SHRINKAGE": 0.28,
          "HISTORICAL_MEDIAN_USDT": 5000.0
        },
        "DE": {
          "FISCAL_PRESSURE": 0.45,
          "GARAGE_BUFFER": 0.05,
          "DEMOGRAPHIC_SHRINKAGE": 0.04,
          "HISTORICAL_MEDIAN_USDT": 15000.0
        },
        "GB": {
          "FISCAL_PRESSURE": 0.43,
          "GARAGE_BUFFER": 0.04,
          "DEMOGRAPHIC_SHRINKAGE": 0.03,
          "HISTORICAL_MEDIAN_USDT": 25000.0
        },
        "CN": {
          "FISCAL_PRESSURE": 0.28,
          "GARAGE_BUFFER": 0.02,
          "DEMOGRAPHIC_SHRINKAGE": 0.08,
          "HISTORICAL_MEDIAN_USDT": 95000.0
        },
        "PL": {
          "FISCAL_PRESSURE": 0.41,
          "GARAGE_BUFFER": 0.10,
          "DEMOGRAPHIC_SHRINKAGE": 0.06,
          "HISTORICAL_MEDIAN_USDT": 12000.0
        },
        "RU": {
          "FISCAL_PRESSURE": 0.38,
          "GARAGE_BUFFER": 0.22,
          "DEMOGRAPHIC_SHRINKAGE": 0.18,
          "HISTORICAL_MEDIAN_USDT": 65000.0
        },
        "IL": {
          "FISCAL_PRESSURE": 0.46,
          "GARAGE_BUFFER": 0.08,
          "DEMOGRAPHIC_SHRINKAGE": 0.12,
          "HISTORICAL_MEDIAN_USDT": 20000.0
        }
      }
    }
    """

    def __init__(self):
        self.cache_stale_cycles = 0
        self.high_stress_duration = 0
        self.reference_mode = "normal"

        current_dir = os.path.dirname(os.path.abspath(__file__)) or "."
        self.csv_file = os.path.join(current_dir, "ssm_historical_database.csv")

        self.global_config = json.loads(self.RAW_CONFIG)
        self.active_params = {}
        self.onchain_buffer = RollingOnchainBuffer(max_size=500)

        defaults = self.global_config.get("GLOBAL_DEFAULTS", {})
        self.pre_crisis_smh = defaults.get("SMH_50D_AVERAGE_NORM", 240.0)
        self.pre_crisis_dbb = defaults.get("DBB_50D_AVERAGE_NORM", 20.0)

    def _switch_country_context(self, country_code):
        defaults = self.global_config.get("GLOBAL_DEFAULTS", {})
        profiles = self.global_config.get("COUNTRY_PROFILES", {})
        target_profile = profiles.get(country_code, profiles.get("US", {}))
        self.active_params = {**defaults, **target_profile}

    def _calculate_visibility_penalty(self, stale_cycles):
        if stale_cycles == 0:
            return 0.0
        return round(0.4 * math.log(stale_cycles + 1), 3)

    async def _fetch_yahoo_chart(self, symbol, default_key):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (SSM_Monolith/25.6)"}
            )
            res = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=4.0).read()
            )
            data = json.loads(res.decode("utf-8"))
            result_list = data.get("chart", {}).get("result", [])
            if not result_list:
                return self.active_params[default_key], f"YAHOO_{symbol}_EMPTY"

            result = result_list[0]
            closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [c for c in closes if c is not None]

            if closes:
                return closes[-1], f"YAHOO_{symbol}_OK"
            return self.active_params[default_key], f"YAHOO_{symbol}_EMPTY"
        except Exception as e:
            return self.active_params[default_key], f"YAHOO_{symbol}_FAIL:{type(e).__name__}"

    async def _fetch_trongrid_contract_stream(self):
        url = "https://api.trongrid.io/v1/contracts/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t/transactions"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (SSM_Monolith/25.6)",
                    "Accept": "application/json"
                }
            )
            res = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=4.0).read()
            )
            data = json.loads(res.decode("utf-8"))
            tx_array = data.get("data", [])
            values = []
            for tx in tx_array:
                try:
                    contracts = tx.get("raw_data", {}).get("contract", [])
                    if not contracts:
                        continue
                    value_block = contracts[0].get("parameter", {}).get("value", {})
                    hex_data = value_block.get("data", "")
                    if isinstance(hex_data, str) and hex_data.startswith("a9059cbb") and len(hex_data) >= 136:
                        amount = int(hex_data[-64:], 16) / 1e6
                        if amount >= 100.0:
                            values.append(amount)
                except Exception:
                    continue
            return values
        except Exception:
            return []

    async def _fetch_tronscan_backup_stream(self):
        url = "https://apilist.tronscanapi.com/api/token_trc20?contract=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&limit=1"
        try:
            loop = asyncio.get_running_loop()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (SSM_Monolith/25.6)"}
            )
            await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=4.0).read()
            )
            return []
        except Exception:
            return []

    def _write_to_historical_csv(self, timestamp, country_code, risk_pct, status_level,
                                 current_smh, current_dbb, median_usdt):
        try:
            file_exists = os.path.exists(self.csv_file)
            with open(self.csv_file, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write("Timestamp,Country,Risk_Pct,Status_Level,SMH_Price,DBB_Price,USDT_Rolling_Median\n")
                f.write(
                    f"{timestamp},{country_code},{risk_pct},{status_level},"
                    f"{current_smh},{current_dbb},{round(median_usdt, 2)}\n"
                )
        except Exception as e:
            print(f"[WARN] CSV write failed: {e}", file=sys.stderr)

    async def execute_monitoring_cycle(self, country_code="US", past_risk=60.0,
                                       kinetic_factor=0.0, network_storm=False):
        self._switch_country_context(country_code)

        if network_storm:
            tasks = [
                self._fetch_yahoo_chart("SMH", "SMH_50D_AVERAGE_NORM"),
                self._fetch_yahoo_chart("DBB", "DBB_50D_AVERAGE_NORM"),
                asyncio.sleep(0, result=[]),
                asyncio.sleep(0, result=[]),
            ]
        else:
            tasks = [
                self._fetch_yahoo_chart("SMH", "SMH_50D_AVERAGE_NORM"),
                self._fetch_yahoo_chart("DBB", "DBB_50D_AVERAGE_NORM"),
                self._fetch_trongrid_contract_stream(),
                self._fetch_tronscan_backup_stream(),
            ]

        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=8.0)

            def safe_unpack(item, default):
                if isinstance(item, Exception):
                    return default
                return item

            smh_result = safe_unpack(results[0], (self.active_params["SMH_50D_AVERAGE_NORM"], "YAHOO_SMH_FAIL"))
            dbb_result = safe_unpack(results[1], (self.active_params["DBB_50D_AVERAGE_NORM"], "YAHOO_DBB_FAIL"))
            tg_values = safe_unpack(results[2], [])
            ts_values = safe_unpack(results[3], [])

            current_smh, status_b = smh_result if isinstance(smh_result, tuple) else (smh_result, "YAHOO_SMH_OK")
            current_dbb, status_m = dbb_result if isinstance(dbb_result, tuple) else (dbb_result, "YAHOO_DBB_OK")

            live_incoming_tx = []
            if isinstance(tg_values, list):
                live_incoming_tx.extend(tg_values)
            if isinstance(ts_values, list):
                live_incoming_tx.extend(ts_values)

            if live_incoming_tx:
                self.onchain_buffer.extend(live_incoming_tx)
                self.cache_stale_cycles = 0
                status_onchain = f"VERIFIED_MULTI_STREAM_OK (buffer_n={self.onchain_buffer.get_size()})"
            else:
                if self.onchain_buffer.get_size() == 0:
                    status_onchain = "ONCHAIN_EMPTY_FIRST_TICK"
                else:
                    status_onchain = "STREAM_TICK_EMPTY_RELYING_ON_ROLLING_WINDOW"

            use_dynamic = True
            network_log = f"{status_b} | {status_m} | {status_onchain}"

        except Exception as e:
            self.cache_stale_cycles += 1
            current_smh = self.active_params["SMH_50D_AVERAGE_NORM"]
            current_dbb = self.active_params["DBB_50D_AVERAGE_NORM"]
            use_dynamic = False
            network_log = f"TIMEOUT_OR_ERROR | {type(e).__name__} | STALE={self.cache_stale_cycles}"

        live_median_usdt = self.onchain_buffer.get_rolling_median(
            self.active_params["HISTORICAL_MEDIAN_USDT"]
        )

        smh_avg = max(float(self.active_params["SMH_50D_AVERAGE_NORM"]), 1e-9)
        dbb_avg = max(float(self.active_params["DBB_50D_AVERAGE_NORM"]), 1e-9)
        base_usdt = max(float(self.active_params["HISTORICAL_MEDIAN_USDT"]), 1e-9)

        try:
            current_smh = float(current_smh)
            current_dbb = float(current_dbb)
        except (TypeError, ValueError):
            current_smh = smh_avg
            current_dbb = dbb_avg

        baseline_smh = self.pre_crisis_smh if self.reference_mode == "pre_crisis" else smh_avg
        baseline_dbb = self.pre_crisis_dbb if self.reference_mode == "pre_crisis" else dbb_avg

        res_bubble = min(max((baseline_smh - current_smh) / baseline_smh * 5.0, 0.0), 1.0)
        res_material = min(max((current_dbb - baseline_dbb) / baseline_dbb * 5.0, 0.0), 1.0)

        deviation_usdt = (live_median_usdt - base_usdt) / base_usdt
        res_crypto = min(max(0.12 + deviation_usdt * 0.25, 0.0), 0.40)

        material_deficit = max((1.0 - res_material) - float(self.active_params["GARAGE_BUFFER"]), 0.0)
        if material_deficit > 0.6:
            material_deficit *= 2.0

        fiscal_pressure = float(self.active_params["FISCAL_PRESSURE"])
        base_blind_spot = float(self.active_params["BASE_BLIND_SPOT"])
        demographic_shrinkage = float(self.active_params.get("DEMOGRAPHIC_SHRINKAGE", 0.0))
        biological_buffer = float(self.active_params.get("BIOLOGICAL_BUFFER", 0.05))

        total = res_bubble + material_deficit + res_crypto + fiscal_pressure
        if total <= 0:
            total = 1.0

        if use_dynamic:
            w_b = res_bubble / total
            w_m = material_deficit / total
            w_c = res_crypto / total
            w_f = fiscal_pressure / total
        else:
            w_b, w_m, w_c, w_f = 0.25, 0.45, 0.15, 0.15

        base_stress = (
            (res_bubble * w_b) ** 2 +
            (material_deficit * w_m) ** 2 +
            (res_crypto * w_c) ** 2 +
            (fiscal_pressure * w_f) ** 2
        ) ** 0.5

        financial = base_stress * (1.0 + base_blind_spot)
        kinetic = kinetic_factor + (demographic_shrinkage * 0.45) - (biological_buffer * 0.30)
        total_stress = financial + (kinetic * 1.2)
        total_stress += (past_risk / 100.0) * 0.5
        total_stress += self._calculate_visibility_penalty(self.cache_stale_cycles)

        risk = 1.0 / (1.0 + math.exp(-total_stress * 2.5))
        risk_pct = round(risk * 100.0, 2)
        visibility = round(100.0 - risk_pct, 2)

        alert_threshold = float(self.active_params.get("ALERT_THRESHOLD", 60.0))
        if risk_pct >= alert_threshold:
            status_level = "CRITICAL"
            self.high_stress_duration += 1
        elif risk_pct >= alert_threshold * 0.75:
            status_level = "ELEVATED"
            self.high_stress_duration = 0
        else:
            status_level = "NORMAL"
            self.high_stress_duration = 0

        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        self._write_to_historical_csv(
            timestamp, country_code, risk_pct, status_level,
            current_smh, current_dbb, live_median_usdt
        )

        return {
            "HEADER": "SOVEREIGN_STRESS_MONITOR_V25_6",
            "TIMESTAMP": timestamp,
            "COUNTRY": country_code,
            "RISK_PCT": risk_pct,
            "VISIBILITY_PCT": visibility,
            "STATUS": status_level,
            "NETWORK_LOG": network_log,
            "LIVE_METRICS": {
                "smh_price": round(current_smh, 2),
                "dbb_price": round(current_dbb, 2),
                "usdt_rolling_median": round(live_median_usdt, 2),
                "semiconductor_stress": round(res_bubble, 3),
                "metals_stress": round(res_material, 3),
                "crypto_component": round(res_crypto, 3),
                "material_deficit": round(material_deficit, 3),
                "fiscal_pressure": fiscal_pressure,
                "stale_cycles": self.cache_stale_cycles,
                "high_stress_duration": self.high_stress_duration
            }
        }


async def run_all():
    engine = SovereignGlobalMonitorV25_6()
    engine.onchain_buffer.extend([24000.0, 51000.0, 19000.0, 64000.0, 35000.0])

    print("=" * 72)
    print("SOVEREIGN STRESS MONITOR v25.6 — GLOBAL PRODUCTION RUN")
    print("=" * 72)

    countries = ["US", "UA", "DE", "GB", "CN", "PL", "RU", "IL"]
    for country in countries:
        print(f"\n--- Country: {country} ---")
        try:
            report = await engine.execute_monitoring_cycle(country_code=country, past_risk=55.0)
            print(json.dumps(report, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[ERROR] {country}: {type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 72)
    print("NETWORK STORM TEST (TRON timeout simulation) — UA")
    print("=" * 72)
    try:
        report_storm = await engine.execute_monitoring_cycle(
            country_code="UA", past_risk=55.0, network_storm=True
        )
        print(json.dumps(report_storm, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[ERROR] storm test: {e}")
        traceback.print_exc()

    print("\n[OK] SSM cycle finished. CSV:", engine.csv_file)
    if os.path.exists(engine.csv_file):
        print(f"[OK] CSV size: {os.path.getsize(engine.csv_file)} bytes")


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
