"""
analysis.py — Changelog diff and metrics computation.
All functions operate on DataFrames loaded from the DB (lowercase columns).
"""
from __future__ import annotations

import pandas as pd


# ── Changelog ─────────────────────────────────────────────────────────────────

def compute_changelog(df_old: pd.DataFrame, df_new: pd.DataFrame) -> dict:
    """
    Compare two period DataFrames and return a change summary dict:

    Keys
    ----
    new_stocks      : list[str]   – share codes that appear in new but not old
    closed_stocks   : list[str]   – share codes that were in old but not new
    changed_stocks  : list[str]   – share codes with any shareholder change
    new_entries     : list[tuple] – (share_code, investor_name) new in new period
    exits           : list[tuple] – (share_code, investor_name) gone in new period
    pct_changes     : pd.DataFrame – rows with meaningful % delta (≥ 0.01 pp)
    """
    old_stocks = set(df_old["share_code"].unique())
    new_stocks_set = set(df_new["share_code"].unique())

    new_stocks   = sorted(new_stocks_set - old_stocks)
    closed_stocks = sorted(old_stocks - new_stocks_set)

    # Build (share_code, investor_name) → percentage mapping
    def _key_pct(df):
        return df.set_index(["share_code", "investor_name"])["percentage"]

    old_kp = _key_pct(df_old)
    new_kp = _key_pct(df_new)

    old_pairs = set(old_kp.index)
    new_pairs = set(new_kp.index)

    new_entries = sorted(new_pairs - old_pairs)
    exits       = sorted(old_pairs - new_pairs)
    common_pairs = old_pairs & new_pairs

    # Percentage changes for holders that stayed
    pct_change_rows = []
    for pair in common_pairs:
        o = old_kp[pair]
        n = new_kp[pair]
        delta = n - o
        if abs(delta) >= 0.01:
            pct_change_rows.append({
                "share_code":    pair[0],
                "investor_name": pair[1],
                "old_pct":       o,
                "new_pct":       n,
                "delta":         delta,
            })

    pct_changes = (
        pd.DataFrame(pct_change_rows).sort_values("share_code")
        if pct_change_rows
        else pd.DataFrame(columns=["share_code", "investor_name", "old_pct", "new_pct", "delta"])
    )

    # Stocks with any change
    changed = set()
    for sc, _ in new_entries + exits:
        changed.add(sc)
    if not pct_changes.empty:
        changed.update(pct_changes["share_code"].tolist())
    changed_stocks = sorted(changed & (old_stocks & new_stocks_set))

    return {
        "new_stocks":     new_stocks,
        "closed_stocks":  closed_stocks,
        "changed_stocks": changed_stocks,
        "new_entries":    new_entries,
        "exits":          exits,
        "pct_changes":    pct_changes,
    }


# ── Metrics ───────────────────────────────────────────────────────────────────

def get_metrics(df: pd.DataFrame) -> dict:
    """Return aggregate statistics for the Metrik tab."""

    total_stocks    = df["share_code"].nunique()
    total_investors = df["investor_name"].nunique()
    local_investors   = df[df["local_foreign"] == "L"]["investor_name"].nunique()
    foreign_investors = df[df["local_foreign"] == "F"]["investor_name"].nunique()

    avg_holders = df.groupby("share_code").size().mean()

    total_pct    = df["percentage"].sum()
    local_pct_share = (
        df[df["local_foreign"] == "L"]["percentage"].sum() / total_pct * 100
        if total_pct > 0 else 0
    )

    # Local vs Foreign counts
    lf_counts = (
        df.groupby("local_foreign")["investor_name"]
        .nunique()
        .reset_index()
        .rename(columns={"investor_name": "count"})
    )
    lf_counts["label"] = lf_counts["local_foreign"].map({"L": "Local", "F": "Foreign"})

    # Investor type distribution
    type_counts = (
        df.groupby("investor_classification")["investor_name"]
        .nunique()
        .reset_index()
        .rename(columns={"investor_name": "count"})
        .sort_values("count", ascending=False)
    )
    type_counts["investor_classification"] = (
        type_counts["investor_classification"].replace("", "Unknown/Other")
    )

    # Top 20 investors by number of distinct stocks
    top_investors_by_stocks = (
        df.groupby("investor_name")["share_code"]
        .nunique()
        .reset_index()
        .rename(columns={"share_code": "n_stocks"})
        .sort_values("n_stocks", ascending=False)
        .head(20)
    )

    # Top 20 foreign investors by stocks
    top_foreign = (
        df[df["local_foreign"] == "F"]
        .groupby("investor_name")["share_code"]
        .nunique()
        .reset_index()
        .rename(columns={"share_code": "n_stocks"})
        .sort_values("n_stocks", ascending=False)
        .head(20)
    )

    # Stocks with most tracked shareholders
    top_stocks_by_holders = (
        df.groupby(["share_code", "issuer_name"])
        .agg(n_holders=("investor_name", "count"), total_pct=("percentage", "sum"))
        .reset_index()
        .sort_values("n_holders", ascending=False)
        .head(30)
    )

    # Country distribution of foreign investors
    foreign_by_country = (
        df[df["local_foreign"] == "F"]
        .groupby("domicile")["investor_name"]
        .nunique()
        .reset_index()
        .rename(columns={"investor_name": "count"})
        .sort_values("count", ascending=False)
        .head(20)
    )
    foreign_by_country = foreign_by_country[foreign_by_country["domicile"] != ""]

    return {
        "total_stocks":           total_stocks,
        "total_investors":        total_investors,
        "local_investors":        local_investors,
        "foreign_investors":      foreign_investors,
        "avg_holders":            avg_holders,
        "local_pct_share":        local_pct_share,
        "lf_counts":              lf_counts,
        "type_counts":            type_counts,
        "top_investors_by_stocks": top_investors_by_stocks,
        "top_foreign":            top_foreign,
        "top_stocks_by_holders":  top_stocks_by_holders,
        "foreign_by_country":     foreign_by_country,
    }


# ── Kongsi Groups ─────────────────────────────────────────────────────────────

def find_kongsi_groups(df: pd.DataFrame, min_pct: float = 5.0, min_stocks: int = 2) -> list[dict]:
    """
    Identify 'kongsi' groups: investors who hold ≥ min_pct% in ≥ min_stocks stocks.

    Returns a list of dicts, each with:
      - investor_name
      - stocks: list of (share_code, issuer_name, percentage)
      - n_stocks
    """
    # Investors with significant stakes in multiple stocks
    significant = df[df["percentage"] >= min_pct].copy()
    investor_stocks = significant.groupby("investor_name")["share_code"].nunique()
    major_investors = investor_stocks[investor_stocks >= min_stocks].index.tolist()

    groups = []
    for inv in sorted(major_investors):
        holdings = (
            significant[significant["investor_name"] == inv][
                ["share_code", "issuer_name", "percentage"]
            ]
            .sort_values("percentage", ascending=False)
        )
        groups.append({
            "investor_name": inv,
            "n_stocks":      len(holdings),
            "stocks":        holdings.to_dict("records"),
        })

    # Sort by n_stocks desc
    groups.sort(key=lambda g: g["n_stocks"], reverse=True)
    return groups
