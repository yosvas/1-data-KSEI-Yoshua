"""
db.py — SQLite persistence layer for KSEI ownership data.
All periods are stored cumulatively; uploading never overwrites data from
other periods.
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def _resolve_db_path() -> Path:
    """
    Determine where to store ksei.db.

    Priority:
      1. KSEI_DATA_DIR env-var (set by launcher.py when running as .exe)
      2. Next to sys.executable when frozen (PyInstaller --onedir)
      3. Next to this source file during development
    """
    env_dir = os.environ.get("KSEI_DATA_DIR")
    if env_dir:
        p = Path(env_dir) / "ksei.db"
    elif getattr(sys, "frozen", False):
        # Frozen exe: store beside the exe, not in the _internal temp dir
        p = Path(os.path.dirname(sys.executable)) / "ksei.db"
    else:
        p = Path(__file__).parent / "ksei.db"

    p.parent.mkdir(parents=True, exist_ok=True)
    return p


DB_PATH = _resolve_db_path()

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL_HOLDINGS = """
CREATE TABLE IF NOT EXISTS holdings (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    date                    TEXT    NOT NULL,
    share_code              TEXT    NOT NULL,
    issuer_name             TEXT,
    investor_name           TEXT,
    investor_classification TEXT,
    local_foreign           TEXT,
    nationality             TEXT,
    domicile                TEXT,
    holdings_scripless      REAL    DEFAULT 0,
    holdings_scrip          REAL    DEFAULT 0,
    total_holding_shares    REAL    DEFAULT 0,
    percentage              REAL    DEFAULT 0,
    source_file             TEXT
)
"""

_DDL_UPLOADS = """
CREATE TABLE IF NOT EXISTS uploads (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    filename         TEXT,
    period_date      TEXT,
    upload_timestamp TEXT,
    row_count        INTEGER
)
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_h_date       ON holdings(date)",
    "CREATE INDEX IF NOT EXISTS idx_h_share      ON holdings(share_code)",
    "CREATE INDEX IF NOT EXISTS idx_h_investor   ON holdings(investor_name)",
]


# ── Connection helper ─────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


# ── Initialisation ────────────────────────────────────────────────────────────

def init_db() -> None:
    con = _conn()
    con.execute(_DDL_HOLDINGS)
    con.execute(_DDL_UPLOADS)
    for idx in _INDEXES:
        con.execute(idx)
    con.commit()
    con.close()


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_available_periods() -> list[str]:
    """Return sorted list of available period dates as 'YYYY-MM-DD' strings."""
    con = _conn()
    rows = con.execute(
        "SELECT DISTINCT date FROM holdings ORDER BY date ASC"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def period_exists(date_str: str) -> bool:
    con = _conn()
    (n,) = con.execute(
        "SELECT COUNT(*) FROM holdings WHERE date = ?", (date_str,)
    ).fetchone()
    con.close()
    return n > 0


def load_period(date_str: str) -> pd.DataFrame:
    """Load all holdings for one period."""
    con = _conn()
    df = pd.read_sql_query(
        "SELECT * FROM holdings WHERE date = ? ORDER BY share_code, percentage DESC",
        con,
        params=(date_str,),
    )
    con.close()
    return df


def get_uploads() -> pd.DataFrame:
    """Return upload history sorted newest-first."""
    con = _conn()
    df = pd.read_sql_query(
        "SELECT filename, period_date, upload_timestamp, row_count "
        "FROM uploads ORDER BY period_date DESC",
        con,
    )
    con.close()
    return df


# ── Write helpers ─────────────────────────────────────────────────────────────

def insert_holdings(df: pd.DataFrame, filename: str) -> int:
    """
    Insert a parsed DataFrame (from parser.parse_ksei_pdf) into the DB.
    Returns the number of rows inserted.
    """
    rows = [
        (
            r.date.strftime("%Y-%m-%d"),
            r.share_code,
            r.issuer_name,
            r.investor_name,
            r.investor_classification,
            r.local_foreign,
            r.nationality,
            r.domicile,
            float(r.holdings_scripless),
            float(r.holdings_scrip),
            float(r.total_holding_shares),
            float(r.percentage),
            filename,
        )
        for r in df.itertuples()
    ]

    period_date = df["date"].iloc[0].strftime("%Y-%m-%d")

    con = _conn()
    con.executemany(
        """INSERT INTO holdings
           (date, share_code, issuer_name, investor_name, investor_classification,
            local_foreign, nationality, domicile, holdings_scripless, holdings_scrip,
            total_holding_shares, percentage, source_file)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    con.execute(
        "INSERT INTO uploads (filename, period_date, upload_timestamp, row_count) "
        "VALUES (?,?,?,?)",
        (filename, period_date, datetime.now().isoformat(), len(rows)),
    )
    con.commit()
    con.close()
    return len(rows)


def delete_period(date_str: str) -> None:
    """Remove all holdings and upload record for a given period."""
    con = _conn()
    con.execute("DELETE FROM holdings WHERE date = ?", (date_str,))
    con.execute("DELETE FROM uploads WHERE period_date = ?", (date_str,))
    con.commit()
    con.close()
