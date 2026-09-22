import sqlite3
import os
import sys
from datetime import datetime, timezone


class SovereignStressDB:
    def __init__(self, db_name="ssm_intelligence.db"):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(root, db_name)
        self._bootstrap()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=30.0)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _bootstrap(self):
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS historical_stress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        country TEXT NOT NULL,
                        risk_pct REAL NOT NULL,
                        status_level TEXT NOT NULL,
                        global_score REAL,
                        structural_score REAL,
                        ground_score REAL,
                        gap_score REAL,
                        smh_price REAL NOT NULL,
                        dbb_price REAL NOT NULL,
                        usdt_median REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_cc_ts ON historical_stress (country, timestamp DESC)"
                )
                conn.commit()
        except Exception as e:
            print(f"[FATAL DB] {e}", file=sys.stderr)
            sys.exit(1)

    def write_triage_log(
        self,
        country,
        risk_pct,
        status_level,
        smh_price,
        dbb_price,
        usdt_median,
        global_score=None,
        structural_score=None,
        ground_score=None,
        gap_score=None,
    ):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO historical_stress (
                        timestamp, country, risk_pct, status_level,
                        global_score, structural_score, ground_score, gap_score,
                        smh_price, dbb_price, usdt_median
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        ts,
                        country.upper().strip(),
                        round(float(risk_pct), 2),
                        status_level.strip(),
                        None if global_score is None else round(float(global_score), 4),
                        None
                        if structural_score is None
                        else round(float(structural_score), 4),
                        None if ground_score is None else round(float(ground_score), 4),
                        None if gap_score is None else round(float(gap_score), 4),
                        round(float(smh_price), 2),
                        round(float(dbb_price), 2),
                        round(float(usdt_median), 2),
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[WARN DB] {e}", file=sys.stderr)
            return False

    def fetch_historical_matrix(self, country, limit=500):
        try:
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT timestamp, risk_pct, status_level,
                           global_score, structural_score, ground_score, gap_score,
                           smh_price, dbb_price, usdt_median
                    FROM historical_stress WHERE country=?
                    ORDER BY timestamp DESC LIMIT ?
                    """,
                    (country.upper().strip(), limit),
                )
                rows = cur.fetchall()
            keys = [
                "timestamp",
                "risk_pct",
                "status_level",
                "global_score",
                "structural_score",
                "ground_score",
                "gap_score",
                "smh_price",
                "dbb_price",
                "usdt_median",
            ]
            return [dict(zip(keys, r)) for r in rows]
        except Exception as e:
            print(f"[ERROR DB] {e}", file=sys.stderr)
            return []
