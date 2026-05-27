"""
Collects repository signals from the GitHub REST API.
Extracts: contributors, commit frequency, stars, forks, issues, PRs,
releases, README presence, CI/CD workflows, topics, age, last activity.
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone
from src.utils import save_csv


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get(endpoint: str, params: dict = None) -> dict | list:
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def _count_pages(endpoint: str, params: dict = None) -> int:
    """Return total item count by reading the last page number from Link header."""
    params = dict(params or {})
    params["per_page"] = 1
    url = f"{BASE_URL}{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    link = r.headers.get("Link", "")
    if 'rel="last"' not in link:
        return len(r.json()) if isinstance(r.json(), list) else 1
    last = [p for p in link.split(",") if 'rel="last"' in p][0]
    page = int(last.split("page=")[-1].split(">")[0])
    return page


def fetch_repo_signals(owner: str, repo: str) -> dict:
    """Return a flat dict of all signals for a single repository."""
    slug = f"{owner}/{repo}"
    print(f"  Fetching {slug}...")

    # Basic metadata
    meta = _get(f"/repos/{owner}/{repo}")
    created_at = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
    pushed_at = datetime.fromisoformat(meta["pushed_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_days = (now - created_at).days
    days_since_push = (now - pushed_at).days

    # Contributors count
    try:
        contributors = _count_pages(f"/repos/{owner}/{repo}/contributors", {"anon": "true"})
    except Exception:
        contributors = 0

    # Commit frequency: commits in the last 52 weeks
    try:
        activity = _get(f"/repos/{owner}/{repo}/stats/commit_activity")
        weekly_commits = [w["total"] for w in activity] if activity else []
        commits_last_year = sum(weekly_commits)
        active_weeks = sum(1 for w in weekly_commits if w > 0)
    except Exception:
        commits_last_year, active_weeks = 0, 0

    # Open issues and PRs (GitHub counts PRs as issues)
    open_issues = meta.get("open_issues_count", 0)

    # Closed issues
    try:
        closed_issues = _count_pages(f"/repos/{owner}/{repo}/issues", {"state": "closed", "per_page": 1})
    except Exception:
        closed_issues = 0

    # Pull requests
    try:
        open_prs = _count_pages(f"/repos/{owner}/{repo}/pulls", {"state": "open"})
        closed_prs = _count_pages(f"/repos/{owner}/{repo}/pulls", {"state": "closed"})
    except Exception:
        open_prs, closed_prs = 0, 0

    # Releases
    try:
        releases = _count_pages(f"/repos/{owner}/{repo}/releases")
    except Exception:
        releases = 0

    # CI/CD workflows
    try:
        workflows = _get(f"/repos/{owner}/{repo}/actions/workflows")
        has_ci = workflows.get("total_count", 0) > 0
    except Exception:
        has_ci = False

    # README presence
    try:
        _get(f"/repos/{owner}/{repo}/readme")
        has_readme = True
    except Exception:
        has_readme = False

    # Branches
    try:
        branch_count = _count_pages(f"/repos/{owner}/{repo}/branches")
    except Exception:
        branch_count = 1

    signals = {
        "owner": owner,
        "repo": repo,
        "full_name": meta.get("full_name", slug),
        "description": meta.get("description", "") or "",
        "stars": meta.get("stargazers_count", 0),
        "forks": meta.get("forks_count", 0),
        "watchers": meta.get("watchers_count", 0),
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "open_prs": open_prs,
        "closed_prs": closed_prs,
        "contributors": contributors,
        "commits_last_year": commits_last_year,
        "active_weeks": active_weeks,
        "releases": releases,
        "has_ci": int(has_ci),
        "has_readme": int(has_readme),
        "branch_count": branch_count,
        "topics": ", ".join(meta.get("topics", [])),
        "language": meta.get("language", "") or "",
        "age_days": age_days,
        "days_since_push": days_since_push,
        "size_kb": meta.get("size", 0),
        "is_fork": int(meta.get("fork", False)),
        "is_template": int(meta.get("is_template", False)),
        "license": meta.get("license", {}).get("spdx_id", "") if meta.get("license") else "",
    }

    time.sleep(0.5)  # stay within rate limits
    return signals


def collect_repos(repo_list: list[tuple[str, str]], output_path: str) -> pd.DataFrame:
    """
    Collect signals for a list of (owner, repo) tuples and save to CSV.
    repo_list: [("torvalds", "linux"), ("psf", "requests"), ...]
    """
    rows = []
    for owner, repo in repo_list:
        try:
            signals = fetch_repo_signals(owner, repo)
            rows.append(signals)
        except Exception as e:
            print(f"  ERROR fetching {owner}/{repo}: {e}")

    df = pd.DataFrame(rows)
    save_csv(df, output_path)
    print(f"Saved {len(df)} repos to {output_path}")
    return df


if __name__ == "__main__":
    # Quick smoke test — replace with your target repo list
    sample = [
        ("psf", "requests"),
        ("pallets", "flask"),
        ("encode", "httpx"),
    ]
    collect_repos(sample, "data/raw/repos_raw.csv")
