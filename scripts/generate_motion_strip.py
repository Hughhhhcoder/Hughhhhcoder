#!/usr/bin/env python3
"""Generate animated motion strip SVG for README section transitions."""

from __future__ import annotations

import argparse
from pathlib import Path

THEME = {
    "dark": {
        "bg0": "#020617",
        "bg1": "#0b1220",
        "bg2": "#062029",
        "line": "#22d3ee",
        "line_soft": "#0ea5e9",
        "dot": "#67e8f9",
        "stroke": "#1f2937",
        "scan": "#22d3ee",
    },
    "light": {
        "bg0": "#f8fafc",
        "bg1": "#eff6ff",
        "bg2": "#e0f2fe",
        "line": "#0284c7",
        "line_soft": "#0ea5e9",
        "dot": "#0891b2",
        "stroke": "#cbd5e1",
        "scan": "#0ea5e9",
    },
}


def render(theme: str, width: int, height: int) -> str:
    t = THEME[theme]
    lines = []
    lines.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated motion strip">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{t["bg0"]}"/>'
        f'<stop offset="50%" stop-color="{t["bg1"]}"/>'
        f'<stop offset="100%" stop-color="{t["bg2"]}"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="transparent"/>'
        f'<stop offset="50%" stop-color="{t["scan"]}" stop-opacity="0.28"/>'
        '<stop offset="100%" stop-color="transparent"/>'
        "</linearGradient>"
    )
    lines.append(
        '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="1.8" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="16" '
        f'fill="url(#bg)" stroke="{t["stroke"]}"/>'
    )

    # horizontal signal lines
    for i in range(8):
        y = 18 + i * 16
        opacity = 0.12 + (i % 3) * 0.06
        dur = 8 + i
        lines.append(
            f'<line x1="16" y1="{y}" x2="{width-16}" y2="{y}" '
            f'stroke="{t["line_soft"]}" stroke-opacity="{opacity:.2f}" stroke-width="1">'
            f'<animate attributeName="stroke-dasharray" values="0,1400;280,1120;0,1400" dur="{dur}s" '
            'repeatCount="indefinite"/></line>'
        )

    # vertical beams
    for i in range(10):
        x = 50 + i * 90
        dur = 10 + i * 0.6
        lines.append(
            f'<rect x="{x}" y="12" width="2" height="{height-24}" fill="{t["line"]}" opacity="0.12">'
            f'<animate attributeName="opacity" values="0.05;0.2;0.05" dur="{dur:.1f}s" repeatCount="indefinite"/></rect>'
        )

    # moving scan band
    lines.append(
        f'<rect x="-{width}" y="0" width="{width}" height="{height}" fill="url(#scan)">'
        f'<animate attributeName="x" values="-{width};{width}" dur="9.5s" repeatCount="indefinite"/></rect>'
    )

    # orbiting particles
    for i in range(20):
        cx = 24 + i * ((width - 48) / 19)
        cy = 24 + (i % 5) * ((height - 48) / 4)
        dur = 7.5 + (i % 6) * 0.9
        dy = 6 + (i % 4) * 2
        lines.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="1.9" fill="{t["dot"]}" filter="url(#glow)">'
            f'<animate attributeName="cy" values="{cy:.2f};{cy+dy:.2f};{cy:.2f}" dur="{dur:.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.2;0.95;0.2" dur="{dur:.1f}s" repeatCount="indefinite"/></circle>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--theme", choices=sorted(THEME.keys()), default="dark")
    parser.add_argument("--width", type=int, default=980)
    parser.add_argument("--height", type=int, default=130)
    args = parser.parse_args()

    svg = render(theme=args.theme, width=args.width, height=args.height)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
