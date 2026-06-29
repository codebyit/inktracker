#!/usr/bin/env python3
"""Generate and push the InkTrack GitHub Wiki from docs/.

Usage:
    python scripts/sync_wiki.py            # build wiki content into build/wiki
    python scripts/sync_wiki.py --push     # build, then clone+push to the wiki repo

The wiki is the single-source mirror of docs/: numbered user-guide pages become
wiki pages, docs/README.md becomes Home, and a _Sidebar.md is generated. Images
are copied as-is and referenced relatively (GitHub wiki supports subfolders).

Requires the wiki to be enabled and initialized once (create any page in the
GitHub UI) before --push will succeed.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO_ROOT, "docs")
BUILD = os.path.join(REPO_ROOT, "build", "wiki")
WIKI_REMOTE = "git@github.com:codebyit/inktracker.wiki.git"


def rmtree(path: str) -> None:
    """Remove a tree, tolerating read-only files and transient locks (Windows/OneDrive)."""
    if not os.path.isdir(path):
        return

    def on_error(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    for _ in range(5):
        try:
            shutil.rmtree(path, onexc=on_error)
            return
        except (PermissionError, OSError):
            time.sleep(0.5)
    shutil.rmtree(path, onexc=on_error)


GUIDES = [
    "01-getting-started.md",
    "02-dashboard.md",
    "03-new-project-wizard.md",
    "04-projects.md",
    "05-service-maintenance.md",
    "06-inventory.md",
    "07-analytics.md",
    "08-settings.md",
    "09-documentation-links.md",
    "10-tips-faq.md",
]


def page_name(filename: str) -> str:
    """docs filename -> wiki page name (README -> Home)."""
    if filename.lower() == "readme.md":
        return "Home"
    slug = filename[:-3] if filename.endswith(".md") else filename
    return "-".join(w.capitalize() for w in slug.split("-"))


def convert_links(text: str) -> str:
    def repl(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith("images/") or "://" in target:
            return m.group(0)
        return f"[{label}]({page_name(target)})"

    return re.sub(r"\[([^\]]+)\]\((\d{2}-[\w-]+\.md|README\.md)\)", repl, text)


def build() -> None:
    if os.path.isdir(BUILD):
        rmtree(BUILD)
    os.makedirs(BUILD)
    for f in GUIDES + ["README.md"]:
        text = convert_links(open(os.path.join(DOCS, f), encoding="utf-8").read())
        open(os.path.join(BUILD, page_name(f) + ".md"), "w", encoding="utf-8").write(text)
    shutil.copytree(os.path.join(DOCS, "images"), os.path.join(BUILD, "images"))
    sidebar = ["## InkTrack Manual\n", "- [Home](Home)"]
    for f in GUIDES:
        title = open(os.path.join(DOCS, f), encoding="utf-8").readline().lstrip("# ").strip()
        sidebar.append(f"- [{title}]({page_name(f)})")
    open(os.path.join(BUILD, "_Sidebar.md"), "w", encoding="utf-8").write("\n".join(sidebar) + "\n")
    print(f"Built {len(GUIDES) + 2} wiki pages into {BUILD}")


def push() -> None:
    work = os.path.join(REPO_ROOT, "build", "wiki-repo")
    if os.path.isdir(work):
        rmtree(work)
    if subprocess.run(["git", "clone", WIKI_REMOTE, work]).returncode != 0:
        sys.exit("Wiki not initialized. Enable it and create one page in the GitHub UI, then retry.")
    for item in os.listdir(work):
        if item != ".git":
            p = os.path.join(work, item)
            rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(BUILD, work, dirs_exist_ok=True)
    subprocess.run(["git", "-C", work, "add", "-A"], check=True)
    subprocess.run(["git", "-C", work, "commit", "-m", "docs: sync user manual to wiki"], check=True)
    subprocess.run(["git", "-C", work, "push", "origin", "HEAD"], check=True)
    print("Pushed wiki.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()
    build()
    if args.push:
        push()
