"""Explicit item selection for non-publishable chapter pilots."""

from __future__ import annotations

import re


def parse_items(value: str) -> list[int]:
    """Parse a nonempty, strictly increasing comma-separated item selection."""
    if not re.fullmatch(r"[0-9]+(?:,[0-9]+)*", value):
        raise ValueError("--items must be comma-separated positive integers")
    items = [int(part) for part in value.split(",")]
    if any(item < 1 for item in items) or items != sorted(set(items)):
        raise ValueError("--items must be positive, unique and increasing")
    return items


def select_source(lines: list[str], items: list[int]) -> list[str]:
    """Keep the intro and selected original items, rejecting unknown IDs."""
    selected = []
    found = set()
    keep = True
    for line in lines:
        match = re.match(r"^### (\d+)\.", line)
        if match:
            item = int(match[1])
            keep = item in items
            if keep:
                found.add(item)
        if keep:
            selected.append(line)
    missing = set(items) - found
    if missing:
        raise ValueError(f"unknown source items: {sorted(missing)}")
    return selected
