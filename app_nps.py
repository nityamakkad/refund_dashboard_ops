"""
IK NPS Tracking Dashboard
Run: streamlit run app_nps.py
"""

import pandas as pd
import numpy as np
import streamlit as st

from nps_data_loader import load_nps
from nps_charts import (
    kpi_nps, chart_nps_by_ssa, chart_nps_by_category,
    chart_respondent_mix, chart_response_rate,
    chart_nps_by_checkpoint, chart_nps_trend,
    chart_nps_heatmap, table_ssa_leaderboard,
    chart_nps_distribution, chart_nps_round_delta,
    _nps_colour, C_GREEN, C_AMBER, C_RED, C_SLATE,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IK NPS Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

  .dash-title {
    font-size: 38px; font-weight: 800; color: #0F172A;
    text-decoration: underline; text-underline-offset: 6px;
    text-decoration-color: #2563EB; margin-bottom: 2px;
  }
  .kpi-card {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 16px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .kpi-label { font-size: 11px; color: #64748B; text-transform: uppercase;
               letter-spacing: 0.06em; }
  .kpi-value { font-size: 26px; font-weight: 700; color: #1E293B; margin: 6px 0 4px 0; }
  .kpi-sub   { font-size: 11px; color: #94A3B8; }
  .nps-score { font-size: 48px; font-weight: 800; margin: 4px 0; }

  .section-header {
    font-size: 17px; font-weight: 600; color: #1E293B;
    border-left: 4px solid #2563EB; padding-left: 10px; margin: 28px 0 14px 0;
  }
  .insight-box {
    background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 10px;
    padding: 14px 18px; font-size: 13.5px; color: #334155; line-height: 1.7;
  }
  .nps-legend {
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 10px 16px; font-size: 12px; color: #475569; margin-bottom: 12px;
  }
  section[data-testid="stSidebar"] { background: #F8FAFC; }
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading NPS data…")
def get_data():
    us = load_nps("data/nps_us.csv",    "US")
    try:
        india = load_nps("data/nps_india.csv", "India")
        combined = pd.concat([us, india], ignore_index=True)
    except FileNotFoundError:
        india    = None
        combined = us
    return us, india, combined

df_us, df_india, df_all = get_data()


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab_us, tab_india, tab_combined = st.tabs(["🇺🇸 US NPS", "🇮🇳 India NPS", "🌐 Combined View"])


# ─────────────────────────────────────────────────────────────────────────────
# SHARED RENDER FUNCTION — same layout for US and India
# ─────────────────────────────────────────────────────────────────────────────

def render_tab(df_raw, region_label):

    if df_raw is None:
        st.info(f"No data file found for {region_label}. Add `data/nps_india.csv` to enable this tab.")
        return

    # ── SIDEBAR FILTERS ───────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### Filters — {region_label}")
        st.caption("Applied to all charts below")
        st.divider()

        def ms(label, series, key):
            opts = sorted(series.dropna().unique().tolist(), key=str)
            return st.multiselect(label, options=opts, default=opts, key=key)

        sel_cat   = ms("📂 Category",    df_raw["Category"], f"cat_{region_label}")
        sel_ssa   = ms("👤 SSA",         df_raw["SSA"],      f"ssa_{region_label}")
        sel_type  = ms("📋 NPS Type",    df_raw["NPS Type"], f"type_{region_label}")
        sel_month = ms("📅 Release Month",df_raw["Release_month"], f"month_{region_label}")

        st.divider()
        st.caption("NPS = (Promoters - Detractors) / Responses × 100")
        st.caption("Green ≥ 50  |  Amber 0–49  |  Red < 0")

    # Apply filters
    df = df_raw.copy()
    if sel_cat:   df = df[df["Category"].isin(sel_cat)]
    if sel_ssa:   df = df[df["SSA"].isin(sel_ssa)]
    if sel_type:  df = df[df["NPS Type"].isin(sel_type)]
    if sel_month: df = df[df["Release_month"].isin(sel_month)]

    if len(df) == 0:
        st.warning("No records match current filters.")
        return

    # ── HEADER ────────────────────────────────────────────────────────────
    st.markdown(f'<div class="dash-title">📈 {region_label} NPS Dashboard</div>',
                unsafe_allow_html=True)
    st.markdown(
        f"<span style='color:#64748B;font-size:13px;'>"
        f"Showing <b>{len(df)}</b> of <b>{len(df_raw)}</b> entries · "
        f"NPS computed from Promoters / Detractors / Responses"
        f"</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── KPI ROW ───────────────────────────────────────────────────────────
    kpi = kpi_nps(df)
    nps_val   = kpi["overall_nps"]
    nps_color = _nps_colour(nps_val) if nps_val is not None else C_SLATE
    nps_label = "Excellent" if (nps_val or 0) >= 70 else \
                "Good"      if (nps_val or 0) >= 50 else \
                "Needs Work"if (nps_val or 0) >= 0  else "Poor"

    c0, c1, c2, c3, c4, c5, c6 = st.columns(7)

    with c0:
        st.markdown(
            f'<div class="kpi-card" style="border-top:4px solid {nps_color};">'
            f'<div class="kpi-label">Overall NPS</div>'
            f'<div class="nps-score" style="color:{nps_color};">'
            f'{nps_val if nps_val is not None else "—"}</div>'
            f'<div class="kpi-sub">{nps_label}</div>'
            f'</div>', unsafe_allow_html=True)

    for col, label, value, sub in [
        (c1, "Avg Response Rate", f"{kpi['avg_response']}%" if kpi['avg_response'] else "—",
             "per cohort entry"),
        (c2, "Total Responses",   f"{kpi['total_responses']:,}", "across all cohorts"),
        (c3, "Total Cohort Size", f"{kpi['total_cohort']:,}",   "learners surveyed"),
        (c4, "Promoters",         f"{kpi['promoters']:,}",
             f"{round(kpi['promoters']/max(kpi['total_responses'],1)*100)}% of responses"),
        (c5, "Passives",          f"{kpi['passives']:,}",
             f"{round(kpi['passives']/max(kpi['total_responses'],1)*100)}% of responses"),
        (c6, "Detractors",        f"{kpi['detractors']:,}",
             f"{round(kpi['detractors']/max(kpi['total_responses'],1)*100)}% of responses"),
    ]:
        with col:
            border_color = C_GREEN if label=="Promoters" else \
                           C_AMBER if label=="Passives"  else \
                           C_RED   if label=="Detractors" else "#E2E8F0"
            st.markdown(
                f'<div class="kpi-card" style="border-top:3px solid {border_color};">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div>'
                f'<div class="kpi-sub">{sub}</div>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="nps-legend">'
        'NPS scale: <b style="color:#16A34A">Excellent ≥ 70</b> &nbsp;|&nbsp; '
        '<b style="color:#16A34A">Good 50–69</b> &nbsp;|&nbsp; '
        '<b style="color:#D97706">Needs Work 0–49</b> &nbsp;|&nbsp; '
        '<b style="color:#EF4444">Poor &lt; 0</b> &nbsp;|&nbsp; '
        'Response rate: <b style="color:#16A34A">≥50% good</b>, '
        '<b style="color:#D97706">30–50% monitor</b>, '
        '<b style="color:#EF4444">&lt;30% low — SSA action needed</b>'
        '</div>', unsafe_allow_html=True)

    # ── SECTION 1: SSA PERFORMANCE ────────────────────────────────────────
    st.markdown('<div class="section-header">① SSA Performance — NPS & Response Rate</div>',
                unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(chart_nps_by_ssa(df), use_container_width=True)
    with col_b:
        st.plotly_chart(chart_response_rate(df), use_container_width=True)

    # ── SECTION 2: RESPONDENT MIX ─────────────────────────────────────────
    st.markdown('<div class="section-header">② Promoter / Passive / Detractor Mix by SSA</div>',
                unsafe_allow_html=True)
    st.plotly_chart(chart_respondent_mix(df), use_container_width=True)

    # ── SECTION 3: CATEGORY & CHECKPOINT ─────────────────────────────────
    st.markdown('<div class="section-header">③ NPS by Category & Checkpoint</div>',
                unsafe_allow_html=True)
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(chart_nps_by_category(df), use_container_width=True)
    with col_d:
        st.plotly_chart(chart_nps_heatmap(df), use_container_width=True)

    st.plotly_chart(chart_nps_by_checkpoint(df), use_container_width=True)

    # ── SECTION 4: TREND & DISTRIBUTION ──────────────────────────────────
    st.markdown('<div class="section-header">④ NPS Trend & Score Distribution</div>',
                unsafe_allow_html=True)
    col_e, col_f = st.columns(2)
    with col_e:
        st.plotly_chart(chart_nps_trend(df), use_container_width=True)
    with col_f:
        st.plotly_chart(chart_nps_distribution(df), use_container_width=True)

    # ── SECTION 5: NPS ROUND DELTA ────────────────────────────────────────
    delta_fig = chart_nps_round_delta(df)
    if delta_fig:
        st.markdown('<div class="section-header">⑤ NPS Improvement — Round 1 to Round 2</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(delta_fig, use_container_width=True)

    # ── SECTION 6: SSA LEADERBOARD ────────────────────────────────────────
    st.markdown('<div class="section-header">⑥ SSA Leaderboard</div>',
                unsafe_allow_html=True)
    lb = table_ssa_leaderboard(df)

    def colour_nps(val):
        color = C_GREEN if val >= 50 else C_AMBER if val >= 0 else C_RED
        return f"color: {color}; font-weight: 700;"

    st.dataframe(
        lb.style.applymap(colour_nps, subset=["NPS"]),
        use_container_width=True, hide_index=True)

    # ── SECTION 7: RAW DATA ───────────────────────────────────────────────
    st.markdown('<div class="section-header">⑦ Filtered Data Table</div>',
                unsafe_allow_html=True)
    show_cols = ["SSA","Category","NPS Type","Cohort Name","Release Date",
                 "Promoters","Passive","Detractors","Responses",
                 "Cohort Size","NPS_computed","Response_pct"]
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(
        df[show_cols].rename(columns={
            "NPS_computed": "NPS Score",
            "Response_pct": "Response %",
        }),
        use_container_width=True, height=320)

    st.download_button(
        "⬇️ Download filtered data",
        data=df[show_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"ik_nps_{region_label.lower()}_filtered.csv",
        mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# RENDER TABS
# ─────────────────────────────────────────────────────────────────────────────

with tab_us:
    render_tab(df_us, "US")

with tab_india:
    render_tab(df_india, "India")

with tab_combined:
    st.markdown('<div class="dash-title">📈 US + India — Combined NPS View</div>',
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if df_india is None:
        st.info("India data not yet loaded. Add `data/nps_india.csv` to see combined view.")
    else:
        kpi_all = kpi_nps(df_all)
        nps_v   = kpi_all["overall_nps"]
        nps_c   = _nps_colour(nps_v)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f'<div class="kpi-card" style="border-top:4px solid {nps_c};">'
                f'<div class="kpi-label">Overall NPS (US + India)</div>'
                f'<div class="nps-score" style="color:{nps_c};">{nps_v}</div>'
                f'</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">US NPS</div>'
                f'<div class="kpi-value" style="color:{_nps_colour(kpi_nps(df_us).get("overall_nps"))};">'
                f'{kpi_nps(df_us).get("overall_nps")}</div></div>', unsafe_allow_html=True)
        with c3:
            india_nps = kpi_nps(df_india)["overall_nps"] if df_india is not None else None
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">India NPS</div>'
                f'<div class="kpi-value" style="color:{_nps_colour(india_nps)};">'
                f'{india_nps if india_nps else "—"}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(chart_nps_by_category(df_all), use_container_width=True)
        with col2:
            st.plotly_chart(chart_nps_trend(df_all), use_container_width=True)
        st.plotly_chart(chart_nps_by_ssa(df_all), use_container_width=True)

st.divider()
st.markdown(
    "<span style='font-size:11px;color:#94A3B8;'>"
    "IK NPS Dashboard · NPS = (Promoters − Detractors) / Responses × 100 · "
    "Add India CSV to unlock India tab · Built with Streamlit + Plotly"
    "</span>", unsafe_allow_html=True)
