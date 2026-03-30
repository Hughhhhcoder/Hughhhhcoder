#!/usr/bin/env python3
"""Generate a premium animated GitHub profile experience SVG (dark/light)."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

API_BASE = "https://api.github.com"
USER_AGENT = "profile-experience-generator/2.0"

DESIGN_TOKENS = {
    "spacing": {"2": 8, "3": 12, "4": 16, "5": 20, "6": 24, "8": 32},
    "radius": {"sm": 12, "md": 16, "lg": 20, "xl": 24},
    "font": {
        "display": "SF Pro Display, Segoe UI, Arial, sans-serif",
        "mono": "JetBrains Mono, SFMono-Regular, Menlo, monospace",
    },
}

DEFAULT_CONFIG = {
    "hero_text": "HughhhhCoder",
    "subtitle": "Design x Engineering x AI Product",
    "description_cn": "专注高质量产品体验与稳定工程架构，持续打造实用 AI 产品。",
    "description_en": "Design-minded full-stack engineer building practical and reliable AI experiences.",
    "motto": "慢慢走，比较快。Slow is smooth, smooth is fast.",
    "contacts": {
        "github": "https://github.com/Hughhhhcoder",
        "email": "Hughz@gmail.com",
    },
    "motion_level": "immersive",
    "core_tech": [
        "Vue",
        "TypeScript",
        "Python",
        "FastAPI",
        "MySQL",
        "Redis",
        "Docker",
        "Tailwind",
        "Git",
        "Linux",
        "JavaScript",
        "Java",
    ],
    "ai_platforms": [
        "OpenAI",
        "Anthropic",
        "Gemini",
        "Hugging Face",
        "AWS",
        "Azure",
        "Groq",
        "Cohere",
    ],
    "featured_repos_limit": 6,
}

THEMES = {
    "dark": {
        "bg0": "#020617",
        "bg1": "#071226",
        "bg2": "#052c33",
        "panel": "#0b1220",
        "panel_alt": "#0f172a",
        "stroke": "#1f2a44",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "accent": "#22d3ee",
        "accent2": "#38bdf8",
        "accent3": "#14b8a6",
        "good": "#22c55e",
        "warn": "#f59e0b",
        "danger": "#fb7185",
        "grid": "#0ea5e9",
        "scan": "#22d3ee",
        "bars": ["#22d3ee", "#38bdf8", "#14b8a6", "#2dd4bf", "#60a5fa", "#0ea5e9", "#67e8f9", "#10b981"],
    },
    "light": {
        "bg0": "#f8fafc",
        "bg1": "#eef2ff",
        "bg2": "#e0f2fe",
        "panel": "#ffffff",
        "panel_alt": "#f8fafc",
        "stroke": "#cbd5e1",
        "text": "#0f172a",
        "muted": "#334155",
        "accent": "#0284c7",
        "accent2": "#0ea5e9",
        "accent3": "#0f766e",
        "good": "#16a34a",
        "warn": "#b45309",
        "danger": "#be123c",
        "grid": "#93c5fd",
        "scan": "#0ea5e9",
        "bars": ["#0284c7", "#0ea5e9", "#0f766e", "#14b8a6", "#2563eb", "#38bdf8", "#22c55e", "#0891b2"],
    },
}

MOTION_PRESETS = {
    "minimal": {
        "scan": False,
        "orbs": False,
        "line_pulse": False,
        "logo_breathe": False,
        "scan_duration": "20s",
        "line_duration": "14s",
    },
    "balanced": {
        "scan": True,
        "orbs": True,
        "line_pulse": True,
        "logo_breathe": True,
        "scan_duration": "13s",
        "line_duration": "10s",
    },
    "immersive": {
        "scan": True,
        "orbs": True,
        "line_pulse": True,
        "logo_breathe": True,
        "scan_duration": "9s",
        "line_duration": "7s",
    },
}

TECH_LOGO = {
    "Python": "python",
    "TypeScript": "typescript",
    "JavaScript": "javascript",
    "Vue": "vue",
    "React": "react",
    "Tailwind": "tailwind",
    "FastAPI": "fastapi",
    "MySQL": "mysql",
    "Redis": "redis",
    "Docker": "docker",
    "Git": "git",
    "Linux": "linux",
    "Java": "java",
    "HTML5": "html5",
    "CSS3": "css3",
    "Node.js": "nodejs",
    "PostgreSQL": "postgresql",
    "Go": "go",
    "Rust": "rust",
    "Vite": "vite",
}

AI_LOGO = {
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "Gemini": "gemini",
    "Hugging Face": "huggingface",
    "AWS": "aws",
    "Azure": "azure",
    "Groq": "groq",
    "Cohere": "cohere",
}

LANGUAGE_TO_TECH = {
    "Python": "Python",
    "TypeScript": "TypeScript",
    "JavaScript": "JavaScript",
    "Vue": "Vue",
    "Java": "Java",
    "HTML": "HTML5",
    "CSS": "CSS3",
    "Go": "Go",
    "Rust": "Rust",
    "Shell": "Linux",
    "Dockerfile": "Docker",
}

KEYWORD_TO_TECH = [
    ("vue", "Vue"),
    ("react", "React"),
    ("tailwind", "Tailwind"),
    ("fastapi", "FastAPI"),
    ("mysql", "MySQL"),
    ("redis", "Redis"),
    ("docker", "Docker"),
    ("typescript", "TypeScript"),
    ("javascript", "JavaScript"),
    ("python", "Python"),
    ("java", "Java"),
    ("node", "Node.js"),
    ("postgres", "PostgreSQL"),
    ("golang", "Go"),
    ("rust", "Rust"),
    ("vite", "Vite"),
]


@dataclass
class Repo:
    name: str
    description: str
    language: str
    stars: int
    forks: int
    size_kb: int
    pushed_at: dt.datetime | None
    private: bool
    html_url: str
    languages: Dict[str, int]


@dataclass
class Snapshot:
    username: str
    display_name: str
    bio: str
    followers: int
    following: int
    public_repos: int
    scanned_repos: int
    private_repos: int
    stars: int
    forks: int
    active_30d: int
    language_rows: List[Tuple[str, int, float]]
    total_bytes: int
    months: List[str]
    month_values: List[int]
    top_repos: List[Repo]
    tech_stack: List[str]
    ai_platforms: List[str]
    generated_at: dt.datetime
    data_mode: str
    status_note: str


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def parse_iso(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compact_bytes(size: int) -> str:
    if size >= 1_000_000_000:
        return f"{size / 1_000_000_000:.2f} GB"
    if size >= 1_000_000:
        return f"{size / 1_000_000:.2f} MB"
    if size >= 1_000:
        return f"{size / 1_000:.2f} KB"
    return f"{size} B"


def wrap_line(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def arc_path(cx: float, cy: float, r: float, start_deg: float, sweep_deg: float) -> str:
    start_rad = math.radians(start_deg)
    end_rad = math.radians(start_deg + sweep_deg)
    x0 = cx + r * math.cos(start_rad)
    y0 = cy + r * math.sin(start_rad)
    x1 = cx + r * math.cos(end_rad)
    y1 = cy + r * math.sin(end_rad)
    large_arc = 1 if sweep_deg > 180 else 0
    return (
        f"M {x0:.2f} {y0:.2f} "
        f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {x1:.2f} {y1:.2f}"
    )


def request_json(url: str, token: str | None) -> object:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} for {url} :: {body[:220]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc}") from exc


def safe_json(url: str, token: str | None, warnings: List[str]) -> object | None:
    try:
        return request_json(url, token)
    except Exception as exc:  # pylint: disable=broad-except
        if len(warnings) < 4:
            warnings.append(str(exc))
        return None


def load_config(path: Path) -> dict:
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        user_raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(user_raw, dict):
            for key, value in user_raw.items():
                config[key] = value

    contacts = config.get("contacts")
    if not isinstance(contacts, dict):
        contacts = dict(DEFAULT_CONFIG["contacts"])
    config["contacts"] = {
        "github": str(contacts.get("github") or DEFAULT_CONFIG["contacts"]["github"]),
        "email": str(contacts.get("email") or DEFAULT_CONFIG["contacts"]["email"]),
    }

    for key in ("core_tech", "ai_platforms"):
        value = config.get(key)
        if not isinstance(value, list):
            value = DEFAULT_CONFIG[key]
        config[key] = [str(item).strip() for item in value if str(item).strip()]

    config["motion_level"] = str(config.get("motion_level") or "immersive").lower()
    if config["motion_level"] not in MOTION_PRESETS:
        config["motion_level"] = "immersive"

    featured_limit = config.get("featured_repos_limit", 6)
    try:
        featured_limit = int(featured_limit)
    except (TypeError, ValueError):
        featured_limit = 6
    config["featured_repos_limit"] = max(3, min(10, featured_limit))

    return config


def fetch_user(username: str, token: str | None, warnings: List[str]) -> dict:
    data = safe_json(f"{API_BASE}/users/{username}", token, warnings)
    if isinstance(data, dict):
        return data
    return {
        "name": username,
        "bio": "",
        "followers": 0,
        "following": 0,
        "public_repos": 0,
    }


def fetch_repositories(
    username: str,
    token: str | None,
    include_private: bool,
    warnings: List[str],
) -> Tuple[List[dict], str]:
    repos: List[dict] = []
    page = 1
    using_private = bool(include_private and token)
    data_mode = "public-only"

    while True:
        if using_private:
            url = (
                f"{API_BASE}/user/repos"
                f"?per_page=100&page={page}&visibility=all&affiliation=owner&sort=updated"
            )
        else:
            url = (
                f"{API_BASE}/users/{username}/repos"
                f"?per_page=100&page={page}&type=owner&sort=updated"
            )

        payload = safe_json(url, token, warnings)

        if using_private and page == 1 and not isinstance(payload, list):
            using_private = False
            data_mode = "public-only"
            page = 1
            repos.clear()
            continue

        if not isinstance(payload, list) or not payload:
            break

        for item in payload:
            if not isinstance(item, dict):
                continue
            owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
            if str(owner.get("login", "")).lower() != username.lower():
                continue
            repos.append(item)

        if len(payload) < 100:
            break
        page += 1

    if using_private:
        data_mode = "public+private"
    elif include_private and not token:
        data_mode = "public-only (no PROFILE_STATS_PAT)"
    return repos, data_mode


def collect_repos(
    username: str,
    repos_raw: Sequence[dict],
    token: str | None,
    include_forks: bool,
    warnings: List[str],
) -> List[Repo]:
    repos: List[Repo] = []

    for raw in repos_raw:
        if not include_forks and bool(raw.get("fork", False)):
            continue
        owner = raw.get("owner") if isinstance(raw.get("owner"), dict) else {}
        if str(owner.get("login", "")).lower() != username.lower():
            continue

        languages: Dict[str, int] = {}
        languages_url = raw.get("languages_url")
        if isinstance(languages_url, str) and languages_url:
            lang_payload = safe_json(languages_url, token, warnings)
            if isinstance(lang_payload, dict):
                for lang, value in lang_payload.items():
                    if isinstance(lang, str) and isinstance(value, int) and value > 0:
                        languages[lang] = value

        primary_language = str(raw.get("language") or "Other")
        size_kb = int(raw.get("size") or 0)
        if not languages and primary_language:
            languages[primary_language] = max(1, size_kb * 1024)

        repos.append(
            Repo(
                name=str(raw.get("name") or "repo"),
                description=str(raw.get("description") or ""),
                language=primary_language,
                stars=int(raw.get("stargazers_count") or 0),
                forks=int(raw.get("forks_count") or 0),
                size_kb=size_kb,
                pushed_at=parse_iso(raw.get("pushed_at")),
                private=bool(raw.get("private", False)),
                html_url=str(raw.get("html_url") or ""),
                languages=languages,
            )
        )

    return repos


def aggregate_languages(repos: Iterable[Repo]) -> Dict[str, int]:
    totals: Dict[str, int] = defaultdict(int)
    for repo in repos:
        for lang, value in repo.languages.items():
            if value > 0:
                totals[lang] += value
    return totals


def build_language_rows(totals: Dict[str, int], max_rows: int = 8) -> Tuple[List[Tuple[str, int, float]], int]:
    total_bytes = sum(totals.values())
    if total_bytes <= 0:
        return [], 0

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    head = ranked[:max_rows]
    if len(ranked) > max_rows:
        other = sum(value for _, value in ranked[max_rows:])
        head.append(("Other", other))

    rows = [(name, value, (value / total_bytes) * 100.0) for name, value in head]
    return rows, total_bytes


def build_months(repos: Sequence[Repo], months: int = 12) -> Tuple[List[str], List[int]]:
    counter: Counter[str] = Counter()
    for repo in repos:
        if repo.pushed_at:
            counter[repo.pushed_at.strftime("%Y-%m")] += 1

    cursor = dt.date.today().replace(day=1)
    keys: List[str] = []
    labels: List[str] = []
    for _ in range(months):
        keys.append(cursor.strftime("%Y-%m"))
        labels.append(cursor.strftime("%b"))
        if cursor.month == 1:
            cursor = cursor.replace(year=cursor.year - 1, month=12)
        else:
            cursor = cursor.replace(month=cursor.month - 1)

    keys.reverse()
    labels.reverse()
    values = [counter.get(k, 0) for k in keys]
    return labels, values


def normalize_catalog_item(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def resolve_tech(config_core: Sequence[str], repos: Sequence[Repo], language_totals: Dict[str, int]) -> List[str]:
    detected: List[str] = []

    for lang in language_totals:
        if lang in LANGUAGE_TO_TECH:
            detected.append(LANGUAGE_TO_TECH[lang])

    for repo in repos:
        text = f"{repo.name} {repo.description}".lower()
        for keyword, tech in KEYWORD_TO_TECH:
            if keyword in text:
                detected.append(tech)

    order = list(TECH_LOGO.keys())
    order_map = {name: idx for idx, name in enumerate(order)}

    merged: List[str] = []
    for item in list(config_core) + detected:
        normalized = normalize_catalog_item(item)
        matched = None
        for tech_name in TECH_LOGO:
            if normalize_catalog_item(tech_name) == normalized:
                matched = tech_name
                break
        if matched and matched not in merged:
            merged.append(matched)

    merged.sort(key=lambda name: order_map.get(name, 999))
    return merged[:20]


def resolve_ai_platforms(config_ai: Sequence[str]) -> List[str]:
    resolved: List[str] = []
    for item in config_ai:
        norm = normalize_catalog_item(item)
        for name in AI_LOGO:
            if normalize_catalog_item(name) == norm and name not in resolved:
                resolved.append(name)
    if not resolved:
        resolved = list(DEFAULT_CONFIG["ai_platforms"])
    return resolved[:8]


def build_snapshot(
    username: str,
    config: dict,
    user: dict,
    repos: Sequence[Repo],
    data_mode: str,
    warnings: List[str],
) -> Snapshot:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=30)

    stars = sum(r.stars for r in repos)
    forks = sum(r.forks for r in repos)
    private_repos = sum(1 for r in repos if r.private)
    active_30d = sum(1 for r in repos if r.pushed_at and r.pushed_at >= cutoff)

    language_totals = aggregate_languages(repos)
    language_rows, total_bytes = build_language_rows(language_totals)
    months, month_values = build_months(repos)

    repo_limit = int(config.get("featured_repos_limit", 6))
    top_repos = sorted(
        repos,
        key=lambda r: (
            r.stars,
            r.forks,
            r.pushed_at or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        ),
        reverse=True,
    )[:repo_limit]

    tech_stack = resolve_tech(config.get("core_tech", []), repos, language_totals)
    ai_platforms = resolve_ai_platforms(config.get("ai_platforms", []))

    status_note = "Data source: public repositories only."
    if data_mode == "public+private":
        status_note = "Data source: public + private repositories (owner scope)."
    elif "PROFILE_STATS_PAT" in data_mode:
        status_note = "Data source: public repositories only (PROFILE_STATS_PAT not configured)."
    if warnings:
        status_note += f" Diagnostics: {warnings[0][:110]}"

    display_name = str(user.get("name") or config.get("hero_text") or username)
    bio = str(user.get("bio") or config.get("description_en") or "")

    return Snapshot(
        username=username,
        display_name=display_name,
        bio=bio,
        followers=int(user.get("followers") or 0),
        following=int(user.get("following") or 0),
        public_repos=int(user.get("public_repos") or 0),
        scanned_repos=len(repos),
        private_repos=private_repos,
        stars=stars,
        forks=forks,
        active_30d=active_30d,
        language_rows=language_rows,
        total_bytes=total_bytes,
        months=months,
        month_values=month_values,
        top_repos=top_repos,
        tech_stack=tech_stack,
        ai_platforms=ai_platforms,
        generated_at=now,
        data_mode=data_mode,
        status_note=status_note,
    )


def logo_uri(root: Path, key: str, cache: Dict[str, str]) -> str | None:
    if key in cache:
        return cache[key]
    path = root / "assets" / "logos" / f"{key}.svg"
    if not path.exists():
        cache[key] = ""
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    cache[key] = f"data:image/svg+xml;base64,{encoded}"
    return cache[key]


def render_logo_tile(
    lines: List[str],
    uri: str | None,
    label: str,
    x: int,
    y: int,
    w: int,
    h: int,
    theme: dict,
    motion: dict,
    idx: int,
) -> None:
    lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>')
    if uri:
        if motion["logo_breathe"]:
            lines.append(
                f'<image href="{uri}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" opacity="0.94">'
                f'<animate attributeName="opacity" values="0.86;1;0.86" dur="{4.8 + (idx % 5) * 0.8:.1f}s" repeatCount="indefinite"/>'
                "</image>"
            )
        else:
            lines.append(
                f'<image href="{uri}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" opacity="0.96"/>'
            )
    else:
        lines.append(f'<text x="{x + w/2:.1f}" y="{y + h/2 + 6:.1f}" text-anchor="middle" fill="{theme["text"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="600">{esc(label)}</text>')


def render_experience(snapshot: Snapshot, config: dict, theme_name: str, motion_level: str, root: Path) -> str:
    theme = THEMES[theme_name]
    motion = MOTION_PRESETS[motion_level]

    width = 1200
    margin = 32
    section_gap = 18
    section_w = width - margin * 2

    tech_cols = 4
    tile_gap = 16
    tile_w = int((section_w - 48 - tile_gap * (tech_cols - 1)) / tech_cols)
    tile_h = 92

    tech_rows = max(1, math.ceil(len(snapshot.tech_stack) / tech_cols))
    ai_rows = max(1, math.ceil(len(snapshot.ai_platforms) / tech_cols))

    hero_h = 320
    tech_h = 86 + tech_rows * (tile_h + 12) + 54 + ai_rows * (tile_h + 12) + 28
    language_h = 560
    repo_rows = max(4, len(snapshot.top_repos))
    repo_h = 520 + repo_rows * 48
    footer_h = 96

    y_hero = margin
    y_tech = y_hero + hero_h + section_gap
    y_lang = y_tech + tech_h + section_gap
    y_repo = y_lang + language_h + section_gap
    y_footer = y_repo + repo_h + section_gap
    total_height = y_footer + footer_h + margin

    logo_cache: Dict[str, str] = {}
    lines: List[str] = []
    lines.append(
        f'<svg width="{width}" height="{total_height}" viewBox="0 0 {width} {total_height}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(snapshot.display_name)} profile experience">'
    )

    lines.append("<defs>")
    lines.append(
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{theme["bg0"]}">'
        f'<animate attributeName="stop-color" values="{theme["bg0"]};{theme["bg1"]};{theme["bg0"]}" dur="20s" repeatCount="indefinite"/>'
        "</stop>"
        f'<stop offset="55%" stop-color="{theme["bg1"]}">'
        f'<animate attributeName="stop-color" values="{theme["bg1"]};{theme["bg2"]};{theme["bg1"]}" dur="22s" repeatCount="indefinite"/>'
        "</stop>"
        f'<stop offset="100%" stop-color="{theme["bg2"]}"/>'
        "</linearGradient>"
    )
    lines.append(
        f'<linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="transparent"/>'
        f'<stop offset="50%" stop-color="{theme["scan"]}" stop-opacity="0.16"/>'
        '<stop offset="100%" stop-color="transparent"/>'
        "</linearGradient>"
    )
    lines.append(
        '<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">'
        '<feGaussianBlur stdDeviation="10" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{total_height - 1}" rx="28" fill="url(#bg)" stroke="{theme["stroke"]}"/>'
    )

    for i in range(32):
        y = 24 + i * 72
        lines.append(
            f'<line x1="22" y1="{y}" x2="{width - 22}" y2="{y}" stroke="{theme["grid"]}" stroke-opacity="0.06"/>'
        )
    for i in range(18):
        x = 28 + i * 66
        lines.append(
            f'<line x1="{x}" y1="20" x2="{x}" y2="{total_height - 20}" stroke="{theme["grid"]}" stroke-opacity="0.04"/>'
        )

    if motion["orbs"]:
        lines.append(
            f'<circle cx="210" cy="140" r="120" fill="{theme["accent2"]}" opacity="0.14" filter="url(#glow)">'
            '<animate attributeName="cx" values="180;260;180" dur="15s" repeatCount="indefinite"/>'
            '<animate attributeName="cy" values="120;170;120" dur="17s" repeatCount="indefinite"/>'
            "</circle>"
        )
        lines.append(
            f'<circle cx="980" cy="260" r="150" fill="{theme["accent3"]}" opacity="0.12" filter="url(#glow)">'
            '<animate attributeName="cx" values="950;1030;950" dur="18s" repeatCount="indefinite"/>'
            '<animate attributeName="cy" values="240;300;240" dur="16s" repeatCount="indefinite"/>'
            "</circle>"
        )

    if motion["scan"]:
        lines.append(
            f'<rect x="{-width}" y="0" width="{width}" height="{total_height}" fill="url(#scan)">'
            f'<animate attributeName="x" values="{-width};{width}" dur="{motion["scan_duration"]}" repeatCount="indefinite"/>'
            "</rect>"
        )

    # Hero
    lines.append(
        f'<rect x="{margin}" y="{y_hero}" width="{section_w}" height="{hero_h}" rx="24" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>'
    )
    lines.append(
        f'<rect x="{margin}" y="{y_hero}" width="{section_w}" height="{hero_h}" rx="24" fill="url(#scan)" opacity="0.32"/>'
    )

    lines.append(
        f'<text x="{margin + 28}" y="{y_hero + 78}" fill="{theme["text"]}" font-size="52" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">{esc(config.get("hero_text") or snapshot.display_name)}</text>'
    )
    lines.append(
        f'<text x="{margin + 30}" y="{y_hero + 122}" fill="{theme["muted"]}" font-size="24" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="500">{esc(config.get("subtitle") or "")}</text>'
    )
    lines.append(
        f'<text x="{margin + 30}" y="{y_hero + 162}" fill="{theme["text"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">{esc(wrap_line(config.get("description_cn") or "", 68))}</text>'
    )
    lines.append(
        f'<text x="{margin + 30}" y="{y_hero + 188}" fill="{theme["muted"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">{esc(wrap_line(config.get("description_en") or snapshot.bio, 88))}</text>'
    )
    lines.append(
        f'<text x="{margin + 30}" y="{y_hero + 214}" fill="{theme["accent"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["mono"]}">{esc(config.get("motto") or "")}</text>'
    )

    chip_y = y_hero + 246
    chip_w = 250
    chip_gap = 14
    chips = [
        ("Followers", str(snapshot.followers), theme["accent"]),
        ("Repositories", str(snapshot.scanned_repos), theme["accent2"]),
        ("Private Included", str(snapshot.private_repos), theme["accent3"]),
        ("Updated", snapshot.generated_at.strftime("%Y-%m-%d"), theme["good"]),
    ]
    for idx, (label, value, color) in enumerate(chips):
        cx = margin + 28 + idx * (chip_w + chip_gap)
        lines.append(
            f'<rect x="{cx}" y="{chip_y}" width="{chip_w}" height="56" rx="14" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>'
        )
        lines.append(
            f'<text x="{cx + 16}" y="{chip_y + 24}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{label}</text>'
        )
        lines.append(
            f'<text x="{cx + 16}" y="{chip_y + 44}" fill="{theme["text"]}" font-size="18" font-family="{DESIGN_TOKENS["font"]["mono"]}" font-weight="700">{value}</text>'
        )
        lines.append(f'<circle cx="{cx + chip_w - 18}" cy="{chip_y + 20}" r="5" fill="{color}"/>')

    # Technology section
    lines.append(
        f'<rect x="{margin}" y="{y_tech}" width="{section_w}" height="{tech_h}" rx="24" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_tech + 44}" fill="{theme["text"]}" font-size="30" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">Technology Matrix</text>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_tech + 70}" fill="{theme["muted"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">Auto-detected from repositories, then completed by profile config.</text>'
    )

    tech_start_y = y_tech + 92
    for idx, tech in enumerate(snapshot.tech_stack):
        row = idx // tech_cols
        col = idx % tech_cols
        x = margin + 24 + col * (tile_w + tile_gap)
        y = tech_start_y + row * (tile_h + 12)
        uri = logo_uri(root, TECH_LOGO.get(tech, ""), logo_cache)
        render_logo_tile(lines, uri, tech, x, y, tile_w, tile_h, theme, motion, idx)

    ai_header_y = tech_start_y + tech_rows * (tile_h + 12) + 28
    lines.append(
        f'<text x="{margin + 24}" y="{ai_header_y}" fill="{theme["text"]}" font-size="24" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">AI Platform Ecosystem</text>'
    )
    ai_start_y = ai_header_y + 18
    for idx, platform in enumerate(snapshot.ai_platforms):
        row = idx // tech_cols
        col = idx % tech_cols
        x = margin + 24 + col * (tile_w + tile_gap)
        y = ai_start_y + row * (tile_h + 12)
        uri = logo_uri(root, AI_LOGO.get(platform, ""), logo_cache)
        render_logo_tile(lines, uri, platform, x, y, tile_w, tile_h, theme, motion, idx + 15)

    # Language intelligence section
    lines.append(
        f'<rect x="{margin}" y="{y_lang}" width="{section_w}" height="{language_h}" rx="24" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_lang + 44}" fill="{theme["text"]}" font-size="30" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">Language Intelligence</text>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_lang + 70}" fill="{theme["muted"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">Byte-level aggregation from each repository languages endpoint.</text>'
    )

    left_x = margin + 24
    left_y = y_lang + 92
    left_w = 500
    left_h = 436
    right_x = left_x + left_w + 20
    right_y = left_y
    right_w = section_w - 48 - left_w - 20
    right_h = left_h

    lines.append(f'<rect x="{left_x}" y="{left_y}" width="{left_w}" height="{left_h}" rx="20" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>')
    lines.append(f'<rect x="{right_x}" y="{right_y}" width="{right_w}" height="{right_h}" rx="20" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>')

    donut_cx = left_x + 250
    donut_cy = left_y + 195
    donut_r = 135
    donut_sw = 42
    lines.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r}" fill="none" stroke="{theme["stroke"]}" stroke-width="{donut_sw}"/>'
    )

    angle = -90.0
    language_rows = snapshot.language_rows if snapshot.language_rows else [("No Data", 1, 100.0)]
    for idx, (lang, _bytes, pct) in enumerate(language_rows[:9]):
        sweep = max(1.2, pct / 100.0 * 360.0)
        path = arc_path(donut_cx, donut_cy, donut_r, angle, sweep)
        color = theme["bars"][idx % len(theme["bars"])]
        lines.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{donut_sw}" stroke-linecap="round" filter="url(#glow)"/>'
        )
        angle += sweep

    lines.append(f'<circle cx="{donut_cx}" cy="{donut_cy}" r="90" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>')
    lines.append(
        f'<text x="{donut_cx}" y="{donut_cy - 8}" text-anchor="middle" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Total Code</text>'
    )
    lines.append(
        f'<text x="{donut_cx}" y="{donut_cy + 20}" text-anchor="middle" fill="{theme["text"]}" font-size="24" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">{compact_bytes(snapshot.total_bytes)}</text>'
    )

    legend_start = left_y + 344
    for idx, (lang, _bytes, pct) in enumerate(language_rows[:6]):
        row = idx // 2
        col = idx % 2
        lx = left_x + 28 + col * 234
        ly = legend_start + row * 30
        color = theme["bars"][idx % len(theme["bars"])]
        lines.append(f'<circle cx="{lx}" cy="{ly}" r="6" fill="{color}"/>')
        lines.append(
            f'<text x="{lx + 14}" y="{ly + 5}" fill="{theme["text"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{esc(lang)} {pct:.1f}%</text>'
        )

    bar_start_y = right_y + 38
    bar_track_w = right_w - 220
    for idx, (lang, _bytes, pct) in enumerate(language_rows[:8]):
        by = bar_start_y + idx * 48
        color = theme["bars"][idx % len(theme["bars"])]
        fill_w = max(14, int(bar_track_w * (pct / 100.0)))
        lines.append(
            f'<text x="{right_x + 22}" y="{by + 18}" fill="{theme["text"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">{esc(lang)}</text>'
        )
        lines.append(
            f'<rect x="{right_x + 196}" y="{by + 2}" width="{bar_track_w}" height="18" rx="9" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>'
        )
        if motion["line_pulse"]:
            lines.append(
                f'<rect x="{right_x + 196}" y="{by + 2}" width="{fill_w}" height="18" rx="9" fill="{color}" opacity="0.92">'
                f'<animate attributeName="width" values="8;{fill_w}" dur="{2.2 + idx * 0.25:.2f}s" repeatCount="1" fill="freeze"/>'
                "</rect>"
            )
        else:
            lines.append(
                f'<rect x="{right_x + 196}" y="{by + 2}" width="{fill_w}" height="18" rx="9" fill="{color}" opacity="0.92"/>'
            )
        lines.append(
            f'<text x="{right_x + 196 + bar_track_w + 16}" y="{by + 18}" fill="{theme["accent2"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["mono"]}">{pct:5.2f}%</text>'
        )

    lines.append(
        f'<text x="{right_x + 22}" y="{right_y + right_h - 26}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Private repositories counted: {snapshot.private_repos}</text>'
    )

    # Repository pulse section
    lines.append(
        f'<rect x="{margin}" y="{y_repo}" width="{section_w}" height="{repo_h}" rx="24" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_repo + 44}" fill="{theme["text"]}" font-size="30" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">Repository Pulse</text>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_repo + 70}" fill="{theme["muted"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}">Contribution rhythm and curated repository highlights.</text>'
    )

    metrics = [
        ("Stars", str(snapshot.stars), theme["accent"]),
        ("Forks", str(snapshot.forks), theme["accent2"]),
        ("Active 30d", str(snapshot.active_30d), theme["good"]),
        ("Public Repos", str(snapshot.public_repos), theme["accent3"]),
    ]
    metric_y = y_repo + 94
    metric_w = int((section_w - 48 - 18 * 3) / 4)
    for idx, (label, value, color) in enumerate(metrics):
        mx = margin + 24 + idx * (metric_w + 18)
        lines.append(f'<rect x="{mx}" y="{metric_y}" width="{metric_w}" height="92" rx="16" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>')
        lines.append(f'<text x="{mx + 16}" y="{metric_y + 30}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{label}</text>')
        lines.append(f'<text x="{mx + 16}" y="{metric_y + 66}" fill="{theme["text"]}" font-size="30" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">{value}</text>')
        lines.append(f'<circle cx="{mx + metric_w - 18}" cy="{metric_y + 22}" r="5" fill="{color}"/>')

    chart_x = margin + 24
    chart_y = metric_y + 112
    chart_w = section_w - 48
    chart_h = 220
    lines.append(f'<rect x="{chart_x}" y="{chart_y}" width="{chart_w}" height="{chart_h}" rx="16" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>')

    month_values = snapshot.month_values if snapshot.month_values else [0] * 12
    max_value = max(month_values) if max(month_values) > 0 else 1
    points: List[Tuple[float, float]] = []
    inner_x = chart_x + 28
    inner_y = chart_y + 24
    inner_w = chart_w - 56
    inner_h = chart_h - 60

    for idx, value in enumerate(month_values):
        x = inner_x + idx * (inner_w / max(1, len(month_values) - 1))
        y = inner_y + inner_h - (value / max_value) * inner_h
        points.append((x, y))

    if points:
        line_path = "M " + " L ".join(f"{px:.2f} {py:.2f}" for px, py in points)
        area_path = (
            f"M {points[0][0]:.2f} {inner_y + inner_h:.2f} "
            + " L "
            + " L ".join(f"{px:.2f} {py:.2f}" for px, py in points)
            + f" L {points[-1][0]:.2f} {inner_y + inner_h:.2f} Z"
        )
        lines.append(f'<path d="{area_path}" fill="{theme["accent2"]}" fill-opacity="0.18"/>')
        if motion["line_pulse"]:
            lines.append(
                f'<path d="{line_path}" fill="none" stroke="{theme["accent"]}" stroke-width="4" stroke-dasharray="12 8">'
                f'<animate attributeName="stroke-dashoffset" values="0;-200" dur="{motion["line_duration"]}" repeatCount="indefinite"/>'
                "</path>"
            )
        else:
            lines.append(
                f'<path d="{line_path}" fill="none" stroke="{theme["accent"]}" stroke-width="4"/>'
            )

        for idx, (px, py) in enumerate(points):
            lines.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" fill="{theme["accent2"]}"/>')
            if idx < len(snapshot.months):
                lines.append(
                    f'<text x="{px:.2f}" y="{chart_y + chart_h - 14}" text-anchor="middle" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{snapshot.months[idx]}</text>'
                )

        if motion["line_pulse"]:
            lines.append(
                f'<circle cx="{points[0][0]:.2f}" cy="{points[0][1]:.2f}" r="6" fill="{theme["accent"]}" filter="url(#glow)">'
                f'<animateMotion dur="{motion["line_duration"]}" repeatCount="indefinite" path="{line_path}"/>'
                "</circle>"
            )

    table_y = chart_y + chart_h + 24
    lines.append(
        f'<text x="{margin + 24}" y="{table_y + 16}" fill="{theme["text"]}" font-size="22" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">Featured Projects</text>'
    )

    header_y = table_y + 48
    lines.append(f'<line x1="{margin + 24}" y1="{header_y}" x2="{margin + section_w - 24}" y2="{header_y}" stroke="{theme["stroke"]}"/>')
    lines.append(f'<text x="{margin + 28}" y="{header_y - 12}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Repository</text>')
    lines.append(f'<text x="{margin + 760}" y="{header_y - 12}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Language</text>')
    lines.append(f'<text x="{margin + 940}" y="{header_y - 12}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Stars</text>')
    lines.append(f'<text x="{margin + 1050}" y="{header_y - 12}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">Forks</text>')

    for idx, repo in enumerate(snapshot.top_repos):
        ry = header_y + 26 + idx * 48
        lines.append(f'<line x1="{margin + 24}" y1="{ry + 16}" x2="{margin + section_w - 24}" y2="{ry + 16}" stroke="{theme["stroke"]}" stroke-opacity="0.55"/>')
        lines.append(
            f'<text x="{margin + 28}" y="{ry}" fill="{theme["text"]}" font-size="16" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="600">{esc(wrap_line(repo.name, 28))}</text>'
        )
        lines.append(
            f'<text x="{margin + 28}" y="{ry + 18}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["display"]}">{esc(wrap_line(repo.description or "No description", 70))}</text>'
        )
        lines.append(
            f'<text x="{margin + 760}" y="{ry}" fill="{theme["accent2"]}" font-size="15" font-family="{DESIGN_TOKENS["font"]["mono"]}">{esc(repo.language or "Other")}</text>'
        )
        lines.append(
            f'<text x="{margin + 940}" y="{ry}" fill="{theme["text"]}" font-size="15" font-family="{DESIGN_TOKENS["font"]["mono"]}">{repo.stars}</text>'
        )
        lines.append(
            f'<text x="{margin + 1050}" y="{ry}" fill="{theme["text"]}" font-size="15" font-family="{DESIGN_TOKENS["font"]["mono"]}">{repo.forks}</text>'
        )

    # Footer
    lines.append(
        f'<rect x="{margin}" y="{y_footer}" width="{section_w}" height="{footer_h}" rx="20" fill="{theme["panel_alt"]}" stroke="{theme["stroke"]}"/>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_footer + 36}" fill="{theme["text"]}" font-size="20" font-family="{DESIGN_TOKENS["font"]["display"]}" font-weight="700">Design Principle</text>'
    )
    lines.append(
        f'<text x="{margin + 24}" y="{y_footer + 62}" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{esc(wrap_line(config.get("motto") or "", 120))}</text>'
    )
    lines.append(
        f'<text x="{margin + section_w - 24}" y="{y_footer + 62}" text-anchor="end" fill="{theme["muted"]}" font-size="14" font-family="{DESIGN_TOKENS["font"]["mono"]}">{esc(wrap_line(snapshot.status_note, 72))}</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--output-dir", default="assets")
    parser.add_argument("--config", default="profile.config.json")
    parser.add_argument("--include-private", action="store_true")
    parser.add_argument("--include-forks", action="store_true")
    parser.add_argument("--motion", choices=["minimal", "balanced", "immersive"])
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = root / args.config
    config = load_config(config_path)
    motion_level = args.motion or config.get("motion_level", "immersive")
    if motion_level not in MOTION_PRESETS:
        motion_level = "immersive"

    token = os.getenv("GH_TOKEN") or os.getenv("PROFILE_STATS_PAT") or os.getenv("GITHUB_TOKEN")

    warnings: List[str] = []
    user = fetch_user(args.username, token, warnings)
    repos_raw, data_mode = fetch_repositories(
        args.username,
        token,
        include_private=args.include_private,
        warnings=warnings,
    )
    repos = collect_repos(
        args.username,
        repos_raw,
        token,
        include_forks=args.include_forks,
        warnings=warnings,
    )

    snapshot = build_snapshot(args.username, config, user, repos, data_mode, warnings)

    output_dir = root / args.output_dir
    write(output_dir / "experience-dark.svg", render_experience(snapshot, config, "dark", motion_level, root))
    write(output_dir / "experience-light.svg", render_experience(snapshot, config, "light", motion_level, root))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
