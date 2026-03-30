#!/usr/bin/env python3
"""Generate stylish animated profile SVG assets for README (dark/light)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

API_BASE = "https://api.github.com"
USER_AGENT = "profile-ui-generator/1.0"

THEMES = {
    "dark": {
        "bg0": "#020617",
        "bg1": "#081226",
        "bg2": "#062c30",
        "panel": "#0b1220",
        "panel2": "#0f172a",
        "stroke": "#1f2a44",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "accent": "#22d3ee",
        "accent2": "#38bdf8",
        "accent3": "#14b8a6",
        "good": "#22c55e",
        "warn": "#f59e0b",
        "chip_bg": "#0f172a",
        "grid": "#0ea5e9",
        "scan": "#22d3ee",
        "palette": ["#22d3ee", "#38bdf8", "#14b8a6", "#0ea5e9", "#2dd4bf", "#06b6d4", "#10b981", "#60a5fa"],
    },
    "light": {
        "bg0": "#f8fafc",
        "bg1": "#f1f5f9",
        "bg2": "#e0f2fe",
        "panel": "#ffffff",
        "panel2": "#f8fafc",
        "stroke": "#cbd5e1",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0284c7",
        "accent2": "#0ea5e9",
        "accent3": "#0f766e",
        "good": "#16a34a",
        "warn": "#b45309",
        "chip_bg": "#eef2ff",
        "grid": "#93c5fd",
        "scan": "#0ea5e9",
        "palette": ["#0284c7", "#0ea5e9", "#0f766e", "#2563eb", "#14b8a6", "#0891b2", "#22c55e", "#38bdf8"],
    },
}


@dataclass
class Repo:
    name: str
    description: str
    language: str
    size_kb: int
    stars: int
    forks: int
    pushed_at: dt.datetime | None
    private: bool
    html_url: str


@dataclass
class ProfileData:
    username: str
    display_name: str
    bio: str
    followers: int
    following: int
    public_repos: int
    total_repos_scanned: int
    private_repos_scanned: int
    total_stars: int
    total_forks: int
    active_30d: int
    language_rows: List[Tuple[str, float]]
    top_repos: List[Repo]
    month_labels: List[str]
    month_values: List[int]
    generated_at: dt.datetime


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fetch_json(url: str, token: str | None) -> object:
    cmd = [
        "curl",
        "-sS",
        "-L",
        "--connect-timeout",
        "20",
        "--max-time",
        "45",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        f"User-Agent: {USER_AGENT}",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
    ]
    if token:
        cmd.extend(["-H", f"Authorization: Bearer {token}"])
    cmd.extend([url, "-w", "\n%{http_code}"])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "curl request failed")

    if "\n" not in proc.stdout:
        raise RuntimeError("unexpected curl output")
    body, status_str = proc.stdout.rsplit("\n", 1)
    try:
        status = int(status_str.strip())
    except ValueError as exc:
        raise RuntimeError("could not parse HTTP status") from exc
    if status >= 400:
        raise RuntimeError(f"http {status}: {url}")
    return json.loads(body)


def safe_fetch_json(url: str, token: str | None) -> object | None:
    try:
        return fetch_json(url, token)
    except Exception as exc:
        print(f"warning: {exc}")
        return None


def fetch_user(username: str, token: str | None) -> dict:
    data = safe_fetch_json(f"{API_BASE}/users/{username}", token)
    if isinstance(data, dict):
        return data
    return {
        "name": username,
        "bio": "",
        "followers": 0,
        "following": 0,
        "public_repos": 0,
    }


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_repositories(username: str, token: str | None, include_private: bool) -> List[dict]:
    repos: List[dict] = []
    page = 1
    use_private_endpoint = bool(include_private and token)

    while True:
        if use_private_endpoint:
            url = (
                f"{API_BASE}/user/repos"
                f"?per_page=100&page={page}&visibility=all&affiliation=owner&sort=updated"
            )
        else:
            url = (
                f"{API_BASE}/users/{username}/repos"
                f"?per_page=100&page={page}&type=owner&sort=updated"
            )

        data = safe_fetch_json(url, token)
        if use_private_endpoint and page == 1 and not isinstance(data, list):
            # Fall back to public endpoint if private listing is unavailable.
            use_private_endpoint = False
            page = 1
            repos.clear()
            continue
        if not isinstance(data, list):
            break
        if not data:
            break

        for item in data:
            if not isinstance(item, dict):
                continue
            owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
            if str(owner.get("login", "")).lower() != username.lower():
                continue
            repos.append(item)

        if len(data) < 100:
            break
        page += 1

    return repos


def summarize(username: str, repos_raw: Sequence[dict], user: dict, include_forks: bool) -> ProfileData:
    now = dt.datetime.now(dt.timezone.utc)
    repos: List[Repo] = []

    for r in repos_raw:
        if not include_forks and bool(r.get("fork", False)):
            continue
        repos.append(
            Repo(
                name=str(r.get("name", "repo")),
                description=str(r.get("description") or ""),
                language=str(r.get("language") or "Other"),
                size_kb=int(r.get("size") or 0),
                stars=int(r.get("stargazers_count") or 0),
                forks=int(r.get("forks_count") or 0),
                pushed_at=parse_dt(r.get("pushed_at")),
                private=bool(r.get("private", False)),
                html_url=str(r.get("html_url") or ""),
            )
        )

    total_stars = sum(x.stars for x in repos)
    total_forks = sum(x.forks for x in repos)
    private_count = sum(1 for x in repos if x.private)

    cutoff = now - dt.timedelta(days=30)
    active_30d = sum(1 for x in repos if x.pushed_at and x.pushed_at >= cutoff)

    lang_weights: Dict[str, int] = defaultdict(int)
    for repo in repos:
        weight = max(1, repo.size_kb * 1024)
        lang_weights[repo.language] += weight

    total_weight = sum(lang_weights.values())
    ranked_langs = sorted(lang_weights.items(), key=lambda kv: kv[1], reverse=True)
    lang_rows: List[Tuple[str, float]] = []
    if total_weight > 0:
        top = ranked_langs[:6]
        other = sum(v for _, v in ranked_langs[6:])
        for name, value in top:
            lang_rows.append((name, (value / total_weight) * 100.0))
        if other > 0:
            lang_rows.append(("Other", (other / total_weight) * 100.0))

    top_repos = sorted(
        repos,
        key=lambda x: (x.stars, x.pushed_at or dt.datetime.min.replace(tzinfo=dt.timezone.utc)),
        reverse=True,
    )[:6]

    month_labels: List[str] = []
    month_values: List[int] = []
    month_counter: Counter[str] = Counter()
    for repo in repos:
        if not repo.pushed_at:
            continue
        month_counter[repo.pushed_at.strftime("%Y-%m")] += 1

    cur = dt.date.today().replace(day=1)
    months: List[dt.date] = []
    for _ in range(12):
        months.append(cur)
        if cur.month == 1:
            cur = cur.replace(year=cur.year - 1, month=12)
        else:
            cur = cur.replace(month=cur.month - 1)
    months.reverse()

    for m in months:
        key = m.strftime("%Y-%m")
        month_labels.append(m.strftime("%b"))
        month_values.append(month_counter.get(key, 0))

    display_name = str(user.get("name") or username)
    bio = str(user.get("bio") or "Design-minded developer building practical AI products.")

    return ProfileData(
        username=username,
        display_name=display_name,
        bio=bio,
        followers=int(user.get("followers") or 0),
        following=int(user.get("following") or 0),
        public_repos=int(user.get("public_repos") or 0),
        total_repos_scanned=len(repos),
        private_repos_scanned=private_count,
        total_stars=total_stars,
        total_forks=total_forks,
        active_30d=active_30d,
        language_rows=lang_rows,
        top_repos=top_repos,
        month_labels=month_labels,
        month_values=month_values,
        generated_at=now,
    )


def wrap_line(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def render_hero(data: ProfileData, theme: str) -> str:
    t = THEMES[theme]
    width, height = 1024, 300

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Profile hero">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{t['bg0']}"/>
    <stop offset="60%" stop-color="{t['bg1']}"/>
    <stop offset="100%" stop-color="{t['bg2']}"/>
  </linearGradient>
  <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="transparent"/>
    <stop offset="50%" stop-color="{t['scan']}" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="transparent"/>
  </linearGradient>
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="8" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>
<rect x="0.5" y="0.5" width="1023" height="299" rx="24" fill="url(#bg)" stroke="{t['stroke']}"/>
<circle cx="168" cy="76" r="84" fill="{t['accent2']}" opacity="0.12" filter="url(#glow)">
  <animate attributeName="cx" values="150;180;150" dur="12s" repeatCount="indefinite"/>
</circle>
<circle cx="884" cy="228" r="96" fill="{t['accent3']}" opacity="0.11" filter="url(#glow)">
  <animate attributeName="cy" values="220;240;220" dur="10s" repeatCount="indefinite"/>
</circle>
<rect x="-1024" y="0" width="1024" height="300" fill="url(#shine)">
  <animate attributeName="x" values="-1024;1024" dur="9.5s" repeatCount="indefinite"/>
</rect>
<text x="54" y="92" fill="{t['text']}" font-size="50" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{esc(data.display_name)}</text>
<text x="56" y="130" fill="{t['muted']}" font-size="20" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Design x Engineering x AI Product</text>
<text x="56" y="166" fill="{t['text']}" font-size="16" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc(wrap_line(data.bio, 88))}</text>
<text x="56" y="196" fill="{t['muted']}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc('Slow is smooth, smooth is fast. 慢慢走，比较快。')}</text>
<g>
  <rect x="56" y="220" width="130" height="34" rx="9" fill="{t['panel2']}" stroke="{t['stroke']}"/>
  <text x="74" y="242" fill="{t['accent']}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Followers</text>
  <text x="170" y="242" text-anchor="end" fill="{t['text']}" font-size="16" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{data.followers}</text>
</g>
<g>
  <rect x="198" y="220" width="130" height="34" rx="9" fill="{t['panel2']}" stroke="{t['stroke']}"/>
  <text x="216" y="242" fill="{t['accent']}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Repos</text>
  <text x="312" y="242" text-anchor="end" fill="{t['text']}" font-size="16" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{data.total_repos_scanned}</text>
</g>
<g>
  <rect x="340" y="220" width="170" height="34" rx="9" fill="{t['panel2']}" stroke="{t['stroke']}"/>
  <text x="358" y="242" fill="{t['accent']}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Updated</text>
  <text x="496" y="242" text-anchor="end" fill="{t['text']}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{data.generated_at.strftime('%Y-%m-%d')}</text>
</g>
</svg>
'''


def donut_arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x0 = cx + r * math.cos(math.radians(a0))
    y0 = cy + r * math.sin(math.radians(a0))
    x1 = cx + r * math.cos(math.radians(a1))
    y1 = cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) > 180 else 0
    return f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x1:.2f} {y1:.2f}"


def render_core(data: ProfileData, theme: str) -> str:
    t = THEMES[theme]
    width = 1024
    projects = data.top_repos[:6]
    languages = data.language_rows[:7] if data.language_rows else [("Other", 100.0)]
    project_rows = max(6, len(projects))
    project_card_h = 70 + project_rows * 44
    height = 980 + project_card_h

    month_vals = data.month_values or [0] * 12
    mv_max = max(month_vals) if max(month_vals) > 0 else 1

    lines: List[str] = []
    lines.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Profile dashboard">'
    )
    lines.append("<defs>")
    lines.append(
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{t["bg0"]}"/><stop offset="65%" stop-color="{t["bg1"]}"/><stop offset="100%" stop-color="{t["bg2"]}"/></linearGradient>'
    )
    lines.append(
        f'<linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="transparent"/><stop offset="50%" stop-color="{t["scan"]}" stop-opacity="0.13"/><stop offset="100%" stop-color="transparent"/></linearGradient>'
    )
    lines.append(
        '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="24" fill="url(#bg)" stroke="{t["stroke"]}"/>'
    )

    for i in range(20):
        y = 40 + i * 62
        lines.append(
            f'<line x1="24" y1="{y}" x2="1000" y2="{y}" stroke="{t["grid"]}" stroke-opacity="0.07" stroke-width="1"/>'
        )

    for i in range(12):
        x = 40 + i * 82
        lines.append(
            f'<line x1="{x}" y1="24" x2="{x}" y2="{height-24}" stroke="{t["grid"]}" stroke-opacity="0.05" stroke-width="1"/>'
        )

    lines.append(
        f'<rect x="-1024" y="0" width="1024" height="{height}" fill="url(#scan)"><animate attributeName="x" values="-1024;1024" dur="12s" repeatCount="indefinite"/></rect>'
    )

    # Section labels
    lines.append(f'<text x="36" y="54" fill="{t["text"]}" font-size="22" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">Interface Overview</text>')
    lines.append(f'<text x="36" y="80" fill="{t["muted"]}" font-size="13" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Modern minimal dashboard generated from GitHub data</text>')

    # Metrics cards
    card_y = 102
    card_w = 232
    metric_items = [
        ("Repos", str(data.total_repos_scanned), t["accent"]),
        ("Stars", str(data.total_stars), t["accent2"]),
        ("Forks", str(data.total_forks), t["accent3"]),
        ("Active 30d", str(data.active_30d), t["good"]),
    ]
    for i, (label, value, col) in enumerate(metric_items):
        x = 36 + i * (card_w + 14)
        lines.append(f'<rect x="{x}" y="{card_y}" width="{card_w}" height="96" rx="14" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
        lines.append(f'<text x="{x+18}" y="{card_y+36}" fill="{t["muted"]}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{label}</text>')
        lines.append(f'<text x="{x+18}" y="{card_y+71}" fill="{t["text"]}" font-size="30" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{value}</text>')
        lines.append(f'<circle cx="{x+200}" cy="{card_y+28}" r="4" fill="{col}" filter="url(#soft)"><animate attributeName="r" values="3;5;3" dur="3.8s" repeatCount="indefinite"/></circle>')

    # About + stack chips
    about_y = 220
    lines.append(f'<rect x="36" y="{about_y}" width="952" height="160" rx="14" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="56" y="{about_y+34}" fill="{t["text"]}" font-size="18" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">About</text>')
    lines.append(f'<text x="56" y="{about_y+62}" fill="{t["muted"]}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Product-minded full-stack developer focused on clean UX and resilient architecture.</text>')
    lines.append(f'<text x="56" y="{about_y+86}" fill="{t["muted"]}" font-size="14" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Building practical AI products with engineering discipline and design taste.</text>')

    chips = ["Vue", "TypeScript", "FastAPI", "Python", "MySQL", "Redis", "Docker", "Tailwind"]
    for idx, chip in enumerate(chips):
        cx = 56 + (idx % 4) * 224
        cy = about_y + 106 + (idx // 4) * 34
        lines.append(f'<rect x="{cx}" y="{cy}" width="198" height="26" rx="13" fill="{t["chip_bg"]}" stroke="{t["stroke"]}"/>')
        lines.append(f'<text x="{cx+16}" y="{cy+18}" fill="{t["text"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{chip}</text>')

    # Language card
    lang_y = 404
    lines.append(f'<rect x="36" y="{lang_y}" width="470" height="430" rx="14" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="56" y="{lang_y+34}" fill="{t["text"]}" font-size="18" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">Language Composition</text>')

    donut_cx, donut_cy, donut_r = 188, lang_y + 218, 108
    lines.append(f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r}" fill="none" stroke="{t["stroke"]}" stroke-width="34"/>')
    lines.append(f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r+22}" fill="none" stroke="{t["accent"]}" stroke-opacity="0.26" stroke-width="1" stroke-dasharray="4 8"><animateTransform attributeName="transform" type="rotate" from="0 {donut_cx} {donut_cy}" to="360 {donut_cx} {donut_cy}" dur="22s" repeatCount="indefinite"/></circle>')

    angle = -90.0
    palette = t["palette"]
    for idx, (lang, pct) in enumerate(languages):
        sweep = max(0.1, pct / 100.0 * 360.0)
        path = donut_arc(donut_cx, donut_cy, donut_r, angle, angle + sweep)
        color = palette[idx % len(palette)]
        lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="34" stroke-linecap="round" filter="url(#soft)"/>')
        angle += sweep

    lines.append(f'<circle cx="{donut_cx}" cy="{donut_cy}" r="74" fill="{t["panel2"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="{donut_cx}" y="{donut_cy-6}" text-anchor="middle" fill="{t["muted"]}" font-size="12" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Private Repos</text>')
    lines.append(f'<text x="{donut_cx}" y="{donut_cy+18}" text-anchor="middle" fill="{t["text"]}" font-size="24" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{data.private_repos_scanned}</text>')

    legend_y = lang_y + 358
    for idx, (lang, pct) in enumerate(languages[:4]):
        lx = 56 + (idx % 2) * 210
        ly = legend_y + (idx // 2) * 24
        color = palette[idx % len(palette)]
        lines.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{color}"/>')
        lines.append(f'<text x="{lx+12}" y="{ly+4}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc(lang)} {pct:.1f}%</text>')

    # Activity card
    act_y = 404
    lines.append(f'<rect x="518" y="{act_y}" width="470" height="430" rx="14" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="538" y="{act_y+34}" fill="{t["text"]}" font-size="18" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">Repo Push Activity (12 months)</text>')

    chart_x, chart_y, chart_w, chart_h = 548, act_y + 70, 410, 170
    lines.append(f'<rect x="{chart_x}" y="{chart_y}" width="{chart_w}" height="{chart_h}" rx="10" fill="{t["panel2"]}" stroke="{t["stroke"]}"/>')

    pts: List[Tuple[float, float]] = []
    for i, value in enumerate(month_vals):
        x = chart_x + 18 + (i * (chart_w - 36) / max(11, len(month_vals)-1))
        y = chart_y + chart_h - 20 - (value / mv_max) * (chart_h - 38)
        pts.append((x, y))

    if pts:
        path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts)
        area = (
            f"M {pts[0][0]:.2f} {chart_y + chart_h - 20:.2f} "
            + " L "
            + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts)
            + f" L {pts[-1][0]:.2f} {chart_y + chart_h - 20:.2f} Z"
        )
        lines.append(f'<path d="{area}" fill="{t["accent2"]}" fill-opacity="0.16"/>')
        lines.append(f'<path d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="3" filter="url(#soft)"/>')
        for idx, (x, y) in enumerate(pts):
            lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{t["accent2"]}"/>')
            if idx < len(data.month_labels):
                lines.append(f'<text x="{x:.2f}" y="{chart_y + chart_h + 18}" text-anchor="middle" fill="{t["muted"]}" font-size="11" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{data.month_labels[idx]}</text>')
        # moving dot
        lines.append(f'<circle cx="{pts[0][0]:.2f}" cy="{pts[0][1]:.2f}" r="5" fill="{t["accent"]}" filter="url(#soft)"><animateMotion dur="8s" repeatCount="indefinite" path="{path}"/></circle>')

    lines.append(f'<text x="548" y="{chart_y + chart_h + 46}" fill="{t["muted"]}" font-size="12" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Signal reflects last push date distribution across your repositories.</text>')

    # Language bars mini in activity card
    bar_y0 = chart_y + chart_h + 70
    for i, (lang, pct) in enumerate(languages[:5]):
        y = bar_y0 + i * 28
        color = palette[i % len(palette)]
        bw = max(8, int(230 * pct / 100.0))
        lines.append(f'<text x="548" y="{y+12}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc(lang)}</text>')
        lines.append(f'<rect x="660" y="{y}" width="250" height="14" rx="7" fill="{t["panel2"]}" stroke="{t["stroke"]}"/>')
        lines.append(f'<rect x="660" y="{y}" width="{bw}" height="14" rx="7" fill="{color}" filter="url(#soft)"/>')
        lines.append(f'<text x="920" y="{y+12}" text-anchor="end" fill="{t["accent2"]}" font-size="12" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{pct:.2f}%</text>')

    # Projects card
    proj_y = 852
    lines.append(f'<rect x="36" y="{proj_y}" width="952" height="{project_card_h}" rx="14" fill="{t["panel"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="56" y="{proj_y+34}" fill="{t["text"]}" font-size="18" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">Featured Repositories</text>')

    for i in range(project_rows):
        y = proj_y + 58 + i * 44
        lines.append(f'<line x1="56" y1="{y+23}" x2="968" y2="{y+23}" stroke="{t["stroke"]}" stroke-opacity="0.5"/>')
        if i < len(projects):
            repo = projects[i]
            lang = repo.language or "Other"
            desc = wrap_line(repo.description or "No description", 56)
            lines.append(f'<text x="56" y="{y+14}" fill="{t["text"]}" font-size="14.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">{esc(repo.name)}</text>')
            lines.append(f'<text x="56" y="{y+33}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc(desc)}</text>')
            lines.append(f'<text x="820" y="{y+14}" fill="{t["accent2"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">{esc(lang)}</text>')
            lines.append(f'<text x="896" y="{y+14}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">★ {repo.stars}</text>')
            lines.append(f'<text x="948" y="{y+14}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" text-anchor="end">⑂ {repo.forks}</text>')
        else:
            lines.append(f'<text x="56" y="{y+18}" fill="{t["muted"]}" font-size="12.5" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">—</text>')

    # Footer
    footer_y = proj_y + project_card_h + 26
    lines.append(f'<rect x="36" y="{footer_y}" width="952" height="76" rx="14" fill="{t["panel2"]}" stroke="{t["stroke"]}"/>')
    lines.append(f'<text x="56" y="{footer_y+31}" fill="{t["text"]}" font-size="15" font-family="JetBrains Mono, ui-monospace, Menlo, monospace" font-weight="700">Design Principle</text>')
    lines.append(f'<text x="56" y="{footer_y+55}" fill="{t["muted"]}" font-size="13" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">Slow is smooth, smooth is fast. Build with intention, ship with quality.</text>')
    lines.append(f'<text x="958" y="{footer_y+55}" text-anchor="end" fill="{t["muted"]}" font-size="12" font-family="JetBrains Mono, ui-monospace, Menlo, monospace">generated {data.generated_at.strftime("%Y-%m-%d %H:%M UTC")}</text>')

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--output-dir", default="assets")
    parser.add_argument("--include-forks", action="store_true")
    parser.add_argument("--include-private", action="store_true")
    args = parser.parse_args()

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    user = fetch_user(args.username, token)
    repos = fetch_repositories(args.username, token, include_private=args.include_private)
    data = summarize(args.username, repos, user, include_forks=args.include_forks)

    out_dir = Path(args.output_dir)
    for theme in ("dark", "light"):
        write(out_dir / f"hero-{theme}.svg", render_hero(data, theme))
        write(out_dir / f"core-{theme}.svg", render_core(data, theme))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
