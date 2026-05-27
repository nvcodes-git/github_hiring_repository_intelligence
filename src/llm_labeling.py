"""
Weak labeling: sends repository summaries to Claude and assigns one of
six engineering-maturity categories. Saves results to data/labeled/.
"""
import os
import time
import pandas as pd
import anthropic
from src.utils import load_csv, save_csv


LABELS = [
    "intern",
    "junior",
    "senior",
    "lead/architect",
    "template/boilerplate",
    "low-value",
]

SYSTEM_PROMPT = """You are an expert software engineering evaluator.
Your task is to classify GitHub repositories by the engineering maturity they reflect — NOT the developer personally.

Classify each repository into exactly one of these six categories:

- intern: Very simple project, minimal structure, no tests, no CI, few commits, likely a course exercise or first project.
- junior: Functional but basic project. Some structure, limited documentation, no CI or very basic one, few contributors.
- senior: Well-structured project with clear architecture, good documentation, tests present, active CI/CD, consistent commit history.
- lead/architect: Complex system showing advanced design (multiple services, design patterns, infrastructure-as-code, extensive CI/CD, many contributors, releases).
- template/boilerplate: Repository is clearly a copy, fork with no changes, scaffold generator output, or starter template with no original work.
- low-value: Empty, abandoned, placeholder, spam, or repository with no meaningful content or activity.

Rules:
- Reply with ONLY the label, nothing else.
- The label must be one of: intern, junior, senior, lead/architect, template/boilerplate, low-value
- Do not explain your reasoning."""


def classify_repo(client: anthropic.Anthropic, summary: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": summary}],
            )
            label = message.content[0].text.strip().lower()
            if label in LABELS:
                return label
            # If the model returned something unexpected, default to low-value
            print(f"  Unexpected label '{label}', defaulting to low-value")
            return "low-value"
        except Exception as e:
            print(f"  API error (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)
    return "low-value"


def label_repos(input_path: str, output_path: str) -> pd.DataFrame:
    df = load_csv(input_path)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    labels = []
    for i, row in df.iterrows():
        print(f"  [{i + 1}/{len(df)}] Labeling {row['full_name']}...")
        label = classify_repo(client, row["summary"])
        labels.append(label)
        time.sleep(0.3)  # stay within rate limits

    df["label"] = labels
    save_csv(df, output_path)
    print(f"\nLabeled {len(df)} repos → {output_path}")
    print(df["label"].value_counts().to_string())
    return df


if __name__ == "__main__":
    label_repos(
        "data/processed/repos_summarized.csv",
        "data/labeled/repos_labeled.csv",
    )
