"""
update_readme.py
────────────────
Fetches live data from the GitHub REST API and rewrites the dynamic sections
of README.md between comment-block markers.

Dynamic sections updated:
  • <!-- SKILLS_START/END -->   — top languages aggregated across all public repos
  • <!-- PROJECTS_START/END --> — top 6 repos ranked by composite score
  • <!-- LAST_UPDATED_START/END --> — UTC timestamp of last run

Usage:
  python update_readme.py

Requires:
  GITHUB_TOKEN  environment variable (highly recommended to avoid rate limits)
  requests      pip install requests urllib3
"""

import os
import re
import sys
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Config ──────────────────────────────────────────────────────────────────

USERNAME    = "manishborikar92"
README_PATH = "README.md"

# Repos to always exclude
EXCLUDE_REPOS = {USERNAME}

# Language → badge colour (shields.io hex, no #)
LANG_COLOURS = {
    "Python":     "3776AB", "JavaScript": "F7DF1E", "TypeScript": "3178C6",
    "C++":        "00599C", "C":          "A8B9CC", "Java":       "ED8B00",
    "Go":         "00ADD8", "Rust":       "DEA584", "Shell":      "89E051",
    "HTML":       "E34F26", "CSS":        "1572B6", "Makefile":   "427819",
    "Dockerfile": "384D54", "PowerShell": "5391FE", "Ruby":       "CC342D",
    "Kotlin":     "7F52FF", "Swift":      "F05138", "Dart":       "0175C2",
    "R":          "276DC3", "MATLAB":     "e16737",
}
DEFAULT_COLOUR = "555555"

# Language → logo name for shields.io
LANG_LOGOS = {
    "JavaScript": "javascript", "TypeScript":  "typescript",
    "Python":     "python",     "C++":         "cplusplus",
    "Shell":      "gnubash",    "Dockerfile":  "docker",
    "PowerShell": "powershell", "HTML":        "html5",
    "CSS":        "css3",
}

# ─── GitHub API Client ───────────────────────────────────────────────────────

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

def create_session() -> requests.Session:
    """Creates a robust session with retries and authentication headers."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    
    if TOKEN:
        session.headers["Authorization"] = f"Bearer {TOKEN}"
    else:
        print("⚠ WARNING: GITHUB_TOKEN not found. You are restricted to 60 API calls per hour.", file=sys.stderr)
        
    return session

def check_rate_limit(response: requests.Response):
    """Checks and warns if rate limits are hit."""
    if response.status_code in (403, 429) and "X-RateLimit-Remaining" in response.headers:
        if response.headers["X-RateLimit-Remaining"] == "0":
            reset_time = datetime.fromtimestamp(int(response.headers["X-RateLimit-Reset"]))
            print(f"\n❌ API Rate Limit Exceeded! Resets at {reset_time}", file=sys.stderr)
            sys.exit(1)

def paginate(session: requests.Session, url: str, params: dict = None) -> list:
    """Robust pagination using GitHub's Link headers."""
    results = []
    current_url = url
    if params is None:
        params = {"per_page": 100}
        
    while current_url:
        r = session.get(current_url, params=params if current_url == url else None, timeout=20)
        check_rate_limit(r)
        r.raise_for_status()
        
        if r.status_code == 204:
            break
            
        data = r.json()
        if isinstance(data, list):
            results.extend(data)
        
        current_url = None
        link_header = r.headers.get("Link")
        if link_header:
            links = link_header.split(",")
            for link in links:
                if 'rel="next"' in link:
                    current_url = link[link.find("<")+1 : link.find(">")]
                    break
    return results

# ─── Fetch Data ──────────────────────────────────────────────────────────────

def fetch_repos(session: requests.Session) -> list[dict]:
    """Return all non-fork, non-excluded public repos."""
    url = f"https://api.github.com/users/{USERNAME}/repos"
    raw = paginate(session, url)
    return [
        r for r in raw
        if not r.get("fork")
        and r.get("name") not in EXCLUDE_REPOS
        and not r.get("private")
    ]

def fetch_commit_counts(session: requests.Session, repos: list[dict]) -> dict[str, int]:
    """
    Fetches the TOTAL commit count of the repo using the pagination Link header.
    """
    counts: dict[str, int] = {}
    total = len(repos)
    
    for i, repo in enumerate(repos, 1):
        name = repo["name"]
        url = f"https://api.github.com/repos/{USERNAME}/{name}/commits?per_page=1"
        
        try:
            r = session.get(url, timeout=15)
            check_rate_limit(r)
            repo_commits = 0
            
            if r.status_code == 200:
                link_header = r.headers.get("Link")
                if link_header:
                    links = link_header.split(",")
                    for link in links:
                        if 'rel="last"' in link:
                            # CRITICAL FIX: Match &page= or ?page= to avoid extracting the '1' from per_page=1
                            match = re.search(r'[&?]page=(\d+)', link)
                            if match:
                                repo_commits = int(match.group(1))
                            break
                    # Fallback if rel="last" is missing
                    if repo_commits == 0:
                        repo_commits = len(r.json())
                else:
                    # If there's no Link header, there is only 1 page of commits.
                    repo_commits = len(r.json())
            elif r.status_code == 409:
                repo_commits = 0

            counts[name] = repo_commits
            print(f"   [{i:>2}/{total}] {name}: {repo_commits} commits")
            
        except requests.RequestException as e:
            print(f"   [{i:>2}/{total}] {name}: Error fetching commits - {e}")
            counts[name] = 0
            
    return counts

def top_repos(repos: list[dict], commit_counts: dict[str, int], n: int = 6) -> list[dict]:
    """Rank repos purely by total commit count."""
    
    # CRITICAL FIX: Explicitly cast values to integers to guarantee mathematical sorting
    # This prevents bugs where "121" is sorted as "lower" than "68".
    sorted_repos = sorted(
        repos,
        key=lambda r: int(commit_counts.get(r.get("name", ""), 0)),
        reverse=True,
    )
    
    # Strictly enforce selecting the top N items
    return sorted_repos[:n]

def fetch_language_bytes(session: requests.Session, repos: list[dict]) -> dict[str, int]:
    """Aggregate language byte counts across all repos."""
    totals: dict[str, int] = {}
    for repo in repos:
        url = f"https://api.github.com/repos/{USERNAME}/{repo['name']}/languages"
        try:
            r = session.get(url, timeout=15)
            check_rate_limit(r)
            if r.status_code == 200:
                for lang, b in r.json().items():
                    totals[lang] = totals.get(lang, 0) + b
        except requests.RequestException:
            continue
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))

# ─── Render Helpers ──────────────────────────────────────────────────────────

def badge(label: str, message: str, colour: str, logo: str = "") -> str:
    label_enc   = label.replace("-", "--").replace(" ", "_")
    message_enc = message.replace("-", "--").replace(" ", "_")
    logo_part   = f"&logo={logo}&logoColor=white" if logo else ""
    return (
        f"![{label}](https://img.shields.io/badge/"
        f"{label_enc}-{message_enc}-{colour}?style=flat-square{logo_part})"
    )

def render_skills(lang_bytes: dict[str, int], top_n: int = 10) -> str:
    """Produce a centred row of language badges for the top N languages."""
    langs = list(lang_bytes.keys())[:top_n]
    if not langs:
        return "_No language data found._"
    badges = []
    for lang in langs:
        colour = LANG_COLOURS.get(lang, DEFAULT_COLOUR)
        logo   = LANG_LOGOS.get(lang, lang.lower().replace("+", "p").replace(" ", ""))
        badges.append(badge(lang, lang, colour, logo))
    return '<div align="center">\n\n' + "\n".join(badges) + "\n\n</div>"

def render_projects(repos: list[dict], commit_counts: dict[str, int] | None = None) -> str:
    """Render top repos as a Markdown table (2-column card layout)."""
    if not repos:
        return "_No repositories found._"

    # Icon map by primary language - using shields.io logos for consistency
    ICON_PREFIX = {
        "Python": "![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)",
        "JavaScript": "![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=white)",
        "TypeScript": "![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)",
        "C++": "![C++](https://img.shields.io/badge/-C++-00599C?style=flat-square&logo=cplusplus&logoColor=white)",
        "Shell": "![Shell](https://img.shields.io/badge/-Shell-89E051?style=flat-square&logo=gnubash&logoColor=white)",
        "PowerShell": "![PowerShell](https://img.shields.io/badge/-PowerShell-5391FE?style=flat-square&logo=powershell&logoColor=white)",
        "HTML": "![HTML](https://img.shields.io/badge/-HTML-E34F26?style=flat-square&logo=html5&logoColor=white)",
        "CSS": "![CSS](https://img.shields.io/badge/-CSS-1572B6?style=flat-square&logo=css3&logoColor=white)",
        "Go": "![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white)",
        "Rust": "![Rust](https://img.shields.io/badge/-Rust-DEA584?style=flat-square&logo=rust&logoColor=white)",
        "Java": "![Java](https://img.shields.io/badge/-Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white)",
        "Ruby": "![Ruby](https://img.shields.io/badge/-Ruby-CC342D?style=flat-square&logo=ruby&logoColor=white)",
    }

    rows = []
    for i in range(0, len(repos), 2):
        left  = repos[i]
        right = repos[i + 1] if i + 1 < len(repos) else None

        def card(repo):
            name     = repo["name"]
            desc     = repo.get("description") or "_No description provided._"
            url      = repo["html_url"]
            lang     = repo.get("language")
            icon     = ICON_PREFIX.get(lang, "![Project](https://img.shields.io/badge/-Project-555555?style=flat-square&logo=github&logoColor=white)")
            star_b   = f"![Stars](https://img.shields.io/github/stars/{USERNAME}/{name}?style=flat-square&color=f59e0b&logo=starship&logoColor=white)"
            fork_b   = f"![Forks](https://img.shields.io/github/forks/{USERNAME}/{name}?style=flat-square&color=6366f1&logo=git&logoColor=white)"
            commits  = (commit_counts or {}).get(name, 0)
            commit_b = (f"![Commits](https://img.shields.io/badge/commits-{commits}-7C3AED?style=flat-square&logo=git&logoColor=white)"
                        if commits else "")
            view_b   = f"[![View](https://img.shields.io/badge/View_Repository-181717?style=flat-square&logo=github&logoColor=white)]({url})"
            
            # Build badge row with proper spacing
            badges = [b for b in [icon, star_b, fork_b, commit_b] if b]
            badge_row = " ".join(badges)
            
            return (
                f"### [{name}]({url})\n"
                f"> {desc}\n\n"
                f"{badge_row}\n\n"
                f"{view_b}"
            )

        left_cell  = card(left)
        right_cell = card(right) if right else ""
        rows.append(
            f'<tr>\n'
            f'<td width="50%" valign="top">\n\n{left_cell}\n\n</td>\n'
            f'<td width="50%" valign="top">\n\n{right_cell}\n\n</td>\n'
            f'</tr>'
        )

    return "<table>\n" + "\n".join(rows) + "\n</table>"

# ─── README Rewriter ─────────────────────────────────────────────────────────

def replace_block(content: str, tag: str, new_body: str) -> str:
    """
    Safely replaces content between markers using absolute string splitting.
    """
    # CRITICAL FIX: Built using string concatenation to prevent editors/chat from deleting HTML tags!
    start_marker = f"<" + f"!-- {tag}_START --" + ">"
    end_marker   = f"<" + f"!-- {tag}_END --" + ">"

    # Failsafe: if the markers aren't in the document, abort quietly
    if start_marker not in content or end_marker not in content:
        print(f"  ⚠  Warning: marker pair {tag}_START/END not found in README.", file=sys.stderr)
        return content

    # Split the document at the markers
    parts_before = content.split(start_marker)
    parts_after = parts_before[1].split(end_marker)

    before_section = parts_before[0]
    after_section = parts_after[1]

    # Reconstruct the document with the new block safely in the middle
    return f"{before_section}{start_marker}\n{new_body}\n{end_marker}{after_section}"

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    session = create_session()

    print("📡 Fetching repositories…")
    repos = fetch_repos(session)
    print(f"   Found {len(repos)} public, non-fork repos.")

    print("\n🔢 Counting total branch commits per repo…")
    commit_counts = fetch_commit_counts(session, repos)

    print("\n🏆 Selecting top 6 repos by commit count…")
    best = top_repos(repos, commit_counts, n=6)
    for r in best:
        n = commit_counts.get(r["name"], 0)
        print(f"   • {r['name']} ({n} commits)")

    print("\n📊 Aggregating language bytes…")
    lang_bytes = fetch_language_bytes(session, repos)
    top_langs  = list(lang_bytes.keys())[:10]
    print(f"   Top langs: {', '.join(top_langs) if top_langs else 'None found'}")

    print(f"\n📝 Rewriting {README_PATH}…")
    try:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        content = replace_block(content, "SKILLS", render_skills(lang_bytes))
        content = replace_block(content, "PROJECTS", render_projects(best, commit_counts))

        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ README updated successfully.")
    except FileNotFoundError:
        print(f"❌ Could not find {README_PATH}. Make sure you are in the correct directory.", file=sys.stderr)

if __name__ == "__main__":
    main()