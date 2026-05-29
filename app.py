"""
KSEI Ownership Dashboard
========================
Run:  streamlit run app.py   (from the 1persen_data folder)
"""
import json
import sys
import zipfile
from math import atan2, cos, pi, sin
from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from analysis import compute_changelog, find_kongsi_groups, get_metrics
from db import (
    DB_PATH,
    delete_period,
    get_available_periods,
    get_uploads,
    init_db,
    insert_holdings,
    load_period,
    period_exists,
)
from parser import parse_ksei_pdf

ANALYTICS_CACHE_VERSION = 2

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KSEI Ownership Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
/* === Base ================================================================ */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
}
.stApp {
    background: #f6f2ec;
    color: #2f2a25;
}
.main .block-container {
    padding-top: 0;
    padding-left: 0.75rem;
    padding-right: 0.75rem;
    max-width: 100%;
}
#MainMenu, footer, header { visibility: hidden; }

/* === Sidebar ============================================================= */
[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

/* === Tabs ================================================================ */
.stTabs [data-baseweb="tab-list"] {
    background: #fbfaf8;
    border-top: 1px solid #e8e0d8;
    border-bottom: 1px solid #e8e0d8;
    gap: 0;
    display: flex;
    width: 100%;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #a19386;
    font-size: 0.875rem;
    font-weight: 650;
    padding: 0.8rem 1rem;
    margin-bottom: -2px;
    border-radius: 0;
    flex: 1 1 0;
    justify-content: center;
}
.stTabs [aria-selected="true"] {
    color: #2f7f45;
    border-bottom-color: #2f7f45;
    font-weight: 600;
}
.stTabs [data-baseweb="tab"]:hover { color: #2f7f45; }

/* === KPI metric cards ==================================================== */
[data-testid="metric-container"] {
    background: #fffdf9;
    border: 1px solid #e8e0d8;
    border-radius: 4px;
    padding: 14px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="metric-container"] > label {
    color: #a19386 !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #2f7f45 !important;
}

/* === Expanders =========================================================== */
[data-testid="stExpander"] {
    background: #fffdf9 !important;
    border: 1px solid #e8e0d8 !important;
    border-radius: 8px !important;
    margin-bottom: 10px !important;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(44, 39, 34, 0.08);
}
[data-testid="stExpander"] summary {
    font-size: 0.875rem;
    font-weight: 750;
    color: #2f2a25;
    padding: 0.9rem 1rem;
}
[data-testid="stExpander"] summary:hover { background: #fbfaf8; }

/* === Dataframes ========================================================== */
[data-testid="stDataFrame"] {
    border: 1px solid #e8e0d8 !important;
    border-radius: 8px !important;
    overflow: hidden;
}

/* === Inputs ============================================================== */
[data-testid="stTextInput"] input {
    border-radius: 8px;
    border-color: #e8e0d8;
    background: #fffdf9;
}

/* === Badge system ======================================================== */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.6;
    white-space: nowrap;
    vertical-align: middle;
}
.bd-ticker {
    background: #14532d;
    color: #fff;
    border-radius: 5px;
    font-family: "SF Mono", "Consolas", monospace;
    font-size: 0.78rem;
    font-weight: 700;
    padding: 2px 8px;
    letter-spacing: 0.02em;
}
.bd-lokal      { background: #dcfce7; color: #15803d; }
.bd-asing      { background: #dbeafe; color: #1d4ed8; }
.bd-corporate  { background: #ede9fe; color: #6d28d9; }
.bd-bank       { background: #d1fae5; color: #065f46; }
.bd-individual { background: #fef9c3; color: #854d0e; }
.bd-insurance  { background: #fee2e2; color: #b91c1c; }
.bd-other      { background: #f1f5f9; color: #475569; }
.bd-domicile   { background: #f8fafc; color: #94a3b8;
                 border: 1px solid #e2e8f0; font-size: 0.65rem; }

/* === Detail card header ================================================== */
.det-hdr {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 3px solid #10b981;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 10px;
    line-height: 2.2;
}
.det-title { font-size: 1rem; font-weight: 700; color: #0f172a; margin: 0 8px; }
.det-meta  { font-size: 0.8rem; color: #64748b; }

/* === Section headers ===================================================== */
.sec-hdr {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #94a3b8;
    padding-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
    margin: 18px 0 10px 0;
}

/* === Reference header ==================================================== */
.ref-topbar {
    min-height: 44px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: center;
    gap: 16px;
    padding: 12px 18px;
    background: #fffdf9;
    border-bottom: 1px solid #e8e0d8;
    margin: 0 -0.75rem;
}
.ref-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #2f2a25;
}
.ref-market {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.ref-idx {
    font-size: 1.05rem;
    font-weight: 800;
}
.ref-dot {
    color: #2f7f45;
    font-weight: 900;
}
.ref-title {
    color: #7c7064;
    font-size: 1rem;
}
.ref-meta {
    color: #a19386;
    font-size: 0.78rem;
    font-weight: 600;
}
.ref-meta { text-align: right; }

/* === Changelog =========================================================== */
.chg-stock-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 8px 0 14px 0;
    border-bottom: 1px solid #efe8df;
    margin-bottom: 14px;
}
.chg-issuer {
    color: #756a60;
    font-weight: 700;
    margin-left: 10px;
}
.chg-summary {
    color: #a19386;
    font-size: 0.8rem;
    font-weight: 700;
}
.chg-empty {
    color: #a19386;
    font-size: 0.86rem;
    padding: 4px 0 10px 0;
}
.chg-rename-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
    gap: 14px;
    align-items: start;
    margin: 18px 0 8px 0;
}
.chg-rename-tile {
    position: relative;
}
.chg-rename-tile > summary {
    list-style: none;
    background: #fffdf9;
    border: 1px solid #e8e0d8;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(44, 39, 34, 0.1);
    color: #2f2a25;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 750;
    min-height: 44px;
    padding: 0 12px;
    user-select: none;
    width: 100%;
}
.chg-rename-tile > summary::-webkit-details-marker {
    display: none;
}
.chg-rename-tile > summary:hover,
.chg-rename-tile[open] > summary {
    border-color: #2f7f45;
    color: #2f7f45;
}
.chg-popover {
    background: #fffdf9;
    border: 1px solid #d7cfc5;
    border-left: 3px solid #2f7f45;
    border-radius: 8px;
    box-shadow: 0 14px 32px rgba(44, 39, 34, 0.18);
    display: none;
    left: 50%;
    max-height: 380px;
    overflow: auto;
    padding: 12px;
    position: fixed;
    top: 220px;
    transform: translateX(-50%);
    width: min(760px, calc(100vw - 48px));
    z-index: 1000;
}
.chg-rename-tile[open] .chg-popover {
    display: block;
}
.chg-popover-close {
    color: #a19386;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: 800;
    line-height: 1;
    margin-left: auto;
    padding: 2px 7px;
}
.chg-popover-close:hover {
    color: #2f2a25;
}
.chg-popover-title {
    align-items: center;
    border-bottom: 1px solid #efe8df;
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    padding-bottom: 10px;
}
.chg-popover-count {
    color: #a19386;
    font-size: 0.78rem;
    font-weight: 700;
}
.chg-rename-table {
    border-collapse: collapse;
    font-size: 0.76rem;
    width: 100%;
}
.chg-rename-table th {
    color: #a19386;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    padding: 7px 8px;
    text-align: left;
    text-transform: uppercase;
    white-space: nowrap;
}
.chg-rename-table td {
    border-top: 1px solid #efe8df;
    color: #51483f;
    padding: 8px;
    vertical-align: top;
}
.chg-rename-table code {
    color: #2f7f45;
    font-weight: 750;
    white-space: nowrap;
}
.chg-detail-card {
    background: #fffdf9;
    border: 1px solid #e8e0d8;
    border-left: 3px solid #2f7f45;
    border-radius: 6px;
    padding: 12px 14px;
    margin: 12px 0 4px 0;
}

/* === Changelog =========================================================== */
.chg-new  { color: #15803d; font-weight: 600; }
.chg-exit { color: #dc2626; font-weight: 600; }
.chg-up   { color: #0ea5e9; font-weight: 600; }
.chg-dn   { color: #f97316; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Badge helpers ─────────────────────────────────────────────────────────────
_TYPE_CLS = {
    "Corporate":  "bd-corporate",
    "Bank":       "bd-bank",
    "Individual": "bd-individual",
    "Insurance":  "bd-insurance",
}

def _b(cls: str, label: str) -> str:
    return f'<span class="badge {cls}">{label}</span>'

def b_ticker(code: str) -> str:
    return f'<span class="badge bd-ticker">{code}</span>'

def b_lf(lf: str) -> str:
    if lf == "L":
        return _b("bd-lokal", "🇮🇩 Lokal")
    if lf == "F":
        return _b("bd-asing", "🌍 Asing")
    return _b("bd-other", "Tidak Terklasifikasi")

def b_type(t: str) -> str:
    return _b(_TYPE_CLS.get(t, "bd-other"), t or "Other")

def b_dom(d: str) -> str:
    return _b("bd-domicile", d) if d else ""


def donut_chart(data, label_col, value_col, colors=None, height=360):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=data[label_col],
                values=data[value_col],
                hole=0.55,
                sort=False,
                direction="clockwise",
                textinfo="percent",
                textposition="inside",
                texttemplate="%{percent:.1%}",
                insidetextorientation="radial",
                hovertemplate="%{label}<br>%{value:,}<br>%{percent:.1%}<extra></extra>",
                marker=dict(colors=colors, line=dict(color="#f6f2ec", width=2)),
            )
        ]
    )
    fig.update_traces(automargin=True)
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=90, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.03,
            font=dict(size=12),
        ),
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    return fig


def ownership_network_chart(df, stock_code, selected_rows=None, max_holders=10, max_related=18, height=460):
    selected = (
        df[df["share_code"] == stock_code].copy()
        if selected_rows is None
        else selected_rows.copy()
    )
    selected = selected.sort_values("percentage", ascending=False).head(max_holders)
    if selected.empty:
        return None

    holders = selected["investor_name"].dropna().drop_duplicates().tolist()
    related = df[
        df["investor_name"].isin(holders) &
        (df["share_code"] != stock_code)
    ].copy()

    if related.empty:
        related_codes = []
    else:
        related_rank = (
            related.groupby(["share_code", "issuer_name"], dropna=False)
            .agg(
                n_holders=("investor_name", "nunique"),
                total_pct=("percentage", "sum"),
                max_pct=("percentage", "max"),
            )
            .reset_index()
            .sort_values(["n_holders", "total_pct", "share_code"], ascending=[False, False, True])
            .head(max_related)
        )
        related_codes = related_rank["share_code"].tolist()
        related = related[related["share_code"].isin(related_codes)]

    fig = go.Figure()
    node_x = {"stock": 0.0}
    node_y = {"stock": 0.0}
    palette = [
        "#2f7f45", "#2b7de1", "#d97706", "#dc2626", "#7c3aed",
        "#0891b2", "#65a30d", "#be185d", "#475569", "#ea580c",
    ]
    holder_color_map = {
        holder: palette[i % len(palette)]
        for i, holder in enumerate(holders)
    }

    def _hex_to_rgba(color: str, alpha: float) -> str:
        color = color.lstrip("#")
        r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    def _label_position(angle: float) -> str:
        x = cos(angle)
        y = sin(angle)
        if abs(x) > abs(y):
            return "middle right" if x >= 0 else "middle left"
        return "bottom center" if y >= 0 else "top center"

    holder_angles = {}
    if len(holders) == 1:
        holder_angles[holders[0]] = -pi / 2
    else:
        for i, holder in enumerate(holders):
            holder_angles[holder] = -pi / 2 + (2 * pi * i / len(holders))

    holder_radius = 1.12
    for holder, angle in holder_angles.items():
        node_x[f"h:{holder}"] = holder_radius * cos(angle)
        node_y[f"h:{holder}"] = holder_radius * sin(angle)

    related_angles = {}
    for code in related_codes:
        connected = related.loc[related["share_code"] == code, "investor_name"].drop_duplicates()
        angles = [holder_angles[h] for h in connected if h in holder_angles]
        if not angles:
            related_angles[code] = -pi / 2
            continue
        x = sum(cos(a) for a in angles) / len(angles)
        y = sum(sin(a) for a in angles) / len(angles)
        related_angles[code] = atan2(y, x)

    related_codes = sorted(related_codes, key=lambda code: related_angles.get(code, 0))
    angle_counts = {}
    related_radius = 2.15
    for code in related_codes:
        base_angle = related_angles.get(code, -pi / 2)
        bucket = round(base_angle, 1)
        offset_i = angle_counts.get(bucket, 0)
        angle_counts[bucket] = offset_i + 1
        offset = (offset_i - 1) * 0.12 if offset_i else 0
        radius = related_radius + (0.18 if offset_i % 2 else 0)
        angle = base_angle + offset
        related_angles[code] = angle
        node_x[f"s:{code}"] = radius * cos(angle)
        node_y[f"s:{code}"] = radius * sin(angle)

    for _, row in selected.iterrows():
        holder = row["investor_name"]
        hid = f"h:{holder}"
        width = max(1.4, min(7, 1.2 + float(row["percentage"]) / 8))
        color = holder_color_map.get(holder, "#2f7f45")
        fig.add_trace(go.Scatter(
            x=[node_x["stock"], node_x[hid]],
            y=[node_y["stock"], node_y[hid]],
            mode="lines",
            line=dict(color=_hex_to_rgba(color, 0.42), width=width),
            hoverinfo="skip",
            showlegend=False,
        ))

    for _, row in related.iterrows():
        holder = row["investor_name"]
        code = row["share_code"]
        hid = f"h:{holder}"
        sid = f"s:{code}"
        if hid not in node_x or sid not in node_x:
            continue
        color = holder_color_map.get(holder, "#756a60")
        fig.add_trace(go.Scatter(
            x=[node_x[hid], node_x[sid]],
            y=[node_y[hid], node_y[sid]],
            mode="lines",
            line=dict(color=_hex_to_rgba(color, 0.24), width=1.2),
            hoverinfo="skip",
            showlegend=False,
        ))

    issuer = (
        df.loc[df["share_code"] == stock_code, "issuer_name"].iloc[0]
        if not df.loc[df["share_code"] == stock_code].empty
        else ""
    )
    fig.add_trace(go.Scatter(
        x=[0],
        y=[0],
        mode="markers+text",
        text=[stock_code],
        textposition="bottom center",
        marker=dict(size=34, color="#2f7f45", line=dict(width=2, color="#14532d")),
        hovertemplate=f"<b>{stock_code}</b><br>{issuer}<extra></extra>",
        name="Saham utama",
    ))

    holder_hover = []
    holder_size = []
    holder_color = []
    holder_text = []
    for holder in holders:
        row = selected[selected["investor_name"] == holder].iloc[0]
        other_count = related[related["investor_name"] == holder]["share_code"].nunique()
        holder_hover.append(
            f"<b>{holder}</b><br>{stock_code}: {row['percentage']:.2f}%"
            f"<br>{other_count} saham terkait<extra></extra>"
        )
        holder_size.append(max(14, min(26, 13 + float(row["percentage"]) / 2)))
        holder_color.append(holder_color_map[holder])
        holder_text.append(holder if len(holder) <= 24 else holder[:23] + "...")

    fig.add_trace(go.Scatter(
        x=[node_x[f"h:{holder}"] for holder in holders],
        y=[node_y[f"h:{holder}"] for holder in holders],
        mode="markers+text",
        text=holder_text,
        textposition=[_label_position(holder_angles[holder]) for holder in holders],
        marker=dict(size=holder_size, color=holder_color, line=dict(width=1, color="#fffdf9")),
        hovertemplate=holder_hover,
        name="Pemegang saham",
    ))

    related_hover = []
    for code in related_codes:
        rows = related[related["share_code"] == code]
        issuer_name = rows["issuer_name"].iloc[0] if not rows.empty else ""
        related_hover.append(
            f"<b>{code}</b><br>{issuer_name}<br>"
            f"{rows['investor_name'].nunique()} pemegang terkait<extra></extra>"
        )

    if related_codes:
        fig.add_trace(go.Scatter(
            x=[node_x[f"s:{code}"] for code in related_codes],
            y=[node_y[f"s:{code}"] for code in related_codes],
            mode="markers+text",
            text=related_codes,
            textposition=[_label_position(related_angles[code]) for code in related_codes],
            marker=dict(size=16, color="#6aa7de", line=dict(width=1, color="#fffdf9")),
            hovertemplate=related_hover,
            name="Saham terkait",
        ))

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(visible=False, range=[-2.75, 2.75]),
        yaxis=dict(visible=False, range=[-2.75, 2.75], scaleanchor="x", scaleratio=1),
        dragmode="pan",
        hovermode="closest",
        font=dict(size=11, color="#51483f"),
    )
    return fig


def ownership_network_html(df, stock_code, selected_rows=None, max_holders=10, max_related=18, height=620):
    selected = (
        df[df["share_code"] == stock_code].copy()
        if selected_rows is None
        else selected_rows.copy()
    )
    selected = selected.sort_values("percentage", ascending=False).head(max_holders)
    if selected.empty:
        return ""

    holders = selected["investor_name"].dropna().drop_duplicates().tolist()
    related = df[
        df["investor_name"].isin(holders) &
        (df["share_code"] != stock_code)
    ].copy()

    if related.empty:
        related_codes = []
    else:
        related_rank = (
            related.groupby(["share_code", "issuer_name"], dropna=False)
            .agg(
                n_holders=("investor_name", "nunique"),
                total_pct=("percentage", "sum"),
            )
            .reset_index()
            .sort_values(["n_holders", "total_pct", "share_code"], ascending=[False, False, True])
            .head(max_related)
        )
        related_codes = related_rank["share_code"].tolist()
        related = related[related["share_code"].isin(related_codes)]

    palette = [
        "#2f7f45", "#2b7de1", "#d97706", "#dc2626", "#7c3aed",
        "#0891b2", "#65a30d", "#be185d", "#475569", "#ea580c",
    ]
    holder_color_map = {
        holder: palette[i % len(palette)]
        for i, holder in enumerate(holders)
    }

    def _hex_to_rgba(color: str, alpha: float) -> str:
        color = color.lstrip("#")
        r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    def _short(text: str, limit: int = 24) -> str:
        text = str(text)
        return text if len(text) <= limit else text[:limit - 1] + "..."

    holder_angles = {}
    if len(holders) == 1:
        holder_angles[holders[0]] = -pi / 2
    else:
        for i, holder in enumerate(holders):
            holder_angles[holder] = -pi / 2 + (2 * pi * i / len(holders))

    related_angles = {}
    for code in related_codes:
        connected = related.loc[related["share_code"] == code, "investor_name"].drop_duplicates()
        angles = [holder_angles[h] for h in connected if h in holder_angles]
        if not angles:
            related_angles[code] = -pi / 2
            continue
        x = sum(cos(a) for a in angles) / len(angles)
        y = sum(sin(a) for a in angles) / len(angles)
        related_angles[code] = atan2(y, x)

    related_codes = sorted(related_codes, key=lambda code: related_angles.get(code, 0))
    issuer = (
        df.loc[df["share_code"] == stock_code, "issuer_name"].iloc[0]
        if not df.loc[df["share_code"] == stock_code].empty
        else ""
    )

    width = 1000
    center_x = width / 2
    center_y = height / 2
    holder_radius = min(190, height * 0.30)
    related_radius = min(290, height * 0.44)

    nodes = [{
        "id": "stock",
        "label": stock_code,
        "type": "stock",
        "x": center_x,
        "y": center_y,
        "r": 22,
        "color": "#2f7f45",
        "title": f"{stock_code}\\n{issuer}",
    }]
    edges = []

    holder_ids = {}
    for holder in holders:
        row = selected[selected["investor_name"] == holder].iloc[0]
        angle = holder_angles[holder]
        node_id = f"h{len(holder_ids)}"
        holder_ids[holder] = node_id
        color = holder_color_map[holder]
        nodes.append({
            "id": node_id,
            "label": _short(holder),
            "type": "holder",
            "x": center_x + holder_radius * cos(angle),
            "y": center_y + holder_radius * sin(angle),
            "r": max(13, min(24, 12 + float(row["percentage"]) / 2)),
            "color": color,
            "title": f"{holder}\\n{stock_code}: {row['percentage']:.2f}%",
        })
        edges.append({
            "source": "stock",
            "target": node_id,
            "color": _hex_to_rgba(color, 0.42),
            "width": max(1.4, min(7, 1.2 + float(row["percentage"]) / 8)),
        })

    angle_counts = {}
    stock_ids = {}
    for code in related_codes:
        base_angle = related_angles.get(code, -pi / 2)
        bucket = round(base_angle, 1)
        offset_i = angle_counts.get(bucket, 0)
        angle_counts[bucket] = offset_i + 1
        angle = base_angle + ((offset_i - 1) * 0.16 if offset_i else 0)
        radius = related_radius + (18 if offset_i % 2 else 0)
        rows = related[related["share_code"] == code]
        issuer_name = rows["issuer_name"].iloc[0] if not rows.empty else ""
        node_id = f"s{len(stock_ids)}"
        stock_ids[code] = node_id
        nodes.append({
            "id": node_id,
            "label": code,
            "type": "related",
            "x": center_x + radius * cos(angle),
            "y": center_y + radius * sin(angle),
            "r": 13,
            "color": "#6aa7de",
            "title": f"{code}\\n{issuer_name}\\n{rows['investor_name'].nunique()} pemegang terkait",
        })

    for _, row in related.iterrows():
        holder = row["investor_name"]
        code = row["share_code"]
        if holder not in holder_ids or code not in stock_ids:
            continue
        color = holder_color_map.get(holder, "#756a60")
        edges.append({
            "source": holder_ids[holder],
            "target": stock_ids[code],
            "color": _hex_to_rgba(color, 0.28),
            "width": 1.2,
        })

    payload = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)
    return f"""
<div id="network-wrap">
  <svg id="network-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Jaringan koneksi saham">
    <g id="edges"></g>
    <g id="nodes"></g>
  </svg>
</div>
<style>
  #network-wrap {{
    background: #fffdf9;
    border: 1px solid #e8e0d8;
    border-radius: 8px;
    height: {height}px;
    overflow: hidden;
    touch-action: none;
  }}
  #network-svg {{
    width: 100%;
    height: 100%;
    cursor: grab;
    user-select: none;
  }}
  #network-svg.dragging {{ cursor: grabbing; }}
  .edge {{ fill: none; stroke-linecap: round; }}
  .node circle {{ stroke: #fffdf9; stroke-width: 2; filter: drop-shadow(0 1px 2px rgba(44,39,34,.22)); }}
  .node text {{ fill: #51483f; font: 700 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; paint-order: stroke; stroke: #fffdf9; stroke-width: 4px; }}
  .node.stock text {{ font-size: 15px; fill: #14532d; }}
  .node.related text {{ font-size: 11px; fill: #315f91; }}
</style>
<script>
(() => {{
  const data = {payload};
  const svg = document.getElementById("network-svg");
  const edgesLayer = document.getElementById("edges");
  const nodesLayer = document.getElementById("nodes");
  const nodesById = new Map(data.nodes.map(n => [n.id, n]));
  let active = null;

  function svgPoint(evt) {{
    const point = svg.createSVGPoint();
    const source = evt.touches ? evt.touches[0] : evt;
    point.x = source.clientX;
    point.y = source.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  }}

  function labelAnchor(node) {{
    const dx = node.x - {center_x};
    const dy = node.y - {center_y};
    if (Math.abs(dx) > Math.abs(dy)) {{
      return dx >= 0 ? ["start", node.r + 8, 4] : ["end", -node.r - 8, 4];
    }}
    return dy >= 0 ? ["middle", 0, node.r + 18] : ["middle", 0, -node.r - 10];
  }}

  function render() {{
    edgesLayer.innerHTML = "";
    for (const edge of data.edges) {{
      const a = nodesById.get(edge.source);
      const b = nodesById.get(edge.target);
      if (!a || !b) continue;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("class", "edge");
      line.setAttribute("x1", a.x);
      line.setAttribute("y1", a.y);
      line.setAttribute("x2", b.x);
      line.setAttribute("y2", b.y);
      line.setAttribute("stroke", edge.color);
      line.setAttribute("stroke-width", edge.width);
      edgesLayer.appendChild(line);
    }}

    nodesLayer.innerHTML = "";
    for (const node of data.nodes) {{
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("class", `node ${{node.type}}`);
      group.setAttribute("data-id", node.id);
      group.setAttribute("transform", `translate(${{node.x}},${{node.y}})`);

      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = node.title;
      group.appendChild(title);

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("r", node.r);
      circle.setAttribute("fill", node.color);
      group.appendChild(circle);

      const [anchor, tx, ty] = labelAnchor(node);
      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", tx);
      text.setAttribute("y", ty);
      text.setAttribute("text-anchor", anchor);
      text.textContent = node.label;
      group.appendChild(text);

      group.addEventListener("mousedown", startDrag);
      group.addEventListener("touchstart", startDrag, {{ passive: false }});
      nodesLayer.appendChild(group);
    }}
  }}

  function startDrag(evt) {{
    evt.preventDefault();
    const id = evt.currentTarget.getAttribute("data-id");
    const node = nodesById.get(id);
    const point = svgPoint(evt);
    active = {{ node, dx: point.x - node.x, dy: point.y - node.y }};
    svg.classList.add("dragging");
  }}

  function drag(evt) {{
    if (!active) return;
    evt.preventDefault();
    const point = svgPoint(evt);
    active.node.x = Math.max(25, Math.min({width - 25}, point.x - active.dx));
    active.node.y = Math.max(25, Math.min({height - 25}, point.y - active.dy));
    render();
  }}

  function endDrag() {{
    active = null;
    svg.classList.remove("dragging");
  }}

  window.addEventListener("mousemove", drag);
  window.addEventListener("mouseup", endDrag);
  window.addEventListener("touchmove", drag, {{ passive: false }});
  window.addEventListener("touchend", endDrag);
  render();
}})();
</script>
"""


def _lf_text(value):
    if value == "L":
        return "Lokal"
    if value == "F":
        return "Asing"
    return "Tidak Terklasifikasi"


def _data_dictionary():
    return pd.DataFrame([
        {"sheet": "ai_holdings", "column": "period_date", "description": "KSEI report period date."},
        {"sheet": "ai_holdings", "column": "ticker", "description": "IDX stock ticker."},
        {"sheet": "ai_holdings", "column": "issuer_name", "description": "Listed company / issuer name."},
        {"sheet": "ai_holdings", "column": "investor_name", "description": "Shareholder name as reported by KSEI."},
        {"sheet": "ai_holdings", "column": "investor_type", "description": "Investor classification, e.g. Corporate, Bank, Individual."},
        {"sheet": "ai_holdings", "column": "local_foreign_label", "description": "Lokal, Asing, or Tidak Terklasifikasi."},
        {"sheet": "ai_holdings", "column": "ownership_pct", "description": "Ownership percentage in percentage points, e.g. 5.25 means 5.25%."},
        {"sheet": "ai_holdings", "column": "ownership_decimal", "description": "Ownership share as decimal, e.g. 0.0525 means 5.25%."},
        {"sheet": "ai_holdings", "column": "rank_in_ticker", "description": "Ownership rank within the same ticker, highest percentage is 1."},
        {"sheet": "stock_summary", "column": "tracked_ownership_pct", "description": "Sum of all tracked holders' ownership percentage for a ticker."},
        {"sheet": "investor_summary", "column": "stock_count", "description": "Number of tickers held by the investor in this dataset."},
        {"sheet": "changelog_*", "column": "delta_pct_points", "description": "Change in ownership percentage points between previous and selected periods."},
    ])


@st.cache_data(show_spinner=False)
def _build_ai_export_frames(date_str: str, previous_period: str | None, db_mtime: float) -> dict:
    period_df = load_period(date_str).copy()
    period_df["period_date"] = pd.to_datetime(period_df["date"]).dt.strftime("%Y-%m-%d")
    period_df["local_foreign_label"] = period_df["local_foreign"].apply(_lf_text)

    stock_summary = (
        period_df.groupby(["share_code", "issuer_name"], dropna=False)
        .agg(
            holder_rows=("investor_name", "count"),
            unique_investors=("investor_name", "nunique"),
            tracked_ownership_pct=("percentage", "sum"),
            local_holder_rows=("local_foreign", lambda s: (s == "L").sum()),
            foreign_holder_rows=("local_foreign", lambda s: (s == "F").sum()),
            unclassified_holder_rows=("local_foreign", lambda s: (~s.isin(["L", "F"])).sum()),
            total_tracked_shares=("total_holding_shares", "sum"),
        )
        .reset_index()
        .rename(columns={"share_code": "ticker"})
        .sort_values(["tracked_ownership_pct", "ticker"], ascending=[False, True])
    )

    investor_summary = (
        period_df.groupby(
            ["investor_name", "investor_classification", "local_foreign", "local_foreign_label", "domicile"],
            dropna=False,
        )
        .agg(
            stock_count=("share_code", "nunique"),
            total_tracked_ownership_pct_sum=("percentage", "sum"),
            total_holding_shares_sum=("total_holding_shares", "sum"),
        )
        .reset_index()
        .rename(columns={
            "investor_classification": "investor_type",
            "local_foreign": "local_foreign_code",
        })
        .sort_values(["stock_count", "total_tracked_ownership_pct_sum"], ascending=[False, False])
    )

    stock_for_merge = stock_summary[["ticker", "holder_rows", "tracked_ownership_pct"]].rename(
        columns={
            "holder_rows": "ticker_holder_rows",
            "tracked_ownership_pct": "ticker_tracked_ownership_pct",
        }
    )
    investor_for_merge = investor_summary[
        ["investor_name", "stock_count", "total_tracked_ownership_pct_sum"]
    ].rename(columns={
        "stock_count": "investor_stock_count",
        "total_tracked_ownership_pct_sum": "investor_total_tracked_pct_sum",
    })

    holdings = period_df.copy()
    holdings["rank_in_ticker"] = (
        holdings.groupby("share_code")["percentage"].rank(method="first", ascending=False).astype(int)
    )
    holdings["ownership_decimal"] = holdings["percentage"] / 100
    holdings = holdings.rename(columns={
        "share_code": "ticker",
        "investor_classification": "investor_type",
        "local_foreign": "local_foreign_code",
        "percentage": "ownership_pct",
    })
    holdings = holdings.merge(stock_for_merge, on="ticker", how="left")
    holdings = holdings.merge(investor_for_merge, on="investor_name", how="left")
    holdings = holdings[
        [
            "period_date", "ticker", "issuer_name", "investor_name", "investor_type",
            "local_foreign_code", "local_foreign_label", "nationality", "domicile",
            "holdings_scripless", "holdings_scrip", "total_holding_shares",
            "ownership_pct", "ownership_decimal", "rank_in_ticker",
            "ticker_holder_rows", "ticker_tracked_ownership_pct",
            "investor_stock_count", "investor_total_tracked_pct_sum",
            "source_file",
        ]
    ].sort_values(["ticker", "rank_in_ticker", "investor_name"])

    frames = {
        "ai_holdings": holdings,
        "stock_summary": stock_summary,
        "investor_summary": investor_summary,
        "data_dictionary": _data_dictionary(),
    }

    if previous_period:
        previous_df = load_period(previous_period)
        chg = compute_changelog(previous_df, period_df)

        entry_counts = pd.Series([code for code, _ in chg["new_entries"]]).value_counts()
        exit_counts = pd.Series([code for code, _ in chg["exits"]]).value_counts()
        pct_counts = (
            chg["pct_changes"].groupby("share_code").size()
            if not chg["pct_changes"].empty
            else pd.Series(dtype="int64")
        )
        rename_counts = pd.Series([r["share_code"] for r in chg["suspected_renames"]]).value_counts()
        changed_codes = sorted(set(chg["changed_stocks"]) | set(chg["new_stocks"]) | set(chg["closed_stocks"]))
        frames["changelog_summary"] = pd.DataFrame([{
            "ticker": code,
            "issuer_name": (
                period_df.loc[period_df["share_code"] == code, "issuer_name"].iloc[0]
                if not period_df.loc[period_df["share_code"] == code].empty
                else (
                    previous_df.loc[previous_df["share_code"] == code, "issuer_name"].iloc[0]
                    if not previous_df.loc[previous_df["share_code"] == code].empty
                    else ""
                )
            ),
            "is_new_stock": code in chg["new_stocks"],
            "is_closed_stock": code in chg["closed_stocks"],
            "new_holder_count": int(entry_counts.get(code, 0)),
            "exited_holder_count": int(exit_counts.get(code, 0)),
            "pct_changed_holder_count": int(pct_counts.get(code, 0)),
            "suspected_rename_count": int(rename_counts.get(code, 0)),
        } for code in changed_codes])

        frames["changelog_new_holders"] = pd.DataFrame(
            chg["new_entries"], columns=["ticker", "investor_name"]
        )
        frames["changelog_exited_holders"] = pd.DataFrame(
            chg["exits"], columns=["ticker", "investor_name"]
        )
        pct_changes = chg["pct_changes"].rename(columns={
            "share_code": "ticker",
            "old_pct": f"ownership_pct_{previous_period}",
            "new_pct": f"ownership_pct_{date_str}",
            "delta": "delta_pct_points",
        })
        frames["changelog_pct_changes"] = pct_changes
        frames["suspected_name_changes"] = pd.DataFrame(chg["suspected_renames"]).rename(columns={
            "share_code": "ticker",
            "old_pct": f"ownership_pct_{previous_period}",
            "new_pct": f"ownership_pct_{date_str}",
        })

    return frames


@st.cache_data(show_spinner=False)
def _export_excel_bytes(date_str: str, previous_period: str | None, db_mtime: float) -> bytes:
    frames = _build_ai_export_frames(date_str, previous_period, db_mtime)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, frame in frames.items():
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def _export_csv_zip_bytes(date_str: str, previous_period: str | None, db_mtime: float) -> bytes:
    frames = _build_ai_export_frames(date_str, previous_period, db_mtime)
    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, frame in frames.items():
            zf.writestr(f"{name}.csv", frame.to_csv(index=False, encoding="utf-8-sig"))
    return output.getvalue()

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()


# ── Cached data loader ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load(date_str: str) -> pd.DataFrame:
    return load_period(date_str)


@st.cache_data(show_spinner=False)
def _changelog_between(p_from: str, p_to: str, db_mtime: float, cache_version: int) -> dict:
    return compute_changelog(load_period(p_from), load_period(p_to))


@st.cache_data(show_spinner=False)
def _metrics_for_period(date_str: str, db_mtime: float, cache_version: int) -> dict:
    return get_metrics(load_period(date_str))


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📊 KSEI 1% Ownership")
    st.markdown("---")

    st.markdown("### 📁 Upload New Period")
    uploaded = st.file_uploader(
        "Upload KSEI PDF",
        type=["pdf"],
        help="Monthly KSEI ownership report PDF",
        label_visibility="collapsed",
    )

    if uploaded is not None:
        with st.spinner(f"Parsing **{uploaded.name}** …"):
            try:
                df_parsed = parse_ksei_pdf(uploaded.read())
            except Exception as exc:
                st.error(f"Parse error: {exc}")
                df_parsed = None

        if df_parsed is not None and df_parsed.empty:
            st.error("No data found in this PDF. Check the file.")
            df_parsed = None

        if df_parsed is not None:
            period_str   = df_parsed["date"].iloc[0].strftime("%Y-%m-%d")
            period_label_up = df_parsed["date"].iloc[0].strftime("%d %b %Y")
            n_rows       = len(df_parsed)

            if period_exists(period_str):
                st.warning(f"Period **{period_label_up}** is already in the database.")
                col1, col2 = st.columns(2)
                if col1.button("🔄 Replace", use_container_width=True):
                    delete_period(period_str)
                    _load.clear()
                    _metrics_for_period.clear()
                    _changelog_between.clear()
                    _build_ai_export_frames.clear()
                    _export_excel_bytes.clear()
                    _export_csv_zip_bytes.clear()
                    insert_holdings(df_parsed, uploaded.name)
                    st.success(f"Replaced — {n_rows:,} rows")
                    st.rerun()
                if col2.button("Skip", use_container_width=True):
                    st.info("Skipped — no changes made.")
            else:
                insert_holdings(df_parsed, uploaded.name)
                _load.clear()
                _metrics_for_period.clear()
                _changelog_between.clear()
                _build_ai_export_frames.clear()
                _export_excel_bytes.clear()
                _export_csv_zip_bytes.clear()
                st.success(f"✅ **{period_label_up}** uploaded — {n_rows:,} rows")
                st.rerun()

    st.markdown("---")

    periods = get_available_periods()

    if not periods:
        st.info("No data yet.\nUpload a PDF to get started.")
        st.stop()

    period_labels = {p: pd.to_datetime(p).strftime("%d %b %Y") for p in periods}
    selected = st.selectbox(
        "📅 View period",
        options=periods,
        format_func=lambda x: period_labels[x],
        index=len(periods) - 1,
    )

    st.markdown("---")
    st.markdown("### ⬇️ Export Data")
    export_previous = max([p for p in periods if p < selected], default=None)
    export_mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0
    export_label = pd.to_datetime(selected).strftime("%Y%m%d")
    export_help = (
        "AI-friendly export: normalized holdings, stock summary, investor summary, "
        "data dictionary, and changelog sheets when a previous period exists."
    )
    export_state_key = f"{selected}:{export_previous}:{export_mtime}"
    if st.session_state.get("export_state_key") != export_state_key:
        st.session_state.pop("excel_export_bytes", None)
        st.session_state.pop("csv_export_bytes", None)
        st.session_state["export_state_key"] = export_state_key

    if st.button("Generate Export Files", help=export_help, use_container_width=True):
        with st.spinner("Menyiapkan file export..."):
            st.session_state["excel_export_bytes"] = _export_excel_bytes(
                selected, export_previous, export_mtime
            )
            st.session_state["csv_export_bytes"] = _export_csv_zip_bytes(
                selected, export_previous, export_mtime
            )

    if "excel_export_bytes" in st.session_state and "csv_export_bytes" in st.session_state:
        st.download_button(
            "Download Excel",
            data=st.session_state["excel_export_bytes"],
            file_name=f"ksei_ai_export_{export_label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help=export_help,
            use_container_width=True,
        )
        st.download_button(
            "Download CSV ZIP",
            data=st.session_state["csv_export_bytes"],
            file_name=f"ksei_ai_export_{export_label}_csv.zip",
            mime="application/zip",
            help=export_help,
            use_container_width=True,
        )

    uploads_df = get_uploads()
    if not uploads_df.empty:
        st.markdown("---")
        st.markdown("### 📋 Uploaded Periods")
        for _, row in uploads_df.iterrows():
            d = pd.to_datetime(row["period_date"]).strftime("%d %b %Y")
            st.markdown(
                f"**{d}** · {int(row['row_count']):,} rows  \n"
                f"<small style='color:#94a3b8'>{row['filename']}</small>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
period_label = pd.to_datetime(selected).strftime("%d %b %Y")

st.markdown(
    f"""
    <div class="ref-topbar">
        <div class="ref-brand">
            <span class="ref-market">ID</span>
            <span class="ref-idx">IDX</span>
            <span class="ref-dot">·</span>
            <span class="ref-title">1% Ownership</span>
        </div>
        <div class="ref-meta">Per {period_label} &nbsp; · &nbsp; Sumber: KSEI</div>
    </div>
    """,
    unsafe_allow_html=True,
)

page_status = st.empty()
page_progress = page_status.progress(5, text="Menyiapkan dashboard dan membaca database...")
db_mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0
df = _load(selected)
page_progress.progress(25, text="Data periode dimuat. Menyusun filter...")

all_types = ["Semua"] + sorted(
    df["investor_classification"].replace("", pd.NA).dropna().unique()
)

tabs = st.tabs([
    "📋 Ringkasan Saham",
    "👤 Per Investor",
    "🔗 Konglo Stocks",
    "📈 Metrik",
    "🔄 Changelog",
])
tab_saham, tab_investor, tab_kongsi, tab_metrik, tab_changelog = tabs


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RINGKASAN SAHAM
# ══════════════════════════════════════════════════════════════════════════════
page_progress.progress(35, text="Menyusun Ringkasan Saham...")
with tab_saham:
    fc1, fc2, fc3, fc4 = st.columns([3, 1, 2, 1])
    q        = fc1.text_input("🔍 Cari kode saham atau nama emiten", placeholder="e.g. BBCA / BCA", key="qs")
    lf       = fc2.selectbox("L/F", ["Semua", "Lokal", "Asing"], key="lfs")
    inv_type = fc3.selectbox("Tipe Investor", all_types, key="its")
    sort_by  = fc4.selectbox("Urutkan", ["Kode", "# Holders ↓"], key="sbs")

    stock_meta = (
        df.groupby(["share_code", "issuer_name"])
        .agg(
            n_holders =("investor_name",  "count"),
            total_pct =("percentage",     "sum"),
            n_local   =("local_foreign",  lambda x: (x == "L").sum()),
            n_foreign =("local_foreign",  lambda x: (x == "F").sum()),
        )
        .reset_index()
    )

    if q:
        q_lo = q.lower()
        stock_meta = stock_meta[
            stock_meta["share_code"].str.lower().str.contains(q_lo, na=False) |
            stock_meta["issuer_name"].str.lower().str.contains(q_lo, na=False)
        ]

    if sort_by == "# Holders ↓":
        stock_meta = stock_meta.sort_values("n_holders", ascending=False)
    else:
        stock_meta = stock_meta.sort_values("share_code")

    st.markdown(f"**{len(stock_meta):,} emiten**")

    disp_meta = stock_meta[["share_code", "issuer_name", "n_holders", "total_pct", "n_local", "n_foreign"]].copy()
    disp_meta.columns = ["Kode", "Emiten", "Holders", "% Tracked", "Lokal", "Asing"]
    disp_meta["% Tracked"] = disp_meta["% Tracked"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(disp_meta, width="stretch", hide_index=True)

    if not stock_meta.empty:
        detail_code = st.selectbox(
            "Detail pemegang saham — pilih emiten:",
            ["—"] + stock_meta["share_code"].tolist(),
            key="detail_code",
        )
        if detail_code != "—":
            sm_row = stock_meta[stock_meta["share_code"] == detail_code]
            if not sm_row.empty:
                sm = sm_row.iloc[0]
                n_loc, n_for = int(sm["n_local"]), int(sm["n_foreign"])
                st.markdown(
                    f'<div class="det-hdr">'
                    f'{b_ticker(detail_code)}'
                    f'<span class="det-title">{sm["issuer_name"]}</span>'
                    f'<span class="det-meta">{int(sm["n_holders"])} holders &nbsp;·&nbsp; '
                    f'<b>{sm["total_pct"]:.2f}%</b> tracked</span>'
                    f'&nbsp;&nbsp;{_b("bd-lokal", f"{n_loc} Lokal")}'
                    f'&nbsp;{_b("bd-asing", f"{n_for} Asing")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            sub = df[df["share_code"] == detail_code].copy()
            if lf == "Lokal":
                sub = sub[sub["local_foreign"] == "L"]
            elif lf == "Asing":
                sub = sub[sub["local_foreign"] == "F"]
            if inv_type != "Semua":
                sub = sub[sub["investor_classification"] == inv_type]

            if sub.empty:
                st.info("No data matches current filters.")
            else:
                disp = sub[
                    ["investor_name", "investor_classification", "local_foreign",
                     "domicile", "total_holding_shares", "percentage"]
                ].copy()
                disp = disp.sort_values("percentage", ascending=False)
                disp.columns = ["Investor", "Tipe", "L/F", "Domisil", "Saham", "%"]
                disp["Saham"] = disp["Saham"].apply(lambda x: f"{int(x):,}")
                disp["%"]     = disp["%"].apply(lambda x: f"{x:.2f}%")
                st.dataframe(disp, width="stretch", hide_index=True)

                st.markdown('<p class="sec-hdr">Jaringan Koneksi</p>', unsafe_allow_html=True)
                nc1, nc2, nc3, _ = st.columns([1, 1, 1.4, 3.6])
                max_holders = nc1.slider("Max holders", 3, 20, 10, 1, key=f"net_h_{detail_code}")
                max_related = nc2.slider("Max saham terkait", 5, 40, 18, 1, key=f"net_s_{detail_code}")
                net_mode = nc3.selectbox(
                    "Mode diagram",
                    ["Drag nodes", "Pan/zoom"],
                    key=f"net_mode_{detail_code}",
                )
                if net_mode == "Drag nodes":
                    st.iframe(
                        ownership_network_html(
                            df,
                            detail_code,
                            selected_rows=sub,
                            max_holders=max_holders,
                            max_related=max_related,
                        ),
                        height=635,
                    )
                else:
                    net_fig = ownership_network_chart(
                        df,
                        detail_code,
                        selected_rows=sub,
                        max_holders=max_holders,
                        max_related=max_related,
                    )
                    if net_fig is not None:
                        st.plotly_chart(
                            net_fig,
                            width="stretch",
                            config={"displayModeBar": True, "scrollZoom": True},
                        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PER INVESTOR
# ══════════════════════════════════════════════════════════════════════════════
page_progress.progress(50, text="Menyusun Per Investor...")
with tab_investor:
    fi1, fi2, fi3, fi4 = st.columns([3, 1, 2, 2])
    qi    = fi1.text_input("🔍 Cari nama investor", placeholder="e.g. Garibaldi Thohir", key="qi")
    lfi   = fi2.selectbox("L/F", ["Semua", "L", "F"], key="lfi")
    iti   = fi3.selectbox("Tipe Investor", all_types, key="iti")
    sorti = fi4.selectbox("Urutkan", ["# Saham ↓", "# Saham ↑", "Nama A-Z"], key="sorti")

    inv_sum = (
        df.groupby(["investor_name", "investor_classification", "local_foreign", "domicile"])
        .agg(n_stocks=("share_code", "nunique"))
        .reset_index()
    )

    if qi:
        inv_sum = inv_sum[inv_sum["investor_name"].str.lower().str.contains(qi.lower(), na=False)]
    if lfi != "Semua":
        inv_sum = inv_sum[inv_sum["local_foreign"] == lfi]
    if iti != "Semua":
        inv_sum = inv_sum[inv_sum["investor_classification"] == iti]

    if sorti == "# Saham ↓":
        inv_sum = inv_sum.sort_values("n_stocks", ascending=False)
    elif sorti == "# Saham ↑":
        inv_sum = inv_sum.sort_values("n_stocks", ascending=True)
    else:
        inv_sum = inv_sum.sort_values("investor_name")

    st.markdown(f"**{len(inv_sum):,} investors**")

    disp_inv = inv_sum[["investor_name", "investor_classification", "local_foreign", "domicile", "n_stocks"]].copy()
    disp_inv.columns = ["Investor", "Tipe", "L/F", "Domisil", "# Saham"]
    st.dataframe(disp_inv, width="stretch", hide_index=True)

    if not inv_sum.empty:
        detail_inv = st.selectbox(
            "Detail portofolio — pilih investor:",
            ["—"] + inv_sum["investor_name"].tolist(),
            key="detail_inv",
        )
        if detail_inv != "—":
            ir_row = inv_sum[inv_sum["investor_name"] == detail_inv]
            if not ir_row.empty:
                ir = ir_row.iloc[0]
                dom_badge = f'&nbsp;{b_dom(ir["domicile"])}' if ir["local_foreign"] == "F" and ir["domicile"] else ""
                st.markdown(
                    f'<div class="det-hdr">'
                    f'<span class="det-title">{detail_inv}</span>'
                    f'&nbsp;{b_type(ir["investor_classification"])}'
                    f'&nbsp;{b_lf(ir["local_foreign"])}'
                    f'{dom_badge}'
                    f'&nbsp;&nbsp;<span class="det-meta">{int(ir["n_stocks"])} saham</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            holdings = (
                df[df["investor_name"] == detail_inv][
                    ["share_code", "issuer_name", "total_holding_shares", "percentage"]
                ]
                .sort_values("percentage", ascending=False)
                .copy()
            )
            holdings.columns = ["Kode", "Emiten", "Saham", "%"]
            holdings["Saham"] = holdings["Saham"].apply(lambda x: f"{int(x):,}")
            holdings["%"]     = holdings["%"].apply(lambda x: f"{x:.2f}%")
            st.dataframe(holdings, width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KONGLO STOCKS
# ══════════════════════════════════════════════════════════════════════════════
page_progress.progress(62, text="Menyusun Konglo Stocks...")
with tab_kongsi:
    st.markdown(
        "Grup investor yang memegang ≥ threshold% di beberapa emiten sekaligus.",
        help="Threshold dapat diubah di bawah.",
    )

    kc1, kc2, _ = st.columns([2, 2, 4])
    min_pct    = kc1.slider("Min kepemilikan (%)", 1.0, 20.0, 1.0, 0.5, key="kp")
    min_stocks = kc2.slider("Min jumlah saham", 2, 10, 2, 1, key="ks")

    groups = find_kongsi_groups(df, min_pct=min_pct, min_stocks=min_stocks)

    if not groups:
        st.info("Tidak ada grup yang memenuhi kriteria. Coba turunkan threshold.")
    else:
        st.markdown(f"**{len(groups):,} investor / grup** memenuhi kriteria")

        for g in groups:
            inv   = g["investor_name"]
            n_s   = g["n_stocks"]
            codes = ", ".join(s["share_code"] for s in g["stocks"][:8])
            if n_s > 8:
                codes += f" … +{n_s-8} lainnya"

            with st.expander(f"**{inv}** &nbsp;·&nbsp; {n_s} saham &nbsp;·&nbsp; `{codes}`"):
                inv_detail = df[df["investor_name"] == inv]
                if not inv_detail.empty:
                    ir = inv_detail.iloc[0]
                    dom_badge = f'&nbsp;{b_dom(ir["domicile"])}' if ir["local_foreign"] == "F" and ir["domicile"] else ""
                    st.markdown(
                        f'{b_type(ir["investor_classification"])}'
                        f'&nbsp;{b_lf(ir["local_foreign"])}'
                        f'{dom_badge}',
                        unsafe_allow_html=True,
                    )

                rows = []
                for s in g["stocks"]:
                    rows.append({
                        "Kode":   s["share_code"],
                        "Emiten": s["issuer_name"],
                        "%":      f"{s['percentage']:.2f}%",
                    })
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — METRIK
# ══════════════════════════════════════════════════════════════════════════════
page_progress.progress(74, text="Menghitung metrik dan grafik...")
with tab_metrik:
    m = _metrics_for_period(selected, db_mtime, ANALYTICS_CACHE_VERSION)
    if "unclassified_investors" not in m:
        m["unclassified_investors"] = 0
    if m["lf_counts"]["label"].isna().any():
        m["lf_counts"]["label"] = m["lf_counts"]["label"].fillna("Tidak Terklasifikasi")

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("Total Emiten",      f"{m['total_stocks']:,}")
    k2.metric("Total Investor",    f"{m['total_investors']:,}")
    k3.metric("Investor Lokal",    f"{m['local_investors']:,}")
    k4.metric("Investor Asing",    f"{m['foreign_investors']:,}")
    k5.metric("Tidak Terklasifikasi", f"{m.get('unclassified_investors', 0):,}")
    k6.metric("Rata-rata Holders", f"{m['avg_holders']:.1f}")
    k7.metric("Dominasi Lokal",    f"{m['local_pct_share']:.1f}%")

    st.markdown("---")

    ca, cb = st.columns(2)

    with ca:
        st.markdown("#### Lokal vs Asing vs Tidak Terklasifikasi")
        lf_data = m["lf_counts"].copy()
        lf_palette = {
            "Lokal": "#10b981",
            "Asing": "#3b82f6",
            "Tidak Terklasifikasi": "#f59e0b",
        }
        lf_colors = [lf_palette.get(label, "#f59e0b") for label in lf_data["label"]]
        st.plotly_chart(
            donut_chart(lf_data, "label", "count", colors=lf_colors),
            width="stretch",
            config={"displayModeBar": False},
        )

    with cb:
        st.markdown("#### Distribusi Tipe Investor")
        type_full = m["type_counts"].copy()
        type_full["investor_classification"] = type_full["investor_classification"].replace("", "Unknown/Other")
        type_main = type_full.head(8).copy()
        type_other = type_full.iloc[8:]
        if not type_other.empty:
            type_main = pd.concat(
                [
                    type_main,
                    pd.DataFrame(
                        [{
                            "investor_classification": "Lainnya",
                            "count": type_other["count"].sum(),
                        }]
                    ),
                ],
                ignore_index=True,
            )
        type_colors = [
            "#0f75bc", "#62b5e5", "#ef4444", "#f2a7a0", "#20a39e",
            "#6fcf97", "#f97316", "#f7c948", "#8b5cf6",
        ][:len(type_main)]
        st.plotly_chart(
            donut_chart(type_main, "investor_classification", "count", colors=type_colors),
            width="stretch",
            config={"displayModeBar": False},
        )

    st.markdown("---")

    cc, cd = st.columns(2)

    with cc:
        st.markdown("#### Top 20 Investor – Paling Banyak Saham")
        chart_top = (
            alt.Chart(m["top_investors_by_stocks"])
            .mark_bar(color="#10b981")
            .encode(
                x      =alt.X("n_stocks:Q", title="Jumlah Saham"),
                y      =alt.Y("investor_name:N", sort="-x", title=""),
                tooltip=["investor_name:N", "n_stocks:Q"],
            )
            .properties(height=420, width="container")
        )
        st.altair_chart(chart_top)

    with cd:
        st.markdown("#### Top 20 Investor Asing – Paling Banyak Saham")
        chart_foreign = (
            alt.Chart(m["top_foreign"])
            .mark_bar(color="#3b82f6")
            .encode(
                x      =alt.X("n_stocks:Q", title="Jumlah Saham"),
                y      =alt.Y("investor_name:N", sort="-x", title=""),
                tooltip=["investor_name:N", "n_stocks:Q"],
            )
            .properties(height=420, width="container")
        )
        st.altair_chart(chart_foreign)

    st.markdown("---")

    ce, cf = st.columns(2)

    with ce:
        st.markdown("#### Saham dengan Paling Banyak Tracked Shareholders")
        chart_holders = (
            alt.Chart(m["top_stocks_by_holders"])
            .mark_bar(color="#f43f5e")
            .encode(
                x      =alt.X("n_holders:Q", title="Jumlah Holder"),
                y      =alt.Y("share_code:N", sort="-x", title=""),
                tooltip=["share_code:N", "issuer_name:N", "n_holders:Q", "total_pct:Q"],
            )
            .properties(height=500, width="container")
        )
        st.altair_chart(chart_holders)

    with cf:
        st.markdown("#### Negara Asal Investor Asing (Top 20)")
        chart_country = (
            alt.Chart(m["foreign_by_country"])
            .mark_bar(color="#8b5cf6")
            .encode(
                x      =alt.X("count:Q", title="Jumlah Investor"),
                y      =alt.Y("domicile:N", sort="-x", title=""),
                tooltip=["domicile:N", "count:Q"],
            )
            .properties(height=500, width="container")
        )
        st.altair_chart(chart_country)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CHANGELOG
# ══════════════════════════════════════════════════════════════════════════════
page_progress.progress(86, text="Menyiapkan changelog antar periode...")
with tab_changelog:
    all_periods = get_available_periods()

    if len(all_periods) < 2:
        st.info("Upload minimal **2 periode** untuk melihat perubahan antar periode.")
        st.stop()

    cp1, cp2, _ = st.columns([2, 2, 4])
    p_from = cp1.selectbox(
        "Dari periode",
        options=all_periods[:-1],
        format_func=lambda x: pd.to_datetime(x).strftime("%d %b %Y"),
        index=len(all_periods) - 2,
        key="pfrom",
    )
    p_to_opts = [p for p in all_periods if p > p_from]
    p_to = cp2.selectbox(
        "Ke periode",
        options=p_to_opts,
        format_func=lambda x: pd.to_datetime(x).strftime("%d %b %Y"),
        index=len(p_to_opts) - 1,
        key="pto",
    )

    with st.spinner("Menghitung perubahan …"):
        df_old = load_period(p_from)
        df_new = load_period(p_to)
        chg = _changelog_between(p_from, p_to, db_mtime, ANALYTICS_CACHE_VERSION)

    lbl_from = pd.to_datetime(p_from).strftime("%d %b %Y")
    lbl_to   = pd.to_datetime(p_to).strftime("%d %b %Y")
    st.markdown(f"Perbandingan **{lbl_from}** → **{lbl_to}**")
    st.markdown("---")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Saham Baru",      len(chg["new_stocks"]))
    m2.metric("Saham Ditutup",   len(chg["closed_stocks"]))
    m3.metric("Saham Berubah",   len(chg["changed_stocks"]))
    m4.metric("Pemegang Masuk",  f"+{len(chg['new_entries'])}", delta=f"+{len(chg['new_entries'])}")
    m5.metric("Pemegang Keluar", f"-{len(chg['exits'])}", delta=f"-{len(chg['exits'])}", delta_color="inverse")

    st.markdown("---")

    if chg["suspected_renames"]:
        st.markdown('<p class="sec-hdr">Kemungkinan Perubahan Nama (bukan perubahan nyata)</p>', unsafe_allow_html=True)
        st.caption(
            "Klik ticker untuk melihat pasangan nama investor yang mirip. "
            "Bagian ini hanya memuat nama yang mirip dengan jumlah saham dan persentase yang tidak berubah."
        )

        rename_by_code = {}
        for r in chg["suspected_renames"]:
            rename_by_code.setdefault(r["share_code"], []).append(r)

        rename_codes = sorted(rename_by_code)
        selected_rename = st.selectbox(
            "Pilih ticker untuk detail kemungkinan perubahan nama",
            ["—"] + rename_codes,
            format_func=lambda code: (
                "Pilih ticker"
                if code == "—"
                else f"{code} · {len(rename_by_code[code])} pasangan"
            ),
            key="rename_detail_select",
        )

        if selected_rename != "—":
            st.markdown(
                f'<div class="chg-detail-card">{b_ticker(selected_rename)}'
                f'<span class="chg-issuer">{len(rename_by_code[selected_rename])} kemungkinan perubahan nama</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            rename_rows = pd.DataFrame(rename_by_code[selected_rename])[
                ["old_name", "new_name", "old_pct", "new_pct", "similarity"]
            ].copy()
            rename_rows.columns = [
                f"Nama ({lbl_from})",
                f"Nama ({lbl_to})",
                f"% ({lbl_from})",
                f"% ({lbl_to})",
                "Kemiripan",
            ]
            rename_rows[f"% ({lbl_from})"] = rename_rows[f"% ({lbl_from})"].apply(lambda x: f"{x:.2f}%")
            rename_rows[f"% ({lbl_to})"] = rename_rows[f"% ({lbl_to})"].apply(lambda x: f"{x:.2f}%")
            rename_rows["Kemiripan"] = rename_rows["Kemiripan"].apply(lambda x: f"{x}%")
            st.dataframe(rename_rows, width="stretch", hide_index=True)
        st.markdown("---")

    def _stock_issuer(frame, code):
        sub = frame[frame["share_code"] == code]
        return sub["issuer_name"].iloc[0] if not sub.empty else ""

    def _holder_rows(frame, code, investors=None):
        sub = frame[frame["share_code"] == code].copy()
        if investors is not None:
            sub = sub[sub["investor_name"].isin(investors)]
        sub = sub.sort_values("percentage", ascending=False)
        disp = sub[
            [
                "investor_name",
                "investor_classification",
                "local_foreign",
                "domicile",
                "total_holding_shares",
                "percentage",
            ]
        ].copy()
        disp.columns = ["Pemegang Saham", "Tipe", "Status", "Domisili", "Saham", "%"]
        disp["Status"] = disp["Status"].map({"L": "Lokal", "F": "Asing"}).fillna(disp["Status"])
        disp["Saham"] = disp["Saham"].apply(lambda x: f"{int(x):,}")
        disp["%"] = disp["%"].apply(lambda x: f"{x:.2f}%")
        return disp

    new_entries_map = {}
    exits_map = {}
    for sc, inv in chg["new_entries"]:
        new_entries_map.setdefault(sc, []).append(inv)
    for sc, inv in chg["exits"]:
        exits_map.setdefault(sc, []).append(inv)

    if chg["new_stocks"]:
        st.markdown('<p class="sec-hdr">Saham Baru</p>', unsafe_allow_html=True)
        for code in chg["new_stocks"]:
            sub = df_new[df_new["share_code"] == code]
            issuer = _stock_issuer(df_new, code)
            with st.expander(code):
                st.markdown(
                    f'<div class="chg-stock-head">'
                    f'<div>{b_ticker(code)}<span class="chg-issuer">{issuer}</span></div>'
                    f'<div class="chg-summary">{len(sub)} investor tercatat</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(_holder_rows(df_new, code), width="stretch", hide_index=True)

    if chg["closed_stocks"]:
        st.markdown('<p class="sec-hdr">Saham Ditutup / Tidak Muncul</p>', unsafe_allow_html=True)
        for code in chg["closed_stocks"]:
            sub = df_old[df_old["share_code"] == code]
            issuer = _stock_issuer(df_old, code)
            with st.expander(code):
                st.markdown(
                    f'<div class="chg-stock-head">'
                    f'<div>{b_ticker(code)}<span class="chg-issuer">{issuer}</span></div>'
                    f'<div class="chg-summary">{len(sub)} investor pada periode sebelumnya</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(_holder_rows(df_old, code), width="stretch", hide_index=True)

    if chg["changed_stocks"]:
        st.markdown('<p class="sec-hdr">Perubahan Pemegang Saham per Emiten</p>', unsafe_allow_html=True)

        changed_rows = []
        pct_counts = (
            chg["pct_changes"].groupby("share_code").size().to_dict()
            if not chg["pct_changes"].empty
            else {}
        )
        for code in chg["changed_stocks"]:
            changed_rows.append({
                "Ticker": code,
                "Emiten": _stock_issuer(df_new, code) or _stock_issuer(df_old, code),
                "Masuk": len(new_entries_map.get(code, [])),
                "Keluar": len(exits_map.get(code, [])),
                "Berubah %": int(pct_counts.get(code, 0)),
            })

        changed_summary = pd.DataFrame(changed_rows)
        st.dataframe(changed_summary, width="stretch", hide_index=True, height=260)

        selected_changed = st.selectbox(
            "Pilih ticker untuk detail perubahan pemegang saham",
            ["—"] + chg["changed_stocks"],
            format_func=lambda code: (
                "Pilih ticker"
                if code == "—"
                else f"{code} · {_stock_issuer(df_new, code) or _stock_issuer(df_old, code)}"
            ),
            key="changed_detail_select",
        )

        if selected_changed != "—":
            code = selected_changed
            issuer = _stock_issuer(df_new, code) or _stock_issuer(df_old, code)
            entered = new_entries_map.get(code, [])
            exited = exits_map.get(code, [])
            pct_sub = pd.DataFrame()
            if not chg["pct_changes"].empty:
                pct_sub = chg["pct_changes"][chg["pct_changes"]["share_code"] == code]

            st.markdown(
                f'<div class="chg-stock-head">'
                f'<div>{b_ticker(code)}<span class="chg-issuer">{issuer}</span></div>'
                f'<div class="chg-summary">+{len(entered)} masuk / -{len(exited)} keluar / '
                f'{len(pct_sub)} berubah %</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if entered:
                st.markdown("**Pemegang baru**")
                st.dataframe(_holder_rows(df_new, code, entered), width="stretch", hide_index=True)

            if exited:
                st.markdown("**Pemegang keluar**")
                old_exit = _holder_rows(df_old, code, exited)
                old_exit = old_exit.rename(columns={"%": f"% ({lbl_from})"})
                st.dataframe(old_exit, width="stretch", hide_index=True)

            if not pct_sub.empty:
                st.markdown("**Perubahan % kepemilikan**")
                disp = pct_sub[["investor_name", "old_pct", "new_pct", "delta"]].copy()
                disp.columns = ["Pemegang Saham", f"% ({lbl_from})", f"% ({lbl_to})", "Delta"]
                disp[f"% ({lbl_from})"] = disp[f"% ({lbl_from})"].apply(lambda x: f"{x:.2f}%")
                disp[f"% ({lbl_to})"] = disp[f"% ({lbl_to})"].apply(lambda x: f"{x:.2f}%")
                disp["Delta"] = disp["Delta"].apply(
                    lambda x: f"+{x:.2f} pp" if x > 0 else f"{x:.2f} pp"
                )
                st.dataframe(disp, width="stretch", hide_index=True)

            if not entered and not exited and pct_sub.empty:
                st.markdown(
                    '<div class="chg-empty">Tidak ada detail perubahan untuk ticker ini.</div>',
                    unsafe_allow_html=True,
                )

    elif not chg["new_stocks"] and not chg["closed_stocks"]:
        st.success("✅ Tidak ada perubahan yang terdeteksi antara dua periode ini.")

page_progress.progress(100, text="Dashboard siap.")
page_status.empty()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("© 2025 Yoshua Iskandar · Sumber data: KSEI · Dashboard ini bukan produk resmi KSEI / IDX.")
