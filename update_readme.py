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
  GITHUB_TOKEN  environment variable (automatically set inside GitHub Actions)
  requests      pip install requests
"""

import os
import re
import sys
from datetime import datetime, timezone

import requests

# ─── Config ──────────────────────────────────────────────────────────────────

USERNAME    = "manishborikar92"
README_PATH = "README.md"

# Repos to always exclude (the profile repo itself + any forks you don't want)
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

# Language → logo name for shields.io (override where logo name differs)
LANG_LOGOS = {
    "JavaScript": "javascript", "TypeScript":  "typescript",
    "Python":     "python",     "C++":         "cplusplus",
    "Shell":      "gnubash",    "Dockerfile":  "docker",
    "PowerShell": "powershell", "HTML":        "html5",
    "CSS":        "css3",
}

# ─── GitHub API helpers ───────────────────────────────────────────────────────

TOKEN = os.environ.get("GITHUB_TOKEN", "")

def _headers():
    h = {"Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def paginate(url: str) -> list:
    """Fetch all pages from a GitHub REST endpoint."""
    results, page = [], 1
    while True:
        r = requests.get(url, headers=_headers(),
                         params={"per_page": 100, "page": page}, timeout=20)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        results.extend(data)
        page += 1
    return results


# ─── Fetch repos ─────────────────────────────────────────────────────────────

def fetch_repos() -> list[dict]:
    """Return all non-fork, non-excluded public repos."""
    raw = paginate(f"https://api.github.com/users/{USERNAME}/repos")
    return [
        r for r in raw
        if not r["fork"]
        and r["name"] not in EXCLUDE_REPOS
        and not r["private"]
    ]


# ─── Commit-count scoring ─────────────────────────────────────────────────────

def fetch_commit_count(repo_name: str) -> int:
    """
    Return the number of commits the authenticated user has made to repo_name.

    Uses the "Link header last-page" trick:
      GET /repos/{owner}/{repo}/commits?author={user}&per_page=1
    GitHub paginates and puts `rel="last"` in the Link header.
    Parsing the `page=N` from that URL gives the total commit count
    in a single API call — no need to paginate through all commits.

    Falls back to 0 on any error (private repo, empty repo, rate-limit, etc.)
    """
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    try:
        r = requests.get(
            url,
            headers=_headers(),
            params={"author": USERNAME, "per_page": 1},
            timeout=15,
        )
        if r.status_code != 200:
            return 0

        link = r.headers.get("Link", "")
        if not link:
            # Only one page — check body to determine if 0 or 1 commit
            return len(r.json()) if isinstance(r.json(), list) else 0

        # Extract page number from the `last` rel link
        # Format: <https://api.github.com/...?page=42>; rel="last"
        match = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
        return int(match.group(1)) if match else 1

    except (requests.RequestException, ValueError, AttributeError):
        return 0


def fetch_commit_counts(repos: list[dict]) -> dict[str, int]:
    """
    Return {repo_name: commit_count} for every repo.
    Logs progress so the Actions log is readable.
    """
    counts: dict[str, int] = {}
    total = len(repos)
    for i, repo in enumerate(repos, 1):
        name = repo["name"]
        count = fetch_commit_count(name)
        counts[name] = count
        print(f"   [{i:>2}/{total}] {name}: {count} commits")
    return counts


def top_repos(repos: list[dict], commit_counts: dict[str, int], n: int = 6) -> list[dict]:
    """Rank repos purely by number of commits the user has authored."""
    return sorted(
        repos,
        key=lambda r: commit_counts.get(r["name"], 0),
        reverse=True,
    )[:n]


# ─── Fetch aggregated languages ───────────────────────────────────────────────

def fetch_language_bytes(repos: list[dict]) -> dict[str, int]:
    """
    Call the languages endpoint for each repo and aggregate byte counts.
    Returns {language: total_bytes} sorted descending.
    """
    totals: dict[str, int] = {}
    for repo in repos:
        url = f"https://api.github.com/repos/{USERNAME}/{repo['name']}/languages"
        try:
            r = requests.get(url, headers=_headers(), timeout=15)
            if r.status_code == 200:
                for lang, b in r.json().items():
                    totals[lang] = totals.get(lang, 0) + b
        except requests.RequestException:
            continue
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


# ─── Render helpers ───────────────────────────────────────────────────────────

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


def lang_badge_inline(language: str | None) -> str:
    if not language:
        return ""
    colour = LANG_COLOURS.get(language, DEFAULT_COLOUR)
    logo   = LANG_LOGOS.get(language, language.lower().replace("+", "p").replace(" ", ""))
    return f"![{language}](https://img.shields.io/badge/{language.replace(' ', '_')}-{colour}?style=flat-square&logo={logo}&logoColor=white)"


def render_projects(repos: list[dict], commit_counts: dict[str, int] | None = None) -> str:
    """Render top repos as a Markdown table (2-column card layout)."""
    if not repos:
        return "_No repositories found._"

    # Emoji map by primary language
    EMOJI = {
        "Python": "🐍", "JavaScript": "🌐", "TypeScript": "💙",
        "C++": "⚡", "Shell": "🖥️", "PowerShell": "🔷",
        "HTML": "🌍", "CSS": "🎨", "Go": "🐹", "Rust": "🦀",
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
            stars    = repo.get("stargazers_count", 0)
            forks    = repo.get("forks_count", 0)
            emoji    = EMOJI.get(lang, "📦")
            lb       = lang_badge_inline(lang)
            star_b   = f"![Stars](https://img.shields.io/github/stars/{USERNAME}/{name}?style=flat-square&color=f59e0b)"
            fork_b   = f"![Forks](https://img.shields.io/github/forks/{USERNAME}/{name}?style=flat-square&color=6366f1)"
            commits  = (commit_counts or {}).get(name, 0)
            commit_b = (f"![Commits](https://img.shields.io/badge/my_commits-{commits}-7C3AED?style=flat-square&logo=git&logoColor=white)"
                        if commits else "")
            view_b   = f"[![Repo](https://img.shields.io/badge/View_Repo-181717?style=flat-square&logo=github&logoColor=white)]({url})"
            return (
                f"### {emoji} [{name}]({url})\n"
                f"> {desc}\n\n"
                f"{lb} {star_b} {fork_b} {commit_b}\n\n"
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


def render_last_updated() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f'<sub>🤖 Auto-updated by GitHub Actions · Last run: <b>{ts}</b></sub>'
    )


# ─── README rewriter ─────────────────────────────────────────────────────────

def replace_block(content: str, tag: str, new_body: str) -> str:
    """
    Replace everything between <!-- TAG_START --> and <!-- TAG_END -->
    (inclusive of the markers themselves).
    """
    pattern = (
        rf"<!-- {tag}_START -->.*?<!-- {tag}_END -->"
    )
    replacement = (
        f"<!-- {tag}_START -->\n{new_body}\n<!-- {tag}_END -->"
    )
    updated, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if n == 0:
        print(f"  ⚠  Warning: marker pair {tag}_START/END not found in README.",
              file=sys.stderr)
    return updated


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("📡 Fetching repositories…")
    repos = fetch_repos()
    print(f"   Found {len(repos)} public, non-fork repos.")

    print("🔢 Counting your commits per repo (this takes ~1s per repo)…")
    commit_counts = fetch_commit_counts(repos)

    print("🏆 Selecting top 6 repos by commit count…")
    best = top_repos(repos, commit_counts, n=6)
    for r in best:
        n = commit_counts.get(r["name"], 0)
        print(f"   • {r['name']}  ({n} commits)")

    print("📊 Aggregating language bytes…")
    lang_bytes = fetch_language_bytes(repos)
    top_langs  = list(lang_bytes.keys())[:10]
    print(f"   Top langs: {', '.join(top_langs)}")

    print(f"📝 Rewriting {README_PATH}…")
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_block(content, "SKILLS",       render_skills(lang_bytes))
    content = replace_block(content, "PROJECTS",     render_projects(best, commit_counts))
    content = replace_block(content, "LAST_UPDATED", render_last_updated())

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ README updated successfully.")


if __name__ == "__main__":
    main()