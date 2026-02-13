from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .data_io import Match


@dataclass
class PlayerStats:
    name: str
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_scored: int = 0
    assists: int = 0
    goals_conceded: int = 0

    @property
    def win_rate(self) -> float:
        if self.matches == 0:
            return 0.0
        return self.wins / self.matches

    @property
    def elo_placeholder(self) -> float:
        return self.win_rate * 1000.0

    @property
    def goals_per_match(self) -> float:
        if self.matches == 0:
            return 0.0
        return self.goals_scored / self.matches


@dataclass
class TimelinePoint:
    date: str
    elo: float


@dataclass
class MatchView:
    match_id: str
    date: str
    note: str
    goals_a: int
    goals_b: int
    winner: str
    team_a_players: list[str] = field(default_factory=list)
    team_b_players: list[str] = field(default_factory=list)


@dataclass
class DashboardData:
    top_scorers: list[PlayerStats]
    top_assists: list[PlayerStats]
    goals_per_match_ranking: list[PlayerStats]
    win_rate_ranking: list[PlayerStats]
    elo_ranking: list[PlayerStats]
    latest_matches: list[MatchView]


def compute_player_stats(matches: list[Match], player_names: list[str]) -> dict[str, PlayerStats]:
    stats = {name: PlayerStats(name=name) for name in player_names}

    for match in matches:
        goals_a = match.goals_a
        goals_b = match.goals_b
        result_a = "draw"
        result_b = "draw"
        if goals_a > goals_b:
            result_a = "win"
            result_b = "loss"
        elif goals_b > goals_a:
            result_a = "loss"
            result_b = "win"

        for row in match.team_a:
            p = stats[row.player]
            p.matches += 1
            p.goals_scored += row.goals
            p.assists += row.assists
            p.goals_conceded += goals_b
            if result_a == "win":
                p.wins += 1
            elif result_a == "loss":
                p.losses += 1
            else:
                p.draws += 1

        for row in match.team_b:
            p = stats[row.player]
            p.matches += 1
            p.goals_scored += row.goals
            p.assists += row.assists
            p.goals_conceded += goals_a
            if result_b == "win":
                p.wins += 1
            elif result_b == "loss":
                p.losses += 1
            else:
                p.draws += 1

    return stats


def match_to_view(match: Match) -> MatchView:
    return MatchView(
        match_id=match.match_id,
        date=match.date.strftime("%Y-%m-%d"),
        note=match.note,
        goals_a=match.goals_a,
        goals_b=match.goals_b,
        winner=match.winner,
        team_a_players=[f"{r.player} (G:{r.goals}, A:{r.assists})" for r in match.team_a],
        team_b_players=[f"{r.player} (G:{r.goals}, A:{r.assists})" for r in match.team_b],
    )


def build_dashboard(matches: list[Match], player_names: list[str]) -> DashboardData:
    stats_by_player = compute_player_stats(matches, player_names)
    all_stats = list(stats_by_player.values())

    top_scorers = sorted(all_stats, key=lambda s: (s.goals_scored, -s.matches, s.name.lower()), reverse=True)[:10]
    top_assists = sorted(all_stats, key=lambda s: (s.assists, -s.matches, s.name.lower()), reverse=True)[:10]
    goals_per_match_ranking = sorted(
        [s for s in all_stats if s.matches >= 1],
        key=lambda s: (s.goals_per_match, s.matches, s.name.lower()),
        reverse=True,
    )[:10]
    win_rate_ranking = sorted(
        [s for s in all_stats if s.matches >= 1],
        key=lambda s: (s.win_rate, s.matches, s.name.lower()),
        reverse=True,
    )[:10]
    elo_ranking = sorted(all_stats, key=lambda s: (s.elo_placeholder, s.matches, s.name.lower()), reverse=True)[:10]

    latest_matches = [match_to_view(m) for m in matches[:10]]

    return DashboardData(
        top_scorers=top_scorers,
        top_assists=top_assists,
        goals_per_match_ranking=goals_per_match_ranking,
        win_rate_ranking=win_rate_ranking,
        elo_ranking=elo_ranking,
        latest_matches=latest_matches,
    )


def player_elo_timeline(matches: list[Match], player_name: str) -> list[TimelinePoint]:
    relevant = []
    for m in matches:
        if any(r.player == player_name for r in m.players):
            relevant.append(m)

    relevant.sort(key=lambda x: (x.date, x.match_id))

    wins = draws = losses = 0
    timeline: list[TimelinePoint] = []

    for match in relevant:
        on_team_a = any(r.player == player_name for r in match.team_a)
        if match.goals_a == match.goals_b:
            draws += 1
        elif (on_team_a and match.goals_a > match.goals_b) or (not on_team_a and match.goals_b > match.goals_a):
            wins += 1
        else:
            losses += 1

        played = wins + draws + losses
        win_rate = wins / played if played else 0.0
        timeline.append(TimelinePoint(date=match.date.strftime("%Y-%m-%d"), elo=win_rate * 1000.0))

    return timeline


def player_matches_views(matches: list[Match], player_name: str) -> list[MatchView]:
    filtered = [m for m in matches if any(r.player == player_name for r in m.players)]
    return [match_to_view(m) for m in filtered]


def player_cumulative_series(matches: list[Match], player_name: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    relevant = [m for m in matches if any(r.player == player_name for r in m.players)]
    relevant.sort(key=lambda x: (x.date, x.match_id))

    labels: list[str] = []
    wins = draws = losses = 0
    goals_scored = assists = goals_conceded = 0

    series = {
        "elo": {"label": "ELO Placeholder", "values": []},
        "wins": {"label": "Wins", "values": []},
        "draws": {"label": "Draws", "values": []},
        "losses": {"label": "Losses", "values": []},
        "goals_scored": {"label": "Goals Scored", "values": []},
        "goals_per_match": {"label": "Goals per Match", "values": []},
        "assists": {"label": "Assists", "values": []},
        "goals_conceded": {"label": "Goals Conceded", "values": []},
        "win_rate": {"label": "Win Rate %", "values": []},
    }

    for match in relevant:
        on_team_a = any(r.player == player_name for r in match.team_a)
        player_goals = sum(r.goals for r in match.players if r.player == player_name)
        player_assists = sum(r.assists for r in match.players if r.player == player_name)

        if match.goals_a == match.goals_b:
            draws += 1
        elif (on_team_a and match.goals_a > match.goals_b) or (not on_team_a and match.goals_b > match.goals_a):
            wins += 1
        else:
            losses += 1

        goals_scored += player_goals
        assists += player_assists
        goals_conceded += match.goals_b if on_team_a else match.goals_a

        played = wins + draws + losses
        win_rate = (wins / played) * 100.0 if played else 0.0
        elo = (wins / played) * 1000.0 if played else 0.0

        labels.append(match.date.strftime("%Y-%m-%d"))
        series["elo"]["values"].append(round(elo, 2))
        series["wins"]["values"].append(wins)
        series["draws"]["values"].append(draws)
        series["losses"]["values"].append(losses)
        series["goals_scored"]["values"].append(goals_scored)
        series["goals_per_match"]["values"].append(round(goals_scored / played, 3))
        series["assists"]["values"].append(assists)
        series["goals_conceded"]["values"].append(goals_conceded)
        series["win_rate"]["values"].append(round(win_rate, 2))

    return labels, series


def serialize_for_template(player_stats: PlayerStats) -> dict[str, Any]:
    return {
        "name": player_stats.name,
        "matches": player_stats.matches,
        "wins": player_stats.wins,
        "draws": player_stats.draws,
        "losses": player_stats.losses,
        "goals_scored": player_stats.goals_scored,
        "goals_per_match": player_stats.goals_per_match,
        "assists": player_stats.assists,
        "goals_conceded": player_stats.goals_conceded,
        "win_rate": player_stats.win_rate,
        "elo_placeholder": player_stats.elo_placeholder,
    }


def parse_date(value: str) -> date:
    return date.fromisoformat(value)
