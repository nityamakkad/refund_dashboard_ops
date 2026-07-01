import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _parse_money(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"nan": np.nan, "": np.nan, "None": np.nan})
        .astype(float)
    )


def _parse_date(series: pd.Series) -> pd.Series:
    """Parse dates safely — converts via list to avoid pandas dotted-name bug."""
    idx  = series.index
    vals = series.tolist()
    parsed = pd.to_datetime(vals, errors="coerce", format="%m/%d/%Y")
    result = pd.Series(parsed, index=idx)
    mask = result.isna() & series.notna() & (series.astype(str).str.strip() != "")
    if mask.any():
        fb = pd.to_datetime(series[mask].tolist(), errors="coerce", dayfirst=True)
        result[mask] = pd.Series(fb, index=series[mask].index)
    return result


def _quarter_label(dt_series: pd.Series) -> pd.Series:
    q  = dt_series.dt.month.map(
        {1:"Q1",2:"Q1",3:"Q1",4:"Q2",5:"Q2",6:"Q2",
         7:"Q3",8:"Q3",9:"Q3",10:"Q4",11:"Q4",12:"Q4"})
    yr = dt_series.dt.year.astype("Int64").astype(str).str[-2:]
    return q + "-" + yr


def _clean_str(series: pd.Series) -> pd.Series:
    return (series.fillna("Not Updated").astype(str).str.strip()
            .replace({"nan":"Not Updated","":"Not Updated",
                      "None":"Not Updated","NaN":"Not Updated"}))


# ──────────────────────────────────────────────
# BIGQUERY CLIENT
# ──────────────────────────────────────────────

def _get_bq_client():
    """Create BigQuery client from Streamlit secrets."""
    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(credentials=creds,
                           project=st.secrets["gcp_service_account"]["project_id"])


# ──────────────────────────────────────────────
# REFUND DATA — from BigQuery
# ──────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Loading refund data from BigQuery…")
def load_refund(_path=None) -> pd.DataFrame:
    """
    Loads refund data from BigQuery.
    Table: ik-dashboard-501113.ik_refunds.refund_data
    Cached for 5 minutes — auto-refreshes when new data is pushed.
    """
    client = _get_bq_client()

    query = """
        SELECT *
        FROM `ik-dashboard-501113.ik_refunds.refund_data`
    """
    df = client.query(query).to_dataframe(dtypes_backend="numpy_nullable")

    # Convert all columns to string for consistent processing
    df = df.astype(str).replace({"<NA>": np.nan, "nan": np.nan, "None": np.nan})

    # ── Extract positionally ambiguous columns by name from BQ ──
    # BQ auto-detect will name the duplicate "Cohort_Start_Date_1" or similar
    # We try both possible names
    def _get_col(df, *candidates):
        for c in candidates:
            if c in df.columns:
                return df[c]
        return pd.Series([np.nan] * len(df))

    # ── Date columns ──
    df["enrollment_date"]     = _parse_date(_get_col(df, "Date_of_Receipt", "Date of Receipt"))
    df["cohort_start_date"]   = _parse_date(_get_col(df, "Cohort_Start_Date_1",
                                                        "Cohort Start Date_1",
                                                        "Cohort_Start_Date1"))
    df["orientation_date"]    = _parse_date(_get_col(df, "Orientation_Date", "Orientation Date"))
    df["first_class_date"]    = _parse_date(_get_col(df, "First_Class_Date", "First Class Date"))
    df["refund_request_date"] = _parse_date(_get_col(df, "Refund_Request_Date__by_learner",
                                                        "Refund Request Date  by learner"))
    df["refund_date"]         = _parse_date(_get_col(df, "Refund_Date", "Refund Date"))

    # ── Money columns ──
    for raw, alias in [
        ("Net_Revenue",        "net_revenue"),
        ("Amount_refunded",    "amount_refunded"),
        ("Credit_Note_Amount", "credit_note_amount"),
        ("Amount_Credited",    "amount_credited"),
    ]:
        col = _get_col(df, raw, raw.replace("_", " "))
        df[alias] = _parse_money(col)

    # ── Date-diff columns ──
    df["days_enroll_to_refund_req"]   = (df["refund_request_date"] - df["enrollment_date"]).dt.days
    df["days_enroll_to_cohort_start"] = (df["cohort_start_date"]   - df["enrollment_date"]).dt.days
    df["days_cohort_to_refund_req"]   = (df["refund_request_date"] - df["cohort_start_date"]).dt.days
    df["days_to_orientation"]         = (df["refund_request_date"] - df["orientation_date"]).dt.days
    df["days_to_first_class"]         = (df["refund_request_date"] - df["first_class_date"]).dt.days

    # ── Before/After flags ──
    df["refund_vs_orientation"] = df["days_to_orientation"].apply(
        lambda x: "Before Orientation" if pd.notna(x) and x < 0
        else ("After Orientation" if pd.notna(x) and x >= 0 else "Not Updated"))
    df["refund_vs_first_class"] = df["days_to_first_class"].apply(
        lambda x: "Before First Class" if pd.notna(x) and x < 0
        else ("After First Class" if pd.notna(x) and x >= 0 else "Not Updated"))

    # ── Quarter / Month labels ──
    df["refund_quarter"]     = _quarter_label(df["refund_date"])
    df["enrollment_quarter"] = _quarter_label(df["enrollment_date"])
    df["enrollment_month"]   = df["enrollment_date"].dt.to_period("M").astype(str)

    # ── Normalise categorical columns ──
    # BQ replaces spaces with underscores in column names — handle both
    def _std(df, *candidates):
        col = _get_col(df, *candidates)
        return _clean_str(col)

    df["BU"]         = _std(df, "BU")
    df["Category"]   = _std(df, "Category")
    df["Course"]     = _std(df, "Course")
    df["Country"]    = _std(df, "Country", "AV")
    df["Payment Mode"] = _std(df, "Payment_Mode", "Payment Mode")
    df["Upfront Payment / Non Upfront / Flexipay"] = _std(df,
        "Upfront_Payment___Non_Upfront___Flexipay",
        "Upfront Payment / Non Upfront / Flexipay")
    df["New / Alumni"]      = _std(df, "New___Alumni", "New / Alumni")
    df["Refund Category"]   = _std(df, "Refund_Category", "Refund Category")
    df["Onboarding Status"] = _std(df, "Onboarding_Status", "Onboarding Status",
                                       "BD", "_onboarding_status")
    df["Refund request received in Trial Window"] = _std(df,
        "Refund_request_received_in_Trial_Window",
        "Refund request received in Trial Window")
    df["Eligible as per refund policy"] = _std(df,
        "Eligible_as_per_refund_policy",
        "Eligible as per refund policy")
    df["Orientation Attended"]  = _std(df, "Orientation_Attended",  "Orientation Attended")
    df["First Class Attended"]  = _std(df, "First_Class_Attended",  "First Class Attended")
    df["Hubspot id"]  = _std(df, "Hubspot_id", "Hubspot id")
    df["Cohort"]      = _std(df, "Cohort")
    df["PA"]          = _std(df, "PA")

    # ── Refund Month as ordered categorical ──
    month_order = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26",
                   "May - 26","Jun - 26","Jul - 26","Aug - 26",
                   "Sep - 26","Oct - 26","Nov - 26","Dec - 26"]
    rm = _std(df, "Refund_Month", "Refund Month")
    df["Refund Month"] = pd.Categorical(rm, categories=month_order, ordered=True)

    return df


# ──────────────────────────────────────────────
# ONBOARDING DATA — from CSV in GitHub
# ──────────────────────────────────────────────

@st.cache_data(show_spinner="Loading onboarding data…")
def load_onboarding(path: str = "onboarding_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df["enrollment_date"]    = _parse_date(df["Deposit Paid Date"])
    df["enrollment_month"]   = df["enrollment_date"].dt.to_period("M").astype(str)
    df["enrollment_quarter"] = _quarter_label(df["enrollment_date"])
    df["Status"] = _clean_str(df["Status"])
    return df
