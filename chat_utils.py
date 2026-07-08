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
    }

    system_prompt = (
        "You are a data analyst assistant for Interview Kickstart refund data. "
        "Answer ONLY from the JSON context. Rules: "
        "1. Be crisp - 1-3 sentences max. "
        "2. Quote exact numbers from context. "
        "3. Mention Not Updated/nan counts if relevant. "
        "4. For compound questions like 'CLIMB CREDIT in March' use cross-tab keys like payment_mode_by_month. "
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
