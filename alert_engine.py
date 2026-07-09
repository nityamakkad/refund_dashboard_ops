"""
Alert engine for IK Refund Dashboard.
Thresholds: Spike 10%, Course 10%, Orientation no-show 40%, First class no-show 40%
"""
import pandas as pd

MONTH_ORDER = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26","May - 26","Jun - 26",
               "Jul - 26","Aug - 26","Sep - 26","Oct - 26","Nov - 26","Dec - 26"]


def compute_alerts(df: pd.DataFrame) -> list:
    alerts = []
    total = len(df)
    if total == 0:
        return alerts

    # 1. Refund Spike (10%)
    mc = {str(k): v for k,v in df["Refund Month"].value_counts().items()}
    present = [m for m in MONTH_ORDER if m in mc]
    if len(present) >= 2:
        cur_m, last_m = present[-1], present[-2]
        cur_n, last_n = mc.get(cur_m,0), mc.get(last_m,0)
        if last_n > 0:
            chg = ((cur_n - last_n) / last_n) * 100
            if chg >= 10:
                alerts.append({"level":"critical","title":"Refund Spike",
                    "detail":f"{cur_m} has {cur_n} refunds vs {last_n} last month (+{chg:.0f}%)"})
            elif chg <= -10:
                alerts.append({"level":"info","title":"Refunds Declining",
                    "detail":f"{cur_m} has {cur_n} refunds vs {last_n} last month ({chg:.0f}%)"})

    # 2. Course Concentration (>10% of total)
    if total > 0:
        for course, cnt in df["Course"].value_counts().items():
            if str(course) in ("Not Updated","nan"): continue
            pct = cnt / total * 100
            if pct >= 10:
                alerts.append({"level":"warning","title":f"High Course: {course}",
                    "detail":f"{cnt} refunds ({pct:.0f}% of total)"})

    # 3. Orientation No-Show (>40%)
    oc = df["Orientation Attended"].value_counts().to_dict()
    o_no, o_yes = oc.get("No",0), oc.get("Yes",0)
    if o_no + o_yes > 0:
        pct = o_no / (o_no+o_yes) * 100
        if pct >= 40:
            alerts.append({"level":"critical","title":"Orientation No-Show",
                "detail":f"{o_no} of {o_no+o_yes} refunders ({pct:.0f}%) did not attend orientation"})

    # 4. First Class No-Show (>40%)
    cc = df["First Class Attended"].value_counts().to_dict()
    c_no, c_yes = cc.get("No",0), cc.get("Yes",0)
    if c_no + c_yes > 0:
        pct = c_no / (c_no+c_yes) * 100
        if pct >= 40:
            alerts.append({"level":"critical","title":"First Class No-Show",
                "detail":f"{c_no} of {c_no+c_yes} refunders ({pct:.0f}%) did not attend first class"})

    # 5. Course Trend (>50% jump, min 3 refunds)
    if len(present) >= 2:
        cur_df  = df[df["Refund Month"].astype(str)==present[-1]]
        last_df = df[df["Refund Month"].astype(str)==present[-2]]
        for course, cur_c in cur_df["Course"].value_counts().items():
            if str(course) in ("Not Updated","nan"): continue
            last_c = last_df["Course"].value_counts().to_dict().get(course, 0)
            if last_c > 0 and cur_c >= 3:
                t = ((cur_c - last_c) / last_c) * 100
                if t >= 50:
                    alerts.append({"level":"warning","title":f"Rising: {course}",
                        "detail":f"{last_c} to {cur_c} refunds month-on-month (+{t:.0f}%)"})

    # 6. Focus summary — always shown as info
    top_month = df["Refund Month"].value_counts()
    if len(top_month):
        alerts.append({"level":"info","title":"Highest Refund Month",
            "detail":f"{top_month.index[0]} — {int(top_month.iloc[0])} refunds"})

    top_cat = df["Category"].value_counts()
    if len(top_cat):
        alerts.append({"level":"info","title":"Top Category",
            "detail":f"{top_cat.index[0]} — {int(top_cat.iloc[0])} refunds"})

    top_reason = df["Refund Category"].value_counts()
    if len(top_reason):
        alerts.append({"level":"info","title":"Top Refund Reason",
            "detail":f"{top_reason.index[0]} — {int(top_reason.iloc[0])} refunds"})

    top_pmode = df["Payment Mode"].value_counts()
    if len(top_pmode):
        alerts.append({"level":"info","title":"Top Payment Mode",
            "detail":f"{top_pmode.index[0]} — {int(top_pmode.iloc[0])} refunds"})

    top_ptype = df["Upfront Payment / Non Upfront / Flexipay"].value_counts()
    if len(top_ptype):
        alerts.append({"level":"info","title":"Payment Type",
            "detail":f"Highest: {top_ptype.index[0]} — {int(top_ptype.iloc[0])} refunds"})

    return alerts
