"""
IK Refund Analysis Dashboard — Final Version
Run: streamlit run app.py
"""

import os
import pandas as pd
import numpy as np
import streamlit as st

from data_loader import load_refund, load_onboarding
from charts import (
    kpi_cards,
    chart_refund_rate_trend,
    chart_quarterly_enroll_vs_refund,
    chart_monthly_refund_line,
    chart_enrollments_vs_refunds,
    chart_bu_count_pie,
    chart_bu_amount_pie,
    chart_category,
    chart_course,
    chart_upfront_count,
    chart_upfront_amount,
    chart_payment_mode,
    chart_refund_reasons,
    chart_days_histogram,
    chart_days_buckets,
    chart_cohort_to_request_buckets,
    chart_by_country,
    chart_onboarding_status,
    chart_new_vs_alumni,
    chart_trial_window,
    chart_eligible_policy,
    chart_subset_overview, chart_subset_amount, chart_phase_timing,
    chart_subset_by_category, chart_reasons_by_subset,
    chart_days_distribution_by_subset, table_subset_summary,
    chart_orientation_split,
    chart_first_class_split,
    chart_orientation_attended,
    chart_first_class_attended,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IK Refund Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

  .dash-title {
    font-size: 40px; font-weight: 800; color: #0F172A;
    letter-spacing: -0.5px;
    text-decoration: underline;
    text-underline-offset: 6px;
    text-decoration-color: #2563EB;
    margin-bottom: 2px;
  }
  .kpi-card {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 18px 16px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06); height: 100%;
  }
  .kpi-label { font-size: 11px; color: #64748B; letter-spacing: 0.06em; text-transform: uppercase; }
  .kpi-value { font-size: 24px; font-weight: 700; color: #1E293B; margin: 6px 0 4px 0; }
  .kpi-sub   { font-size: 11px; color: #94A3B8; }
  .section-header {
    font-size: 17px; font-weight: 600; color: #1E293B;
    border-left: 4px solid #2563EB; padding-left: 10px; margin: 28px 0 14px 0;
  }
  .insight-box {
    background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 10px;
    padding: 14px 18px; font-size: 13.5px; color: #334155;
    line-height: 1.7; margin-bottom: 16px;
  }
  .insight-box ul { margin: 0; padding-left: 18px; }
  .insight-box li { margin-bottom: 5px; }
  .warn-box {
    background: #FFFBEB; border: 1px solid #FCD34D; border-radius: 8px;
    padding: 10px 14px; font-size: 13px; color: #92400E; margin-bottom: 12px;
  }
  .calc-note {
    background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px;
    padding: 10px 14px; font-size: 12.5px; color: #1E40AF; margin-bottom: 12px;
  }
  section[data-testid="stSidebar"] { background: #F8FAFC; }
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────────────────────

def get_data():
    # Refund data → BigQuery (auto-refreshes every 5 min via cache)
    # Onboarding data → CSV in GitHub repo
    df_r = load_refund()
    df_o = load_onboarding("onboarding_data.csv")
    return df_r, df_o

df_raw, df_onboard = get_data()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILTERS
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔍 Filters")
    st.caption("Applied to all charts and KPIs")
    st.divider()

    def clean_series(series):
        return series.fillna("Not Updated").astype(str).str.strip().replace(
            {"nan":"Not Updated","":"Not Updated","None":"Not Updated","NaN":"Not Updated"})

    def multiselect_filter(label, series, key):
        all_opts = sorted(series.unique().tolist(), key=str)
        return st.multiselect(label, options=all_opts, default=all_opts, key=key)

    # Month filter
    month_order = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26","May - 26","Jun - 26",
                   "Jul - 26","Aug - 26","Sep - 26","Oct - 26","Nov - 26","Dec - 26"]
    avail_months = [m for m in month_order
                    if m in df_raw["Refund Month"].astype(str).values]
    sel_month = st.multiselect("📅 Refund Month", options=avail_months,
                               default=avail_months, key="month")

    # Quarter filter
    avail_quarters = sorted(df_raw["refund_quarter"].dropna().unique().tolist())
    sel_quarter = st.multiselect("🗓️ Refund Quarter", options=avail_quarters,
                                 default=avail_quarters, key="quarter")

    st.divider()
    st.caption("BU → Category → Course filters cascade")

    # ── CASCADING FILTERS: BU → Category → Course ──────────────────────────
    # Step 1: BU — full dataset
    bu_opts = sorted(clean_series(df_raw["BU"]).unique().tolist(), key=str)
    sel_bu = st.multiselect("🏢 Business Unit (BU)", options=bu_opts,
                             default=bu_opts, key="bu")

    # Step 2: Category — only show categories under selected BUs
    # If BU selection changed, reset category and course to all-selected
    df_after_bu = df_raw[clean_series(df_raw["BU"]).isin(sel_bu)] if sel_bu else df_raw
    cat_opts = sorted(clean_series(df_after_bu["Category"]).unique().tolist(), key=str)

    # Auto-reset: if previously selected categories are no longer all valid
    # (e.g. user filtered to AI then came back to All), reset to all
    prev_bu = st.session_state.get("_prev_bu", bu_opts)
    if set(sel_bu) != set(prev_bu):
        st.session_state["_prev_bu"] = sel_bu
        # Reset downstream — force all selected
        for k in ["category", "course"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
    st.session_state["_prev_bu"] = sel_bu

    sel_category = st.multiselect("📂 Program Category", options=cat_opts,
                                   default=cat_opts, key="category")

    # Step 3: Course — only show courses under selected BU + Category combo
    df_after_cat = df_after_bu[clean_series(df_after_bu["Category"]).isin(sel_category)] if sel_category else df_after_bu
    course_opts = sorted(clean_series(df_after_cat["Course"]).unique().tolist(), key=str)

    # Auto-reset course if category changed
    prev_cat = st.session_state.get("_prev_cat", cat_opts)
    if set(sel_category) != set(prev_cat):
        st.session_state["_prev_cat"] = sel_category
        if "course" in st.session_state:
            del st.session_state["course"]
        st.rerun()
    st.session_state["_prev_cat"] = sel_category

    sel_course = st.multiselect("🎓 Course", options=course_opts,
                                 default=course_opts, key="course")

    st.divider()

    # Independent filters
    sel_country    = multiselect_filter("🌍 Country / Region",    clean_series(df_raw["Country"]),  "country")
    sel_payment    = multiselect_filter("💳 Payment Mode",        clean_series(df_raw["Payment Mode"]), "payment_mode")
    sel_upfront    = multiselect_filter("📦 Payment Type",
                                        clean_series(df_raw["Upfront Payment / Non Upfront / Flexipay"]), "upfront")
    sel_eligible   = multiselect_filter("✅ Eligible per Refund Policy",
                                        clean_series(df_raw["Eligible as per refund policy"]), "eligible")
    sel_new_alumni = multiselect_filter("👤 New / Alumni",        clean_series(df_raw["New / Alumni"]), "new_alumni")
    sel_ob_status  = multiselect_filter("🎯 Onboarding Status",   clean_series(df_raw["Onboarding Status"]), "ob_status")
    sel_trial      = multiselect_filter("⏱️ In Trial Window",
                                        clean_series(df_raw["Refund request received in Trial Window"]), "trial")
    sel_retained   = multiselect_filter("📋 Refund Type",
                                        clean_series(df_raw["Refund Type"]), "retained")
    sel_vs_orient  = multiselect_filter("🎯 Refund vs Orientation Date",
                                        clean_series(df_raw["refund_vs_orientation"]), "vs_orient")
    sel_vs_class   = multiselect_filter("📚 Refund vs First Class Date",
                                        clean_series(df_raw["refund_vs_first_class"]), "vs_class")
    sel_orient_att = multiselect_filter("✋ Attended Orientation",
                                        clean_series(df_raw["Orientation Attended"]), "orient_att")
    sel_class_att  = multiselect_filter("🖥️ Attended First Live Class",
                                        clean_series(df_raw["First Class Attended"]), "class_att")

    st.divider()
    st.caption("Q1=Jan–Mar · Q2=Apr–Jun · Q3=Jul–Sep · Q4=Oct–Dec")


# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def apply_str_filter(df, col, sel):
    clean = df[col].fillna("Not Updated").astype(str).str.strip().replace(
        {"nan":"Not Updated","":"Not Updated","None":"Not Updated","NaN":"Not Updated"})
    return df[clean.isin(sel)]

df = df_raw.copy()
if sel_month:
    df = df[df["Refund Month"].astype(str).isin(sel_month)]
if sel_quarter:
    df = df[df["refund_quarter"].isin(sel_quarter)]

# Cascading: BU → Category → Course applied in sequence
df = apply_str_filter(df, "BU",       sel_bu)
df = apply_str_filter(df, "Category", sel_category)
df = apply_str_filter(df, "Course",   sel_course)

# Independent filters
df = apply_str_filter(df, "Country",   sel_country)
df = apply_str_filter(df, "Payment Mode", sel_payment)
df = apply_str_filter(df, "Upfront Payment / Non Upfront / Flexipay", sel_upfront)
df = apply_str_filter(df, "Eligible as per refund policy", sel_eligible)
df = apply_str_filter(df, "New / Alumni",        sel_new_alumni)
df = apply_str_filter(df, "Onboarding Status",   sel_ob_status)
df = apply_str_filter(df, "Refund request received in Trial Window", sel_trial)
df = apply_str_filter(df, "Refund Type",   sel_retained)
df = apply_str_filter(df, "refund_vs_orientation",     sel_vs_orient)
df = apply_str_filter(df, "refund_vs_first_class",     sel_vs_class)
df = apply_str_filter(df, "Orientation Attended",      sel_orient_att)
df = apply_str_filter(df, "First Class Attended",      sel_class_att)

# Filter onboarding by same month/quarter for enrollment KPI
df_onboard_filtered = df_onboard.copy()
if sel_month:
    month_map = {
        "Jan - 26":"2026-01","Feb - 26":"2026-02","Mar - 26":"2026-03",
        "Apr - 26":"2026-04","May - 26":"2026-05","Jun - 26":"2026-06"
    }
    selected_periods = [month_map[m] for m in sel_month if m in month_map]
    if selected_periods:
        df_onboard_filtered = df_onboard_filtered[
            df_onboard_filtered["enrollment_month"].isin(selected_periods)]
if sel_quarter:
    df_onboard_filtered = df_onboard_filtered[
        df_onboard_filtered["enrollment_quarter"].isin(sel_quarter)]

total_enrollments = len(df_onboard_filtered)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="dash-title">📊 IK Refund Analysis Dashboard</div>',
            unsafe_allow_html=True)
st.markdown(
    f"<span style='color:#64748B;font-size:13px;'>"
    f"Source: <code>BigQuery: ik_refunds.refund_data</code> · <code>onboarding_data.csv</code> · "
    f"Showing <b>{len(df)}</b> of <b>{len(df_raw)}</b> refund records"
    f"</span>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if len(df) == 0:
    st.warning("No records match the current filters. Please adjust your selection.")
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab_main, tab_engagement = st.tabs(["📊 Refund Analysis", "🎯 Engagement Analysis"])

with tab_main:
    # KPI ROW
    # ─────────────────────────────────────────────────────────────────────────────
    
    kpi = kpi_cards(df, total_enrollments)
    total_refunded_amt = df["amount_refunded"].sum()
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    total_net_revenue = df["net_revenue"].sum()
    
    for col, label, value, sub in [
        (c1, "Total Refunds",          f"{kpi['total_refunds']}",             "drops in selected period"),
        (c2, "Total Enrollments",      f"{total_enrollments:,}",              "deposits paid in period"),
        (c3, "Refund Rate",            f"{kpi['refund_pct']:.1f}%",           "refunds ÷ enrollments"),
        (c4, "Total Net Revenue",      f"${total_net_revenue:,.0f}",          "net rev of refunded learners"),
        (c5, "Total Refunded Amt",     f"${total_refunded_amt:,.0f}",         "actual cash refunded"),
        (c6, "Median Days to Request", f"{kpi['avg_days_to_req']:.0f} days"
                                       if not pd.isna(kpi['avg_days_to_req']) else "—",
                                       "enrollment → refund request"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{value}</div>'
                f'<div class="kpi-sub">{sub}</div>'
                f'</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="calc-note">'
        '📐 <b>How metrics are calculated:</b> '
        'Refund Rate = refund records ÷ enrollments (Deposit Paid Date) for the same period · '
        'Median Days = median of (Refund Request Date − Date of Receipt) — '
        'median used because 4 enrollments from 2024/2025 skew the mean to 37 days; true median is 16 days · '
        'Total Refunded Amt = sum of "Amount refunded" column (actual cash returned)'
        '</div>', unsafe_allow_html=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ① MONTHLY & QUARTERLY TRENDS
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">① Trends — Refund Rate, Volume & Enrollments</div>',
                unsafe_allow_html=True)
    
    # Hero chart: Refund Rate % line + refund count + enrollment bars
    st.plotly_chart(chart_refund_rate_trend(df, df_onboard_filtered),
                    use_container_width=True)
    
    st.markdown(
        '<div class="warn-box">⚠️ <b>Maturity note:</b> Jun-26 refund data is still accruing — '
        'refund rate for this month will rise. Apr–May 2026 is the most mature comparison window.</div>',
        unsafe_allow_html=True)
    
    # Quarterly + Monthly side by side below
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.plotly_chart(chart_quarterly_enroll_vs_refund(df, df_onboard_filtered),
                        use_container_width=True)
    with col_t2:
        st.plotly_chart(chart_monthly_refund_line(df, df_onboard_filtered),
                        use_container_width=True)
    
    
    # Section 2 removed — covered by the quarterly + monthly combo charts in Section 1
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ③ SEGMENTATION
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">② Segmentation — BU, Category, Course</div>',
                unsafe_allow_html=True)
    # Pies side by side in narrow columns, padded either side
    _, col_s1, col_s2, _ = st.columns([0.5, 2, 2, 0.5])
    with col_s1:
        st.plotly_chart(chart_bu_count_pie(df), use_container_width=True)
    with col_s2:
        st.plotly_chart(chart_bu_amount_pie(df), use_container_width=True)
    # Category full width — needs room for all 7 bars + labels
    st.plotly_chart(chart_category(df), use_container_width=True)
    # Course full width below
    st.plotly_chart(chart_course(df), use_container_width=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ④ PAYMENT TYPE ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">③ Payment Type Analysis</div>',
                unsafe_allow_html=True)
    # Upfront count + amount side by side
    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(chart_upfront_count(df), use_container_width=True)
    with col6:
        st.plotly_chart(chart_upfront_amount(df), use_container_width=True)
    # Payment mode gets full width so labels aren't cramped
    st.plotly_chart(chart_payment_mode(df), use_container_width=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑤ REFUND REASONS
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">④ Why Are Students Refunding?</div>',
                unsafe_allow_html=True)
    st.plotly_chart(chart_refund_reasons(df), use_container_width=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑥ TIMING ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">⑤ Timing Analysis — Days Between Key Events</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="calc-note">'
        '📐 <b>How days are calculated:</b><br>'
        '• <b>Enrollment → Refund Request:</b> Refund Request Date − Date of Receipt (enrollment date)<br>'
        '• <b>Cohort Start → Refund Request:</b> Refund Request Date − Cohort Start Date<br>'
        'All in calendar days. '
        '<b>Negative values in Chart 3 are valid</b> — these students enrolled early for a future cohort and refunded before it started. '
        'Blank dates excluded from calculations.'
        '</div>', unsafe_allow_html=True)
    
    col8, col9, col10 = st.columns(3)
    with col8:
        st.plotly_chart(chart_days_histogram(df), use_container_width=True)
    with col9:
        st.plotly_chart(chart_days_buckets(df), use_container_width=True)
    with col10:
        st.plotly_chart(chart_cohort_to_request_buckets(df), use_container_width=True)
    
    # Summary stats table for both metrics
    dd_pairs = [
        ("days_enroll_to_refund_req",  "Enrollment → Refund Request"),
        ("days_cohort_to_refund_req",  "Cohort Start → Refund Request"),
    ]
    rows = []
    for col_name, label in dd_pairs:
        v = df[col_name].dropna()
        rows.append({"Metric": label, "Mean": round(v.mean(),1),
                     "Median": v.median(), "Min": v.min(),
                     "Max": v.max(), "Blanks": df[col_name].isna().sum()})
    stats_df = pd.DataFrame(rows).set_index("Metric")
    st.dataframe(stats_df, use_container_width=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑦ REGION / ONBOARDING / LEARNER TYPE
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">⑥ Region, Onboarding Status & Learner Type</div>',
                unsafe_allow_html=True)
    # Country is narrow (only 2 bars), onboarding gets more space
    col11, col12 = st.columns([1, 2])
    with col11:
        st.plotly_chart(chart_by_country(df), use_container_width=True)
    with col12:
        st.plotly_chart(chart_onboarding_status(df), use_container_width=True)
    # Bottom row: two donuts — padded so they don't stretch full width
    _, col13, col14, _ = st.columns([0.5, 2, 2, 0.5])
    with col13:
        st.plotly_chart(chart_new_vs_alumni(df), use_container_width=True)
    with col14:
        st.plotly_chart(chart_trial_window(df), use_container_width=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑧ REFUND POLICY ELIGIBILITY
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">⑦ Refund Policy Eligibility</div>',
                unsafe_allow_html=True)
    st.plotly_chart(chart_eligible_policy(df), use_container_width=True)
    
    # Breakdown table
    elig_grp = df.groupby("Eligible as per refund policy").agg(
        Count=("Hubspot id","count"),
        Amount_Refunded=("amount_refunded","sum"),
        Pct_of_Total=("Hubspot id","count")
    ).reset_index()
    elig_grp["Pct_of_Total"] = (elig_grp["Count"] / elig_grp["Count"].sum() * 100).round(1).astype(str) + "%"
    elig_grp["Amount_Refunded"] = elig_grp["Amount_Refunded"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(elig_grp.rename(columns={
        "Eligible as per refund policy":"Eligible per Policy",
        "Amount_Refunded":"Amount Refunded",
        "Pct_of_Total":"% of Total Refunds"
    }), use_container_width=True, hide_index=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑧ ENGAGEMENT — ORIENTATION & FIRST CLASS
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">⑧ Engagement — Orientation & First Class</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="calc-note">'
        '📐 <b>How calculated:</b> "Before" = Refund Request Date earlier than event date · '
        '"After" = on or after event date · "Not Updated" = date missing in source data.'
        '</div>', unsafe_allow_html=True)
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.plotly_chart(chart_orientation_split(df), use_container_width=True)
    with col_e2:
        st.plotly_chart(chart_first_class_split(df), use_container_width=True)
    col_e3, col_e4 = st.columns(2)
    with col_e3:
        st.plotly_chart(chart_orientation_attended(df), use_container_width=True)
    with col_e4:
        st.plotly_chart(chart_first_class_attended(df), use_container_width=True)
    
    st.markdown("**Engagement Summary**")
    _rows = []
    for _c, _l in [("Orientation Attended","Attended Orientation"),
                   ("First Class Attended","Attended First Live Class"),
                   ("refund_vs_orientation","Refunded Before/After Orientation"),
                   ("refund_vs_first_class","Refunded Before/After First Class")]:
        if _c in df.columns:
            _g = df.groupby(_c).agg(Count=("Hubspot id","count"),Amount=("amount_refunded","sum")).reset_index()
            _g.columns = ["Value","Count","Amount ($)"]
            _g["Metric"] = _l
            _g["Amount ($)"] = _g["Amount ($)"].apply(lambda x: f"${x:,.0f}")
            _rows.append(_g[["Metric","Value","Count","Amount ($)"]])
    if _rows:
        st.dataframe(pd.concat(_rows, ignore_index=True), use_container_width=True, hide_index=True)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑨ AI INSIGHTS
    # ─────────────────────────────────────────────────────────────────────────────
    
    api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
    
    if api_key:
        import insights as ins
        ins.API_KEY = api_key
        st.markdown('<div class="section-header">⑧ AI-Generated Insights</div>',
                    unsafe_allow_html=True)
        st.caption("Powered by GPT-4o-mini · Updates when filters change")
    
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            with st.expander("📈 Trend & Volume", expanded=True):
                stats = df.groupby("Refund Month", observed=True).agg(
                    count=("Hubspot id","count"), amount=("amount_refunded","sum")).to_json()
                with st.spinner("Analysing…"):
                    text = ins.insight_overview(stats)
                bullets = [l.strip().lstrip("•-").strip() for l in text.strip().split("\n") if l.strip()]
                st.markdown('<div class="insight-box"><ul>' +
                            "".join(f"<li>{b}</li>" for b in bullets if b) +
                            "</ul></div>", unsafe_allow_html=True)
    
            with st.expander("💳 Payment Type Risk", expanded=False):
                stats = df.groupby("Upfront Payment / Non Upfront / Flexipay").agg(
                    count=("Hubspot id","count"), amount=("amount_refunded","sum")).to_json()
                with st.spinner("Analysing…"):
                    text = ins.insight_payment_type(stats)
                bullets = [l.strip().lstrip("•-").strip() for l in text.strip().split("\n") if l.strip()]
                st.markdown('<div class="insight-box"><ul>' +
                            "".join(f"<li>{b}</li>" for b in bullets if b) +
                            "</ul></div>", unsafe_allow_html=True)
    
        with col_i2:
            with st.expander("🎓 Course Risk", expanded=True):
                stats = df.groupby("Course").agg(
                    count=("Hubspot id","count"), amount=("amount_refunded","sum")).to_json()
                with st.spinner("Analysing…"):
                    text = ins.insight_course(stats)
                bullets = [l.strip().lstrip("•-").strip() for l in text.strip().split("\n") if l.strip()]
                st.markdown('<div class="insight-box"><ul>' +
                            "".join(f"<li>{b}</li>" for b in bullets if b) +
                            "</ul></div>", unsafe_allow_html=True)
    
            with st.expander("⚠️ Refund Reasons", expanded=False):
                stats = df.groupby("Refund Category").agg(
                    count=("Hubspot id","count"), amount=("amount_refunded","sum")).to_json()
                with st.spinner("Analysing…"):
                    text = ins.insight_reasons(stats)
                bullets = [l.strip().lstrip("•-").strip() for l in text.strip().split("\n") if l.strip()]
                st.markdown('<div class="insight-box"><ul>' +
                            "".join(f"<li>{b}</li>" for b in bullets if b) +
                            "</ul></div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-header">⑧ AI-Generated Insights</div>',
                    unsafe_allow_html=True)
        st.info(
            "💡 **To enable AI insights:** Streamlit Cloud → your app → "
            "**Settings → Secrets** → add:\n\n"
            "```\nOPENAI_API_KEY = \"sk-proj-...\"\n```\n\n"
            "Get your key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)",
            icon="🔑")
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # ⑩ FILTERED DATA TABLE
    # ─────────────────────────────────────────────────────────────────────────────
    
    st.markdown('<div class="section-header">⑩ Filtered Data Table</div>',
                unsafe_allow_html=True)
    display_cols = [
        "Hubspot id","Cohort","BU","Category","Course","Country",
        "Upfront Payment / Non Upfront / Flexipay","Payment Mode",
        "net_revenue","amount_refunded",
        "Refund Category","Refund Month","Eligible as per refund policy",
        "days_enroll_to_refund_req",
        "Refund request received in Trial Window",
        "Onboarding Status","New / Alumni",
    ]
    show_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[show_cols].rename(columns={
            "Upfront Payment / Non Upfront / Flexipay": "Payment Type",
            "net_revenue":         "Net Revenue ($)",
            "amount_refunded":     "Amount Refunded ($)",
            "days_enroll_to_refund_req": "Days: Enroll→Request",
            "Refund request received in Trial Window": "In Trial Window",
            "Eligible as per refund policy": "Eligible per Policy",
        }),
        use_container_width=True, height=350)
    
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=df[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="ik_refund_filtered.csv", mime="text/csv")
    
    # ─────────────────────────────────────────────────────────────────────────────
    

with tab_engagement:
    # ENGAGEMENT — ORIENTATION & FIRST CLASS ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────

    st.markdown(
        '<div class="section-header">Engagement — Orientation & First Class Analysis</div>',
        unsafe_allow_html=True)

    valid_sub    = df[df["Attendance Subset"] != "Not Updated"]
    total_valid  = len(valid_sub)
    if total_valid > 0:
        attended_both    = len(valid_sub[valid_sub["Attendance Subset"]=="Attended Both"])
        attended_neither = len(valid_sub[valid_sub["Attendance Subset"]=="Attended Neither"])
        before_orient    = int((valid_sub["days_to_orientation"] < 0).sum())
        after_orient     = int((valid_sub["days_to_orientation"] >= 0).sum())
        st.markdown(
            f'<div class="calc-note">'
            f'<b>Quick Read:</b> Of <b>{total_valid}</b> learners with attendance data — '
            f'<b style="color:#16A34A">{attended_both} ({attended_both/total_valid*100:.0f}%)</b> attended both · '
            f'<b style="color:#EF4444">{attended_neither} ({attended_neither/total_valid*100:.0f}%)</b> attended neither · '
            f'<b style="color:#F59E0B">{before_orient}</b> refunded before orientation · '
            f'<b style="color:#2563EB">{after_orient}</b> refunded after orientation',
            unsafe_allow_html=True)

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.plotly_chart(chart_subset_overview(df), use_container_width=True)
    with col_e2:
        st.plotly_chart(chart_subset_amount(df), use_container_width=True)

    st.plotly_chart(chart_phase_timing(df), use_container_width=True)

    st.plotly_chart(chart_subset_by_category(df), use_container_width=True)

    st.plotly_chart(chart_reasons_by_subset(df), use_container_width=True)

    st.markdown("**Attendance Subset — Master Summary**")
    st.caption("Before/After counts include only rows where event date is available. "
               "No Orient. Date = rows missing orientation date. "
               "Before + After + No Date = Total Refunds per subset.")
    st.dataframe(table_subset_summary(df), use_container_width=True, hide_index=True)

st.divider()
st.markdown(
    "<span style='font-size:11px;color:#94A3B8;'>"
    "IK Refund Dashboard · Data: Google Sheets export · "
    "Add column AD (Agentic/IP) to refund sheet to unlock that filter · "
    "Add column AD (Agentic/IP) to refund sheet to unlock that filter · Built with Streamlit + Plotly"
    "</span>", unsafe_allow_html=True)
