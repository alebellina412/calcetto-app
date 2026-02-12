from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
import random
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


@dataclass
class Match:
    match_id: str
    file_name: str
    date: date
    note: str
    players: list[MatchPlayerRow]

    @property
    def team_a(self) -> list[MatchPlayerRow]:
        return [p for p in self.players if p.team == "A"]

    @property
    def team_b(self) -> list[MatchPlayerRow]:
        return [p for p in self.players if p.team == "B"]

    @property
    def goals_a(self) -> int:
        return sum(p.goals for p in self.team_a)

    @property
    def goals_b(self) -> int:
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
DATA_DIR = Path(os.getenv("CALCETTO_DATA_DIR", str(BASE_DIR / "data"))).resolve()
PLAYERS_FILE = DATA_DIR / "players.csv"
MATCHES_DIR = DATA_DIR / "matches"
DELETED_FILE = DATA_DIR / "deleted_matches.json"


def ensure_data_layout() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)

    if not PLAYERS_FILE.exists():
        pd.DataFrame(columns=["id", "name"]).to_csv(PLAYERS_FILE, index=False)

    if not DELETED_FILE.exists():
        DELETED_FILE.write_text("[]", encoding="utf-8")


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def load_players() -> list[Player]:
    ensure_data_layout()
    df = pd.read_csv(PLAYERS_FILE)
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
    ensure_data_layout()
    df = pd.DataFrame([{"id": p.id, "name": p.name} for p in players])
    df.to_csv(PLAYERS_FILE, index=False)


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
    ensure_data_layout()
    try:
        raw = json.loads(DELETED_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("deleted_matches.json is invalid JSON") from exc

    if not isinstance(raw, list):
        raise ValueError("deleted_matches.json must be a JSON list")

    return {str(item) for item in raw}


def save_deleted_matches(match_ids: set[str]) -> None:
    ensure_data_layout()
    DELETED_FILE.write_text(json.dumps(sorted(match_ids), indent=2), encoding="utf-8")


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

    players_df = pd.read_excel(path, sheet_name="players")
    expected_cols = ["team", "player", "goals"]
    if list(players_df.columns) != expected_cols:
        raise ValueError(f"players sheet must have columns exactly {expected_cols}")

    if len(players_df) != 10:
        raise ValueError("players sheet must contain exactly 10 rows")

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

        seen_players.add(player)
        counts[team] += 1
        rows.append(MatchPlayerRow(team=team, player=player, goals=goals))

    if counts["A"] != 5 or counts["B"] != 5:
        raise ValueError("players sheet must contain exactly 5 players in A and 5 in B")

    return Match(
        match_id=path.stem,
        file_name=path.name,
        date=match_date,
        note=note,
        players=rows,
    )


def load_matches(players: list[Player], deleted_match_ids: set[str] | None = None) -> tuple[list[Match], list[InvalidMatchFile]]:
    ensure_data_layout()
    deleted = deleted_match_ids or set()
    valid_names = {p.name for p in players}

    matches: list[Match] = []
    invalid_files: list[InvalidMatchFile] = []

    for path in sorted(MATCHES_DIR.glob("*.xlsx")):
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
    ensure_data_layout()

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

    base_date = match_date.strftime('%Y-%m-%d')
    # Keep required filename format while avoiding collisions within the same second.
    for offset in range(0, 120):
        stamp = (datetime.now() + timedelta(seconds=offset)).strftime('%H%M%S')
        candidate = f"{base_date}__{stamp}__match"
        file_path = MATCHES_DIR / f"{candidate}.xlsx"
        if not file_path.exists():
            match_id = candidate
            break
    else:
        raise ValueError("Could not generate a unique match filename")

    meta_df = pd.DataFrame([{"key": "date", "value": match_date.strftime("%Y-%m-%d")}, {"key": "note", "value": note or ""}])
    players_df = pd.DataFrame([{"team": r.team, "player": r.player, "goals": r.goals} for r in rows])

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        meta_df.to_excel(writer, sheet_name="meta", index=False)
        players_df.to_excel(writer, sheet_name="players", index=False)

    return match_id


def bootstrap_mock_data_if_needed() -> None:
    ensure_data_layout()

    players = load_players()
    has_match_files = any(MATCHES_DIR.glob("*.xlsx"))

    if players and has_match_files:
        return

    if not players:
        first_names = [
            "Luca", "Marco", "Davide", "Andrea", "Matteo", "Francesco", "Simone", "Alessio", "Riccardo", "Stefano",
            "Federico", "Gabriele", "Leonardo", "Tommaso", "Nicolo", "Giulio", "Edoardo", "Filippo", "Daniele", "Pietro",
        ]
        last_names = [
            "Rossi", "Bianchi", "Romano", "Gallo", "Costa", "Conti", "Moretti", "Greco", "Ferrari", "Esposito",
            "Ricci", "Marino", "Giordano", "Lombardi", "Barbieri", "Rinaldi", "Caruso", "Fontana", "Serra", "Villa",
        ]
        generated: list[Player] = []
        used: set[str] = set()
        while len(generated) < 20:
            candidate = f"{random.choice(first_names)} {random.choice(last_names)}"
            key = _normalize_name(candidate)
            if key in used:
                continue
            used.add(key)
            generated.append(Player(id=len(generated) + 1, name=candidate))
        save_players(generated)
        players = generated

    if not has_match_files:
        rng = random.Random(42)
        today = date.today()
        all_names = [p.name for p in players]
        for i in range(15):
            days_ago = rng.randint(0, 90)
            d = today - timedelta(days=days_ago)
            selected = rng.sample(all_names, 10)
            rows: list[MatchPlayerRow] = []
            for idx, name in enumerate(selected):
                team = "A" if idx < 5 else "B"
                goals = rng.randint(0, 4)
                rows.append(MatchPlayerRow(team=team, player=name, goals=goals))
            note = f"Mock match {i + 1}"
            write_match_excel(match_date=d, note=note, rows=rows)
