

# ── SECTION — ENGAGEMENT ANALYSIS (Orientation & First Class) ─────────────

def chart_orientation_split(df: pd.DataFrame) -> go.Figure:
    """Before vs After Orientation — count and amount."""
    grp = df.groupby("refund_vs_orientation").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["bucket","count","amount"]
    color_map = {
        "Before Orientation": C_AMBER,
        "After Orientation":  C_RED,
        "Not Updated":        C_SLATE,
    }
    colors = [color_map.get(b, C_SLATE) for b in grp["bucket"]]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("# Refunds vs Orientation Date",
                                        "Amount Refunded vs Orientation Date ($)"))
    fig.add_trace(go.Bar(x=grp["bucket"], y=grp["count"],
                         marker_color=colors, text=grp["count"],
                         textposition="outside", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=grp["bucket"], y=grp["amount"],
                         marker_color=colors,
                         text=[f"${v:,.0f}" for v in grp["amount"]],
                         textposition="outside", showlegend=False), row=1, col=2)
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.update_layout(title="Refunds Before vs After Orientation Date", **layout)
    return fig


def chart_first_class_split(df: pd.DataFrame) -> go.Figure:
    """Before vs After First Class — count and amount."""
    grp = df.groupby("refund_vs_first_class").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["bucket","count","amount"]
    color_map = {
        "Before First Class": C_AMBER,
        "After First Class":  C_RED,
        "Not Updated":        C_SLATE,
    }
    colors = [color_map.get(b, C_SLATE) for b in grp["bucket"]]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("# Refunds vs First Class Date",
                                        "Amount Refunded vs First Class Date ($)"))
    fig.add_trace(go.Bar(x=grp["bucket"], y=grp["count"],
                         marker_color=colors, text=grp["count"],
                         textposition="outside", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=grp["bucket"], y=grp["amount"],
                         marker_color=colors,
                         text=[f"${v:,.0f}" for v in grp["amount"]],
                         textposition="outside", showlegend=False), row=1, col=2)
    layout = {**CHART_LAYOUT}
    layout["height"] = 300
    fig.update_layout(title="Refunds Before vs After First Class Date", **layout)
    return fig


def chart_orientation_attended(df: pd.DataFrame) -> go.Figure:
    """Did the learner attend orientation before refunding?"""
    grp = df.groupby("Orientation Attended").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["attended","count","amount"]
    color_map = {"Yes": C_GREEN, "No": C_RED, "Not Updated": C_SLATE}
    colors = [color_map.get(a, C_SLATE) for a in grp["attended"]]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("# Refunds by Orientation Attended",
                                        "Amount Refunded by Orientation Attended ($)"))
    fig.add_trace(go.Bar(x=grp["attended"], y=grp["count"],
                         marker_color=colors, text=grp["count"],
                         textposition="outside", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=grp["attended"], y=grp["amount"],
                         marker_color=colors,
                         text=[f"${v:,.0f}" for v in grp["amount"]],
                         textposition="outside", showlegend=False), row=1, col=2)
    layout = {**CHART_LAYOUT}
    layout["height"] = 280
    fig.update_layout(title="Attended Orientation Before Refunding?", **layout)
    return fig


def chart_first_class_attended(df: pd.DataFrame) -> go.Figure:
    """Did the learner attend the first live class before refunding?"""
    grp = df.groupby("First Class Attended").agg(
        count=("Hubspot id","count"),
        amount=("amount_refunded","sum")).reset_index()
    grp.columns = ["attended","count","amount"]
    color_map = {"Yes": C_GREEN, "No": C_RED, "Not Updated": C_SLATE}
    colors = [color_map.get(a, C_SLATE) for a in grp["attended"]]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("# Refunds by First Class Attended",
                                        "Amount Refunded by First Class Attended ($)"))
    fig.add_trace(go.Bar(x=grp["attended"], y=grp["count"],
                         marker_color=colors, text=grp["count"],
                         textposition="outside", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=grp["attended"], y=grp["amount"],
                         marker_color=colors,
                         text=[f"${v:,.0f}" for v in grp["amount"]],
                         textposition="outside", showlegend=False), row=1, col=2)
    layout = {**CHART_LAYOUT}
    layout["height"] = 280
    fig.update_layout(title="Attended First Live Class Before Refunding?", **layout)
    return fig
