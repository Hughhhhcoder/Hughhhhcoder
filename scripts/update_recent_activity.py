#!/usr/bin/env python3
"""Update the public-activity block in the profile README."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import urllib.request
from pathlib import Path


USERNAME = os.environ.get("GITHUB_USERNAME", "Hughhhhcoder")
README = Path(__file__).resolve().parents[1] / "README.md"
START = "<!-- RECENT_ACTIVITY:start -->"
END = "<!-- RECENT_ACTIVITY:end -->"
LAST_UPDATE = "<!-- RECENT_ACTIVITY:last_update -->"


def request_events() -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HughChaw-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/events/public?per_page=100",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return payload if isinstance(payload, list) else []


def markdown_text(value: str, limit: int = 72) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    value = value[: limit - 1] + "…" if len(value) > limit else value
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def event_link(event: dict) -> str:
    payload = event.get("payload") or {}
    for key in ("issue", "pull_request", "release"):
        item = payload.get(key)
        if isinstance(item, dict) and item.get("html_url"):
            return str(item["html_url"])
    repo = (event.get("repo") or {}).get("name", "")
    if event.get("type") == "PullRequestEvent" and payload.get("number"):
        return f"https://github.com/{repo}/pull/{payload['number']}"
    if event.get("type") == "IssuesEvent" and payload.get("issue", {}).get("number"):
        return f"https://github.com/{repo}/issues/{payload['issue']['number']}"
    return f"https://github.com/{repo}" if repo else "https://github.com/Hughhhhcoder"


def describe(event: dict) -> str | None:
    event_type = event.get("type", "")
    payload = event.get("payload") or {}
    repo = (event.get("repo") or {}).get("name", "").removeprefix(f"{USERNAME}/")
    repo_link = f"https://github.com/{event.get('repo', {}).get('name', '')}"
    full_repo = f"[{markdown_text(repo)}]({repo_link})" if repo else "a repository"
    target = event_link(event)

    if event_type == "PushEvent":
        count = len(payload.get("commits") or [])
        count = count or 1
        ref = str(payload.get("ref", "")).removeprefix("refs/heads/")
        suffix = f" on `{markdown_text(ref, 40)}`" if ref else ""
        return f"⬆️ Pushed {count} commit{'s' if count != 1 else ''} to {full_repo}{suffix}"
    if event_type == "CreateEvent" and payload.get("ref_type") == "repository":
        return f"📔 Created {full_repo}"
    if event_type == "ForkEvent":
        fork = (payload.get("forkee") or {}).get("full_name", "a new fork")
        return f"🔱 Forked {full_repo} into `{markdown_text(fork, 48)}`"
    if event_type == "WatchEvent":
        return f"⭐ Starred {full_repo}"
    if event_type == "ReleaseEvent":
        tag = (payload.get("release") or {}).get("tag_name", "a release")
        return f"🚀 Released `{markdown_text(tag, 40)}` from {full_repo}"
    if event_type == "IssuesEvent":
        issue = payload.get("issue") or {}
        action = payload.get("action", "updated")
        title = markdown_text(issue.get("title", "an issue"), 66)
        return f"{('🟢' if action == 'opened' else '✅' if action == 'closed' else '📝')} {action.title()} issue [{title}]({target}) in {full_repo}"
    if event_type == "PullRequestEvent":
        pull = payload.get("pull_request") or {}
        action = "merged" if pull.get("merged") else payload.get("action", "updated")
        number = pull.get("number") or payload.get("number")
        title = markdown_text(pull.get("title") or (f"PR #{number}" if number else "a pull request"), 66)
        icon = "🎉" if action == "merged" else "💪" if action == "opened" else "🔧"
        return f"{icon} {action.title()} PR [{title}]({target}) in {full_repo}"
    if event_type == "IssueCommentEvent":
        issue = payload.get("issue") or {}
        title = markdown_text(issue.get("title", "an issue"), 66)
        return f"💬 Commented on [{title}]({target}) in {full_repo}"
    if event_type == "PullRequestReviewEvent":
        pull = payload.get("pull_request") or {}
        title = markdown_text(pull.get("title", "a pull request"), 66)
        return f"🔎 Reviewed [{title}]({target}) in {full_repo}"
    return None


def format_date(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(dt.timezone.utc).strftime("%b %-d, %Y")
    except (TypeError, ValueError):
        return "recently"


def update_readme() -> None:
    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        raise RuntimeError("README activity markers are missing")
    items = []
    for event in events:
        description = describe(event)
        if description:
            items.append(f"- {description} · <sub>{format_date(event.get('created_at'))}</sub>")
        if len(items) == 5:
            break
    if not items:
        items = ["- No public activity to display yet."]
    block = "\n".join(items)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    content = pattern.sub(f"{START}\n{block}\n{END}", content, count=1)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("Updated %Y-%m-%d %H:%M UTC")
    content = re.sub(
        re.escape(LAST_UPDATE) + r".*?(?=\n\n|\n<|\Z)",
        f"{LAST_UPDATE}\n<sub>{html.escape(timestamp)}</sub>",
        content,
        count=1,
        flags=re.DOTALL,
    )
    README.write_text(content, encoding="utf-8")


events = request_events()
update_readme()
print(f"updated recent activity for {USERNAME}")
