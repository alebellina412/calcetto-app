from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIRS = [ROOT / "data", ROOT / "data_mock"]


def migrate_file(path: Path) -> bool:
    try:
        meta_df = pd.read_excel(path, sheet_name="meta")
        players_df = pd.read_excel(path, sheet_name="players")
    except Exception:
        return False

    if list(players_df.columns) == ["team", "player", "goals", "assists"]:
        return False
    if list(players_df.columns) != ["team", "player", "goals"]:
        return False

    players_df = players_df.copy()
    players_df["assists"] = 0

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        players_df.to_excel(writer, sheet_name="players", index=False)
    return True


def main() -> None:
    updated = 0
    scanned = 0
    for base in DATA_DIRS:
        matches_dir = base / "matches"
        if not matches_dir.exists():
            continue
        for path in sorted(matches_dir.glob("*.xlsx")):
            scanned += 1
            if migrate_file(path):
                updated += 1
    print(f"Scanned: {scanned}")
    print(f"Updated: {updated}")


if __name__ == "__main__":
    main()
