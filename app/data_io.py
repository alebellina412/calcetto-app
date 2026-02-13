from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass
class Player:
    id: int
    name: str


@dataclass
class MatchPlayerRow:
    team: str
    player: str
    goals: int
    assists: int = 0


@dataclass
class Match:
    match_id: str
    file_name: str
    date: date
    note: str
    players: list[MatchPlayerRow]
    goals_a_override: int | None = None
    goals_b_override: int | None = None

    @property
    def team_a(self) -> list[MatchPlayerRow]:
        return [p for p in self.players if p.team == "A"]

    @property
    def team_b(self) -> list[MatchPlayerRow]:
        return [p for p in self.players if p.team == "B"]

    @property
    def goals_a(self) -> int:
        if self.goals_a_override is not None:
            return self.goals_a_override
        return sum(p.goals for p in self.team_a)

    @property
    def goals_b(self) -> int:
        if self.goals_b_override is not None:
            return self.goals_b_override
        return sum(p.goals for p in self.team_b)

    @property
    def winner(self) -> str:
        if self.goals_a > self.goals_b:
            return "A"
        if self.goals_b > self.goals_a:
            return "B"
        return "Draw"


@dataclass
class InvalidMatchFile:
    file_name: str
    error: str


@dataclass
class DataBundle:
    players: list[Player]
    matches: list[Match]
    deleted_match_ids: set[str]
    invalid_files: list[InvalidMatchFile]


BASE_DIR = Path(__file__).resolve().parent.parent
REAL_DATA_DIR = Path(os.getenv("CALCETTO_DATA_DIR", str(BASE_DIR / "data"))).resolve()
MOCK_DATA_DIR = Path(os.getenv("CALCETTO_MOCK_DATA_DIR", str(BASE_DIR / "data_mock"))).resolve()


@dataclass(frozen=True)
class DataPaths:
    data_dir: Path
    players_file: Path
    matches_dir: Path
    deleted_file: Path


def _build_paths(data_dir: Path) -> DataPaths:
    return DataPaths(
        data_dir=data_dir,
        players_file=data_dir / "players.csv",
        matches_dir=data_dir / "matches",
        deleted_file=data_dir / "deleted_matches.json",
    )


def ensure_data_layout(paths: DataPaths) -> None:
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.matches_dir.mkdir(parents=True, exist_ok=True)

    if not paths.players_file.exists():
        pd.DataFrame(columns=["id", "name"]).to_csv(paths.players_file, index=False)

    if not paths.deleted_file.exists():
        paths.deleted_file.write_text("[]", encoding="utf-8")


def _has_usable_data(paths: DataPaths) -> bool:
    if not paths.players_file.exists() or not paths.matches_dir.exists():
        return False
    try:
        players_df = pd.read_csv(paths.players_file)
    except Exception:
        return False
    has_players = not players_df.empty
    has_matches = any(paths.matches_dir.glob("*.xlsx"))
    return has_players and has_matches


def _resolve_active_paths() -> DataPaths:
    real_paths = _build_paths(REAL_DATA_DIR)
    mock_paths = _build_paths(MOCK_DATA_DIR)
    ensure_data_layout(real_paths)
    ensure_data_layout(mock_paths)
    if _has_usable_data(real_paths):
        return real_paths
    return mock_paths


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def load_players() -> list[Player]:
    paths = _resolve_active_paths()
    df = pd.read_csv(paths.players_file)
    if df.empty:
        return []
    expected_cols = ["id", "name"]
    if list(df.columns) != expected_cols:
        raise ValueError(f"players.csv must have columns {expected_cols}")
    players: list[Player] = []
    for _, row in df.iterrows():
        players.append(Player(id=int(row["id"]), name=str(row["name"]).strip()))
    return players


def save_players(players: Iterable[Player]) -> None:
    paths = _resolve_active_paths()
    df = pd.DataFrame([{"id": p.id, "name": p.name} for p in players])
    df.to_csv(paths.players_file, index=False)


def add_player(name: str) -> Player:
    cleaned = " ".join(name.strip().split())
    if not cleaned:
        raise ValueError("Player name cannot be empty")

    players = load_players()
    normalized = _normalize_name(cleaned)
    if any(_normalize_name(p.name) == normalized for p in players):
        raise ValueError("Player name already exists")

    next_id = (max((p.id for p in players), default=0) + 1)
    new_player = Player(id=next_id, name=cleaned)
    players.append(new_player)
    save_players(players)
    return new_player


def load_deleted_matches() -> set[str]:
    paths = _resolve_active_paths()
    try:
        raw = json.loads(paths.deleted_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("deleted_matches.json is invalid JSON") from exc

    if not isinstance(raw, list):
        raise ValueError("deleted_matches.json must be a JSON list")

    return {str(item) for item in raw}


def save_deleted_matches(match_ids: set[str]) -> None:
    paths = _resolve_active_paths()
    paths.deleted_file.write_text(json.dumps(sorted(match_ids), indent=2), encoding="utf-8")


def soft_delete_match(match_id: str) -> None:
    deleted = load_deleted_matches()
    deleted.add(match_id)
    save_deleted_matches(deleted)


def _parse_match_excel(path: Path, valid_player_names: set[str]) -> Match:
    try:
        xls = pd.ExcelFile(path)
    except Exception as exc:  # pragma: no cover - broad for corrupted files
        raise ValueError(f"Cannot open Excel file: {exc}") from exc

    if sorted(xls.sheet_names) != ["meta", "players"]:
        raise ValueError("Excel file must contain exactly two sheets: meta and players")

    meta_df = pd.read_excel(path, sheet_name="meta")
    if len(meta_df.columns) != 2:
        raise ValueError("meta sheet must have 2 columns")
    meta_df = meta_df.iloc[:, :2]
    meta_df.columns = ["key", "value"]

    meta_map = {str(k).strip(): str(v).strip() for k, v in zip(meta_df["key"], meta_df["value"])}
    if "date" not in meta_map:
        raise ValueError("meta sheet must include key 'date'")

    try:
        match_date = datetime.strptime(meta_map["date"], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("meta date must be in format YYYY-MM-DD") from exc

    note = meta_map.get("note", "")
    goals_a_override: int | None = None
    goals_b_override: int | None = None
    if "goals_a" in meta_map and "goals_b" in meta_map:
        try:
            goals_a_override = int(meta_map["goals_a"])
            goals_b_override = int(meta_map["goals_b"])
        except ValueError as exc:
            raise ValueError("meta goals_a/goals_b must be integers") from exc

    players_df = pd.read_excel(path, sheet_name="players")
    cols = list(players_df.columns)
    if cols not in (["team", "player", "goals"], ["team", "player", "goals", "assists"]):
        raise ValueError("players sheet columns must be ['team','player','goals'] or ['team','player','goals','assists']")

    if len(players_df) < 2:
        raise ValueError("players sheet must contain at least 2 rows")

    rows: list[MatchPlayerRow] = []
    seen_players: set[str] = set()
    counts = {"A": 0, "B": 0}

    for i, row in players_df.iterrows():
        team = str(row["team"]).strip()
        player = str(row["player"]).strip()

        if team not in {"A", "B"}:
            raise ValueError(f"Row {i + 2}: team must be 'A' or 'B'")

        if player not in valid_player_names:
            raise ValueError(f"Row {i + 2}: unknown player '{player}'")

        if player in seen_players:
            raise ValueError(f"Row {i + 2}: duplicate player '{player}' in match")

        goals_value = row["goals"]
        if pd.isna(goals_value):
            raise ValueError(f"Row {i + 2}: goals cannot be empty")
        if int(goals_value) != goals_value:
            raise ValueError(f"Row {i + 2}: goals must be an integer")
        goals = int(goals_value)
        if goals < 0:
            raise ValueError(f"Row {i + 2}: goals must be >= 0")

        assists = 0
        if "assists" in players_df.columns:
            assists_value = row["assists"]
            if pd.isna(assists_value):
                assists_value = 0
            if int(assists_value) != assists_value:
                raise ValueError(f"Row {i + 2}: assists must be an integer")
            assists = int(assists_value)
            if assists < 0:
                raise ValueError(f"Row {i + 2}: assists must be >= 0")

        seen_players.add(player)
        counts[team] += 1
        rows.append(MatchPlayerRow(team=team, player=player, goals=goals, assists=assists))

    if counts["A"] == 0 or counts["B"] == 0:
        raise ValueError("players sheet must contain at least one player in each team")

    return Match(
        match_id=path.stem,
        file_name=path.name,
        date=match_date,
        note=note,
        players=rows,
        goals_a_override=goals_a_override,
        goals_b_override=goals_b_override,
    )


def load_matches(players: list[Player], deleted_match_ids: set[str] | None = None) -> tuple[list[Match], list[InvalidMatchFile]]:
    paths = _resolve_active_paths()
    deleted = deleted_match_ids or set()
    valid_names = {p.name for p in players}

    matches: list[Match] = []
    invalid_files: list[InvalidMatchFile] = []

    for path in sorted(paths.matches_dir.glob("*.xlsx")):
        if path.stem in deleted:
            continue
        try:
            match = _parse_match_excel(path, valid_names)
            matches.append(match)
        except Exception as exc:
            invalid_files.append(InvalidMatchFile(file_name=path.name, error=str(exc)))

    matches.sort(key=lambda m: (m.date, m.match_id), reverse=True)
    return matches, invalid_files


def load_bundle() -> DataBundle:
    players = load_players()
    deleted = load_deleted_matches()
    matches, invalid_files = load_matches(players=players, deleted_match_ids=deleted)
    return DataBundle(
        players=players,
        matches=matches,
        deleted_match_ids=deleted,
        invalid_files=invalid_files,
    )


def write_match_excel(match_date: date, note: str, rows: list[MatchPlayerRow]) -> str:
    paths = _resolve_active_paths()

    if len(rows) != 10:
        raise ValueError("A match must include exactly 10 player rows")

    team_a = [r for r in rows if r.team == "A"]
    team_b = [r for r in rows if r.team == "B"]
    if len(team_a) != 5 or len(team_b) != 5:
        raise ValueError("A match must include exactly 5 players in each team")

    names = [r.player for r in rows]
    if len(set(names)) != 10:
        raise ValueError("Duplicate players are not allowed in the same match")

    for r in rows:
        if r.goals < 0:
            raise ValueError("Goals must be >= 0")
        if r.assists < 0:
            raise ValueError("Assists must be >= 0")

    base_date = match_date.strftime('%Y-%m-%d')
    # Keep required filename format while avoiding collisions within the same second.
    for offset in range(0, 120):
        stamp = (datetime.now() + timedelta(seconds=offset)).strftime('%H%M%S')
        candidate = f"{base_date}__{stamp}__match"
        file_path = paths.matches_dir / f"{candidate}.xlsx"
        if not file_path.exists():
            match_id = candidate
            break
    else:
        raise ValueError("Could not generate a unique match filename")

    goals_a = sum(r.goals for r in team_a)
    goals_b = sum(r.goals for r in team_b)
    meta_df = pd.DataFrame(
        [
            {"key": "date", "value": match_date.strftime("%Y-%m-%d")},
            {"key": "note", "value": note or ""},
            {"key": "goals_a", "value": goals_a},
            {"key": "goals_b", "value": goals_b},
        ]
    )
    players_df = pd.DataFrame(
        [{"team": r.team, "player": r.player, "goals": r.goals, "assists": r.assists} for r in rows]
    )

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        players_df.to_excel(writer, sheet_name="players", index=False)

    return match_id


def initialize_data_dirs() -> None:
    ensure_data_layout(_build_paths(REAL_DATA_DIR))
    ensure_data_layout(_build_paths(MOCK_DATA_DIR))
