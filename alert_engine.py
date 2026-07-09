"""
Alert engine for IK Refund Dashboard.
Computes alerts from filtered df. Used by both dashboard and weekly email.

Thresholds:
  SPIKE_PCT        = 10%  — current month refunds > last month by 10%
  COURSE_CONC_PCT  = 10%  — single course > 10% of total refunds
  ORIENT_NSHOW_PCT = 40%  — >40% of refunders didn't attend orientation
  CLASS_NSHOW_PCT  = 40%  — >40% of refunders didn't attend first class
"""

import pandas as pd
import numpy as np

SPIKE_PCT        = 10
COURSE_CONC_PCT  = 10
ORIENT_NSHOW_PCT = 40
CLASS_NSHOW_PCT  = 40

MONTH_ORDER = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26","May - 26","Jun - 26",
               "Jul - 26","Aug - 26","Sep - 26","Oct - 26","Nov - 26","Dec - 26"]


def compute_alerts(df: pd.DataFrame) -> list:
    """
    Returns list of alert dicts: {level, title, detail}
    level: 'critical' | 'warning' | 'info'
    """
    alerts = []
    total = len(df)
    if total == 0:
        return alerts

    # ── 1. Refund Spike ──────────────────────────────────────────────────────
    month_counts = df["Refund Month"].value_counts().to_dict()
    # Find two most recent months that have data
    present = [m for m in MONTH_ORDER if str(m) in [str(k) for k in month_counts.keys()]]
    if len(present) >= 2:
        cur_m   = present[-1]
        last_m  = present[-2]
        cur_n   = month_counts.get(cur_m, 0)
        last_n  = month_counts.get(last_m, 0)
        if last_n > 0:
            change_pct = ((cur_n - last_n) / last_n) * 100
            if change_pct >= SPIKE_PCT:
                alerts.append({
                    "level": "critical",
                    "title": f"Refund Spike: {cur_m}",
                    "detail": (f"{cur_m} has {cur_n} refunds — "
                               f"{change_pct:.0f}% higher than {last_m} ({last_n}). "
                               f"Threshold: {SPIKE_PCT}% increase."),
                })
            elif change_pct <= -SPIKE_PCT:
                alerts.append({
                    "level": "info",
                    "title": f"Refund Drop: {cur_m}",
                    "detail": (f"{cur_m} has {cur_n} refunds — "
                               f"{abs(change_pct):.0f}% lower than {last_m} ({last_n})."),
                })

    # ── 2. Course Concentration ───────────────────────────────────────────────
    course_counts = df["Course"].value_counts()
    for course, count in course_counts.items():
        pct = count / total * 100
        if str(course) in ("Not Updated","nan"): continue
        if pct >= COURSE_CONC_PCT:
            alerts.append({
                "level": "warning",
                "title": f"High Refunds: {course}",
                "detail": (f"{course} accounts for {count} refunds "
                           f"({pct:.1f}% of total). "
                           f"Threshold: {COURSE_CONC_PCT}% of total."),
            })

    # ── 3. Orientation No-Show Trend ─────────────────────────────────────────
    orient_counts = df["Orientation Attended"].value_counts().to_dict()
    o_no  = orient_counts.get("No", 0)
    o_yes = orient_counts.get("Yes", 0)
    o_valid = o_no + o_yes
    if o_valid > 0:
        o_nshow_pct = o_no / o_valid * 100
        if o_nshow_pct >= ORIENT_NSHOW_PCT:
            alerts.append({
                "level": "critical",
                "title": "High Orientation No-Show Among Refunders",
                "detail": (f"{o_no} of {o_valid} refunders ({o_nshow_pct:.0f}%) "
                           f"did NOT attend orientation before refunding. "
                           f"Threshold: {ORIENT_NSHOW_PCT}%."),
            })

    # ── 4. First Live Class No-Show Trend ────────────────────────────────────
    class_counts = df["First Class Attended"].value_counts().to_dict()
    c_no  = class_counts.get("No", 0)
    c_yes = class_counts.get("Yes", 0)
    c_valid = c_no + c_yes
    if c_valid > 0:
        c_nshow_pct = c_no / c_valid * 100
        if c_nshow_pct >= CLASS_NSHOW_PCT:
            alerts.append({
                "level": "critical",
                "title": "High First Class No-Show Among Refunders",
                "detail": (f"{c_no} of {c_valid} refunders ({c_nshow_pct:.0f}%) "
                           f"did NOT attend the first live class before refunding. "
                           f"Threshold: {CLASS_NSHOW_PCT}%."),
            })

    # ── 5. Course Refund Trend (course appearing in last 2 months) ───────────
    if len(present) >= 2:
        cur_m  = present[-1]
        last_m = present[-2]
        cur_df  = df[df["Refund Month"].astype(str) == str(cur_m)]
        last_df = df[df["Refund Month"].astype(str) == str(last_m)]
        cur_courses  = cur_df["Course"].value_counts().to_dict()
        last_courses = last_df["Course"].value_counts().to_dict()
        for course, cur_c in cur_courses.items():
            if str(course) in ("Not Updated","nan"): continue
            last_c = last_courses.get(course, 0)
            if last_c > 0:
                trend_pct = ((cur_c - last_c) / last_c) * 100
                if trend_pct >= 50 and cur_c >= 3:  # 50% jump and at least 3 refunds
                    alerts.append({
                        "level": "warning",
                        "title": f"Increasing Refunds: {course}",
                        "detail": (f"{course} went from {last_c} refunds ({last_m}) "
                                   f"to {cur_c} refunds ({cur_m}) — "
                                   f"{trend_pct:.0f}% increase."),
                    })

    return alerts


def alerts_to_email_html(alerts: list) -> str:
    """Convert alerts list to HTML section for weekly email."""
    if not alerts:
        return (
            "<div style='background:#F0FDF4;border-left:4px solid #16A34A;"
            "padding:12px 28px;font-size:13px;color:#166534;'>"
            "No alerts this week — all metrics within thresholds.</div>"
        )

    level_styles = {
        "critical": ("background:#FEF2F2","border-left:4px solid #EF4444","color:#991B1B"),
        "warning":  ("background:#FFFBEB","border-left:4px solid #F59E0B","color:#92400E"),
        "info":     ("background:#EFF6FF","border-left:4px solid #2563EB","color:#1E40AF"),
    }
    icons = {"critical":"🔴","warning":"🟡","info":"🔵"}

    html = ""
    for a in alerts:
        bg, border, color = level_styles.get(a["level"], level_styles["warning"])
        icon = icons.get(a["level"], "⚠️")
        html += (
            f"<div style='{bg};{border};padding:10px 28px;margin-bottom:4px;"
            f"font-size:13px;{color};'>"
            f"<b>{icon} {a['title']}</b><br>{a['detail']}</div>"
        )
    return html
