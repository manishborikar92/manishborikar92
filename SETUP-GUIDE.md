# 🚀 Dynamic GitHub Profile README — Complete Setup & Architecture Guide

Everything you need to understand, maintain, and automate your self-updating GitHub profile repository.

---

## Table of Contents

1. [How It All Works](#1-how-it-all-works)
2. [Files Overview](#2-files-overview)
3. [Folder Structure](#3-folder-structure)
4. [Prerequisites](#4-prerequisites)
5. [Step 1 — Local Development & Testing](#step-1--local-development--testing)
6. [Step 2 — GitHub Actions Permissions](#step-2--github-actions-permissions)
7. [Step 3 — Triggering Workflows](#step-3--triggering-workflows)
8. [How Automation Works After Setup](#how-automation-works-after-setup)
9. [What Is Dynamic vs Static](#what-is-dynamic-vs-static)
10. [Badge Architecture & Performance](#badge-architecture--performance)
11. [Customisation Reference](#customisation-reference)
12. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## 1. How It All Works

The profile automation is partitioned into three distinct, single-purpose GitHub Actions workflows:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        GitHub Actions Automation                       │
│                                                                        │
│  update_readme.yml (00:00 UTC daily + push to main)                   │
│  ├── update_readme.py                                                  │
│  │   ├── Calls GitHub REST API (authenticated with GITHUB_TOKEN)       │
│  │   ├── Counts total commits per repo (Link pagination trick)         │
│  │   ├── Aggregates language bytes across all public repos             │
│  │   ├── Curates top languages (excludes installer/build scripts)      │
│  │   ├── Ranks top 6 repos and generates pre-baked static shields      │
│  │   ├── Rewrites README.md between SKILLS and PROJECTS markers        │
│  │   └── Downloads and caches 4 dynamic SVG cards to profile-stats/    │
│  └── Commits + pushes "chore: auto-update README & stats [skip ci]"    │
│                                                                        │
│  snake.yml (00:15 UTC daily + manual dispatch)                         │
│  └── Generates contribution snake SVGs → pushes to 'output' branch     │
│                                                                        │
│  ci.yml (Pull Requests & feature branches)                             │
│  └── Runs flake8 linter, pytest suite, and --dry-run CLI check         │
└────────────────────────────────────────────────────────────────────────┘
```

Your **personal bio, header, stats layout, and contact links are preserved in the template** and are never modified by the script. Only the dynamic sections between comment markers and the cached SVG files are updated automatically.

---

## 2. Files Overview

| File | Purpose | Edit by hand? |
|------|---------|---------------|
| `README.md` | Profile template with static sections + comment markers | ✅ Yes — for bio/links |
| `update_readme.py` | Python script that fetches data, rewrites README, and caches SVGs | Only for config |
| `requirements.txt` | Runtime dependencies (`requests`, `urllib3`) | Only when adding deps |
| `requirements-dev.txt` | Development & CI dependencies (`pytest`, `flake8`) | Only when adding tools |
| `pytest.ini` | Pytest configuration file | Rare |
| `tests/test_update_readme.py` | Unit tests for parser, badges, ranking, and SVG validator | When modifying script |
| `.gitignore` | Prevents checking in virtualenvs, caches, and OS files | As needed |
| `.github/workflows/update_readme.yml` | Updates README and caches stats SVGs (00:00 UTC daily) | No |
| `.github/workflows/snake.yml` | Generates contribution snake SVGs (00:15 UTC daily) | No |
| `.github/workflows/ci.yml` | CI pipeline running linting and tests on Pull Requests | No |

---

## 3. Folder Structure

Your repository is structured as follows:

```
manishborikar92/
├── .gitignore
├── pytest.ini
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── SETUP-GUIDE.md
├── update_readme.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── snake.yml
│       └── update_readme.yml
├── profile-stats/
│   ├── github-activity-graph.svg
│   ├── github-stats.svg
│   ├── github-streak.svg
│   └── github-top-langs.svg
└── tests/
    └── test_update_readme.py
```

---

## 4. Prerequisites

- Python 3.10+ installed
- Git installed (`git --version` to check)
- GitHub repository named `manishborikar92` matching your GitHub username

---

## Step 1 — Local Development & Testing

You can run the updater script and test suite locally:

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Run unit tests
pytest

# 3. Test the script in dry-run mode (preview without writing to README or downloading SVGs)
python update_readme.py --dry-run

# 4. Update README without re-downloading SVGs
python update_readme.py --no-svg

# 5. Full run (requires GITHUB_TOKEN env var for full API quota)
python update_readme.py
```

---

## Step 2 — GitHub Actions Permissions

Ensure GitHub Actions has permission to push automated updates:

1. Go to `https://github.com/manishborikar92/manishborikar92`
2. Click **Settings** → **Actions** → **General**
3. Under **Workflow permissions**, select **Read and write permissions**
4. Click **Save**

---

## Step 3 — Triggering Workflows

Workflows run automatically on schedule, but you can trigger them manually:

1. Go to `https://github.com/manishborikar92/manishborikar92/actions`
2. Select **Update Dynamic README** or **Generate Contribution Snake**
3. Click **Run workflow** → select branch `main` → click **Run workflow**

---

## How Automation Works After Setup

| Trigger | Workflow | What happens |
|---------|----------|-------------|
| **Daily 00:00 UTC** | `update_readme.yml` | Refreshes project rankings, skills, and locally cached stats SVGs. Pushes single `[skip ci]` commit. |
| **Daily 00:15 UTC** | `snake.yml` | Regenerates snake animation and pushes to `output` branch. |
| **Push to main** (README/code) | `update_readme.yml` | Re-runs updater immediately so manual template edits take effect right away. (Snake job is NOT run on push). |
| **Pull Request to main** | `ci.yml` | Runs `flake8`, `pytest`, and `--dry-run` to ensure code changes don't break production. |
| **Manual Dispatch** | Any workflow | Runs on demand via GitHub Actions UI. |

---

## 9. What Is Dynamic vs Static

### 🔒 Static (hardcoded — edit these yourself in README.md)
- Name, pronouns, roles, location
- `building`, `focus`, `currently`, `philosophy`, `fun_fact` in `whoami`
- Social and contact links (LinkedIn, Email, GitHub)
- Overall layout, markdown tables, and headers

### ⚡ Dynamic (auto-updated by GitHub Actions — do not edit manually)
- **Top 6 featured projects**: Ranked by commit count; updated daily.
- **Skill badges**: Curated top languages by aggregated byte count; updated daily.
- **Locally cached stats cards**: SVGs in `profile-stats/` refreshed daily.
- **Contribution snake**: Animated SVG in `output` branch refreshed daily.

---

## 10. Badge Architecture & Performance

### Pre-baked Static Shields vs Dynamic Shields

In the featured projects section, badges for Stars and Forks use a **pre-baked static Shields approach**:

```markdown
<!-- Pre-baked Static Badge (Used in this repository) -->
![Stars](https://img.shields.io/badge/stars-2-f59e0b?style=flat-square&logo=starship&logoColor=white)
![Forks](https://img.shields.io/badge/forks-0-6366f1?style=flat-square&logo=git&logoColor=white)
```

**How it works & why it's better:**
1. **No Live GitHub API Dependency on Page Visits**: Traditional dynamic shields (`img.shields.io/github/stars/...`) cause Shields.io to query GitHub's REST API on *every visitor page load*. With 6 projects and 2 metrics each, that caused 12 live external API hops per visitor, leading to Shields.io rate limits and broken image icons.
2. **Pre-baked Values**: The Python updater script already fetches `stargazers_count` and `forks_count` in its daily API pass. It embeds these exact numbers directly into static badge URLs (`badge/stars-2-f59e0b`).
3. **Served by Shields.io CDN**: Badge images are still rendered and served by Shields.io, but Shields.io serves them instantly from cache without making upstream GitHub API calls.
4. **Visually Indistinguishable**: Visitors see the exact same layout, icons, colors, and fonts, but the page loads faster and never breaks.

---

## 11. Customisation Reference

### Change how many top projects are shown
In `update_readme.py`:
```python
best = top_repos(repos, commit_counts, n=6)   # change 6 to any number
```

### Exclude a repo from projects
In `update_readme.py`:
```python
EXCLUDE_REPOS = {"manishborikar92", "hidden-repo"}
```

### Exclude a language from skills
In `update_readme.py`:
```python
EXCLUDE_LANGUAGES = {"Blade", "Batchfile", "Inno Setup", "Handlebars"}
```

### Add or change language badge colors
In `update_readme.py`:
```python
LANG_COLOURS = {
    "PHP": "777BB4",
    "Python": "3776AB",
    # ...
}
```

---

## 12. Troubleshooting & FAQ

### ❌ Workflow fails with "exit code 128"
**Cause:** GitHub Actions lacks write permissions to push commits.  
**Fix:** Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.

### ❌ Tests fail locally with coverage error
**Cause:** Outdated global `pytest-cov` installed in user site-packages.  
**Fix:** The repository includes a `pytest.ini` with `addopts = -p no:cov` which automatically resolves this.

### ❌ Rate limit warnings in local runs
**Cause:** GitHub limits unauthenticated REST API calls to 60/hour per IP.  
**Fix:** Set your `GITHUB_TOKEN` environment variable before running locally:
```bash
# PowerShell
$env:GITHUB_TOKEN="ghp_your_token_here"
python update_readme.py
```
*(In GitHub Actions, `GITHUB_TOKEN` is automatically supplied with higher quotas).*

---

*Last updated: October 2026 · Automated with GitHub Actions*
