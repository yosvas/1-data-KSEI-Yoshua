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

# Make sure local modules are importable even if cwd differs
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

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── General ── */
.block-container { padding-top: 1.2rem; }

/* ── KPI cards ── */
[data-testid="metric-container"] {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 12px 16px;
    border: 1px solid #e9ecef;
}

/* ── Badges ── */
.badge-local   { background:#d4edda; color:#155724; padding:2px 9px;
                 border-radius:12px; font-size:.75rem; font-weight:600; }
.badge-foreign { background:#cce5ff; color:#004085; padding:2px 9px;
                 border-radius:12px; font-size:.75rem; font-weight:600; }
.badge-type    { background:#e2e3e5; color:#383d41; padding:2px 9px;
                 border-radius:12px; font-size:.75rem; }

/* ── Ticker chip ── */
.ticker { background:#212529; color:#fff; padding:2px 8px;
          border-radius:5px; font-weight:700; font-size:.85rem; }

/* ── Changelog colours ── */
.chg-new  { color:#28a745; font-weight:600; }
.chg-exit { color:#dc3545; font-weight:600; }
.chg-up   { color:#17a2b8; font-weight:600; }
.chg-dn   { color:#fd7e14; font-weight:600; }

/* ── Section divider ── */
.sec-hdr { font-size:1rem; font-weight:700; color:#343a40;
           border-bottom:2px solid #dee2e6; padding-bottom:4px;
           margin-top:8px; margin-bottom:8px; }
</style>
""",
    unsafe_allow_html=True,
)

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

    # ── Upload ────────────────────────────────────────────────────────────────
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
            period_label = df_parsed["date"].iloc[0].strftime("%d %b %Y")
            n_rows       = len(df_parsed)

            if period_exists(period_str):
                st.warning(f"Period **{period_label}** is already in the database.")
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
                st.success(f"✅ **{period_label}** uploaded — {n_rows:,} rows")
                st.rerun()

    st.markdown("---")

    # ── Period selector ───────────────────────────────────────────────────────
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

    # ── Upload history ────────────────────────────────────────────────────────
    uploads_df = get_uploads()
    if not uploads_df.empty:
        st.markdown("---")
        st.markdown("### 📋 Uploaded Periods")
        for _, row in uploads_df.iterrows():
            d = pd.to_datetime(row["period_date"]).strftime("%d %b %Y")
            st.markdown(
                f"**{d}** · {int(row['row_count']):,} rows  \n"
                f"<small style='color:#6c757d'>{row['filename']}</small>",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
df = _load(selected)
period_label = pd.to_datetime(selected).strftime("%d %b %Y")

st.markdown(
    f"## 📊 KSEI Ownership &nbsp;·&nbsp; "
    f"<span style='color:#6c757d;font-size:1rem'>Period: {period_label}</span>",
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
    # ── Filters ───────────────────────────────────────────────────────────────
    fc1, fc2, fc3, fc4 = st.columns([3, 1, 2, 1])
    q = fc1.text_input("🔍 Cari kode saham atau nama emiten", placeholder="e.g. BBCA / BCA", key="qs")
    lf = fc2.selectbox("L/F", ["Semua", "Lokal", "Asing"], key="lfs")
    inv_type = fc3.selectbox("Tipe Investor", all_types, key="its")
    sort_by = fc4.selectbox("Urutkan", ["Kode", "# Holders ↓"], key="sbs")

    # ── Build stock list ──────────────────────────────────────────────────────
    stock_meta = (
        df.groupby(["share_code", "issuer_name"])
        .agg(
            n_holders   =("investor_name",  "count"),
            total_pct   =("percentage",     "sum"),
            n_local     =("local_foreign",  lambda x: (x == "L").sum()),
            n_foreign   =("local_foreign",  lambda x: (x == "F").sum()),
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

    for _, sm in stock_meta.iterrows():
        code   = sm["share_code"]
        name   = sm["issuer_name"]
        n_h    = int(sm["n_holders"])
        t_pct  = sm["total_pct"]
        n_loc  = int(sm["n_local"])
        n_for  = int(sm["n_foreign"])

        title = (
            f"`{code}` &nbsp; **{name}** &nbsp;·&nbsp; "
            f"{t_pct:.2f}% tracked &nbsp;·&nbsp; "
            f"{n_h} holders ({n_loc}L / {n_for}F)"
        )

        with st.expander(title):
            sub = df[df["share_code"] == code].copy()

            # Apply tab-level filters inside expander
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
                disp.columns = ["Investor", "Type", "L/F", "Domicile", "Shares", "%"]
                disp["Shares"] = disp["Shares"].apply(lambda x: f"{int(x):,}")
                disp["%"]      = disp["%"].apply(lambda x: f"{x:.2f}%")
                st.dataframe(disp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PER INVESTOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_investor:
    fi1, fi2, fi3, fi4 = st.columns([3, 1, 2, 2])
    qi   = fi1.text_input("🔍 Cari nama investor", placeholder="e.g. Garibaldi Thohir", key="qi")
    lfi  = fi2.selectbox("L/F", ["Semua", "L", "F"], key="lfi")
    iti  = fi3.selectbox("Tipe Investor", all_types, key="iti")
    sorti = fi4.selectbox("Urutkan", ["# Saham ↓", "# Saham ↑", "Nama A-Z"], key="sorti")

    # Build investor summary
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

    for _, ir in inv_sum.iterrows():
        inv_name  = ir["investor_name"]
        n_stocks  = int(ir["n_stocks"])
        inv_type  = ir["investor_classification"] or "—"
        lf_val    = ir["local_foreign"]
        domicile  = ir["domicile"] or "—"
        lf_tag    = "🇮🇩 Lokal" if lf_val == "L" else f"🌍 Asing · {domicile}"

        title = f"**{inv_name}** &nbsp;·&nbsp; {n_stocks} saham &nbsp;·&nbsp; {inv_type} &nbsp;·&nbsp; {lf_tag}"

        with st.expander(title):
            holdings = (
                df[df["investor_name"] == inv_name][
                    ["share_code", "issuer_name", "total_holding_shares", "percentage"]
                ]
                .sort_values("percentage", ascending=False)
                .copy()
            )
            holdings.columns = ["Kode", "Emiten", "Saham", "%"]
            holdings["Saham"] = holdings["Saham"].apply(lambda x: f"{int(x):,}")
            holdings["%"]     = holdings["%"].apply(lambda x: f"{x:.2f}%")
            st.dataframe(holdings, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KONGSI STOCKS
# ══════════════════════════════════════════════════════════════════════════════
with tab_kongsi:
    st.markdown(
        "Grup investor yang memegang ≥ threshold% di beberapa emiten sekaligus.",
        help="Threshold dapat diubah di bawah.",
    )

    kc1, kc2, _ = st.columns([2, 2, 4])
    min_pct    = kc1.slider("Min kepemilikan (%)", 1.0, 20.0, 5.0, 0.5, key="kp")
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
                rows = []
                for s in g["stocks"]:
                    rows.append({
                        "Kode":   s["share_code"],
                        "Emiten": s["issuer_name"],
                        "%":      f"{s['percentage']:.2f}%",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — METRIK
# ══════════════════════════════════════════════════════════════════════════════
with tab_metrik:
    m = get_metrics(df)

    # ── KPI row ───────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Emiten",       f"{m['total_stocks']:,}")
    k2.metric("Total Investor",     f"{m['total_investors']:,}")
    k3.metric("Investor Lokal",     f"{m['local_investors']:,}")
    k4.metric("Investor Asing",     f"{m['foreign_investors']:,}")
    k5.metric("Rata-rata Holders",  f"{m['avg_holders']:.1f}")
    k6.metric("Dominasi Lokal",     f"{m['local_pct_share']:.1f}%")

    st.markdown("---")

    # ── Donut charts ──────────────────────────────────────────────────────────
    ca, cb = st.columns(2)

    with ca:
        st.markdown("#### Lokal vs Asing (Jumlah Investor)")
        lf_data = m["lf_counts"].copy()
        chart_lf = (
            alt.Chart(lf_data)
            .mark_arc(innerRadius=55)
            .encode(
                theta =alt.Theta("count:Q"),
                color =alt.Color(
                    "label:N",
                    scale=alt.Scale(domain=["Local","Foreign"], range=["#2ecc71","#3498db"]),
                    legend=alt.Legend(title=""),
                ),
                tooltip=["label:N", "count:Q"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart_lf, use_container_width=True)

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
            .properties(height=220)
        )
        st.altair_chart(chart_type, use_container_width=True)

    st.markdown("---")

    # ── Bar charts ────────────────────────────────────────────────────────────
    cc, cd = st.columns(2)

    with cc:
        st.markdown("#### Top 20 Investor – Paling Banyak Saham")
        chart_top = (
            alt.Chart(m["top_investors_by_stocks"])
            .mark_bar(color="#27ae60")
            .encode(
                x      =alt.X("n_stocks:Q", title="Jumlah Saham"),
                y      =alt.Y("investor_name:N", sort="-x", title=""),
                tooltip=["investor_name:N", "n_stocks:Q"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_top, use_container_width=True)

    with cd:
        st.markdown("#### Top 20 Investor Asing – Paling Banyak Saham")
        chart_foreign = (
            alt.Chart(m["top_foreign"])
            .mark_bar(color="#3498db")
            .encode(
                x      =alt.X("n_stocks:Q", title="Jumlah Saham"),
                y      =alt.Y("investor_name:N", sort="-x", title=""),
                tooltip=["investor_name:N", "n_stocks:Q"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_foreign, use_container_width=True)

    st.markdown("---")

    ce, cf = st.columns(2)

    with ce:
        st.markdown("#### Saham dengan Paling Banyak Tracked Shareholders")
        chart_holders = (
            alt.Chart(m["top_stocks_by_holders"])
            .mark_bar(color="#e74c3c")
            .encode(
                x      =alt.X("n_holders:Q", title="Jumlah Holder"),
                y      =alt.Y("share_code:N", sort="-x", title=""),
                tooltip=["share_code:N", "issuer_name:N", "n_holders:Q", "total_pct:Q"],
            )
            .properties(height=500)
        )
        st.altair_chart(chart_holders, use_container_width=True)

    with cf:
        st.markdown("#### Negara Asal Investor Asing (Top 20)")
        chart_country = (
            alt.Chart(m["foreign_by_country"])
            .mark_bar(color="#9b59b6")
            .encode(
                x      =alt.X("count:Q", title="Jumlah Investor"),
                y      =alt.Y("domicile:N", sort="-x", title=""),
                tooltip=["domicile:N", "count:Q"],
            )
            .properties(height=500)
        )
        st.altair_chart(chart_country, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CHANGELOG
# ══════════════════════════════════════════════════════════════════════════════
with tab_changelog:
    all_periods = get_available_periods()

    if len(all_periods) < 2:
        st.info("Upload minimal **2 periode** untuk melihat perubahan antar periode.")
        st.stop()

    # Period pickers
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

    # ── Summary metrics ───────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Saham Baru",       len(chg["new_stocks"]))
    m2.metric("Saham Ditutup",    len(chg["closed_stocks"]))
    m3.metric("Saham Berubah",    len(chg["changed_stocks"]))
    m4.metric("Pemegang Masuk",   f"+{len(chg['new_entries'])}", delta=f"+{len(chg['new_entries'])}")
    m5.metric("Pemegang Keluar",  f"-{len(chg['exits'])}", delta=f"-{len(chg['exits'])}", delta_color="inverse")

    st.markdown("---")

    # ── New stocks ────────────────────────────────────────────────────────────
    if chg["new_stocks"]:
        st.markdown('<p class="sec-hdr">🆕 Saham Baru</p>', unsafe_allow_html=True)
        for code in chg["new_stocks"]:
            sub   = df_new[df_new["share_code"] == code]
            name  = sub["issuer_name"].iloc[0] if not sub.empty else ""
            n_inv = len(sub)
            st.markdown(f"- `{code}` **{name}** — {n_inv} investor tercatat")

    # ── Closed stocks ─────────────────────────────────────────────────────────
    if chg["closed_stocks"]:
        st.markdown('<p class="sec-hdr">❌ Saham Ditutup / Tidak Muncul</p>', unsafe_allow_html=True)
        for code in chg["closed_stocks"]:
            sub  = df_old[df_old["share_code"] == code]
            name = sub["issuer_name"].iloc[0] if not sub.empty else ""
            st.markdown(f"- `{code}` **{name}**")

    # ── Per-stock changes ─────────────────────────────────────────────────────
    if chg["changed_stocks"]:
        st.markdown('<p class="sec-hdr">🔄 Perubahan Pemegang Saham per Emiten</p>', unsafe_allow_html=True)

        # Pre-index for fast lookups
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

            with st.expander(f"{code} — {issuer}  ·  +{len(entered)} masuk / -{len(exited)} keluar"):
                if entered:
                    st.markdown("**🟢 Masuk (pemegang baru):**")
                    for inv in entered:
                        row_inv = sub_new[sub_new["investor_name"] == inv]
                        pct     = row_inv["percentage"].iloc[0] if not row_inv.empty else 0.0
                        inv_type = row_inv["investor_classification"].iloc[0] if not row_inv.empty else ""
                        lf_v    = row_inv["local_foreign"].iloc[0] if not row_inv.empty else ""
                        lf_tag  = "Lokal" if lf_v == "L" else "Asing"
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;▶ **{inv}** · {inv_type} · {lf_tag} · `{pct:.2f}%`"
                        )

                if exited:
                    st.markdown("**🔴 Keluar (tidak muncul lagi):**")
                    for inv in exited:
                        row_inv  = df_old[(df_old["share_code"] == code) & (df_old["investor_name"] == inv)]
                        pct      = row_inv["percentage"].iloc[0] if not row_inv.empty else 0.0
                        inv_type = row_inv["investor_classification"].iloc[0] if not row_inv.empty else ""
                        st.markdown(
                            f"&nbsp;&nbsp;&nbsp;◀ **{inv}** · {inv_type} · sebelumnya `{pct:.2f}%`"
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
                    st.dataframe(disp, use_container_width=True, hide_index=True)

    elif not chg["new_stocks"] and not chg["closed_stocks"]:
        st.success("✅ Tidak ada perubahan yang terdeteksi antara dua periode ini.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Sumber data: KSEI · Dashboard ini bukan produk resmi KSEI / IDX.")
