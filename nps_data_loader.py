import pandas as pd
import numpy as np


SUMMARY_ROWS = ["Total LevelUp","Total Switchup","Total Agentic",
                "Total Fastrack","Total","SSA","Team"]

CHECKPOINT_ORDER = {
    "LevelUp":  ["EM","Week 5","Week 8"],
    "Switchup": ["NPS 1","NPS 2"],
    "Agentic":  ["NPS 1","NPS 2"],
    "Fastrack": ["NPS 1","NPS 2"],
    "PwC":      ["NPS 1","NPS 2"],
}

NPS_SCORE_COLOR = {
    "Promoter":  "#16A34A",
    "Passive":   "#D97706",
    "Detractor": "#EF4444",
}


def _clean_str(series):
    return (series.fillna("Not Updated").astype(str).str.strip()
            .replace({"nan":"Not Updated","":"Not Updated","None":"Not Updated"}))


def _parse_date(series):
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _compute_nps(df):
    """Compute NPS = (Promoters - Detractors) / Responses * 100."""
    return np.where(
        df["Responses"] > 0,
        ((df["Promoters"] - df["Detractors"]) / df["Responses"] * 100).round(1),
        np.nan)


def load_nps(path: str, region: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)

    # Drop summary rows
    df = df[~df["Category"].isin(SUMMARY_ROWS)]
    df = df[df["SSA"].notna()]
    df = df[~df["SSA"].isin(SUMMARY_ROWS)]
    df = df[df["NPS Type"].notna()]
    df = df.reset_index(drop=True)

    # Numeric columns
    for col in ["Promoters","Passive","Detractors","Cohort Size","Responses"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Computed metrics
    df["NPS_computed"]  = _compute_nps(df)
    df["Response_pct"]  = np.where(
        df["Cohort Size"] > 0,
        (df["Responses"] / df["Cohort Size"] * 100).round(1), np.nan)
    df["Total_respondents"] = df["Promoters"] + df["Passive"] + df["Detractors"]

    # Promoter/Detractor classification for labelling
    df["Promoter_pct"]  = np.where(df["Responses"]>0, df["Promoters"]/df["Responses"]*100, np.nan)
    df["Passive_pct"]   = np.where(df["Responses"]>0, df["Passive"]  /df["Responses"]*100, np.nan)
    df["Detractor_pct"] = np.where(df["Responses"]>0, df["Detractors"]/df["Responses"]*100, np.nan)

    # Date
    df["Release_date"]   = _parse_date(df["Release Date"])
    df["Release_month"]  = df["Release_date"].dt.to_period("M").astype(str)
    df["Release_quarter"]= df["Release_date"].dt.month.map(
        {1:"Q1",2:"Q1",3:"Q1",4:"Q2",5:"Q2",6:"Q2",
         7:"Q3",8:"Q3",9:"Q3",10:"Q4",11:"Q4",12:"Q4"}).fillna("Unknown")

    # Categorical
    df["SSA"]      = _clean_str(df["SSA"])
    df["Category"] = _clean_str(df["Category"])
    df["NPS Type"] = _clean_str(df["NPS Type"])
    df["Cohort Name"] = _clean_str(df["Cohort Name"])
    df["Region"]   = region

    return df
