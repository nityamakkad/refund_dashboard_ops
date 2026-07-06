import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

C_GREEN  = "#16A34A"
C_AMBER  = "#D97706"
C_RED    = "#EF4444"
C_BLUE   = "#2563EB"
C_TEAL   = "#0D9488"
C_SLATE  = "#64748B"
C_VIOLET = "#7C3AED"

NPS_COLORS  = [C_GREEN, C_AMBER, C_RED, C_BLUE, C_TEAL, C_VIOLET, "#F97316", "#EC4899"]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=12, color="#1E293B"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def _nps_colour(score):
    if pd.isna(score): return C_SLATE
    if score >= 50:    return C_GREEN
    if score >= 0:     return C_AMBER
    return C_RED


# ── KPI CARDS ─────────────────────────────────────────────────────────────

def kpi_nps(df):
    valid     = df[df["Responses"] > 0]
    overall   = (
        ((df["Promoters"].sum() - df["Detractors"].sum()) / df["Responses"].sum() * 100)
        if df["Responses"].sum() > 0 else np.nan)
    avg_resp  = df["Response_pct"].dropna().mean()
    total_resp= int(df["Responses"].sum())
    total_coh = int(df["Cohort Size"].sum())
    promoters = int(df["Promoters"].sum())
    detractors= int(df["Detractors"].sum())
    passives  = int(df["Passive"].sum())
    return dict(
        overall_nps  = round(overall, 1) if not pd.isna(overall) else None,
        avg_response = round(avg_resp, 1) if not pd.isna(avg_resp) else None,
        total_responses=total_resp,
        total_cohort = total_coh,
        promoters    = promoters,
        passives     = passives,
        detractors   = detractors,
    )


# ── 1. Overall NPS by SSA (ranked bar) ───────────────────────────────────

def chart_nps_by_ssa(df):
    grp = df[df["Responses"]>0].groupby("SSA").apply(
        lambda x: pd.Series({
            "NPS": round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100, 1),
            "Responses": int(x["Responses"].sum()),
            "Response_pct": round(x["Response_pct"].dropna().mean(), 1),
        })).reset_index().sort_values("NPS", ascending=True)

    colors = [_nps_colour(s) for s in grp["NPS"]]
    fig = go.Figure(go.Bar(
        y=grp["SSA"], x=grp["NPS"], orientation="h",
        marker_color=colors, opacity=0.88,
        text=[f"NPS: {n}  |  {r}% resp" for n,r in zip(grp["NPS"],grp["Response_pct"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(280, len(grp)*36)
    layout["margin"] = dict(l=80, r=200, t=40, b=10)
    fig.update_xaxes(range=[-100, 160])
    fig.add_vline(x=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="NPS by SSA (green ≥50, amber 0–49, red <0)",
                      xaxis_title="NPS Score", **layout)
    return fig


# ── 2. NPS by Category ────────────────────────────────────────────────────

def chart_nps_by_category(df):
    grp = df[df["Responses"]>0].groupby("Category").apply(
        lambda x: pd.Series({
            "NPS": round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1),
            "Responses": int(x["Responses"].sum()),
        })).reset_index().sort_values("NPS", ascending=False)

    colors = [_nps_colour(s) for s in grp["NPS"]]
    fig = go.Figure(go.Bar(
        x=grp["Category"], y=grp["NPS"],
        marker_color=colors, opacity=0.88,
        text=[f"{n}" for n in grp["NPS"]],
        textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="NPS by Program Category",
                      yaxis_title="NPS Score", **layout)
    return fig


# ── 3. Promoter / Passive / Detractor stacked bar by SSA ─────────────────

def chart_respondent_mix(df):
    grp = df[df["Responses"]>0].groupby("SSA").agg(
        Promoters=("Promoters","sum"),
        Passive=("Passive","sum"),
        Detractors=("Detractors","sum"),
        Responses=("Responses","sum")).reset_index()
    grp["P_pct"]  = (grp["Promoters"] /grp["Responses"]*100).round(1)
    grp["Pa_pct"] = (grp["Passive"]   /grp["Responses"]*100).round(1)
    grp["D_pct"]  = (grp["Detractors"]/grp["Responses"]*100).round(1)
    grp = grp.sort_values("P_pct", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Promoters", y=grp["SSA"], x=grp["P_pct"],
                         orientation="h", marker_color=C_GREEN, opacity=0.88,
                         text=[f"{v}%" for v in grp["P_pct"]], textposition="inside"))
    fig.add_trace(go.Bar(name="Passives",  y=grp["SSA"], x=grp["Pa_pct"],
                         orientation="h", marker_color=C_AMBER, opacity=0.88,
                         text=[f"{v}%" for v in grp["Pa_pct"]], textposition="inside"))
    fig.add_trace(go.Bar(name="Detractors",y=grp["SSA"], x=grp["D_pct"],
                         orientation="h", marker_color=C_RED, opacity=0.88,
                         text=[f"{v}%" for v in grp["D_pct"]], textposition="inside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(300, len(grp)*36)
    layout["margin"] = dict(l=80, r=20, t=40, b=10)
    fig.update_layout(title="Promoter / Passive / Detractor Mix by SSA (%)",
                      barmode="stack", xaxis_title="% of Responses", **layout)
    return fig


# ── 4. Response Rate by SSA ───────────────────────────────────────────────

def chart_response_rate(df):
    grp = df.groupby("SSA").agg(
        Responses=("Responses","sum"),
        CohortSize=("Cohort Size","sum")).reset_index()
    grp["Resp_pct"] = (grp["Responses"]/grp["CohortSize"]*100).round(1)
    grp = grp.sort_values("Resp_pct", ascending=True)

    colors = [C_GREEN if v >= 50 else C_AMBER if v >= 30 else C_RED
              for v in grp["Resp_pct"]]
    fig = go.Figure(go.Bar(
        y=grp["SSA"], x=grp["Resp_pct"],
        orientation="h", marker_color=colors, opacity=0.88,
        text=[f"{v}%  ({int(r)}/{int(c)})" for v,r,c in
              zip(grp["Resp_pct"],grp["Responses"],grp["CohortSize"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(280, len(grp)*36)
    layout["margin"] = dict(l=80, r=180, t=40, b=10)
    fig.add_vline(x=50, line_dash="dash", line_color=C_SLATE, line_width=1,
                  annotation_text="50% target", annotation_position="top")
    fig.update_xaxes(range=[0, 130])
    fig.update_layout(title="Response Rate by SSA (green ≥50%, amber 30–50%, red <30%)",
                      xaxis_title="Response %", **layout)
    return fig


# ── 5. NPS by Checkpoint (EM / Week5 / Week8 or NPS1 / NPS2) ─────────────

def chart_nps_by_checkpoint(df):
    grp = df[df["Responses"]>0].groupby(["SSA","NPS Type"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).reset_index(name="NPS")

    checkpoints = df["NPS Type"].dropna().unique().tolist()
    colors = {c: NPS_COLORS[i % len(NPS_COLORS)] for i,c in enumerate(checkpoints)}

    fig = go.Figure()
    for cp in checkpoints:
        sub = grp[grp["NPS Type"]==cp]
        fig.add_trace(go.Bar(
            name=cp, x=sub["SSA"], y=sub["NPS"],
            marker_color=colors[cp], opacity=0.85,
            text=[f"{v}" for v in sub["NPS"]], textposition="outside"))

    layout = {**CHART_LAYOUT}
    layout["height"] = 350
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="NPS by SSA and Checkpoint (EM / Week 5 / Week 8 or NPS 1 / NPS 2)",
                      barmode="group", yaxis_title="NPS Score", **layout)
    return fig


# ── 6. NPS trend by release month ─────────────────────────────────────────

def chart_nps_trend(df):
    grp = df[df["Responses"]>0].groupby("Release_month").apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).reset_index(name="NPS").sort_values("Release_month")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grp["Release_month"], y=grp["NPS"],
        mode="lines+markers+text",
        text=[f"{v}" for v in grp["NPS"]],
        textposition="top center",
        line=dict(color=C_BLUE, width=2.5),
        marker=dict(size=9, color=[_nps_colour(s) for s in grp["NPS"]],
                    line=dict(color="white", width=2)),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.06)"))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="Overall NPS Trend by Release Month",
                      yaxis_title="NPS Score", xaxis_title="Release Month",
                      **layout)
    return fig


# ── 7. NPS by Category + Checkpoint heatmap ───────────────────────────────

def chart_nps_heatmap(df):
    pivot = df[df["Responses"]>0].groupby(["Category","NPS Type"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).unstack(fill_value=np.nan)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0,C_RED],[0.5,"#FFFFFF"],[1,C_GREEN]],
        zmid=0, zmin=-100, zmax=100,
        text=[[f"{v:.0f}" if not np.isnan(v) else "—"
               for v in row] for row in pivot.values],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="NPS", thickness=12)))
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    layout["margin"] = dict(l=100, r=80, t=40, b=60)
    fig.update_layout(title="NPS Heatmap — Category vs Checkpoint",
                      xaxis_title="Checkpoint", yaxis_title="Category",
                      **layout)
    return fig


# ── 8. SSA Leaderboard table data ─────────────────────────────────────────

def table_ssa_leaderboard(df):
    grp = df[df["Responses"]>0].groupby("SSA").apply(lambda x: pd.Series({
        "NPS":           round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1),
        "Promoters":     int(x["Promoters"].sum()),
        "Passives":      int(x["Passive"].sum()),
        "Detractors":    int(x["Detractors"].sum()),
        "Responses":     int(x["Responses"].sum()),
        "Cohort Size":   int(x["Cohort Size"].sum()),
        "Response %":    round(x["Responses"].sum()/x["Cohort Size"].sum()*100,1)
                         if x["Cohort Size"].sum()>0 else 0,
        "Cohorts":       x["Cohort Name"].nunique(),
    })).reset_index().sort_values("NPS", ascending=False)
    grp.insert(0,"Rank",range(1,len(grp)+1))
    return grp


# ── 9. NPS distribution histogram ────────────────────────────────────────

def chart_nps_distribution(df):
    vals = df["NPS_computed"].dropna()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vals, nbinsx=20,
        marker_color=C_BLUE, opacity=0.8))
    fig.add_vline(x=vals.median(), line_dash="dash", line_color=C_SLATE,
                  annotation_text=f"Median: {vals.median():.0f}",
                  annotation_position="top right")
    fig.add_vline(x=0, line_dash="solid", line_color=C_RED, line_width=1.5)
    layout = {**CHART_LAYOUT}
    layout["height"] = 280
    fig.update_layout(title="Distribution of NPS Scores",
                      xaxis_title="NPS Score", yaxis_title="# Entries",
                      **layout)
    return fig


# ── 10. NPS1 vs NPS2 delta (for Agentic/Switchup) ────────────────────────

def chart_nps_round_delta(df):
    cats = df[df["NPS Type"].isin(["NPS 1","NPS 2"])]
    if len(cats) == 0:
        return None
    grp = cats[cats["Responses"]>0].groupby(["SSA","NPS Type"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).unstack()

    if "NPS 1" not in grp.columns or "NPS 2" not in grp.columns:
        return None

    grp["Delta"] = grp["NPS 2"] - grp["NPS 1"]
    grp = grp.dropna(subset=["Delta"]).sort_values("Delta", ascending=True).reset_index()

    colors = [C_GREEN if d >= 0 else C_RED for d in grp["Delta"]]
    fig = go.Figure(go.Bar(
        y=grp["SSA"], x=grp["Delta"],
        orientation="h", marker_color=colors, opacity=0.88,
        text=[f"{'+' if d>=0 else ''}{d:.0f}" for d in grp["Delta"]],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(260, len(grp)*36)
    layout["margin"] = dict(l=80, r=80, t=40, b=10)
    fig.add_vline(x=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="NPS Improvement: NPS 2 minus NPS 1 by SSA",
                      xaxis_title="NPS Delta", **layout)
    return fig


# ── 11. NPS by Cohort ─────────────────────────────────────────────────────

def chart_nps_by_cohort(df):
    """NPS per cohort — shows which cohorts are performing well."""
    grp = df[df["Responses"]>0].groupby(["Cohort Name","Category"]).apply(
        lambda x: pd.Series({
            "NPS": round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1),
            "Responses": int(x["Responses"].sum()),
            "Cohort Size": int(x["Cohort Size"].sum()),
        })).reset_index().sort_values("NPS", ascending=True)

    colors = [_nps_colour(s) for s in grp["NPS"]]
    fig = go.Figure(go.Bar(
        y=[f"{r['Cohort Name']} ({r['Category']})" for _,r in grp.iterrows()],
        x=grp["NPS"], orientation="h",
        marker_color=colors, opacity=0.88,
        text=[f"NPS: {n}  Resp: {r}/{c}" for n,r,c in
              zip(grp["NPS"],grp["Responses"],grp["Cohort Size"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(300, len(grp)*32)
    layout["margin"] = dict(l=200, r=200, t=40, b=10)
    fig.add_vline(x=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_xaxes(range=[-100, 160])
    fig.update_layout(title="NPS by Cohort & Category",
                      xaxis_title="NPS Score", **layout)
    return fig


def chart_cohort_response(df):
    """Response rate per cohort — flags low-engagement cohorts."""
    grp = df.groupby(["Cohort Name","Category"]).agg(
        Responses=("Responses","sum"),
        CohortSize=("Cohort Size","sum")).reset_index()
    grp["Resp_pct"] = (grp["Responses"]/grp["CohortSize"]*100).round(1)
    grp = grp.sort_values("Resp_pct", ascending=True)

    colors = [C_GREEN if v>=50 else C_AMBER if v>=30 else C_RED for v in grp["Resp_pct"]]
    fig = go.Figure(go.Bar(
        y=[f"{r['Cohort Name']} ({r['Category']})" for _,r in grp.iterrows()],
        x=grp["Resp_pct"], orientation="h",
        marker_color=colors, opacity=0.88,
        text=[f"{v}%  ({int(r)}/{int(c)})" for v,r,c in
              zip(grp["Resp_pct"],grp["Responses"],grp["CohortSize"])],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(300, len(grp)*32)
    layout["margin"] = dict(l=200, r=180, t=40, b=10)
    fig.add_vline(x=50, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_xaxes(range=[0, 140])
    fig.update_layout(title="Response Rate by Cohort & Category",
                      xaxis_title="Response %", **layout)
    return fig


# ── COHORT PROGRESSION CHARTS ──────────────────────────────────────────────

def chart_cohort_nps1_vs_nps2(df):
    """Agentic/Switchup: grouped bar NPS 1 vs NPS 2 per cohort."""
    sub = df[df["NPS Type"].isin(["NPS 1","NPS 2"]) & (df["Responses"]>0)]
    if len(sub) == 0:
        return None
    pivot = sub.groupby(["Category","Cohort Name","NPS Type"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).unstack().reset_index()
    pivot["label"] = pivot["Category"].str[:3] + " | " + pivot["Cohort Name"].str[-22:]

    fig = go.Figure()
    if "NPS 1" in pivot.columns:
        fig.add_trace(go.Bar(name="NPS 1", x=pivot["label"], y=pivot["NPS 1"],
                             marker_color=C_TEAL, opacity=0.85,
                             text=[f"{v:.0f}" if not pd.isna(v) else "" for v in pivot["NPS 1"]],
                             textposition="outside"))
    if "NPS 2" in pivot.columns:
        fig.add_trace(go.Bar(name="NPS 2", x=pivot["label"], y=pivot["NPS 2"],
                             marker_color=C_BLUE, opacity=0.85,
                             text=[f"{v:.0f}" if not pd.isna(v) else "" for v in pivot["NPS 2"]],
                             textposition="outside"))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(400, len(pivot)*22)
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="Cohort NPS: Round 1 vs Round 2 (Agentic & Switchup)",
                      barmode="group", yaxis_title="NPS Score",
                      xaxis_tickangle=-45, **layout)
    return fig


def chart_cohort_checkpoint_progression(df):
    """LevelUp: line per cohort showing EM -> Week 5 -> Week 8 progression."""
    sub = df[df["NPS Type"].isin(["EM","Week 5","Week 8"]) & (df["Responses"]>0)]
    if len(sub) == 0:
        return None
    pivot = sub.groupby(["Cohort Name","NPS Type"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).unstack().reset_index()
    checkpoint_order = ["EM","Week 5","Week 8"]
    available = [c for c in checkpoint_order if c in pivot.columns]

    colors_cycle = [C_BLUE, C_TEAL, C_GREEN, C_AMBER, C_VIOLET,
                    "#F97316","#EC4899","#0EA5E9","#6366F1","#14B8A6",
                    "#F59E0B","#EF4444","#8B5CF6","#10B981","#64748B","#2563EB","#D97706"]
    fig = go.Figure()
    for i, (_, row) in enumerate(pivot.iterrows()):
        y_vals = [row.get(c, np.nan) for c in available]
        if all(pd.isna(v) for v in y_vals):
            continue
        fig.add_trace(go.Scatter(
            x=available, y=y_vals,
            name=str(row["Cohort Name"])[-22:],
            mode="lines+markers",
            line=dict(color=colors_cycle[i % len(colors_cycle)], width=2),
            marker=dict(size=7), connectgaps=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = 420
    layout["legend"] = dict(orientation="v", yanchor="top", y=1,
                            xanchor="left", x=1.02, font=dict(size=10))
    layout["margin"] = dict(l=10, r=200, t=40, b=10)
    fig.add_hline(y=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_layout(title="LevelUp Cohort Progression: EM -> Week 5 -> Week 8",
                      yaxis_title="NPS Score", **layout)
    return fig


def chart_cohort_nps_ranked(df):
    """All cohorts ranked by overall NPS — colour coded."""
    grp = df[df["Responses"]>0].groupby(["Category","Cohort Name"]).apply(
        lambda x: round((x["Promoters"].sum()-x["Detractors"].sum())/x["Responses"].sum()*100,1)
    ).reset_index(name="NPS").sort_values("NPS", ascending=True)
    grp["label"] = grp["Category"].str[:3] + " | " + grp["Cohort Name"].str[-22:]
    colors = [_nps_colour(s) for s in grp["NPS"]]
    fig = go.Figure(go.Bar(
        y=grp["label"], x=grp["NPS"],
        orientation="h", marker_color=colors, opacity=0.88,
        text=[f"{v:.0f}" for v in grp["NPS"]],
        textposition="outside", cliponaxis=False))
    layout = {**CHART_LAYOUT}
    layout["height"] = max(420, len(grp)*22)
    layout["margin"] = dict(l=200, r=80, t=40, b=10)
    fig.add_vline(x=0, line_dash="dash", line_color=C_SLATE, line_width=1)
    fig.update_xaxes(range=[-100, 150])
    fig.update_layout(title="All Cohorts Ranked by NPS",
                      xaxis_title="NPS Score", **layout)
    return fig
