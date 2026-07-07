import pandas as pd
import numpy as np
import streamlit as st


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _parse_money(series):
    cleaned = (series.astype(str).str.replace(",", "", regex=False).str.strip()
               .replace({"nan": np.nan, "": np.nan, "None": np.nan,
                         "Not Updated": np.nan, "NaN": np.nan, "<NA>": np.nan}))
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_date(series):
    """
    Parse dates from multiple formats including BQ date strings.
    Handles: MM/DD/YYYY, DD-Mon-YYYY, and BQ format "Mon Jan 26 2026 00:00:00 GMT+0530..."
    """
    idx  = series.index
    raw  = series.fillna("").astype(str).str.strip()

    # Strip BQ timezone suffix for parsing: "Mon Jan 26 2026 00:00:00 GMT+0530 ..." -> "Mon Jan 26 2026"
    cleaned = raw.str.replace(r" \d{2}:\d{2}:\d{2}.*$", "", regex=True).str.strip()
    cleaned = cleaned.replace("", np.nan)

    vals = cleaned.tolist()

    # Try MM/DD/YYYY first
    result = pd.to_datetime(vals, errors="coerce", format="%m/%d/%Y")
    result = pd.Series(result, index=idx)

    # Fallback 1: dayfirst (e.g. 27-Mar-2026)
    mask = result.isna() & cleaned.notna()
    if mask.any():
        fb = pd.to_datetime(cleaned[mask].tolist(), errors="coerce", dayfirst=True)
        result[mask] = pd.Series(fb.values, index=series[mask].index)

    # Fallback 2: BQ weekday format "Mon Jan 26 2026"
    mask2 = result.isna() & cleaned.notna()
    if mask2.any():
        fb2 = pd.to_datetime(cleaned[mask2].tolist(), errors="coerce", format="%a %b %d %Y")
        result[mask2] = pd.Series(fb2.values, index=series[mask2].index)

    # Fallback 3: generic pandas parsing
    mask3 = result.isna() & cleaned.notna()
    if mask3.any():
        fb3 = pd.to_datetime(cleaned[mask3].tolist(), errors="coerce")
        result[mask3] = pd.Series(fb3.values, index=series[mask3].index)

    return result


def _quarter_label(dt_series):
    q  = dt_series.dt.month.map(
        {1:"Q1",2:"Q1",3:"Q1",4:"Q2",5:"Q2",6:"Q2",
         7:"Q3",8:"Q3",9:"Q3",10:"Q4",11:"Q4",12:"Q4"})
    yr = dt_series.dt.year.astype("Int64").astype(str).str[-2:]
    return q + "-" + yr


def _clean(series):
    return (series.fillna("Not Updated").astype(str).str.strip()
            .replace({"nan":"Not Updated","":"Not Updated",
                      "None":"Not Updated","NaN":"Not Updated"}))


def _get_bq_client():
    from google.cloud import bigquery
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return bigquery.Client(
        credentials=creds,
        project=st.secrets["gcp_service_account"]["project_id"])


# ──────────────────────────────────────────────
# BIGQUERY COLUMN MAP
# Exact names as they appear in BigQuery after
# uploading the cleaned CSV (header row 1 skipped)
# ──────────────────────────────────────────────
BQ_COL = {
    "hubspot_id":        "Hubspot id",
    "cohort":            "Cohort",
    "enrollment_date":   "Date of Receipt",
    "cohort_start":      "Cohort Start Date New",   # col 48 — AY equivalent
    "orientation_date":  "Orientation Date",
    "first_class_date":  "First Class Date",
    "refund_req_date":   "Refund Request Date  by learner",
    "refund_date":       "Refund Date",
    "net_revenue":       "Net Revenue",
    "amount_refunded":   "Amount refunded",
    "credit_note_amt":   "Credit Note Amount",
    "amount_credited":   "Amount Credited",
    "bu":                "BU",
    "category":          "Category",
    "course":            "Course",
    "country":           "Region ",
    "payment_mode":      "Payment Mode",
    "upfront_type":      "Upfront Payment or Non Upfront or Flexipay",
    "new_alumni":        "New or Alumni",
    "refund_category":   "Refund Category",
    "refund_month":      "Refund Month",
    "month_year":        "Month and Year",
    "onboarding_status": "Onboarding Status",
    "trial_window":      "Refund request received in Trial Window",
    "eligible_policy":   "Eligible as per refund policy",
    "orientation_att":   "Orientation Attended",
    "first_class_att":   "First Class Attended",
    "sale_retained":     "Sale Retained or Dropped",
    "refund_type":       "Type",
    "student_retained":  "Student Retained or Dropped For Retention",
    "pa":                "PA",
}


@st.cache_data(ttl=300, show_spinner="Loading refund data from BigQuery…")
def load_refund(_path=None):
    client = _get_bq_client()
    query = "SELECT * FROM `ik-dashboard-501113.ik_refunds.refund_data`"
    df = client.query(query).to_dataframe()
    df = df.astype(str).replace({"<NA>": np.nan, "nan": np.nan, "None": np.nan})

    c = BQ_COL  # shorthand

    # ── Dates ──
    df["enrollment_date"]     = _parse_date(df[c["enrollment_date"]])
    df["cohort_start_date"]   = _parse_date(df[c["cohort_start"]])
    df["orientation_date"]    = _parse_date(df[c["orientation_date"]])
    df["first_class_date"]    = _parse_date(df[c["first_class_date"]])
    df["refund_request_date"] = _parse_date(df[c["refund_req_date"]])
    df["refund_date"]         = _parse_date(df[c["refund_date"]])

    # ── Money ──
    df["net_revenue"]       = _parse_money(df[c["net_revenue"]])
    df["amount_refunded"]   = _parse_money(df[c["amount_refunded"]])
    df["credit_note_amount"]= _parse_money(df[c["credit_note_amt"]])
    df["amount_credited"]   = _parse_money(df[c["amount_credited"]])

    # ── Date diffs ──
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

    # ── Quarter / Month ──
    df["refund_quarter"]     = _quarter_label(df["refund_date"])
    df["enrollment_quarter"] = _quarter_label(df["enrollment_date"])
    df["enrollment_month"]   = df["enrollment_date"].dt.to_period("M").astype(str)

    # ── Categorical columns — standardised names ──
    df["BU"]       = _clean(df[c["bu"]])
    df["Category"] = _clean(df[c["category"]])
    df["Course"]   = _clean(df[c["course"]])

    # Country — use Region column directly (Country col removed from source)
    df["Country"] = _clean(df[c["country"]])

    df["Payment Mode"]   = _clean(df[c["payment_mode"]])
    df["New / Alumni"]   = _clean(df[c["new_alumni"]])
    df["Refund Category"]= _clean(df[c["refund_category"]])
    df["Onboarding Status"] = _clean(df[c["onboarding_status"]])
    df["Orientation Attended"]  = _clean(df[c["orientation_att"]])
    df["First Class Attended"]  = _clean(df[c["first_class_att"]])
    df["Sale Retained / Dropped"] = _clean(df[c["sale_retained"]])
    df["Refund Type"]              = _clean(df[c["refund_type"]])
    df["Eligible as per refund policy"] = _clean(df[c["eligible_policy"]])
    df["Refund request received in Trial Window"] = _clean(df[c["trial_window"]])
    df["Hubspot id"] = _clean(df[c["hubspot_id"]])
    df["Cohort"]     = _clean(df[c["cohort"]])
    df["PA"]         = _clean(df[c["pa"]])

    # Upfront type — rename to standard
    df["Upfront Payment / Non Upfront / Flexipay"] = _clean(df[c["upfront_type"]])

    # ── Refund Month — BQ stores as date string "Mon Jan 26 2026 00:00:00 GMT+0530"
    # Convert to standard "Jan - 26" format
    month_order = ["Jan - 26","Feb - 26","Mar - 26","Apr - 26",
                   "May - 26","Jun - 26","Jul - 26","Aug - 26",
                   "Sep - 26","Oct - 26","Nov - 26","Dec - 26"]
    _mnames = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

    def _parse_rm(val):
        s = str(val).strip()
        if s in ("nan","None","Not Updated","","<NA>"):
            return "Not Updated"
        if " - " in s and len(s) <= 9:
            return s  # already correct format
        try:  # BQ date string: "Mon Jan 26 2026 ..."
            parts = s.split()
            if len(parts) >= 4 and parts[1][:3] in _mnames:
                return parts[1][:3] + " - " + parts[3][-2:]
        except:
            pass
        try:  # pandas fallback
            dt = pd.to_datetime(s, errors="coerce")
            if pd.notna(dt):
                return _mnames[dt.month-1] + " - " + str(dt.year)[-2:]
        except:
            pass
        return "Not Updated"

    raw_rm = df[c["refund_month"]].fillna("").astype(str)
    df["Refund Month"] = pd.Categorical(
        raw_rm.apply(_parse_rm), categories=month_order, ordered=True)

    return df


# ──────────────────────────────────────────────
# ONBOARDING — CSV from GitHub (unchanged)
# ──────────────────────────────────────────────

@st.cache_data(show_spinner="Loading onboarding data…")
def load_onboarding(path="onboarding_data.csv"):
    df = pd.read_csv(path, dtype=str)
    df["enrollment_date"]    = _parse_date(df["Deposit Paid Date"])
    df["enrollment_month"]   = df["enrollment_date"].dt.to_period("M").astype(str)
    df["enrollment_quarter"] = _quarter_label(df["enrollment_date"])
    df["Status"] = _clean(df["Status"])
    return df
