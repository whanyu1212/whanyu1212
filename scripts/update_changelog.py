"""Rebuild the ~/changelog section of README.md from GitHub.

Takes the newest release from each project below plus the newest merged
upstream contribution, and keeps the three most recent. Everything between the
changelog markers in README.md is replaced; the rest of the file is untouched.

    GITHUB_TOKEN=... python3 scripts/update_changelog.py

The token is optional locally but avoids the unauthenticated rate limit.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- changelog:start -->", "<!-- changelog:end -->"

USER = "whanyu1212"
RELEASE_REPOS = ["gem-dota", "Wisp", "Krill.jl", "OpenCouch", "QuantRL-Lab"]
UPSTREAM = {"repo": "bojieli/ai-agent-book", "label": "ai-agent-book"}
ENTRIES = 3
MAX_SUMMARY = 200


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if token := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def first_sentence(body):
    """First sentence of the first prose paragraph, skipping headings, quotes and lists."""
    paragraphs = re.split(r"\n\s*\n", (body or "").replace("\r", ""))
    for para in paragraphs:
        lines = [l.strip() for l in para.splitlines() if l.strip()]
        if not lines or re.match(r"(#|>|[-*+] |\d+\. |\||```|<)", lines[0]):
            continue
        text = " ".join(lines)
        sentence = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text, maxsplit=1)[0]
        if len(sentence) > MAX_SUMMARY:
            sentence = sentence[:MAX_SUMMARY].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        return sentence
    return ""


def latest_releases():
    for repo in RELEASE_REPOS:
        releases = [r for r in api(f"repos/{USER}/{repo}/releases?per_page=5") if not r["draft"]]
        if not releases:
            continue
        rel = releases[0]
        yield {
            "date": rel["published_at"][:10],
            "title": f"{repo} {rel['tag_name']}",
            "url": rel["html_url"],
            "summary": first_sentence(rel["body"]) or (rel["name"] or "").strip(),
        }


def latest_upstream_pr():
    query = f"repo:{UPSTREAM['repo']}+author:{USER}+is:pr+is:merged"
    items = api(f"search/issues?q={query}&sort=updated&order=desc&per_page=10")["items"]
    if not items:
        return
    pr = max(items, key=lambda i: i["closed_at"])
    yield {
        "date": pr["closed_at"][:10],
        "title": f"{UPSTREAM['label']} #{pr['number']}",
        "url": pr["html_url"],
        "summary": f"Merged upstream: {pr['title'].strip().rstrip('.')}.",
    }


def render(entries):
    lines = [f"- **{e['date']} · [{e['title']}]({e['url']})** — {e['summary']}" for e in entries]
    return "\n".join(lines)


def main():
    entries = sorted([*latest_releases(), *latest_upstream_pr()], key=lambda e: e["date"], reverse=True)
    block = f"{START}\n{render(entries[:ENTRIES])}\n{END}"

    text = README.read_text()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md is missing the {START} / {END} markers")
    updated = pattern.sub(lambda _: block, text)
    if updated != text:
        README.write_text(updated)
        print("Changelog updated.")
    else:
        print("Changelog already current.")


if __name__ == "__main__":
    main()
