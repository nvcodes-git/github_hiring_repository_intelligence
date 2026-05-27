"""
Cleans and normalizes raw repository signals before summarization.
"""
import pandas as pd
from src.utils import load_csv, save_csv


NUMERIC_COLS = [
    "stars", "forks", "watchers", "open_issues", "closed_issues",
    "open_prs", "closed_prs", "contributors", "commits_last_year",
    "active_weeks", "releases", "has_ci", "has_readme", "branch_count",
    "age_days", "days_since_push", "size_kb", "is_fork", "is_template",
]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in ["description", "language", "topics", "license"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    df = df.drop_duplicates(subset=["full_name"])

    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["commits_per_active_week"] = df.apply(
        lambda r: round(r["commits_last_year"] / r["active_weeks"], 2)
        if r["active_weeks"] > 0 else 0,
        axis=1,
    )

    df["issue_close_ratio"] = df.apply(
        lambda r: round(r["closed_issues"] / (r["open_issues"] + r["closed_issues"]), 3)
        if (r["open_issues"] + r["closed_issues"]) > 0 else 0,
        axis=1,
    )

    df["pr_total"] = df["open_prs"] + df["closed_prs"]

    return df


def run(input_path: str, output_path: str) -> pd.DataFrame:
    df = load_csv(input_path)
    df = clean(df)
    df = add_derived_features(df)
    save_csv(df, output_path)
    print(f"Preprocessed {len(df)} repos → {output_path}")
    return df


if __name__ == "__main__":
    run("data/raw/repos_raw.csv", "data/processed/repos_processed.csv")
