"""
Converts processed repository signals into natural language summaries
that are fed as input to the LLM labeler and later to the BERT model.
"""
import pandas as pd
from src.utils import load_csv, save_csv


def build_summary(row: pd.Series) -> str:
    parts = []

    parts.append(f"Repository: {row['full_name']}.")

    if row.get("description"):
        parts.append(f"Description: {row['description']}.")

    if row.get("language"):
        parts.append(f"Primary language: {row['language']}.")

    parts.append(
        f"It has {row['stars']} stars, {row['forks']} forks, "
        f"and {row['contributors']} contributors."
    )

    parts.append(
        f"In the last year there were {row['commits_last_year']} commits "
        f"across {row['active_weeks']} active weeks "
        f"({row['commits_per_active_week']} commits/active week on average)."
    )

    parts.append(
        f"Issues: {row['open_issues']} open, {row['closed_issues']} closed "
        f"(close ratio: {row['issue_close_ratio']})."
    )

    parts.append(
        f"Pull requests: {row['open_prs']} open, {row['closed_prs']} closed."
    )

    parts.append(f"Releases published: {row['releases']}.")

    parts.append(
        f"CI/CD workflows: {'present' if row['has_ci'] else 'absent'}. "
        f"README: {'present' if row['has_readme'] else 'absent'}. "
        f"Branches: {row['branch_count']}."
    )

    if row.get("topics"):
        parts.append(f"Topics: {row['topics']}.")

    if row.get("license"):
        parts.append(f"License: {row['license']}.")

    parts.append(
        f"Repository age: {row['age_days']} days. "
        f"Last push: {row['days_since_push']} days ago. "
        f"Size: {row['size_kb']} KB."
    )

    flags = []
    if row.get("is_fork"):
        flags.append("fork")
    if row.get("is_template"):
        flags.append("template")
    if flags:
        parts.append(f"Flags: {', '.join(flags)}.")

    return " ".join(parts)


def run(input_path: str, output_path: str) -> pd.DataFrame:
    df = load_csv(input_path)
    df["summary"] = df.apply(build_summary, axis=1)
    save_csv(df, output_path)
    print(f"Generated summaries for {len(df)} repos → {output_path}")
    return df


if __name__ == "__main__":
    run("data/processed/repos_processed.csv", "data/processed/repos_summarized.csv")
