"""
KSEI Ownership Dashboard
========================
Run:  streamlit run app.py   (from the 1persen_data folder)
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from analysis import compute_changelog, find_kongsi_groups, get_metrics
from db import (
    delete_period,
    get_available_periods,
    get_uploads,
    init_db,
    insert_holdings,
    load_period,
    period_exists,
)
from parser import parse_ksei_pdf

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
.main .block-container {
    padding-top: 0.75rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
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
    background: transparent;
    border-bottom: 2px solid #e2e8f0;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #64748b;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.6rem 1rem;
    margin-bottom: -2px;
    border-radius: 0;
}
.stTabs [aria-selected="true"] {
    color: #0f172a;
    border-bottom-color: #10b981;
    font-weight: 600;
}
.stTabs [data-baseweb="tab"]:hover { color: #0f172a; }

/* === KPI metric cards ==================================================== */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="metric-container"] > label {
    color: #64748b !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* === Expanders =========================================================== */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    margin-bottom: 5px !important;
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-size: 0.875rem;
    font-weight: 500;
    color: #0f172a;
    padding: 0.65rem 1rem;
}
[data-testid="stExpander"] summary:hover { background: #f8fafc; }

/* === Dataframes ========================================================== */
[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    overflow: hidden;
}

/* === Inputs ============================================================== */
[data-testid="stTextInput"] input {
    border-radius: 8px;
    border-color: #e2e8f0;
    background: white;
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
    return _b("bd-lokal", "🇮🇩 Lokal") if lf == "L" else _b("bd-asing", "🌍 Asing")

def b_type(t: str) -> str:
    return _b(_TYPE_CLS.get(t, "bd-other"), t or "Other")

def b_dom(d: str) -> str:
    return _b("bd-domicile", d) if d else ""

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()


# ── Cached data loader ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load(date_str: str) -> pd.DataFrame:
    return load_period(date_str)


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
                    insert_holdings(df_parsed, uploaded.name)
                    st.success(f"Replaced — {n_rows:,} rows")
                    st.rerun()
                if col2.button("Skip", use_container_width=True):
                    st.info("Skipped — no changes made.")
            else:
                insert_holdings(df_parsed, uploaded.name)
                _load.clear()
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
df = _load(selected)
period_label = pd.to_datetime(selected).strftime("%d %b %Y")

st.markdown(
    f"<div style='padding:0.25rem 0 0.75rem 0; border-bottom:1px solid #e2e8f0; margin-bottom:0.75rem'>"
    f"<span style='font-size:1.2rem;font-weight:700;color:#0f172a'>📊 KSEI Ownership</span>"
    f"&nbsp;&nbsp;<span style='color:#94a3b8;font-size:0.875rem'>Period: {period_label}</span>"
    f"</div>",
    unsafe_allow_html=True,
)

all_types = ["Semua"] + sorted(
    df["investor_classification"].replace("", pd.NA).dropna().unique()
)

tabs = st.tabs([
    "📋 Ringkasan Saham",
    "👤 Per Investor",
    "🔗 Kongsi Stocks",
    "📈 Metrik",
    "🔄 Changelog",
])
tab_saham, tab_investor, tab_kongsi, tab_metrik, tab_changelog = tabs


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RINGKASAN SAHAM
# ══════════════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PER INVESTOR
# ══════════════════════════════════════════════════════════════════════════════
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
# TAB 3 — KONGSI STOCKS
# ══════════════════════════════════════════════════════════════════════════════
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
with tab_metrik:
    m = get_metrics(df)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Emiten",      f"{m['total_stocks']:,}")
    k2.metric("Total Investor",    f"{m['total_investors']:,}")
    k3.metric("Investor Lokal",    f"{m['local_investors']:,}")
    k4.metric("Investor Asing",    f"{m['foreign_investors']:,}")
    k5.metric("Rata-rata Holders", f"{m['avg_holders']:.1f}")
    k6.metric("Dominasi Lokal",    f"{m['local_pct_share']:.1f}%")

    st.markdown("---")

    ca, cb = st.columns(2)

    with ca:
        st.markdown("#### Lokal vs Asing (Jumlah Investor)")
        lf_data = m["lf_counts"].copy()
        chart_lf = (
            alt.Chart(lf_data)
            .mark_arc(innerRadius=55)
            .encode(
                theta  =alt.Theta("count:Q"),
                color  =alt.Color(
                    "label:N",
                    scale=alt.Scale(domain=["Local","Foreign"], range=["#10b981","#3b82f6"]),
                    legend=alt.Legend(title=""),
                ),
                tooltip=["label:N", "count:Q"],
            )
            .properties(height=220, width="container")
        )
        st.altair_chart(chart_lf)

    with cb:
        st.markdown("#### Distribusi Tipe Investor")
        type_data = m["type_counts"].head(9).copy()
        chart_type = (
            alt.Chart(type_data)
            .mark_arc(innerRadius=55)
            .encode(
                theta  =alt.Theta("count:Q"),
                color  =alt.Color("investor_classification:N", legend=alt.Legend(title="")),
                tooltip=["investor_classification:N", "count:Q"],
            )
            .properties(height=220, width="container")
        )
        st.altair_chart(chart_type)

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
        df_old = _load(p_from)
        df_new = _load(p_to)
        chg    = compute_changelog(df_old, df_new)

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
        st.markdown('<p class="sec-hdr">⚠️ Kemungkinan Perubahan Nama (bukan perubahan nyata)</p>', unsafe_allow_html=True)
        st.caption(
            "Pasangan investor di bawah ini tercatat masuk/keluar, "
            "namun namanya sangat mirip dan kepemilikannya hampir sama. "
            "Kemungkinan hanya perbedaan penulisan di laporan KSEI — bukan perpindahan kepemilikan."
        )
        for r in chg["suspected_renames"]:
            c1, c2 = st.columns(2)
            c1.markdown(
                f"❌ `{r['old_name']}` &nbsp; `{r['old_pct']:.2f}%`",
                unsafe_allow_html=True,
            )
            c2.markdown(
                f"✅ `{r['new_name']}` &nbsp; `{r['new_pct']:.2f}%`",
                unsafe_allow_html=True,
            )
            st.caption(
                f"{r['share_code']} · Kemiripan nama: {r['similarity']}%"
            )
        st.markdown("---")

    if chg["new_stocks"]:
        st.markdown('<p class="sec-hdr">🆕 Saham Baru</p>', unsafe_allow_html=True)
        for code in chg["new_stocks"]:
            sub   = df_new[df_new["share_code"] == code]
            name  = sub["issuer_name"].iloc[0] if not sub.empty else ""
            n_inv = len(sub)
            st.markdown(
                f"&nbsp;{b_ticker(code)} &nbsp;**{name}** — {n_inv} investor tercatat",
                unsafe_allow_html=True,
            )

    if chg["closed_stocks"]:
        st.markdown('<p class="sec-hdr">❌ Saham Ditutup / Tidak Muncul</p>', unsafe_allow_html=True)
        for code in chg["closed_stocks"]:
            sub  = df_old[df_old["share_code"] == code]
            name = sub["issuer_name"].iloc[0] if not sub.empty else ""
            st.markdown(
                f"&nbsp;{b_ticker(code)} &nbsp;**{name}**",
                unsafe_allow_html=True,
            )

    if chg["changed_stocks"]:
        st.markdown('<p class="sec-hdr">🔄 Perubahan Pemegang Saham per Emiten</p>', unsafe_allow_html=True)

        new_entries_map: dict[str, list] = {}
        exits_map:       dict[str, list] = {}
        for sc, inv in chg["new_entries"]:
            new_entries_map.setdefault(sc, []).append(inv)
        for sc, inv in chg["exits"]:
            exits_map.setdefault(sc, []).append(inv)

        for code in chg["changed_stocks"]:
            sub_new = df_new[df_new["share_code"] == code]
            issuer  = sub_new["issuer_name"].iloc[0] if not sub_new.empty else ""
            entered = new_entries_map.get(code, [])
            exited  = exits_map.get(code, [])

            pct_sub = pd.DataFrame()
            if not chg["pct_changes"].empty:
                pct_sub = chg["pct_changes"][chg["pct_changes"]["share_code"] == code]

            with st.expander(
                f"{code} — {issuer}  ·  +{len(entered)} masuk / -{len(exited)} keluar"
            ):
                if entered:
                    st.markdown("**🟢 Masuk (pemegang baru):**")
                    for inv in entered:
                        row_inv  = sub_new[sub_new["investor_name"] == inv]
                        pct      = row_inv["percentage"].iloc[0] if not row_inv.empty else 0.0
                        inv_t    = row_inv["investor_classification"].iloc[0] if not row_inv.empty else ""
                        lf_v     = row_inv["local_foreign"].iloc[0] if not row_inv.empty else ""
                        st.markdown(
                            f"&nbsp;&nbsp;▶ **{inv}** &nbsp;{b_type(inv_t)}&nbsp;{b_lf(lf_v)}&nbsp; `{pct:.2f}%`",
                            unsafe_allow_html=True,
                        )

                if exited:
                    st.markdown("**🔴 Keluar (tidak muncul lagi):**")
                    for inv in exited:
                        row_inv  = df_old[(df_old["share_code"] == code) & (df_old["investor_name"] == inv)]
                        pct      = row_inv["percentage"].iloc[0] if not row_inv.empty else 0.0
                        inv_t    = row_inv["investor_classification"].iloc[0] if not row_inv.empty else ""
                        st.markdown(
                            f"&nbsp;&nbsp;◀ **{inv}** &nbsp;{b_type(inv_t)}&nbsp; sebelumnya `{pct:.2f}%`",
                            unsafe_allow_html=True,
                        )

                if not pct_sub.empty:
                    st.markdown("**📊 Perubahan % Kepemilikan:**")
                    disp = pct_sub[["investor_name", "old_pct", "new_pct", "delta"]].copy()
                    disp.columns = ["Investor", f"% ({lbl_from})", f"% ({lbl_to})", "Δ"]
                    disp[f"% ({lbl_from})"] = disp[f"% ({lbl_from})"].apply(lambda x: f"{x:.2f}%")
                    disp[f"% ({lbl_to})"]   = disp[f"% ({lbl_to})"].apply(lambda x: f"{x:.2f}%")
                    disp["Δ"] = disp["Δ"].apply(
                        lambda x: f"▲ {x:.2f}%" if x > 0 else f"▼ {abs(x):.2f}%"
                    )
                    st.dataframe(disp, width="stretch", hide_index=True)

    elif not chg["new_stocks"] and not chg["closed_stocks"]:
        st.success("✅ Tidak ada perubahan yang terdeteksi antara dua periode ini.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("© 2025 Yoshua Iskandar · Sumber data: KSEI · Dashboard ini bukan produk resmi KSEI / IDX.")
