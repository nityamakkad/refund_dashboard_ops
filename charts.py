import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

C_BLUE   = "#2563EB"
C_RED    = "#EF4444"
C_GREEN  = "#16A34A"
C_AMBER  = "#D97706"
C_TEAL   = "#0D9488"
C_SLATE  = "#64748B"

UPFRONT_COLORS = {
    "Upfront": C_GREEN, "Flexipay": C_AMBER,
    "Non upfront": C_RED, "Unknown": C_SLATE, "Not Updated": C_SLATE,
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#1E293B"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def kpi_cards(df, total_enrollments):
    total_refunds = len(df)
    total_revenue = df["net_revenue"].sum()
    refund_pct    = (total_refunds / total_enrollments * 100) if total_enrollments else 0
    avg_days      = df["days_enroll_to_refund_req"].dropna().median()
    trial_pct     = (df["Refund request received in Trial Window"]
                     .str.strip().str.lower().eq("yes").sum()
                     / total_refunds * 100) if total_refunds else 0
    return dict(total_refunds=total_refunds, total_revenue=total_revenue,
                refund_pct=refund_pct, avg_days_to_req=avg_days, trial_pct=trial_pct)


# ── SECTION 1 ─────────────────────────────────────────────────────────────

def chart_refund_rate_trend(df_r, df_o):
    month_map  = {"Jan - 26":"2026-01","Feb - 26":"2026-02","Mar - 26":"2026-03",
                  "Apr - 26":"2026-04","May - 26":"2026-05","Jun - 26":"2026-06",
                  "Jul - 26":"2026-07","Aug - 26":"2026-08","Sep - 26":"2026-09",
                  "Oct - 26":"2026-10","Nov - 26":"2026-11","Dec - 26":"2026-12"}
    label_map  = {"2026-01":"Jan-26","2026-02":"Feb-26","2026-03":"Mar-26",
                  "2026-04":"Apr-26","2026-05":"May-26","2026-06":"Jun-26",
                  "2026-07":"Jul-26","2026-08":"Aug-26","2026-09":"Sep-26",
                  "2026-10":"Oct-26","2026-11":"Nov-26","2026-12":"Dec-26"}
    enr = df_o.groupby("enrollment_month").size().rename("enrollments").reset_index()
    ref = df_r.groupby("Refund Month", observed=True).size().rename("refunds").reset_index()
    ref["enrollment_month"] = ref["Refund Month"].astype(str).map(month_map)
    ref = ref[ref["enrollment_month"].notna()]
    merged = enr.merge(ref[["enrollment_month","refunds"]], on="enrollment_month", how="left").fillna({"refunds":0})
    merged["refunds"] = merged["refunds"].astype(int)
    merged["refund_rate"] = (merged["refunds"] / merged["enrollments"] * 100).round(1)
    merged = merged[merged["enrollment_month"].isin(label_map)].sort_values("enrollment_month")
    merged["label"] = merged["enrollment_month"].map(label_map)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=merged["label"], y=merged["enrollments"], name="Enrollments",
                         marker_color="#93C5FD", opacity=0.65,
                         text=merged["enrollments"], textposition="inside",
                         textfont=dict(color="#475569", size=11)), secondary_y=False)
    fig.add_trace(go.Scatter(x=merged["label"], y=merged["refunds"], name="Refund Count",
                             mode="lines+markers+text", text=merged["refunds"],
                             textposition="top center", textfont=dict(color=C_RED, size=11),
                             line=dict(color=C_RED, width=2.5),
                             marker=dict(size=9, color=C_RED, line=dict(color="white", width=2))),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=merged["label"], y=merged["refund_rate"], name="Refund Rate %",
                             mode="lines+markers+text",
                             text=[f"{v}%" for v in merged["refund_rate"]],
                             textposition="bottom center",
                             textfont=dict(color=C_BLUE, size=12),
                             line=dict(color=C_BLUE, width=3),
                             marker=dict(size=10, color=C_BLUE, line=dict(color="white", width=2))),
                  secondary_y=True)
    fig.update_yaxes(title_text="Enrollments", secondary_y=False, showgrid=True, gridcolor="#F1F5F9")
    fig.update_yaxes(title_text="Count / Rate %", secondary_y=True, showgrid=False)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(title="Monthly Refund Rate % · Refund Count · Enrollments",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      **{k:v for k,v in CHART_LAYOUT.items() if k!="legend"})
    return fig


def chart_quarterly_enroll_vs_refund(df_r, df_o):
    all_months = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26","May - 26","Jun - 26",
                  "Jul - 26","Aug - 26","Sep - 26","Oct - 26","Nov - 26","Dec - 26"]
    grp = df_r.groupby("Refund Month", observed=True)["amount_refunded"].sum().reset_index()
    grp.columns = ["month","amount"]
    grp["month"] = pd.Categorical(grp["month"].astype(str), categories=all_months, ordered=True)
    grp = grp[grp["month"].notna() & grp["amount"].gt(0)].sort_values("month")
    fig = go.Figure(go.Bar(x=grp["month"].astype(str), y=grp["amount"],
                           marker_color=C_TEAL, opacity=0.88,
                           text=[f"${v/1000:.0f}K" for v in grp["amount"]],
                           textposition="outside", textfont=dict(size=13, color="#0F172A")))
    layout = {**CHART_LAYOUT}
    layout["height"] = 320
    fig.update_layout(title="Amount Refunded by Month ($)", yaxis_title="Amount ($)",
                      xaxis_title="Refund Month", **layout)
    return fig


def chart_monthly_refund_line(df_r, df_o):
    month_order  = ["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06",
                    "2026-07","2026-08","2026-09","2026-10","2026-11","2026-12"]
    month_labels = {"2026-01":"Jan-26","2026-02":"Feb-26","2026-03":"Mar-26",
                    "2026-04":"Apr-26","2026-05":"May-26","2026-06":"Jun-26",
                    "2026-07":"Jul-26","2026-08":"Aug-26","2026-09":"Sep-26",
                    "2026-10":"Oct-26","2026-11":"Nov-26","2026-12":"Dec-26"}
    ref_month_map = {"Jan - 26":"Jan-26","Feb - 26":"Feb-26","Mar - 26":"Mar-26",
                     "Apr - 26":"Apr-26","May - 26":"May-26","Jun - 26":"Jun-26",
                     "Jul - 26":"Jul-26","Aug - 26":"Aug-26","Sep - 26":"Sep-26",
                     "Oct - 26":"Oct-26","Nov - 26":"Nov-26","Dec - 26":"Dec-26"}
    enr = df_o.groupby("enrollment_month").size().rename("enrollments").reset_index()
    enr["label"] = enr["enrollment_month"].map(month_labels)
    enr = enr[enr["label"].notna()].sort_values("enrollment_month")
    ref = df_r.groupby("Refund Month", observed=True).size().rename("refunds").reset_index()
    ref["label"] = ref["Refund Month"].astype(str).map(ref_month_map)
    ref = ref[ref["label"].notna()].sort_values("label")
    merged = enr.merge(ref[["label","refunds"]], on="label", how="left").fillna({"refunds": 0})
    merged["refunds"] = merged["refunds"].astype(int)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=merged["label"], y=merged["enrollments"], name="Enrollments",
                         marker_color=C_BLUE, opacity=0.7,
                         text=merged["enrollments"], textposition="inside",
                         textfont=dict(color="white", size=13)), secondary_y=False)
    fig.add_trace(go.Scatter(x=merged["label"], y=merged["refunds"], name="Refund Count",
                             mode="lines+markers+text", text=merged["refunds"],
                             textposition="top center", textfont=dict(color=C_RED, size=12),
                             line=dict(color=C_RED, width=2.5),
                             marker=dict(size=10, color=C_RED, line=dict(color="white", width=2))),
                  secondary_y=True)
    fig.update_yaxes(title_text="Enrollments", secondary_y=False, showgrid=True, gridcolor="#F1F5F9")
    fig.update_yaxes(title_text="Refund Count", secondary_y=True, showgrid=False)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(title="Monthly Enrollments & Refund Count",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      **{k:v for k,v in CHART_LAYOUT.items() if k!="legend"})
    return fig


# ── SECTION 2 ─────────────────────────────────────────────────────────────

def chart_enrollments_vs_refunds(df_o, df_r):
    enr = df_o.groupby("enrollment_month").size().rename("enrollments").reset_index()
    ref = df_r.groupby("enrollment_month").size().rename("refunds").reset_index()
    merged = enr.merge(ref, on="enrollment_month", how="left").fillna({"refunds": 0})
    merged["refund_pct"] = (merged["refunds"] / merged["enrollments"] * 100).round(1)
    merged = merged[merged["enrollment_month"].notna()].sort_values("enrollment_month")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=merged["enrollment_month"], y=merged["enrollments"],
                         name="Enrollments", marker_color="#BFDBFE", opacity=0.9), secondary_y=False)
    fig.add_trace(go.Bar(x=merged["enrollment_month"], y=merged["refunds"],
                         name="Refunds", marker_color=C_RED, opacity=0.85), secondary_y=False)
    fig.add_trace(go.Scatter(x=merged["enrollment_month"], y=merged["refund_pct"],
                             name="Refund %", mode="lines+markers",
                             line=dict(color="#1E293B", width=2), marker=dict(size=6)),
                  secondary_y=True)
    fig.update_yaxes(title_text="Count", secondary_y=False)
    fig.update_yaxes(title_text="Refund %", secondary_y=True, showgrid=False)
    fig.update_layout(title="Enrollments vs Refunds by Month (Enrollment Cohort)",
                      barmode="overlay", **CHART_LAYOUT)
    return fig


# ── SECTION 3 ─────────────────────────────────────────────────────────────

def chart_bu_count_pie(df):
    grp = df.groupby("BU").size().reset_index(name="count")
    fig = go.Figure(go.Pie(labels=grp["BU"], values=grp["count"], hole=0.45,
                           marker_colors=[C_BLUE, C_AMBER], textinfo="label+percent+value"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=20, r=20, t=40, b=20)
    fig.update_layout(title="Refund Count by BU", **layout)
    return fig


def chart_bu_amount_pie(df):
    grp = df.groupby("BU").agg(amount=("amount_refunded","sum")).reset_index()
    fig = go.Figure(go.Pie(labels=grp["BU"], values=grp["amount"], hole=0.45,
                           marker_colors=[C_BLUE, C_AMBER], textinfo="label+percent",
                           hovertemplate="%{label}: $%{value:,.0f}<extra></extra>"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=20, r=20, t=40, b=20)
    fig.update_layout(title="Total Amount Refunded by BU ($)", **layout)
    return fig


def chart_category(df):
    grp = (df.groupby("Category").agg(count=("Hubspot id","count"), amount=("amount_refunded","sum"))
             .sort_values("count", ascending=True).reset_index())
    palette = ["#6366F1","#0EA5E9","#10B981","#F59E0B","#F97316","#8B5CF6","#EC4899","#14B8A6"]
    colors = [palette[i % len(palette)] for i in range(len(grp))]
    fig = go.Figure(go.Bar(y=grp["Category"], x=grp["count"], orientation="h",
                           marker_color=colors, opacity=0.9,
                           text=[f"${v:,.0f}" for v in grp["amount"]],
                           textposition="outside", textfont=dict(size=11)))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=90, r=130, t=40, b=10)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(range=[0, grp["count"].max() * 1.9])
    fig.update_layout(title="Refunds by Program Category", xaxis_title="# Refunds", **layout)
    return fig


def chart_course(df):
    grp = (df.groupby("Course").agg(count=("Hubspot id","count"), amount=("amount_refunded","sum"))
             .sort_values("count", ascending=False).head(15).reset_index())
    fig = px.bar(grp, x="Course", y="count", color="count",
                 color_continuous_scale=[[0,"#BFDBFE"],[1,C_BLUE]],
                 text=[f"${v/1000:.0f}K" for v in grp["amount"]])
    fig.update_traces(textposition="outside")
    fig.update_coloraxes(showscale=False)
    layout = {**CHART_LAYOUT}
    layout["height"] = 320
    fig.update_layout(title="Top Courses by Refund Volume ($ = amount refunded)",
                      yaxis_title="# Refunds", **layout)
    return fig


# ── SECTION 4 ─────────────────────────────────────────────────────────────

def chart_upfront_count(df):
    col = "Upfront Payment / Non Upfront / Flexipay"
    grp = df.groupby(col).size().reset_index(name="count")
    grp.columns = ["type","count"]
    colors = [UPFRONT_COLORS.get(t, C_SLATE) for t in grp["type"]]
    fig = go.Figure(go.Bar(x=grp["type"], y=grp["count"], marker_color=colors,
                           text=grp["count"], textposition="outside"))
    fig.update_layout(title="Refund Count by Payment Type", yaxis_title="# Refunds", **CHART_LAYOUT)
    return fig


def chart_upfront_amount(df):
    col = "Upfront Payment / Non Upfront / Flexipay"
    grp = df.groupby(col).agg(amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["type","amount"]
    colors = [UPFRONT_COLORS.get(t, C_SLATE) for t in grp["type"]]
    fig = go.Figure(go.Bar(x=grp["type"], y=grp["amount"], marker_color=colors,
                           text=[f"${v:,.0f}" for v in grp["amount"]], textposition="outside"))
    fig.update_layout(title="Total Amount Refunded by Payment Type ($)",
                      yaxis_title="Amount Refunded ($)", **CHART_LAYOUT)
    return fig


def chart_payment_mode(df):
    grp = (df.groupby("Payment Mode").agg(count=("Hubspot id","count"), amount=("amount_refunded","sum"))
             .sort_values("amount", ascending=True).reset_index())
    fig = go.Figure(go.Bar(y=grp["Payment Mode"], x=grp["amount"], orientation="h",
                           marker=dict(color=grp["count"], colorscale=[[0,"#BFDBFE"],[1,C_BLUE]],
                                       showscale=True, colorbar=dict(title="# Refunds", thickness=12)),
                           text=[f"n={v}" for v in grp["count"]], textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=120, r=40, t=40, b=10)
    fig.update_layout(title="Amount Refunded by Payment Mode (colour = count)",
                      xaxis_title="Amount Refunded ($)", **layout)
    return fig


# ── SECTION 5 ─────────────────────────────────────────────────────────────

def chart_refund_reasons(df):
    grp = (df.groupby("Refund Category").agg(count=("Hubspot id","count"), amount=("amount_refunded","sum"))
             .sort_values("count", ascending=True).reset_index())
    norm = (grp["count"] - grp["count"].min()) / (grp["count"].max() - grp["count"].min() + 1)
    colors = [f"rgba(239,{int(68+50*(1-n))},{int(68+50*(1-n))},{0.5+0.5*n})" for n in norm]
    fig = go.Figure(go.Bar(y=grp["Refund Category"], x=grp["count"], orientation="h",
                           marker_color=colors,
                           text=[f"${v:,.0f}" for v in grp["amount"]], textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 320
    layout["margin"] = dict(l=160, r=130, t=40, b=10)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(range=[0, grp["count"].max() * 2.0])
    fig.update_layout(title="Refund Reasons — Count & Amount Refunded ($)",
                      xaxis_title="# Refunds", **layout)
    return fig


# ── SECTION 6 ─────────────────────────────────────────────────────────────

def chart_days_histogram(df):
    vals = df["days_enroll_to_refund_req"].dropna()
    median_val = vals.median()
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=vals, nbinsx=25, marker_color=C_BLUE, opacity=0.8, name="# Refunds"))
    fig.add_vline(x=median_val, line_dash="dash", line_color=C_RED, line_width=2,
                  annotation_text=f"Median: {median_val:.0f}d", annotation_position="top right")
    fig.update_layout(title="Days: Enrollment → Refund Request",
                      xaxis_title="Days", yaxis_title="# Refunds", **CHART_LAYOUT)
    return fig


def chart_days_buckets(df):
    vals = df["days_enroll_to_refund_req"].dropna()
    bins   = [-1, 7, 14, 30, 60, 10000]
    labels = ["0-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
    bucketed = pd.cut(vals, bins=bins, labels=labels)
    grp = bucketed.value_counts().reindex(labels).reset_index()
    grp.columns = ["bucket","count"]
    bucket_colors = [C_RED, "#F97316", C_AMBER, C_TEAL, C_SLATE]
    fig = go.Figure(go.Bar(x=grp["bucket"], y=grp["count"], marker_color=bucket_colors,
                           text=grp["count"], textposition="outside"))
    fig.update_layout(title="Enrollment → Request (Bucketed)",
                      xaxis_title="Days After Enrollment", yaxis_title="# Refunds", **CHART_LAYOUT)
    return fig


def chart_cohort_to_request_buckets(df):
    vals = df["days_cohort_to_refund_req"].dropna()
    bins   = [-10000, -1, 7, 14, 30, 60, 10000]
    labels = ["Before cohort started", "0-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
    bucketed = pd.cut(vals, bins=bins, labels=labels)
    grp = bucketed.value_counts().reindex(labels).reset_index()
    grp.columns = ["bucket","count"]
    bucket_colors = [C_SLATE, C_RED, "#F97316", C_AMBER, C_TEAL, "#6366F1"]
    fig = go.Figure(go.Bar(x=grp["bucket"], y=grp["count"], marker_color=bucket_colors,
                           text=grp["count"], textposition="outside"))
    fig.update_layout(title="Cohort Start → Request (Bucketed)",
                      xaxis_title="Days After Cohort Start", yaxis_title="# Refunds", **CHART_LAYOUT)
    return fig


# ── SECTION 7 ─────────────────────────────────────────────────────────────

def chart_by_country(df):
    grp = df.groupby("Country").agg(count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    fig = px.bar(grp, x="Country", y="count", text=[f"${v/1000:.0f}K" for v in grp["amount"]],
                 color="Country", color_discrete_sequence=[C_BLUE, C_TEAL, C_AMBER])
    fig.update_traces(textposition="outside")
    fig.update_layout(title="Refunds by Country ($ = amount refunded)",
                      showlegend=False, yaxis_title="# Refunds", **CHART_LAYOUT)
    return fig


def chart_onboarding_status(df):
    grp = df.groupby("Onboarding Status").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    color_map = {"Onboarded":C_GREEN,"Incomplete OB":C_AMBER,"Not Updated":C_SLATE,"VM - 4 Attempts":C_RED}
    colors = [color_map.get(s, C_BLUE) for s in grp["Onboarding Status"]]
    fig = go.Figure(go.Bar(y=grp["Onboarding Status"], x=grp["count"], orientation="h",
                           marker_color=colors, opacity=0.9,
                           text=[f"  n={c}  ${a:,.0f}" for c,a in zip(grp["count"],grp["amount"])],
                           textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = 280
    layout["margin"] = dict(l=120, r=220, t=40, b=10)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(range=[0, grp["count"].max() * 2.2])
    fig.update_layout(title="Refunds by Onboarding Status", xaxis_title="# Refunds", **layout)
    return fig


def chart_new_vs_alumni(df):
    grp = df.groupby("New / Alumni").size().reset_index(name="count")
    grp.columns = ["type","count"]
    color_map = {"New":C_TEAL,"Alumni":"#7C3AED","Unknown":C_SLATE,"Not Updated":C_SLATE}
    colors = [color_map.get(t, C_SLATE) for t in grp["type"]]
    fig = go.Figure(go.Pie(labels=grp["type"], values=grp["count"], hole=0.45,
                           marker_colors=colors, textinfo="label+percent+value"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=20, r=20, t=40, b=20)
    fig.update_layout(title="New vs Alumni — Refund Split", **layout)
    return fig


def chart_trial_window(df):
    grp = df.groupby("Refund request received in Trial Window").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["trial","count","amount"]
    color_map = {"Yes":C_BLUE,"No":C_AMBER,"Unknown":C_SLATE,"Not Updated":C_SLATE}
    colors = [color_map.get(t, C_SLATE) for t in grp["trial"]]
    fig = go.Figure(go.Pie(labels=grp["trial"], values=grp["count"], hole=0.45,
                           marker_colors=colors, textinfo="label+percent+value",
                           hovertemplate="%{label}: %{value} refunds · $%{customdata:,.0f}<extra></extra>",
                           customdata=grp["amount"]))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=20, r=20, t=40, b=20)
    fig.update_layout(title="Within Trial Window?", **layout)
    return fig


def chart_eligible_policy(df):
    grp = df.groupby("Eligible as per refund policy").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["eligible","count","amount"]
    color_map = {"Yes":C_GREEN,"No":C_RED,"Not Updated":C_SLATE}
    colors = [color_map.get(e, C_SLATE) for e in grp["eligible"]]
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("# Refunds by Policy Eligibility",
                                        "Amount Refunded by Policy Eligibility ($)"))
    fig.add_trace(go.Bar(x=grp["eligible"], y=grp["count"], marker_color=colors,
                         text=grp["count"], textposition="outside", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=grp["eligible"], y=grp["amount"], marker_color=colors,
                         text=[f"${v:,.0f}" for v in grp["amount"]],
                         textposition="outside", showlegend=False), row=1, col=2)
    layout = {**CHART_LAYOUT}
    layout["height"] = 280
    layout["margin"] = dict(l=30, r=30, t=50, b=20)
    fig.update_layout(title="Eligible as per Refund Policy", **layout)
    return fig


# ── SECTION 8 — ENGAGEMENT ────────────────────────────────────────────────

def chart_orientation_split(df):
    grp = df.groupby("refund_vs_orientation").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["bucket","count","amount"]
    order = ["Before Orientation","After Orientation","Not Updated"]
    grp["bucket"] = pd.Categorical(grp["bucket"], categories=order, ordered=True)
    grp = grp.sort_values("bucket")
    color_map = {"Before Orientation":"#F59E0B","After Orientation":"#2563EB","Not Updated":C_SLATE}
    colors = [color_map.get(str(b), C_SLATE) for b in grp["bucket"]]
    fig = go.Figure(go.Bar(
        x=grp["bucket"].astype(str), y=grp["count"],
        marker_color=colors, opacity=0.88,
        text=[f"{c} | ${a/1000:.0f}K" for c,a in zip(grp["count"],grp["amount"])],
        textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.update_layout(title="Refund Timing vs Orientation Date", yaxis_title="# Refunds", **layout)
    return fig


def chart_first_class_split(df):
    grp = df.groupby("refund_vs_first_class").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["bucket","count","amount"]
    order = ["Before First Class","After First Class","Not Updated"]
    grp["bucket"] = pd.Categorical(grp["bucket"], categories=order, ordered=True)
    grp = grp.sort_values("bucket")
    color_map = {"Before First Class":"#F59E0B","After First Class":"#2563EB","Not Updated":C_SLATE}
    colors = [color_map.get(str(b), C_SLATE) for b in grp["bucket"]]
    fig = go.Figure(go.Bar(
        x=grp["bucket"].astype(str), y=grp["count"],
        marker_color=colors, opacity=0.88,
        text=[f"{c} | ${a/1000:.0f}K" for c,a in zip(grp["count"],grp["amount"])],
        textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.update_layout(title="Refund Timing vs First Class Date", yaxis_title="# Refunds", **layout)
    return fig


def chart_orientation_attended(df):
    grp = df.groupby("Orientation Attended").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["attended","count","amount"]
    order = ["Yes","No","Not Updated"]
    grp["attended"] = pd.Categorical(grp["attended"], categories=order, ordered=True)
    grp = grp.sort_values("attended")
    color_map = {"Yes":C_GREEN,"No":C_RED,"Not Updated":C_SLATE}
    colors = [color_map.get(str(a), C_SLATE) for a in grp["attended"]]
    fig = go.Figure(go.Bar(
        y=grp["attended"].astype(str), x=grp["count"],
        orientation="h", marker_color=colors, opacity=0.88,
        text=[f"n={c}  ${a/1000:.0f}K" for c,a in zip(grp["count"],grp["amount"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = 240
    layout["margin"] = dict(l=100, r=160, t=40, b=10)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(range=[0, grp["count"].max() * 2.2])
    fig.update_layout(title="Attended Orientation — Refund Count & Amount",
                      xaxis_title="# Refunds", **layout)
    return fig


def chart_first_class_attended(df):
    grp = df.groupby("First Class Attended").agg(
        count=("Hubspot id","count"), amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["attended","count","amount"]
    order = ["Yes","No","Not Updated"]
    grp["attended"] = pd.Categorical(grp["attended"], categories=order, ordered=True)
    grp = grp.sort_values("attended")
    color_map = {"Yes":C_GREEN,"No":C_RED,"Not Updated":C_SLATE}
    colors = [color_map.get(str(a), C_SLATE) for a in grp["attended"]]
    fig = go.Figure(go.Bar(
        y=grp["attended"].astype(str), x=grp["count"],
        orientation="h", marker_color=colors, opacity=0.88,
        text=[f"n={c}  ${a/1000:.0f}K" for c,a in zip(grp["count"],grp["amount"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = 240
    layout["margin"] = dict(l=100, r=160, t=40, b=10)
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(range=[0, grp["count"].max() * 2.2])
    fig.update_layout(title="Attended First Live Class — Refund Count & Amount",
                      xaxis_title="# Refunds", **layout)
    return fig


# ══════════════════════════════════════════════════════════════════════════
# ENGAGEMENT TAB — ORIENTATION & FIRST CLASS ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

SUBSET_COLORS = {
    "Attended Both":      "#16A34A",
    "Orientation Only":   "#2563EB",
    "First Class Only":   "#D97706",
    "Attended Neither":   "#EF4444",
    "Not Updated":        "#94A3B8",
}
SUBSET_ORDER = ["Attended Both","Orientation Only","First Class Only",
                "Attended Neither","Not Updated"]


def _subset_df(df):
    """Return only rows that have valid attendance data (exclude Not Updated)."""
    return df[df["Attendance Subset"] != "Not Updated"]


def chart_subset_overview(df):
    """Donut: distribution of attendance subsets."""
    grp = df.groupby("Attendance Subset").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp["Attendance Subset"] = pd.Categorical(
        grp["Attendance Subset"], categories=SUBSET_ORDER, ordered=True)
    grp = grp.sort_values("Attendance Subset")
    colors = [SUBSET_COLORS.get(str(s), C_SLATE) for s in grp["Attendance Subset"]]
    fig = go.Figure(go.Pie(
        labels=grp["Attendance Subset"].astype(str),
        values=grp["count"], hole=0.45,
        marker_colors=colors, textinfo="label+percent+value",
        hovertemplate="%{label}<br>%{value} refunds · $%{customdata:,.0f}<extra></extra>",
        customdata=grp["amount"]))
    layout = {**CHART_LAYOUT}
    layout["height"] = 320
    layout["margin"] = dict(l=20, r=20, t=40, b=20)
    fig.update_layout(title="Refunds by Attendance Subset", **layout)
    return fig


def chart_subset_amount(df):
    """Bar: amount refunded per subset."""
    grp = df.groupby("Attendance Subset").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp["Attendance Subset"] = pd.Categorical(
        grp["Attendance Subset"], categories=SUBSET_ORDER, ordered=True)
    grp = grp.sort_values("Attendance Subset")
    colors = [SUBSET_COLORS.get(str(s), C_SLATE) for s in grp["Attendance Subset"]]
    fig = go.Figure(go.Bar(
        x=grp["Attendance Subset"].astype(str), y=grp["amount"],
        marker_color=colors, opacity=0.88,
        text=[f"${v/1000:.0f}K  n={c}" for v,c in zip(grp["amount"],grp["count"])],
        textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 320
    fig.update_layout(title="Amount Refunded by Attendance Subset ($)",
                      yaxis_title="Amount ($)", **layout)
    return fig


def chart_phase_timing(df):
    """Grouped bar: for each subset, before vs after orientation and first class."""
    active = _subset_df(df)
    subsets = [s for s in SUBSET_ORDER if s != "Not Updated" and s in active["Attendance Subset"].values]
    rows = []
    for sub in subsets:
        s = active[active["Attendance Subset"]==sub]
        rows.append(dict(
            subset=sub,
            before_orient=int((s["days_to_orientation"] < 0).sum()),
            after_orient =int((s["days_to_orientation"] >= 0).sum()),
            before_class =int((s["days_to_first_class"] < 0).sum()),
            after_class  =int((s["days_to_first_class"] >= 0).sum()),
        ))
    grp = pd.DataFrame(rows)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("vs Orientation Date","vs First Class Date"))
    for col_i, (b_col, a_col, lbl) in enumerate([
        ("before_orient","after_orient","Orientation"),
        ("before_class","after_class","First Class")], 1):
        fig.add_trace(go.Bar(name="Before "+lbl, x=grp["subset"], y=grp[b_col],
                             marker_color="#F59E0B", opacity=0.88,
                             text=grp[b_col], textposition="inside",
                             showlegend=(col_i==1)), row=1, col=col_i)
        fig.add_trace(go.Bar(name="After "+lbl, x=grp["subset"], y=grp[a_col],
                             marker_color="#2563EB", opacity=0.88,
                             text=grp[a_col], textposition="inside",
                             showlegend=(col_i==1)), row=1, col=col_i)
    layout = {**CHART_LAYOUT}
    layout["height"] = 380
    fig.update_layout(title="Refund Timing: Before vs After Events by Subset",
                      barmode="stack", **layout)
    return fig


def chart_subset_by_category(df):
    """Grouped bar: subset breakdown per program category."""
    active = _subset_df(df)
    grp = active.groupby(["Category","Attendance Subset"]).size().reset_index(name="count")
    fig = px.bar(grp, x="Category", y="count", color="Attendance Subset",
                 barmode="group", color_discrete_map=SUBSET_COLORS,
                 category_orders={"Attendance Subset": SUBSET_ORDER})
    layout = {**CHART_LAYOUT}
    layout["height"] = 360
    fig.update_layout(title="Attendance Subset by Program Category", **layout)
    return fig


def chart_reasons_by_subset(df):
    """Heatmap: refund reason vs attendance subset."""
    active = _subset_df(df)
    active = active[active["Refund Category"].notna() &
                    ~active["Refund Category"].isin(["Not Updated",""])]
    if len(active) == 0:
        return go.Figure()
    pivot = active.groupby(["Refund Category","Attendance Subset"]).size().unstack(fill_value=0)
    cols  = [s for s in SUBSET_ORDER if s in pivot.columns and s != "Not Updated"]
    pivot = pivot[cols].loc[pivot[cols].sum(axis=1).nlargest(12).index]
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0,"#F0FDF4"],[0.5,"#FEF9C3"],[1,"#EF4444"]],
        text=pivot.values, texttemplate="%{text}",
        showscale=True, colorbar=dict(title="Count", thickness=12)))
    layout = {**CHART_LAYOUT}
    layout["height"] = 420
    layout["margin"] = dict(l=190, r=40, t=40, b=60)
    fig.update_layout(title="Top Refund Reasons by Attendance Subset",
                      xaxis_title="Attendance Subset",
                      yaxis_title="Refund Reason", **layout)
    return fig


def chart_days_distribution_by_subset(df):
    """Box plot: days from refund request relative to orientation per subset."""
    active = _subset_df(df)
    fig = go.Figure()
    for s in SUBSET_ORDER:
        if s == "Not Updated": continue
        rows = active[active["Attendance Subset"]==s]["days_to_orientation"].dropna()
        if len(rows) == 0: continue
        fig.add_trace(go.Box(y=rows, name=s,
                             marker_color=SUBSET_COLORS.get(s, C_SLATE),
                             boxmean=True, showlegend=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = 340
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1,
                  annotation_text="Orientation date", annotation_position="right")
    fig.update_layout(
        title="Days Relative to Orientation by Subset (negative = before orientation)",
        yaxis_title="Days", **layout)
    return fig


def table_subset_summary(df):
    """Master summary table — one row per subset."""
    rows = []
    total = len(df)
    for sub in SUBSET_ORDER:
        s = df[df["Attendance Subset"]==sub]
        if len(s) == 0: continue
        before_o = int((s["days_to_orientation"] < 0).sum())
        after_o  = int((s["days_to_orientation"] >= 0).sum())
        before_c = int((s["days_to_first_class"]  < 0).sum())
        after_c  = int((s["days_to_first_class"]  >= 0).sum())
        top_r = s["Refund Category"].value_counts()
        top_reason = top_r.index[0] if len(top_r) > 0 else "—"
        rows.append({
            "Subset":             sub,
            "# Refunds":          len(s),
            "% of Total":         f"{len(s)/total*100:.1f}%",
            "Amount Refunded":    f"${s['amount_refunded'].sum():,.0f}",
            "Avg Amount":         f"${s['amount_refunded'].mean():,.0f}",
            "Before Orientation": before_o,
            "After Orientation":  after_o,
            "Before 1st Class":   before_c,
            "After 1st Class":    after_c,
            "Top Reason":         top_reason,
        })
    return pd.DataFrame(rows)
