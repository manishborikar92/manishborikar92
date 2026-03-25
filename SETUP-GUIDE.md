# 🚀 Dynamic GitHub Profile README — Complete Setup Guide

Everything you need to go from zero to a fully automated, self-updating GitHub profile. Follow the steps in order — no steps are optional unless explicitly marked.

---

## Table of Contents

1. [How It All Works](#1-how-it-all-works)
2. [Files Overview](#2-files-overview)
3. [Folder Structure](#3-folder-structure)
4. [Prerequisites](#4-prerequisites)
5. [Step 1 — Clone Your Profile Repo](#step-1--clone-your-profile-repo)
6. [Step 2 — Add the Files](#step-2--add-the-files)
7. [Step 3 — Configure GitHub Actions Permissions](#step-3--configure-github-actions-permissions)
8. [Step 4 — Push Everything to GitHub](#step-4--push-everything-to-github)
9. [Step 5 — Trigger the Workflow Manually](#step-5--trigger-the-workflow-manually)
10. [Step 6 — Verify It Worked](#step-6--verify-it-worked)
11. [How Automation Works After Setup](#how-automation-works-after-setup)
12. [What Is Dynamic vs Static](#what-is-dynamic-vs-static)
13. [Customisation Reference](#customisation-reference)
14. [Troubleshooting](#troubleshooting)

---

## 1. How It All Works

```
┌──────────────────────────────────────────────────────────┐
│                   GitHub Actions (daily)                 │
│                                                          │
│  update_readme.py                                        │
│  ├── Calls GitHub REST API                               │
│  │   ├── Fetches all your public repos                   │
│  │   ├── Counts YOUR commits per repo (Link header trick)│
│  │   └── Aggregates language bytes across all repos      │
│  │                                                       │
│  ├── Ranks top 6 repos by your commit count              │
│  ├── Builds skill badges from real language data         │
│  └── Rewrites README.md between comment markers          │
│      └── Commits + pushes "chore: auto-update README"    │
│                                                          │
│  snake job (parallel)                                    │
│  └── Generates contribution snake SVG → output branch    │
└──────────────────────────────────────────────────────────┘
```

Your **personal information is hardcoded** in the README template and never touched by the script. Everything else — skills, top projects, stats, snake — updates automatically every day at 06:00 UTC.

---

## 2. Files Overview

| File | Purpose | Edit by hand? |
|------|---------|---------------|
| `README.md` | Profile template with static info + comment markers | ✅ Yes — for personal info only |
| `update_readme.py` | Python script that fetches GitHub data and rewrites README | Only for config changes |
| `requirements.txt` | Python dependencies (`requests`) | No |
| `.github/workflows/update_readme.yml` | GitHub Actions workflow — runs daily + on push | No |

---

## 3. Folder Structure

Your `manishborikar92` repository must look exactly like this after setup:

```
manishborikar92/              ← root of the repo
├── README.md
├── update_readme.py
├── requirements.txt
└── .github/
    └── workflows/
        └── update_readme.yml
```

> ⚠️ The `.github/workflows/` folder path is **case-sensitive** and must be exact.
> On Windows, Git respects the casing — do not rename it.

---

## 4. Prerequisites

- Git installed on your machine (`git --version` to check)
- A terminal / command prompt
- The 4 files provided:
  - `README.md`
  - `update_readme.py`
  - `requirements.txt`
  - `update_readme.yml` (goes inside `.github/workflows/`)

---

## Step 1 — Clone Your Profile Repo

Open a terminal and run:

```bash
git clone https://github.com/manishborikar92/manishborikar92.git
cd manishborikar92
```

This downloads your existing profile repo to your machine so you can add files to it.

---

## Step 2 — Add the Files

### 2a — Copy the root-level files

Place these three files directly in the repo root (replacing the existing `README.md`):

```
README.md           → manishborikar92/README.md
update_readme.py    → manishborikar92/update_readme.py
requirements.txt    → manishborikar92/requirements.txt
```

### 2b — Create the workflows folder and add the workflow

The `.github/workflows/` folder likely does not exist yet. Create it:

**On Mac / Linux:**
```bash
mkdir -p .github/workflows
```

**On Windows (Command Prompt):**
```cmd
mkdir .github\workflows
```

**On Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force -Path .github\workflows
```

Then copy `update_readme.yml` into it:

```
update_readme.yml  →  manishborikar92/.github/workflows/update_readme.yml
```

### 2c — Verify the structure

```bash
# Mac/Linux
find . -not -path './.git/*' | sort

# Windows PowerShell
Get-ChildItem -Recurse | Where-Object { $_.FullName -notlike '*\.git\*' }
```

Expected output:
```
.
./README.md
./requirements.txt
./update_readme.py
./.github
./.github/workflows
./.github/workflows/update_readme.yml
```

---

## Step 3 — Configure GitHub Actions Permissions

This is the **most commonly missed step** — without it the workflow will fail with exit code 128.

1. Go to `https://github.com/manishborikar92/manishborikar92`
2. Click **Settings** (the tab in your repo, not your account settings)
3. In the left sidebar, click **Actions** → **General**
4. Scroll down to the **Workflow permissions** section
5. Select **Read and write permissions**
6. Click **Save**

```
Settings → Actions → General → Workflow permissions
                                ● Read and write permissions  ← select this
                                ○ Read repository contents...
                                              [Save]
```

---

## Step 4 — Push Everything to GitHub

Back in your terminal (inside the `manishborikar92` folder):

```bash
# Stage all new and changed files
git add .

# Verify what's staged — should show README.md,
# update_readme.py, requirements.txt, and the workflow file
git status

# Commit
git commit -m "feat: add dynamic README automation"

# Push to GitHub
git push origin main
```

> If your default branch is `master` instead of `main`, use `git push origin master`.

---

## Step 5 — Trigger the Workflow Manually

The workflow is scheduled to run daily at 06:00 UTC, but you need to trigger it **once manually** right now to populate the dynamic sections for the first time.

1. Go to `https://github.com/manishborikar92/manishborikar92/actions`
2. In the left sidebar, click **"Update Dynamic README"**
3. Click the **"Run workflow"** dropdown button (top right of the table)
4. Leave branch as `main`
5. Click the green **"Run workflow"** button

```
Actions → Update Dynamic README → Run workflow ▼ → Run workflow
```

The workflow will now start. You will see it appear in the list with a yellow spinner (running).

---

## Step 6 — Verify It Worked

### 6a — Check the workflow run succeeded

1. Click the running workflow to open it
2. You should see two jobs: **"Refresh projects & skills"** and **"Refresh contribution snake"**
3. Both should show a green ✅ checkmark within ~60 seconds
4. Click **"Refresh projects & skills"** → expand **"Run updater script"** to see the live log:

```
📡 Fetching repositories…
   Found 18 public, non-fork repos.
🔢 Counting your commits per repo…
   [ 1/18] Song-Recognition-Bot: 47 commits
   [ 2/18] pointviz: 31 commits
   ...
🏆 Selecting top 6 repos by commit count…
   • Song-Recognition-Bot  (47 commits)
   • pointviz  (31 commits)
   ...
📊 Aggregating language bytes…
   Top langs: Python, JavaScript, TypeScript, ...
📝 Rewriting README.md…
✅ README updated successfully.
```

### 6b — Check your profile

Go to `https://github.com/manishborikar92`

You should now see:
- ✅ Animated wave banner at the top
- ✅ Typing animation
- ✅ `> tech_stack --core` section filled with real language badges
- ✅ `> projects --featured` section showing your 6 most-committed repos as cards
- ✅ GitHub stats and streak cards
- ✅ Contribution activity graph
- ✅ Contribution snake animation (from the `output` branch)
- ✅ "Auto-updated by GitHub Actions · Last run: YYYY-MM-DD HH:MM UTC" at the bottom

> **If the profile page looks unchanged:** hard-refresh with `Ctrl+Shift+R` (Mac: `Cmd+Shift+R`) or open an incognito window. GitHub caches profile pages aggressively.

---

## How Automation Works After Setup

Once set up, you never need to touch anything again. The workflow fires automatically in three situations:

| Trigger | When | What happens |
|---------|------|-------------|
| **Daily schedule** | Every day at 06:00 UTC | Full refresh — new repos, updated commit counts, updated languages |
| **Push to main** | When you edit `README.md` or `update_readme.py` | Re-runs immediately so you see changes fast |
| **Manual dispatch** | Whenever you click "Run workflow" | Full refresh on demand |

Each successful run commits a single `chore: auto-update README [skip ci]` commit to your repo. The `[skip ci]` tag prevents that commit from triggering another workflow run (avoiding an infinite loop).

---

## What Is Dynamic vs Static

### 🔒 Static (hardcoded — edit these yourself in README.md)

| Content | Location in README.md |
|---------|----------------------|
| Your name | `whoami` code block |
| Pronouns | `whoami` code block |
| Role titles | `whoami` code block |
| Location | `whoami` code block |
| What you're building/learning | `whoami` code block |
| Fun fact | `whoami` code block |
| LinkedIn URL | Badge in header |
| Email address | Badge in header |

### ⚡ Dynamic (auto-updated by the script — do not edit manually)

| Content | Source | Updates |
|---------|--------|---------|
| Top 6 projects | GitHub API — your commit count per repo | Daily |
| Skill badges | GitHub API — language bytes across all repos | Daily |
| Last updated timestamp | Script runtime | Every run |
| Stats card (commits, stars, PRs) | github-readme-stats CDN | Every page load |
| Top languages card | github-readme-stats CDN | Every page load |
| Streak counter | streak-stats CDN | Every page load |
| Activity graph | github-readme-activity-graph CDN | Every page load |
| Contribution snake | GitHub Actions → `output` branch SVG | Daily |

---

## Customisation Reference

### Change your personal info

Open `README.md` and edit the `whoami` Python code block directly. The script never touches this section.

### Change how many top projects are shown

Open `update_readme.py`, find line 29 area — the call in `main()`:

```python
best = top_repos(repos, commit_counts, n=6)   # change 6 to any number
```

### Exclude a repo from appearing in projects

Open `update_readme.py`, find `EXCLUDE_REPOS` near the top:

```python
EXCLUDE_REPOS = {"manishborikar92"}
```

Add any repo names you want to hide:

```python
EXCLUDE_REPOS = {"manishborikar92", "old-experiment", "forked-repo"}
```

### Change how many languages appear in the skills section

In `update_readme.py`, find the `render_skills` call in `main()`:

```python
content = replace_block(content, "SKILLS", render_skills(lang_bytes))
```

The `render_skills` function defaults to `top_n=10`. Pass a different value:

```python
content = replace_block(content, "SKILLS", render_skills(lang_bytes, top_n=8))
```

### Change the workflow schedule

Open `.github/workflows/update_readme.yml` and edit the cron expression:

```yaml
schedule:
  - cron: "0 6 * * *"   # daily at 06:00 UTC
```

Cron format: `minute hour day month weekday`

Examples:
- `"0 0 * * *"` — midnight UTC daily
- `"0 12 * * 1"` — every Monday at noon UTC
- `"0 6 * * 1,4"` — every Monday and Thursday at 06:00 UTC

---

## Troubleshooting

### ❌ Workflow fails with "exit code 128"
**Cause:** GitHub Actions doesn't have write permission to push commits.
**Fix:** Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save. Then re-run the workflow.

---

### ❌ Workflow fails with "Node.js 20 deprecated" warning
**Cause:** GitHub Actions is transitioning from Node.js 20 to Node.js 24. Node.js 20 will be completely removed on September 16, 2026.
**Fix:** The provided workflow file uses the latest action versions that support Node.js 24:
- `actions/checkout@v6` (Node.js 24 runtime - requires Actions Runner v2.327.1+)
- `actions/setup-python@v6` (Node.js 24 runtime - requires Actions Runner v2.327.1+)
- `crazy-max/ghaction-github-pages@v5` (Node.js 24 runtime - requires Actions Runner v2.327.1+)

These versions are already configured in the workflow and will work without warnings. GitHub-hosted runners already meet the minimum version requirement.

---

### ❌ Skills or projects section still shows the placeholder text
**Cause:** The workflow hasn't successfully run yet, or the comment markers in `README.md` were accidentally edited.
**Fix:** Check the Actions tab for errors. If the markers are missing, re-upload the original `README.md` template (the comment markers `<!-- SKILLS_START -->` etc. must be present exactly as written).

---

### ❌ Snake animation shows a broken image
**Cause:** The `output` branch doesn't exist yet — the snake job hasn't run successfully.
**Fix:** Go to Actions → "Update Dynamic README" → Run workflow. After it succeeds, check that an `output` branch appears in your repo's branch list. Then hard-refresh your profile.

---

### ❌ Profile page doesn't show the README at all
**Cause:** The repo must be **public** and named exactly `manishborikar92` (matching your username).
**Fix:** Go to the repo → Settings → scroll to "Danger Zone" → Change visibility → Make public.

---

### ❌ Stats card shows "Something went wrong / Could not fetch total commits"
**Cause:** `include_all_commits=true` was added to the stats card URL. This causes rate-limit failures.
**Fix:** The current `README.md` does **not** include this parameter. If you added it manually, remove it. The correct URL ends with `&text_color=c9d1d9` — no `include_all_commits`.

---

### ❌ Commit counts all show 0 in the Actions log
**Cause:** The `GITHUB_TOKEN` wasn't passed to the script, or the API is rate-limiting unauthenticated requests.
**Fix:** Verify the workflow step includes:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
This is already in the provided `update_readme.yml`. If you edited the file, check it's still there.

---

*Last updated: March 2026 · Works with GitHub REST API v2022-11-28*
