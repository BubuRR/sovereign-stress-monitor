# ======================================================================
# SSM — SQLite persistence layer
# ======================================================================
import sqlite3
import os
import sys
from datetime import datetime, timezone


class SovereignStressDB:
    def __init__(self, db_name="ssm_intelligence.db"):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        # DB always lives in project root (one level above core/)
        self.db_path = os.path.join(os.path.dirname(self.current_dir), db_name)
        self._bootstrap_database()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _bootstrap_database(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historical_stress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        country TEXT NOT NULL,
                        risk_pct REAL NOT NULL,
                        status_level TEXT NOT NULL,
                        smh_price REAL NOT NULL,
                        dbb_price REAL NOT NULL,
                        usdt_median REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_country_timestamp
                    ON historical_stress (country, timestamp DESC)
                """)
                conn.commit()
        except Exception as e:
            print(f"[FATAL DB] init failed: {e}", file=sys.stderr)
            sys.exit(1)

    def write_triage_log(
        self,
        country: str,
        risk_pct: float,
        status_level: str,
        smh_price: float,
        dbb_price: float,
        usdt_median: float,
    ):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO historical_stress (
                timestamp, country, risk_pct, status_level,
                smh_price, dbb_price, usdt_median
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                conn.cursor().execute(
                    query,
                    (
                        ts,
                        country.upper().strip(),
                        round(float(risk_pct), 2),
                        status_level.strip(),
                        round(float(smh_price), 2),
                        round(float(dbb_price), 2),
                        round(float(usdt_median), 2),
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[WARN DB] write failed for {country}: {e}", file=sys.stderr)
            return False

    def fetch_historical_matrix(self, country: str, limit: int = 500):
        query = """
            SELECT timestamp, risk_pct, status_level, smh_price, dbb_price, usdt_median
            FROM historical_stress
            WHERE country = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (country.upper().strip(), limit))
                rows = cursor.fetchall()
            return [
                {
                    "timestamp": r[0],
                    "risk_pct": r[1],
                    "status_level": r[2],
                    "smh_price": r[3],
                    "dbb_price": r[4],
                    "usdt_median": r[5],
                }
                for r in rows
            ]
        except Exception as e:
            print(f"[ERROR DB] read failed for {country}: {e}", file=sys.stderr)
            return []
