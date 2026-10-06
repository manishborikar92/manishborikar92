"""
update_readme.py
────────────────
Fetches live data from the GitHub REST API and rewrites the dynamic sections
of README.md between comment-block markers.

Dynamic sections updated:
  • <!-- SKILLS_START/END -->   — curated top languages aggregated across public repos
  • <!-- PROJECTS_START/END --> — top 6 repos ranked by commit count with pre-baked static shields

Usage:
  python update_readme.py
  python update_readme.py --dry-run
  python update_readme.py --no-svg

Requires:
  GITHUB_TOKEN  environment variable (highly recommended to avoid rate limits)
  requests      pip install -r requirements.txt
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone

# Force UTF-8 encoding for stdout/stderr to avoid UnicodeEncodeError on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── Config ──────────────────────────────────────────────────────────────────

USERNAME    = "manishborikar92"
README_PATH = "README.md"

# Repos to always exclude
EXCLUDE_REPOS = {USERNAME}

# Build, installer, and templating scripts excluded from core skills stack
EXCLUDE_LANGUAGES = {"Blade", "Batchfile", "Inno Setup", "Handlebars"}

# Language → badge colour (shields.io hex, no #)
LANG_COLOURS = {
    "Python":     "3776AB", "JavaScript": "F7DF1E", "TypeScript": "3178C6",
    "PHP":        "777BB4", "C++":        "00599C", "C":          "A8B9CC",
    "Java":       "ED8B00", "Go":         "00ADD8", "Rust":       "DEA584",
    "Shell":      "89E051", "HTML":       "E34F26", "CSS":        "1572B6",
    "Makefile":   "427819", "Dockerfile": "384D54", "PowerShell": "5391FE",
    "Ruby":       "CC342D", "Kotlin":     "7F52FF", "Swift":      "F05138",
    "Dart":       "0175C2", "R":          "276DC3", "MATLAB":     "e16737",
}
DEFAULT_COLOUR = "555555"

# Language → logo name for shields.io
LANG_LOGOS = {
    "JavaScript": "javascript", "TypeScript":  "typescript",
    "Python":     "python",     "C++":         "cplusplus",
    "PHP":        "php",        "Shell":       "gnubash",
    "Dockerfile": "docker",     "PowerShell":  "powershell",
    "HTML":       "html5",      "CSS":         "css3",
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
    if response.status_code in (403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset_ts = response.headers.get("X-RateLimit-Reset")
            reset_time = datetime.fromtimestamp(int(reset_ts)) if reset_ts else "soon"
            print(f"\n❌ API Rate Limit Exceeded! Resets at {reset_time}", file=sys.stderr)
            sys.exit(1)
        try:
            data = response.json()
            msg = data.get("message", "").lower()
            if "rate limit" in msg or "secondary rate" in msg:
                print(f"\n❌ GitHub Secondary Rate Limit: {data.get('message')}", file=sys.stderr)
                sys.exit(1)
        except Exception:
            pass

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
                            match = re.search(r'[&?]page=(\d+)', link)
                            if match:
                                repo_commits = int(match.group(1))
                            break
                    if repo_commits == 0:
                        repo_commits = len(r.json())
                else:
                    repo_commits = len(r.json())
            elif r.status_code == 409:
                repo_commits = 0
            else:
                r.raise_for_status()

            counts[name] = repo_commits
            print(f"   [{i:>2}/{total}] {name}: {repo_commits} commits")
            
        except requests.RequestException as e:
            print(f"   [{i:>2}/{total}] {name}: Error fetching commits - {e}", file=sys.stderr)
            counts[name] = 0
            
    return counts

def top_repos(repos: list[dict], commit_counts: dict[str, int], n: int = 6) -> list[dict]:
    """Rank repos purely by total commit count."""
    sorted_repos = sorted(
        repos,
        key=lambda r: int(commit_counts.get(r.get("name", ""), 0)),
        reverse=True,
    )
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

def render_skills(lang_bytes: dict[str, int], top_n: int = 10, exclude_langs: set[str] = EXCLUDE_LANGUAGES) -> str:
    """Produce a centred row of language badges for the top N languages, excluding build/installer scripts."""
    filtered_langs = [l for l in lang_bytes.keys() if l not in exclude_langs]
    langs = filtered_langs[:top_n]
    if not langs:
        return "_No language data found._"
    badges = []
    for lang in langs:
        colour = LANG_COLOURS.get(lang, DEFAULT_COLOUR)
        logo   = LANG_LOGOS.get(lang, lang.lower().replace("+", "p").replace(" ", ""))
        badges.append(badge(lang, lang, colour, logo))
    return '<div align="center">\n\n' + "\n".join(badges) + "\n\n</div>"

def render_projects(repos: list[dict], commit_counts: dict[str, int] | None = None) -> str:
    """Render top repos as a Markdown table (2-column card layout) using pre-baked static Shields badges."""
    if not repos:
        return "_No repositories found._"

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
            stars    = repo.get("stargazers_count", 0)
            forks    = repo.get("forks_count", 0)
            star_b   = f"![Stars](https://img.shields.io/badge/stars-{stars}-f59e0b?style=flat-square&logo=starship&logoColor=white)"
            fork_b   = f"![Forks](https://img.shields.io/badge/forks-{forks}-6366f1?style=flat-square&logo=git&logoColor=white)"
            commits  = (commit_counts or {}).get(name, 0)
            commit_b = (f"![Commits](https://img.shields.io/badge/commits-{commits}-7C3AED?style=flat-square&logo=git&logoColor=white)"
                        if commits else "")
            view_b   = f"[![View](https://img.shields.io/badge/View_Repository-181717?style=flat-square&logo=github&logoColor=white)]({url})"
            
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
    """Safely replaces content between markers using absolute string splitting."""
    start_marker = f"<" + f"!-- {tag}_START --" + ">"
    end_marker   = f"<" + f"!-- {tag}_END --" + ">"

    if start_marker not in content or end_marker not in content:
        print(f"  ⚠  Warning: marker pair {tag}_START/END not found in README.", file=sys.stderr)
        return content

    parts_before = content.split(start_marker)
    parts_after = parts_before[1].split(end_marker)

    before_section = parts_before[0]
    after_section = parts_after[1]

    return f"{before_section}{start_marker}\n{new_body}\n{end_marker}{after_section}"

def is_valid_svg(content: str) -> bool:
    """Validates that response content is genuine SVG and not an HTML error or challenge page."""
    if not content:
        return False
    c = content.strip().lower()
    if "<!doctype html" in c or "<html" in c:
        return False
    if not (c.startswith("<svg") or c.startswith("<?xml")):
        return False
    if "</svg>" not in c:
        return False
    error_keywords = ["error", "something went wrong", "please check your username", "rate limit", "limit exceeded"]
    if any(kw in c for kw in error_keywords):
        return False
    return True

def download_static_svgs(session: requests.Session):
    """Downloads static SVG files from stats endpoints to keep them locally cached."""
    dir_name = "profile-stats"
    os.makedirs(dir_name, exist_ok=True)

    urls = {
        "github-stats.svg": f"https://github-stats-extended.vercel.app/api?username={USERNAME}&show_icons=true&theme=midnight-purple&count_private=true&hide_border=true&bg_color=0d1117&title_color=A78BFA&icon_color=A78BFA&text_color=c9d1d9",
        "github-top-langs.svg": f"https://github-stats-extended.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&theme=midnight-purple&hide_border=true&bg_color=0d1117&title_color=A78BFA&text_color=c9d1d9&langs_count=8",
        "github-streak.svg": f"https://streak-stats.demolab.com?user={USERNAME}&theme=midnight-purple&hide_border=true&background=0d1117&stroke=A78BFA&ring=A78BFA&fire=F59E0B&currStreakLabel=A78BFA&sideLabels=A78BFA&dates=c9d1d9",
        "github-activity-graph.svg": f"https://github-readme-activity-graph.vercel.app/graph?username={USERNAME}&bg_color=0d1117&color=A78BFA&line=7C3AED&point=F59E0B&area=true&hide_border=true"
    }

    print("\n📥 Downloading static SVG cards…")
    for filename, url in urls.items():
        filepath = os.path.join(dir_name, filename)
        try:
            print(f"   Downloading {filename}…")
            r = session.get(url, timeout=20)
            if r.status_code == 200 and is_valid_svg(r.text):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(r.text)
                print(f"   ✅ Saved {filename}")
            else:
                print(f"   ⚠ WARNING: Failed or invalid {filename} (HTTP Status {r.status_code}) - Retaining existing cache.")
        except Exception as e:
            print(f"   ⚠ WARNING: Error downloading {filename} - {e} - Retaining existing cache.")

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Update GitHub profile README dynamic sections.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch data and preview output without writing files")
    parser.add_argument("--no-svg", action="store_true", help="Skip downloading static SVG cards")
    parser.add_argument("--readme", default=README_PATH, help="Path to README file (default: README.md)")
    args = parser.parse_args()

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
    curated_langs = [l for l in lang_bytes.keys() if l not in EXCLUDE_LANGUAGES][:10]
    print(f"   Top curated langs: {', '.join(curated_langs) if curated_langs else 'None found'}")

    skills_block = render_skills(lang_bytes)
    projects_block = render_projects(best, commit_counts)

    if args.dry_run:
        print("\n🔍 DRY RUN COMPLETE: Generated dynamic blocks without writing to disk.")
        return

    print(f"\n📝 Rewriting {args.readme}…")
    try:
        with open(args.readme, "r", encoding="utf-8") as f:
            content = f.read()

        content = replace_block(content, "SKILLS", skills_block)
        content = replace_block(content, "PROJECTS", projects_block)

        with open(args.readme, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ README updated successfully.")
    except FileNotFoundError:
        print(f"❌ Could not find {args.readme}. Make sure you are in the correct directory.", file=sys.stderr)

    if not args.no_svg:
        download_static_svgs(session)

if __name__ == "__main__":
    main()