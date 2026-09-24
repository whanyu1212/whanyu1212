"""Refresh the GitHub Stats lines in the profile card SVG.

Rewrites the values on the "Repos" and "Contributions (1y)" lines and
re-pads their dot leaders so each line keeps its width and the values stay
right-aligned. Nothing else in the SVG is touched.

    GITHUB_TOKEN=... python3 scripts/update_card_stats.py [path/to/card.svg]

A token is required for the GraphQL API (the Actions GITHUB_TOKEN works).
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = "whanyu1212"
CARD = Path(__file__).resolve().parent.parent / "pictures" / "profile-card.svg"

REPOS_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    contributionsCollection { contributionCalendar { totalContributions } }
  }
}
"""


def request(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def graphql(query, variables):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN (or GH_TOKEN) to query the GitHub GraphQL API")
    body = json.dumps({"query": query, "variables": variables}).encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    result = json.loads(request("https://api.github.com/graphql", body, headers))
    if "errors" in result:
        raise SystemExit(f"GraphQL error: {result['errors']}")
    return result["data"]


def profile_contributions():
    """The "N contributions in the last year" figure shown on the profile.

    The GraphQL calendar total can differ from what visitors see, so prefer the
    profile's own contribution graph and fall back to the API if it changes.
    """
    try:
        html = request(f"https://github.com/users/{USER}/contributions")
    except OSError:
        return None
    match = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    return int(match.group(1).replace(",", "")) if match else None


def fetch_stats():
    stars, after = 0, None
    while True:
        user = graphql(REPOS_QUERY, {"login": USER, "after": after})["user"]
        repos = user["repositories"]
        stars += sum(r["stargazerCount"] for r in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]
    contributions = profile_contributions()
    if contributions is None:
        contributions = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return {
        "repos": repos["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "contributions": contributions,
    }


def set_value(svg, key, value):
    """Replace a stat line's value and re-pad its dot leader to keep the line width."""
    pattern = re.compile(
        r'(<tspan class="key">' + re.escape(key) + r'</tspan><tspan class="txt">: </tspan>'
        r'<tspan class="dots">)(\.+) (</tspan><tspan class="val">)([^<]*)(</tspan>)'
    )
    match = pattern.search(svg)
    if not match:
        raise SystemExit(f'Could not find the "{key}" line in the card')
    dots = max(1, len(match.group(2)) + len(match.group(4)) - len(value))
    replacement = f"{match.group(1)}{'.' * dots} {match.group(3)}{value}{match.group(5)}"
    return svg[: match.start()] + replacement + svg[match.end() :]


def main():
    card = Path(sys.argv[1]) if len(sys.argv) > 1 else CARD
    stats = fetch_stats()
    svg = card.read_text()
    updated = set_value(svg, "Repos", f"{stats['repos']} | Stars: {stats['stars']}")
    updated = set_value(
        updated, "Contributions (1y)", f"{stats['contributions']:,} | Followers: {stats['followers']}"
    )
    if updated != svg:
        card.write_text(updated)
        print(f"Card stats updated: {stats}")
    else:
        print(f"Card stats already current: {stats}")


if __name__ == "__main__":
    main()
