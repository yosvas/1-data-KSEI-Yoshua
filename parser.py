"""
parser.py — Parse KSEI monthly ownership PDFs into a clean DataFrame.
"""
import io
import re
import pdfplumber
import pandas as pd


COLUMNS = [
    "date", "share_code", "issuer_name", "investor_name",
    "investor_classification", "local_foreign", "nationality", "domicile",
    "holdings_scripless", "holdings_scrip", "total_holding_shares", "percentage",
]


def _to_float(s: str) -> float:
    """Convert Indonesian number format to float.
    '100.722.000' → 100722000.0
    '1,29'        → 1.29
    """
    if not s:
        return 0.0
    s = str(s).strip().replace(" ", "")
    if not s or s in ("-", "—"):
        return 0.0
    # Remove thousand-separator dots, then swap decimal comma to dot
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_ksei_pdf(source) -> pd.DataFrame:
    """
    Parse a KSEI monthly ownership PDF.

    Parameters
    ----------
    source : str | Path | bytes | BytesIO
        File path or raw bytes.

    Returns
    -------
    pd.DataFrame  with lowercase columns as defined in COLUMNS.
    """
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)

    raw_rows = []

    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row is None:
                        continue
                    # Normalise: pad or trim to 12 cells
                    row = list(row) + [""] * 12
                    row = row[:12]
                    # Skip header rows
                    if row[0] == "DATE":
                        continue
                    # Must have a date-like value and a share code
                    if not row[0] or not row[1]:
                        continue
                    # Sometimes date and share_code are concatenated in one cell,
                    # e.g. "30-Apr-2026AADI" — split them
                    date_cell = str(row[0]).strip()
                    m = re.match(r"(\d{2}-[A-Za-z]{3}-\d{4})([A-Z]{2,5}.*)", date_cell)
                    if m:
                        row[0] = m.group(1)
                        row[1] = (m.group(2) + str(row[1])).strip()
                    raw_rows.append(row)

    if not raw_rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame(raw_rows, columns=COLUMNS)

    # --- Parse numeric columns ---
    for col in ("holdings_scripless", "holdings_scrip", "total_holding_shares"):
        df[col] = df[col].apply(_to_float).astype("float64")

    df["percentage"] = df["percentage"].apply(_to_float)

    # --- Parse date ---
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["date"])

    # --- Strip strings ---
    str_cols = [
        "share_code", "issuer_name", "investor_name",
        "investor_classification", "local_foreign", "nationality", "domicile",
    ]
    for col in str_cols:
        df[col] = df[col].fillna("").str.strip()

    df["local_foreign"] = df["local_foreign"].str.upper()

    # Remove obvious junk rows (no investor name)
    df = df[df["investor_name"] != ""]

    return df.reset_index(drop=True)
