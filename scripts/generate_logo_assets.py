#!/usr/bin/env python3
"""Generate local SVG logo tiles for tech stack and AI platforms."""

from __future__ import annotations

from pathlib import Path

LOGOS = {
    # Core tech
    "python": {"label": "Python", "mark": "Py", "c1": "#3776AB", "c2": "#FFD43B"},
    "typescript": {"label": "TypeScript", "mark": "TS", "c1": "#3178C6", "c2": "#60A5FA"},
    "javascript": {"label": "JavaScript", "mark": "JS", "c1": "#F7DF1E", "c2": "#F59E0B"},
    "vue": {"label": "Vue", "mark": "Vue", "c1": "#42B883", "c2": "#35495E"},
    "react": {"label": "React", "mark": "R", "c1": "#61DAFB", "c2": "#0891B2"},
    "tailwind": {"label": "Tailwind", "mark": "TW", "c1": "#06B6D4", "c2": "#0EA5E9"},
    "fastapi": {"label": "FastAPI", "mark": "FA", "c1": "#009688", "c2": "#14B8A6"},
    "mysql": {"label": "MySQL", "mark": "SQL", "c1": "#0EA5E9", "c2": "#1E3A8A"},
    "redis": {"label": "Redis", "mark": "RD", "c1": "#DC382D", "c2": "#EF4444"},
    "docker": {"label": "Docker", "mark": "DK", "c1": "#2496ED", "c2": "#38BDF8"},
    "git": {"label": "Git", "mark": "Git", "c1": "#F05032", "c2": "#FB7185"},
    "linux": {"label": "Linux", "mark": "Lx", "c1": "#111827", "c2": "#374151"},
    "java": {"label": "Java", "mark": "Jv", "c1": "#EA580C", "c2": "#F97316"},
    "html5": {"label": "HTML5", "mark": "H5", "c1": "#E34F26", "c2": "#F97316"},
    "css3": {"label": "CSS3", "mark": "C3", "c1": "#1572B6", "c2": "#3B82F6"},
    "nodejs": {"label": "Node.js", "mark": "Nd", "c1": "#339933", "c2": "#65A30D"},
    "postgresql": {"label": "PostgreSQL", "mark": "PG", "c1": "#336791", "c2": "#60A5FA"},
    "go": {"label": "Go", "mark": "Go", "c1": "#00ADD8", "c2": "#22D3EE"},
    "rust": {"label": "Rust", "mark": "Rs", "c1": "#B45309", "c2": "#92400E"},
    "vite": {"label": "Vite", "mark": "Vt", "c1": "#646CFF", "c2": "#A78BFA"},
    # AI platforms
    "openai": {"label": "OpenAI", "mark": "OA", "c1": "#10A37F", "c2": "#34D399"},
    "anthropic": {"label": "Anthropic", "mark": "An", "c1": "#D97706", "c2": "#F59E0B"},
    "gemini": {"label": "Gemini", "mark": "Gm", "c1": "#7C3AED", "c2": "#3B82F6"},
    "huggingface": {"label": "Hugging Face", "mark": "HF", "c1": "#F59E0B", "c2": "#FDE68A"},
    "aws": {"label": "AWS", "mark": "AWS", "c1": "#111827", "c2": "#F59E0B"},
    "azure": {"label": "Azure", "mark": "Az", "c1": "#0078D4", "c2": "#38BDF8"},
    "groq": {"label": "Groq", "mark": "Gq", "c1": "#4F46E5", "c2": "#22D3EE"},
    "cohere": {"label": "Cohere", "mark": "Ch", "c1": "#9333EA", "c2": "#EC4899"},
}


def render_tile(label: str, mark: str, c1: str, c2: str) -> str:
    return f'''<svg width="256" height="112" viewBox="0 0 256 112" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label} logo tile">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{c1}"/>
    <stop offset="100%" stop-color="{c2}"/>
  </linearGradient>
  <filter id="b" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="8" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect x="0.5" y="0.5" width="255" height="111" rx="18" fill="#0B1220" stroke="#1F2A44"/>
<rect x="0.5" y="0.5" width="255" height="111" rx="18" fill="url(#g)" fill-opacity="0.10"/>
<circle cx="56" cy="56" r="26" fill="url(#g)" filter="url(#b)"/>
<text x="56" y="62" text-anchor="middle" fill="#E2E8F0" font-size="22" font-family="SF Pro Display, Segoe UI, Arial, sans-serif" font-weight="700">{mark}</text>
<text x="96" y="63" fill="#E2E8F0" font-size="20" font-family="SF Pro Display, Segoe UI, Arial, sans-serif" font-weight="600">{label}</text>
</svg>
'''


def main() -> int:
    out_dir = Path(__file__).resolve().parents[1] / "assets" / "logos"
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, spec in LOGOS.items():
        content = render_tile(spec["label"], spec["mark"], spec["c1"], spec["c2"])
        (out_dir / f"{key}.svg").write_text(content, encoding="utf-8")
    print(f"generated {len(LOGOS)} logo files -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
