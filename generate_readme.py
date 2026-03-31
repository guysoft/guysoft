#!/usr/bin/env python3
"""Generate README.md from template using GitHub API and RSS feed."""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

GITHUB_USERNAME = "guysoft"
TEMPLATE_PATH = "templates/README.md.tpl"
CONFIG_PATH = "config.yml"
OUTPUT_PATH = "README.md"
RSS_URL = "https://guysoft.wordpress.com/feed/"

CONTRIBUTIONS_QUERY = """
query {
  user(login: "%s") {
    repositoriesContributedTo(
      first: 7
      orderBy: {field: PUSHED_AT, direction: DESC}
      contributionTypes: [COMMIT, PULL_REQUEST, ISSUE]
      includeUserRepositories: true
    ) {
      nodes {
        nameWithOwner
        url
        description
        pushedAt
      }
    }
    repositories(
      first: 30
      orderBy: {field: PUSHED_AT, direction: DESC}
      ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]
    ) {
      nodes {
        nameWithOwner
        url
        description
        latestRelease {
          tagName
          url
          publishedAt
        }
      }
    }
  }
}
""" % GITHUB_USERNAME


def github_graphql(query):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "readme-generator",
    }
    if token:
        headers["Authorization"] = f"bearer {token}"

    data = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=data, headers=headers
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())

    if "errors" in result:
        print(f"GraphQL errors: {result['errors']}", file=sys.stderr)
        sys.exit(1)
    return result["data"]


def github_rest(endpoint):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"User-Agent": "readme-generator", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(
        f"https://api.github.com/{endpoint}", headers=headers
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def humanize(iso_timestamp):
    """Convert ISO timestamp to human-readable relative time like '2 days ago'."""
    if not iso_timestamp:
        return "unknown"
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = now - dt

    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


def fetch_contributions():
    data = github_graphql(CONTRIBUTIONS_QUERY)
    user = data["user"]

    contributions = []
    for repo in user["repositoriesContributedTo"]["nodes"]:
        contributions.append({
            "name": repo["nameWithOwner"],
            "url": repo["url"],
            "description": repo.get("description") or "No description",
            "pushed_at": repo["pushedAt"],
        })

    releases = []
    for repo in user["repositories"]["nodes"]:
        rel = repo.get("latestRelease")
        if rel:
            releases.append({
                "name": repo["nameWithOwner"],
                "url": repo["url"],
                "description": repo.get("description") or "No description",
                "tag": rel["tagName"],
                "release_url": rel["url"],
                "published_at": rel["publishedAt"],
            })

    releases.sort(key=lambda r: r["published_at"] or "", reverse=True)
    return contributions[:7], releases[:10]


def fetch_rss(url, count=5):
    req = urllib.request.Request(url, headers={"User-Agent": "readme-generator"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        tree = ET.parse(resp)

    root = tree.getroot()
    items = []

    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        if pub_date:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub_date)
                pub_iso = dt.isoformat()
            except Exception:
                pub_iso = pub_date
        else:
            pub_iso = ""

        items.append({"title": title, "url": link, "published_at": pub_iso})
        if len(items) >= count:
            break

    return items


def parse_config(path):
    """Parse the simple config.yml to extract pinned_repos list."""
    repos = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                repos.append(line[2:].strip())
    return repos


def fetch_pinned_repos(repo_slugs):
    lines = []
    for slug in repo_slugs:
        try:
            info = github_rest(f"repos/{slug}")
            desc = info.get("description") or "No description"
            stars = info.get("stargazers_count", 0)
            lines.append(
                f"- [{info['full_name']}]({info['html_url']}) - {desc} ⭐ {stars}"
            )
        except Exception as e:
            print(f"Warning: could not fetch {slug}: {e}", file=sys.stderr)
    return "\n".join(lines)


def build_contributions_section(contributions):
    lines = []
    for c in contributions:
        lines.append(
            f"- [{c['name']}]({c['url']}) - {c['description']} ({humanize(c['pushed_at'])})"
        )
    return "\n".join(lines)


def build_releases_section(releases):
    lines = []
    for r in releases:
        lines.append(
            f"- [{r['name']}]({r['url']}) ([{r['tag']}]({r['release_url']}), "
            f"{humanize(r['published_at'])}) - {r['description']}"
        )
    return "\n".join(lines)


def build_blog_section(posts):
    lines = []
    for p in posts:
        lines.append(f"- [{p['title']}]({p['url']}) ({humanize(p['published_at'])})")
    return "\n".join(lines)


def main():
    print("Fetching GitHub data...")
    contributions, releases = fetch_contributions()
    print(f"  {len(contributions)} contributions, {len(releases)} releases")

    print("Fetching RSS feed...")
    posts = fetch_rss(RSS_URL)
    print(f"  {len(posts)} blog posts")

    print("Fetching pinned repos...")
    pinned_slugs = parse_config(CONFIG_PATH)
    pinned_md = fetch_pinned_repos(pinned_slugs)
    print(f"  {len(pinned_slugs)} pinned repos")

    template = Path(TEMPLATE_PATH).read_text()

    readme = template
    readme = readme.replace("<!-- PINNED_REPOS -->", pinned_md)
    readme = readme.replace("<!-- CONTRIBUTIONS -->", build_contributions_section(contributions))
    readme = readme.replace("<!-- RELEASES -->", build_releases_section(releases))
    readme = readme.replace("<!-- BLOG_POSTS -->", build_blog_section(posts))

    Path(OUTPUT_PATH).write_text(readme)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
