from __future__ import annotations
import re
from datetime import date

# Season 2 starts after this date
SEASON2_START = date(2025, 5, 1)

def _extract_mvp_name(note: str) -> str:
    """Extract MVP surname/name from match note."""
    if not note:
        return ""
    # Expected format: 'mvp=<name>' somewhere in the note string.
    m = re.search(r'mvp=([^;]+)', note, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _month_label(d: date) -> str:
    """Return a short month label like 'Gen'25'."""
    months = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
               "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    return f"{months[d.month - 1]}'{str(d.year)[2:]}"

def normalize_name(value: str) -> str:
    """Normalize player name (lowercase, stripped)."""
    return " ".join(value.strip().split()).lower()
