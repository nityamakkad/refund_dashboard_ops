import streamlit as st

def render_chat(df, tab_key):
    """
    Data-grounded chat interface.
    Builds a concise summary of df as context, sends to OpenAI,
    returns a crisp factual answer. Never hallucinates — only answers
    from computed stats. Flags Not Updated counts.
    """
    import requests, json

    api_key = st.secrets.get("OPENAI_API_KEY","") if hasattr(st,"secrets") else ""
    if not api_key:
        st.info("Add OPENAI_API_KEY in Streamlit Secrets to enable the chat assistant.", icon="🔑")
        return

    # ── Build data context from current filtered df ──
    def safe_grp(col, val_col=None):
        if col not in df.columns: return {}
        if val_col:
            return df.groupby(col, dropna=False)[val_col].sum().round(0).astype(int).to_dict()
        return df[col].value_counts(dropna=False).to_dict()

    total = len(df)
    amt_total = df["amount_refunded"].sum()

    ctx = {
        "total_refunds": total,
        "total_amount_refunded": round(float(amt_total), 0),
        "refund_by_month":    safe_grp("Refund Month"),
        "refund_by_bu":       safe_grp("BU"),
        "refund_by_category": safe_grp("Category"),
        "refund_by_course":   safe_grp("Course"),
        "refund_by_reason":   safe_grp("Refund Category"),
        "refund_by_payment_type": safe_grp("Upfront Payment / Non Upfront / Flexipay"),
        "refund_by_payment_mode": safe_grp("Payment Mode"),
        "refund_by_country":  safe_grp("Country"),
        "orientation_attended": safe_grp("Orientation Attended"),
        "first_class_attended": safe_grp("First Class Attended"),
        "attendance_subset":  safe_grp("Attendance Subset"),
        "refund_timing_orientation": {
            "before_orientation": int((df["days_to_orientation"] < 0).sum()),
            "after_orientation":  int((df["days_to_orientation"] >= 0).sum()),
            "no_date":            int(df["days_to_orientation"].isna().sum()),
        },
        "refund_timing_first_class": {
            "before_first_class": int((df["days_to_first_class"] < 0).sum()),
            "after_first_class":  int((df["days_to_first_class"] >= 0).sum()),
            "no_date":            int(df["days_to_first_class"].isna().sum()),
        },
        "onboarding_status": safe_grp("Onboarding Status"),
        "eligible_per_policy": safe_grp("Eligible as per refund policy"),
        "trial_window":       safe_grp("Refund request received in Trial Window"),
        "new_vs_alumni":      safe_grp("New / Alumni"),
        "median_days_enroll_to_request": round(float(df["days_enroll_to_refund_req"].dropna().median()), 1)
                                          if df["days_enroll_to_refund_req"].notna().any() else None,
    }

    system_prompt = f"""You are a data analyst assistant for Interview Kickstart's refund analysis dashboard.
You answer questions ONLY based on the data context provided below. 
Rules:
- Be crisp and direct — answer in 1-3 sentences max
- Always mention the actual numbers from the data
- If a field has "Not Updated", "nan", or null values, mention that count explicitly
- Never guess or invent numbers not in the context
- If the question cannot be answered from the context, say so clearly
- For rankings (max/min), state the exact value and count

Current filtered data context (JSON):
{json.dumps(ctx, indent=2, default=str)}"""

    # ── Chat UI ──
    if f"messages_{tab_key}" not in st.session_state:
        st.session_state[f"messages_{tab_key}"] = []

    msgs = st.session_state[f"messages_{tab_key}"]

    # Display chat history
    for msg in msgs:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input
    if prompt := st.chat_input("Ask about refund data... (e.g. 'How many refunded after orientation?')", key=f"chat_input_{tab_key}"):
        msgs.append({"role":"user","content":prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner(""):
                try:
                    resp = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Content-Type":"application/json",
                                 "Authorization":f"Bearer {api_key}"},
                        json={"model":"gpt-4o-mini","max_tokens":300,
                              "messages":[
                                  {"role":"system","content":system_prompt},
                                  *[{"role":m["role"],"content":m["content"]} for m in msgs]
                              ]},
                        timeout=20)
                    answer = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    answer = f"Error: {e}"
                st.write(answer)
                msgs.append({"role":"assistant","content":answer})

