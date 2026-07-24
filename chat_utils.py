import streamlit as st


def render_chat(df, tab_key):
    import requests, json

    api_key = st.secrets.get("OPENAI_API_KEY","") if hasattr(st,"secrets") else ""
    if not api_key:
        st.info("Add OPENAI_API_KEY in Streamlit Secrets to enable the assistant.", icon="🔑")
        return

    def safe_grp(col, val_col=None):
        if col not in df.columns: return {}
        if val_col:
            return {str(k): round(float(v),0) for k,v in df.groupby(col,dropna=False)[val_col].sum().items()}
        return {str(k): int(v) for k,v in df[col].value_counts(dropna=False).items()}

    def cross(col1, col2):
        if col1 not in df.columns or col2 not in df.columns: return {}
        out = {}
        for v1 in df[col1].astype(str).unique():
            sub = df[df[col1].astype(str)==v1]
            out[v1] = {str(k): int(n) for k,n in sub[col2].value_counts(dropna=False).items()}
        return out

    def cross3(col1, col2, col3):
        if not all(c in df.columns for c in [col1,col2,col3]): return {}
        out = {}
        for v1 in df[col1].astype(str).unique():
            sub1 = df[df[col1].astype(str)==v1]
            out[v1] = {}
            for v2 in sub1[col2].astype(str).unique():
                sub2 = sub1[sub1[col2].astype(str)==v2]
                out[v1][v2] = {str(k): int(n) for k,n in sub2[col3].value_counts(dropna=False).items()}
        return out

    total = len(df)
    ctx = {
        "total_refunds": total,
        "total_amount_refunded": round(float(df["amount_refunded"].sum()),0),
        "refund_by_month":        safe_grp("Refund Month"),
        "refund_by_bu":           safe_grp("BU"),
        "refund_by_category":     safe_grp("Category"),
        "refund_by_course":       safe_grp("Course"),
        "refund_by_reason":       safe_grp("Refund Category"),
        "refund_by_payment_mode": safe_grp("Payment Mode"),
        "refund_by_payment_type": safe_grp("Upfront Payment / Non Upfront / Flexipay"),
        "refund_by_country":      safe_grp("Country"),
        "refund_by_new_alumni":   safe_grp("New / Alumni"),
        "onboarding_status":      safe_grp("Onboarding Status"),
        "eligible_per_policy":    safe_grp("Eligible as per refund policy"),
        "trial_window":           safe_grp("Refund request received in Trial Window"),
        "orientation_attended":   safe_grp("Orientation Attended"),
        "first_class_attended":   safe_grp("First Class Attended"),
        "attendance_subset":      safe_grp("Attendance Subset"),
        "refund_timing_orientation": {
            "before": int((df["days_to_orientation"]<0).sum()),
            "after":  int((df["days_to_orientation"]>=0).sum()),
            "no_date":int(df["days_to_orientation"].isna().sum()),
        },
        "refund_timing_first_class": {
            "before": int((df["days_to_first_class"]<0).sum()),
            "after":  int((df["days_to_first_class"]>=0).sum()),
            "no_date":int(df["days_to_first_class"].isna().sum()),
        },
        "median_days_enroll_to_request": round(float(df["days_enroll_to_refund_req"].dropna().median()),1)
                                          if df["days_enroll_to_refund_req"].notna().any() else None,
        "days_enroll_to_request_distribution": {
            "within_7_days":   int((df["days_enroll_to_refund_req"] <= 7).sum()),
            "8_to_14_days":    int(((df["days_enroll_to_refund_req"] > 7)  & (df["days_enroll_to_refund_req"] <= 14)).sum()),
            "15_to_30_days":   int(((df["days_enroll_to_refund_req"] > 14) & (df["days_enroll_to_refund_req"] <= 30)).sum()),
            "31_to_60_days":   int(((df["days_enroll_to_refund_req"] > 30) & (df["days_enroll_to_refund_req"] <= 60)).sum()),
            "after_60_days":   int((df["days_enroll_to_refund_req"] > 60).sum()),
            "after_7_days":    int((df["days_enroll_to_refund_req"] > 7).sum()),
            "after_14_days":   int((df["days_enroll_to_refund_req"] > 14).sum()),
            "after_30_days":   int((df["days_enroll_to_refund_req"] > 30).sum()),
            "no_date":         int(df["days_enroll_to_refund_req"].isna().sum()),
            "mean_days": round(float(df["days_enroll_to_refund_req"].dropna().mean()),1) if df["days_enroll_to_refund_req"].notna().any() else None,
            "min_days":  int(df["days_enroll_to_refund_req"].dropna().min()) if df["days_enroll_to_refund_req"].notna().any() else None,
            "max_days":  int(df["days_enroll_to_refund_req"].dropna().max()) if df["days_enroll_to_refund_req"].notna().any() else None,
        },
        "days_to_orientation_distribution": {
            "before_orientation": int((df["days_to_orientation"] < 0).sum()),
            "after_orientation":  int((df["days_to_orientation"] >= 0).sum()),
            "within_7_days_after": int(((df["days_to_orientation"] >= 0) & (df["days_to_orientation"] <= 7)).sum()),
            "no_date":            int(df["days_to_orientation"].isna().sum()),
        },
        "days_to_first_class_distribution": {
            "before_first_class": int((df["days_to_first_class"] < 0).sum()),
            "after_first_class":  int((df["days_to_first_class"] >= 0).sum()),
            "within_7_days_after": int(((df["days_to_first_class"] >= 0) & (df["days_to_first_class"] <= 7)).sum()),
            "no_date":            int(df["days_to_first_class"].isna().sum()),
        },
        "amount_by_payment_mode": safe_grp("Payment Mode","amount_refunded"),
        "amount_by_course":       safe_grp("Course","amount_refunded"),
        "amount_by_category":     safe_grp("Category","amount_refunded"),
        "amount_by_month":        safe_grp("Refund Month","amount_refunded"),
        "payment_mode_by_month":  cross("Payment Mode","Refund Month"),
        "payment_mode_by_bu":     cross("Payment Mode","BU"),
        "payment_mode_by_course": cross("Payment Mode","Course"),
        "course_by_month":        cross("Course","Refund Month"),
        "course_by_bu":           cross("Course","BU"),
        "bu_by_month":            cross("BU","Refund Month"),
        "reason_by_course":       cross("Refund Category","Course"),
        "reason_by_category":     cross("Refund Category","Category"),
        "reason_by_month":        cross("Refund Category","Refund Month"),
        "orientation_by_course":  cross("Orientation Attended","Course"),
        "orientation_by_bu":      cross("Orientation Attended","BU"),
        "first_class_by_course":  cross("First Class Attended","Course"),
        "subset_by_category":     cross("Attendance Subset","Category"),
        "subset_by_course":       cross("Attendance Subset","Course"),
        "trial_by_month":         cross("Refund request received in Trial Window","Refund Month"),
        "payment_mode_x_month_x_orientation": cross3("Payment Mode","Refund Month","Orientation Attended"),
        "payment_mode_x_month_x_first_class": cross3("Payment Mode","Refund Month","First Class Attended"),
        "course_x_month_x_orientation":       cross3("Course","Refund Month","Orientation Attended"),
        "bu_x_month_x_orientation":           cross3("BU","Refund Month","Orientation Attended"),
        "reason_x_bu_x_month":                cross3("Refund Category","BU","Refund Month"),
    }

    system_prompt = (
        "You are a data analyst assistant for Interview Kickstart refund data. "
        "Answer ONLY from the JSON context. Rules: "
        "1. Be crisp - 1-3 sentences max. "
        "2. Quote exact numbers from context. "
        "3. Mention Not Updated/nan counts if relevant. "
        "4. For compound questions like 'CLIMB CREDIT in March' use cross-tab keys like payment_mode_by_month. "
        "For 3-level questions (e.g. CLIMB CREDIT in March who attended orientation) use 3-way keys like payment_mode_x_month_x_orientation. "         "For questions about days since enrollment/deposit/receipt (Date of Receipt col E vs Refund Request Date col AI) use days_enroll_to_request_distribution — keys: within_7_days, after_7_days, 8_to_14_days, 15_to_30_days, 31_to_60_days, after_60_days, after_14_days, after_30_days. "         "For questions about before/after orientation or first class use days_to_orientation_distribution and days_to_first_class_distribution. "
        "5. Never invent data. 6. If unanswerable, say so clearly.\n\n"
        f"DATA CONTEXT:\n{json.dumps(ctx,indent=1,default=str)}"
    )

    key = f"msgs_{tab_key}"
    if key not in st.session_state:
        st.session_state[key] = []
    msgs = st.session_state[key]

    for m in msgs:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    if prompt := st.chat_input(
        "Ask about refund data... (e.g. 'CLIMB CREDIT refunds in March?')",
        key=f"chat_input_{tab_key}"):
        msgs.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner(""):
                try:
                    resp = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Content-Type":"application/json","Authorization":f"Bearer {api_key}"},
                        json={"model":"gpt-4o-mini","max_tokens":300,
                              "messages":[{"role":"system","content":system_prompt},
                                          *[{"role":m["role"],"content":m["content"]} for m in msgs]]},
                        timeout=20)
                    answer = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    answer = f"Error: {e}"
                st.write(answer)
                msgs.append({"role":"assistant","content":answer})
