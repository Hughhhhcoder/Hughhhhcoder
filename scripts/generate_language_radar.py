#!/usr/bin/env python3
"""Generate a dual-view language spectrum SVG from GitHub repo language stats."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


API_BASE = "https://api.github.com"
USER_AGENT = "language-radar-generator/2.0"

THEME_STYLES = {
    "dark": {
        "palette": [
            "#22d3ee",
            "#38bdf8",
            "#14b8a6",
            "#0ea5e9",
            "#2dd4bf",
            "#06b6d4",
            "#10b981",
            "#67e8f9",
            "#7dd3fc",
        ],
        "bg0": "#020617",
        "bg1": "#0b1220",
        "bg2": "#062029",
        "header0": "#22d3ee",
        "header1": "#0ea5e9",
        "panel0": "#0f172a",
        "panel1": "#111827",
        "stroke": "#1f2937",
        "text_title": "#e2e8f0",
        "text_body": "#cbd5e1",
        "text_dim": "#94a3b8",
        "text_accent": "#7dd3fc",
        "track": "#0b1220",
        "inner": "#050b16",
        "scan": "#22d3ee",
        "shine": "#e0f2fe",
        "ring_dash": "#0e7490",
        "outer_ring": "#0f2c3a",
    },
    "light": {
        "palette": [
            "#0284c7",
            "#0ea5e9",
            "#0f766e",
            "#2563eb",
            "#14b8a6",
            "#0891b2",
            "#22c55e",
            "#06b6d4",
            "#38bdf8",
        ],
        "bg0": "#f8fafc",
        "bg1": "#f1f5f9",
        "bg2": "#e2e8f0",
        "header0": "#0ea5e9",
        "header1": "#0284c7",
        "panel0": "#ffffff",
        "panel1": "#f8fafc",
        "stroke": "#cbd5e1",
        "text_title": "#0f172a",
        "text_body": "#1e293b",
        "text_dim": "#475569",
        "text_accent": "#0369a1",
        "track": "#e2e8f0",
        "inner": "#ffffff",
        "scan": "#0ea5e9",
        "shine": "#f8fafc",
        "ring_dash": "#38bdf8",
        "outer_ring": "#bae6fd",
    },
}


def fetch_json(url: str, token: str | None) -> object:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", USER_AGENT)
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while requesting: {url}") from exc


def fetch_repositories(username: str, token: str | None, include_private: bool) -> List[dict]:
    repos: List[dict] = []
    page = 1
    while True:
        if include_private:
            if not token:
                raise RuntimeError("include_private requires GH_TOKEN or GITHUB_TOKEN.")
            url = (
                f"{API_BASE}/user/repos"
                f"?per_page=100&page={page}&visibility=all&affiliation=owner&sort=updated"
            )
        else:
            url = (
                f"{API_BASE}/users/{username}/repos"
                f"?per_page=100&page={page}&type=owner&sort=updated"
            )

        page_data = fetch_json(url, token)
        if not isinstance(page_data, list):
            raise RuntimeError("Unexpected response while fetching repositories.")
        if not page_data:
            break

        if include_private:
            owner_repos = [
                repo
                for repo in page_data
                if isinstance(repo, dict)
                and isinstance(repo.get("owner"), dict)
                and str(repo["owner"].get("login", "")).lower() == username.lower()
            ]
            repos.extend(owner_repos)
        else:
            repos.extend(page_data)

        if len(page_data) < 100:
            break
        page += 1
    return repos


def aggregate_languages(
    repos: Iterable[dict], token: str | None, include_forks: bool
) -> Tuple[Dict[str, int], int]:
    totals: Dict[str, int] = defaultdict(int)
    repo_count = 0

    for repo in repos:
        if not include_forks and repo.get("fork", False):
            continue
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        data = fetch_json(str(languages_url), token)
        if not isinstance(data, dict):
            continue
        repo_count += 1
        for lang, size in data.items():
            if isinstance(lang, str) and isinstance(size, int) and size > 0:
                totals[lang] += size

    return totals, repo_count


def build_language_rows(totals: Dict[str, int], max_rows: int) -> Tuple[List[Tuple[str, int, float]], int]:
    grand_total = sum(totals.values())
    if grand_total <= 0:
        return [], 0

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if len(ranked) <= max_rows:
        rows = ranked
    else:
        head = ranked[:max_rows]
        others = sum(value for _, value in ranked[max_rows:])
        rows = head + [("Other", others)]

    result = [(lang, size, (size / grand_total) * 100.0) for lang, size in rows]
    return result, grand_total


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def polar_to_cartesian(cx: float, cy: float, r: float, angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg)
    return cx + (r * math.cos(rad)), cy + (r * math.sin(rad))


def arc_path(cx: float, cy: float, r: float, start_deg: float, sweep_deg: float) -> str:
    start_x, start_y = polar_to_cartesian(cx, cy, r, start_deg)
    end_x, end_y = polar_to_cartesian(cx, cy, r, start_deg + sweep_deg)
    large_arc = 1 if sweep_deg > 180 else 0
    return (
        f"M {start_x:.2f} {start_y:.2f} "
        f"A {r:.2f} {r:.2f} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f}"
    )


def compact_bytes(size: int) -> str:
    if size >= 1_000_000_000:
        return f"{size / 1_000_000_000:.2f} GB"
    if size >= 1_000_000:
        return f"{size / 1_000_000:.2f} MB"
    if size >= 1_000:
        return f"{size / 1_000:.2f} KB"
    return f"{size} B"


def render_svg(
    username: str,
    rows: List[Tuple[str, int, float]],
    total_bytes: int,
    repo_count: int,
    generated_at: dt.datetime,
    theme: str,
) -> str:
    style = THEME_STYLES[theme]

    width = 980
    panel_top = 138
    row_height = 44
    row_count = max(len(rows), 1)
    bars_top = panel_top + 56
    bars_bottom = bars_top + (row_count * row_height)
    height = max(560, int(bars_bottom + 72))

    max_bar_width = 300
    bar_x = 612
    label_x = 470
    pct_x = 930

    donut_cx = 225
    donut_cy = panel_top + 205
    donut_r = 116
    donut_stroke = 36

    lines: List[str] = []
    lines.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'fill="none" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="Language spectrum">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{style["bg0"]}"/>'
        f'<stop offset="55%" stop-color="{style["bg1"]}"/>'
        f'<stop offset="100%" stop-color="{style["bg2"]}"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="header" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{style["header0"]}"/>'
        f'<stop offset="100%" stop-color="{style["header1"]}"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{style["panel0"]}"/>'
        f'<stop offset="100%" stop-color="{style["panel1"]}"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="transparent"/>'
        f'<stop offset="50%" stop-color="{style["scan"]}" stop-opacity="0.16"/>'
        '<stop offset="100%" stop-color="transparent"/>'
        "</linearGradient>"
    )
    lines.append(
        '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="2.5" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="24" '
        f'fill="url(#bg)" stroke="{style["stroke"]}"/>'
    )
    lines.append(
        '<rect x="24" y="24" width="932" height="92" rx="14" '
        f'fill="{style["panel0"]}" stroke="{style["stroke"]}"/>'
    )
    lines.append(
        '<rect x="24" y="24" width="932" height="92" rx="14" fill="url(#header)" opacity="0.10"/>'
    )

    # sweeping scan across the full card
    lines.append(
        f'<rect x="-980" y="0" width="980" height="{height}" fill="url(#scan)">'
        '<animate attributeName="x" values="-980;980" dur="11s" repeatCount="indefinite"/>'
        "</rect>"
    )

    lines.append(
        '<text x="42" y="61" font-size="24" '
        f'fill="{style["text_title"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace" '
        'font-weight="700">Language Spectrum • Dual View</text>'
    )
    lines.append(
        f'<text x="42" y="88" font-size="14" fill="{style["text_accent"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
        f'@{esc(username)} | repositories scanned: {repo_count} | total bytes: {total_bytes:,}</text>'
    )
    lines.append(
        f'<text x="42" y="108" font-size="12" fill="{style["text_dim"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
        f'updated: {generated_at.strftime("%Y-%m-%d %H:%M UTC")}</text>'
    )

    lines.append(
        f'<rect x="24" y="{panel_top}" width="410" height="{height - panel_top - 24}" rx="16" '
        f'fill="url(#panel)" stroke="{style["stroke"]}"/>'
    )
    lines.append(
        f'<rect x="446" y="{panel_top}" width="510" height="{height - panel_top - 24}" rx="16" '
        f'fill="url(#panel)" stroke="{style["stroke"]}"/>'
    )
    lines.append(
        f'<text x="44" y="{panel_top + 28}" font-size="14" fill="{style["text_accent"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace" '
        'font-weight="700">Donut Radar</text>'
    )
    lines.append(
        f'<text x="468" y="{panel_top + 28}" font-size="14" fill="{style["text_accent"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace" '
        'font-weight="700">Percentage Bars</text>'
    )

    if not rows:
        lines.append(
            f'<text x="42" y="180" font-size="15" fill="{style["text_dim"]}" '
            'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
            "No language data found.</text>"
        )
        lines.append("</svg>")
        return "\n".join(lines) + "\n"

    lines.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r}" '
        f'fill="none" stroke="{style["stroke"]}" stroke-width="36"/>'
    )
    lines.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r + 20}" '
        f'fill="none" stroke="{style["outer_ring"]}" stroke-width="1.2" opacity="0.9"/>'
    )
    lines.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r + 31}" fill="none" '
        f'stroke="{style["ring_dash"]}" stroke-width="1" opacity="0.35" stroke-dasharray="4 8">'
        f'<animateTransform attributeName="transform" type="rotate" from="0 {donut_cx} {donut_cy}" '
        f'to="360 {donut_cx} {donut_cy}" dur="24s" repeatCount="indefinite"/></circle>'
    )

    angle = -90.0
    gap = 1.4
    palette = style["palette"]
    for idx, (_, _, pct) in enumerate(rows):
        color = palette[idx % len(palette)]
        sweep = (pct / 100.0) * 360.0
        if sweep <= 0:
            continue
        if sweep >= 359.9:
            lines.append(
                f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r}" fill="none" '
                f'stroke="{color}" stroke-width="{donut_stroke}" stroke-linecap="round"/>'
            )
            continue
        actual_sweep = max(0.1, sweep - gap)
        start_angle = angle + (gap / 2.0)
        path = arc_path(donut_cx, donut_cy, donut_r, start_angle, actual_sweep)
        lines.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{donut_stroke}" '
            'stroke-linecap="round" filter="url(#glow)"/>'
        )
        angle += sweep

    lines.append(
        f'<circle cx="{donut_cx}" cy="{donut_cy}" r="{donut_r - (donut_stroke / 2) - 7}" '
        f'fill="{style["inner"]}" stroke="{style["stroke"]}"/>'
    )
    lines.append(
        f'<text x="{donut_cx}" y="{donut_cy - 6}" text-anchor="middle" '
        f'font-size="13" fill="{style["text_dim"]}" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
        "TOTAL CODE</text>"
    )
    lines.append(
        f'<text x="{donut_cx}" y="{donut_cy + 16}" text-anchor="middle" '
        f'font-size="18" fill="{style["text_title"]}" font-weight="700" '
        'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
        f"{compact_bytes(total_bytes)}</text>"
    )

    legend_y = donut_cy + donut_r + 26
    for idx, (lang, _, pct) in enumerate(rows[:4]):
        color = palette[idx % len(palette)]
        lx = 54 + ((idx % 2) * 170)
        ly = legend_y + ((idx // 2) * 22)
        lines.append(f'<circle cx="{lx}" cy="{ly}" r="5" fill="{color}"/>')
        lines.append(
            f'<text x="{lx + 12}" y="{ly + 4}" font-size="12.5" fill="{style["text_body"]}" '
            'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
            f"{esc(lang)} {pct:.1f}%</text>"
        )

    for idx, (lang, _, pct) in enumerate(rows):
        y = bars_top + idx * row_height
        bar_width = max(8, int(max_bar_width * pct / 100))
        color = palette[idx % len(palette)]

        lines.append(
            f'<text x="{label_x}" y="{y+14}" font-size="14" fill="{style["text_body"]}" '
            'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
            f"{esc(lang)}</text>"
        )
        lines.append(
            f'<text x="{pct_x}" y="{y+14}" text-anchor="end" font-size="13" '
            f'fill="{style["text_accent"]}" '
            'font-family="JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace">'
            f"{pct:5.2f}%</text>"
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y}" width="{max_bar_width}" height="16" rx="8" '
            f'fill="{style["track"]}" stroke="{style["stroke"]}"/>'
        )
        lines.append(
            f'<rect x="{bar_x}" y="{y}" width="{bar_width}" height="16" rx="8" fill="{color}" '
            'filter="url(#glow)" opacity="0.95"/>'
        )

        shimmer_w = max(16, int(bar_width * 0.25))
        shimmer_start = bar_x
        shimmer_end = bar_x + max(2, bar_width - shimmer_w)
        lines.append(
            f'<rect x="{shimmer_start}" y="{y+2}" width="{shimmer_w}" height="12" rx="6" '
            f'fill="{style["shine"]}" opacity="0.30">'
            f'<animate attributeName="x" values="{shimmer_start};{shimmer_end};{shimmer_start}" '
            f'dur="{6.0 + (idx * 0.4):.1f}s" repeatCount="indefinite"/></rect>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--output", required=True, help="Output SVG path")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=7,
        help="How many languages to display before grouping into Other",
    )
    parser.add_argument(
        "--include-forks",
        action="store_true",
        help="Include forked repositories in aggregation",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private repositories accessible by the token owner",
    )
    parser.add_argument(
        "--theme",
        choices=sorted(THEME_STYLES.keys()),
        default="dark",
        help="Visual theme for generated SVG",
    )
    args = parser.parse_args()

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    repos = fetch_repositories(
        username=args.username,
        token=token,
        include_private=args.include_private,
    )
    totals, repo_count = aggregate_languages(repos, token, args.include_forks)
    rows, total_bytes = build_language_rows(totals, max_rows=args.max_rows)

    svg = render_svg(
        username=args.username,
        rows=rows,
        total_bytes=total_bytes,
        repo_count=repo_count,
        generated_at=dt.datetime.now(dt.timezone.utc),
        theme=args.theme,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
