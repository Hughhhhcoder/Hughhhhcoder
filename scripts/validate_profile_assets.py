#!/usr/bin/env python3
"""Validate generated profile SVG assets for GitHub-safe rendering."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXTERNAL_REF_PATTERNS = [
    re.compile(r'href="https?://', re.IGNORECASE),
    re.compile(r'xlink:href="https?://', re.IGNORECASE),
    re.compile(r'url\(https?://', re.IGNORECASE),
]


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.exists():
        return [f"missing file: {path}"]

    content = path.read_text(encoding="utf-8")

    if "<svg" not in content or "viewBox=" not in content:
        errors.append(f"{path}: invalid svg root or missing viewBox")

    for pattern in EXTERNAL_REF_PATTERNS:
        if pattern.search(content):
            errors.append(f"{path}: found external url reference ({pattern.pattern})")

    width_match = re.search(r'width="([0-9.]+)"', content)
    height_match = re.search(r'height="([0-9.]+)"', content)
    if width_match and height_match:
        try:
            width = float(width_match.group(1))
            height = float(height_match.group(1))
            if width < 900:
                errors.append(f"{path}: width too small ({width})")
            if height < 1200:
                errors.append(f"{path}: height too small ({height})")
        except ValueError:
            errors.append(f"{path}: width/height parse error")

    font_sizes = [float(v) for v in re.findall(r'font-size="([0-9.]+)"', content)]
    small_fonts = [v for v in font_sizes if v < 14.0]
    if small_fonts:
        errors.append(f"{path}: found font-size below 14 ({min(small_fonts):.1f})")

    if content.count("<image ") < 12:
        errors.append(f"{path}: expected logo image embeds not found")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", nargs="+", required=True)
    args = parser.parse_args()

    all_errors: list[str] = []
    for file_str in args.files:
        all_errors.extend(validate_file(Path(file_str)))

    if all_errors:
        for err in all_errors:
            print(err)
        return 1

    print("profile assets validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
