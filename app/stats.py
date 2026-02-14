from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import math
from typing import Any

from .data_io import Match

ELO_INITIAL_RATING = 1000.0
ELO_K_FACTOR = 24.0
ELO_SCALE = 400.0


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
    elo_rating: float = ELO_INITIAL_RATING

    @property
    def win_rate(self) -> float:
        if self.matches == 0:
            return 0.0
        return self.wins / self.matches

    @property
    def elo_placeholder(self) -> float:
        # Backward-compatible alias used by existing templates.
        return self.elo_rating

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
            p = stats.setdefault(row.player, PlayerStats(name=row.player))
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
            p = stats.setdefault(row.player, PlayerStats(name=row.player))
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

    ratings = _compute_elo_ratings(matches=matches, player_names=list(stats.keys()))
    for name, rating in ratings.items():
        stats.setdefault(name, PlayerStats(name=name)).elo_rating = rating

    return stats


def _sorted_matches(matches: list[Match]) -> list[Match]:
    return sorted(matches, key=lambda m: (m.date, m.match_id))


def _expected_score(team_rating: float, opp_rating: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (opp_rating - team_rating) / ELO_SCALE))


def _compute_elo_ratings(matches: list[Match], player_names: list[str]) -> dict[str, float]:
    ratings = {name: ELO_INITIAL_RATING for name in player_names}

    for match in _sorted_matches(matches):
        team_a_names = [r.player for r in match.team_a]
        team_b_names = [r.player for r in match.team_b]
        if not team_a_names or not team_b_names:
            continue

        for name in team_a_names + team_b_names:
            ratings.setdefault(name, ELO_INITIAL_RATING)

        rating_a = sum(ratings[name] for name in team_a_names) / len(team_a_names)
        rating_b = sum(ratings[name] for name in team_b_names) / len(team_b_names)
        expected_a = _expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        if match.goals_a > match.goals_b:
            actual_a, actual_b = 1.0, 0.0
        elif match.goals_b > match.goals_a:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a = actual_b = 0.5

        delta_a = ELO_K_FACTOR * (actual_a - expected_a)
        delta_b = ELO_K_FACTOR * (actual_b - expected_b)

        for name in team_a_names:
            ratings[name] += delta_a
        for name in team_b_names:
            ratings[name] += delta_b

    return ratings


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
    elo_ranking = sorted(all_stats, key=lambda s: (s.elo_rating, s.matches, s.name.lower()), reverse=True)[:10]

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
    timeline: list[TimelinePoint] = []

    # Recompute progressively to expose per-match historical points.
    running = {player_name: ELO_INITIAL_RATING}
    for match in _sorted_matches(matches):
        team_a_names = [r.player for r in match.team_a]
        team_b_names = [r.player for r in match.team_b]
        if not team_a_names or not team_b_names:
            continue

        for name in team_a_names + team_b_names:
            running.setdefault(name, ELO_INITIAL_RATING)

        rating_a = sum(running[name] for name in team_a_names) / len(team_a_names)
        rating_b = sum(running[name] for name in team_b_names) / len(team_b_names)
        expected_a = _expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        if match.goals_a > match.goals_b:
            actual_a, actual_b = 1.0, 0.0
        elif match.goals_b > match.goals_a:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a = actual_b = 0.5

        delta_a = ELO_K_FACTOR * (actual_a - expected_a)
        delta_b = ELO_K_FACTOR * (actual_b - expected_b)

        for name in team_a_names:
            running[name] += delta_a
        for name in team_b_names:
            running[name] += delta_b

        if player_name in team_a_names or player_name in team_b_names:
            timeline.append(TimelinePoint(date=match.date.strftime("%Y-%m-%d"), elo=round(running[player_name], 2)))

    return timeline


def player_matches_views(matches: list[Match], player_name: str) -> list[MatchView]:
    filtered = [m for m in matches if any(r.player == player_name for r in m.players)]
    return [match_to_view(m) for m in filtered]


def comparison_matches_views(
    matches: list[Match], primary_player: str, secondary_player: str
) -> tuple[list[MatchView], list[MatchView], list[MatchView]]:
    together: list[MatchView] = []
    only_primary: list[MatchView] = []
    only_secondary: list[MatchView] = []

    for match in matches:
        primary_in = any(r.player == primary_player for r in match.players)
        secondary_in = any(r.player == secondary_player for r in match.players)
        if primary_in and secondary_in:
            together.append(match_to_view(match))
        elif primary_in:
            only_primary.append(match_to_view(match))
        elif secondary_in:
            only_secondary.append(match_to_view(match))

    return together, only_primary, only_secondary


def multi_player_matches_views(
    matches: list[Match], primary_player: str, compare_players: list[str]
) -> tuple[list[MatchView], list[MatchView], dict[str, list[MatchView]]]:
    together: list[MatchView] = []
    primary_only: list[MatchView] = []
    compare_only: dict[str, list[MatchView]] = {name: [] for name in compare_players}
    compare_set = set(compare_players)

    for match in matches:
        names_in_match = {r.player for r in match.players}
        primary_in = primary_player in names_in_match
        compare_in = [name for name in compare_players if name in names_in_match]
        if primary_in and len(compare_in) == len(compare_players):
            together.append(match_to_view(match))
        if primary_in and not (names_in_match & compare_set):
            primary_only.append(match_to_view(match))
        if not primary_in:
            for name in compare_in:
                compare_only[name].append(match_to_view(match))

    return together, primary_only, compare_only


def player_cumulative_series(matches: list[Match], player_name: str) -> tuple[list[str], dict[str, dict[str, Any]]]:
    labels: list[str] = []
    wins = draws = losses = 0
    goals_scored = assists = goals_conceded = 0
    ratings: dict[str, float] = {}

    series = {
        "elo": {"label": "ELO", "values": []},
        "wins": {"label": "Wins", "values": []},
        "draws": {"label": "Draws", "values": []},
        "losses": {"label": "Losses", "values": []},
        "goals_scored": {"label": "Goals Scored", "values": []},
        "goals_per_match": {"label": "Goals per Match", "values": []},
        "assists": {"label": "Assists", "values": []},
        "goals_conceded": {"label": "Goals Conceded", "values": []},
        "win_rate": {"label": "Win Rate %", "values": []},
    }

    for match in _sorted_matches(matches):
        team_a_names = [r.player for r in match.team_a]
        team_b_names = [r.player for r in match.team_b]
        if not team_a_names or not team_b_names:
            continue

        for name in team_a_names + team_b_names:
            ratings.setdefault(name, ELO_INITIAL_RATING)

        rating_a = sum(ratings[name] for name in team_a_names) / len(team_a_names)
        rating_b = sum(ratings[name] for name in team_b_names) / len(team_b_names)
        expected_a = _expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        if match.goals_a > match.goals_b:
            actual_a, actual_b = 1.0, 0.0
        elif match.goals_b > match.goals_a:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a = actual_b = 0.5

        delta_a = ELO_K_FACTOR * (actual_a - expected_a)
        delta_b = ELO_K_FACTOR * (actual_b - expected_b)

        for name in team_a_names:
            ratings[name] += delta_a
        for name in team_b_names:
            ratings[name] += delta_b

        if player_name not in team_a_names and player_name not in team_b_names:
            continue

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
        elo = ratings.get(player_name, ELO_INITIAL_RATING)

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


def multi_player_cumulative_series(
    matches: list[Match], player_names: list[str]
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    labels: list[str] = []
    ratings: dict[str, float] = {}
    counters = {
        name: {"wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "assists": 0, "goals_conceded": 0}
        for name in player_names
    }
    series = {
        "elo": {"label": "ELO", "values_by_player": {name: [] for name in player_names}},
        "wins": {"label": "Wins", "values_by_player": {name: [] for name in player_names}},
        "draws": {"label": "Draws", "values_by_player": {name: [] for name in player_names}},
        "losses": {"label": "Losses", "values_by_player": {name: [] for name in player_names}},
        "goals_scored": {"label": "Goals Scored", "values_by_player": {name: [] for name in player_names}},
        "goals_per_match": {"label": "Goals per Match", "values_by_player": {name: [] for name in player_names}},
        "assists": {"label": "Assists", "values_by_player": {name: [] for name in player_names}},
        "goals_conceded": {"label": "Goals Conceded", "values_by_player": {name: [] for name in player_names}},
        "win_rate": {"label": "Win Rate %", "values_by_player": {name: [] for name in player_names}},
    }

    selected = set(player_names)
    for match in _sorted_matches(matches):
        team_a_names = [r.player for r in match.team_a]
        team_b_names = [r.player for r in match.team_b]
        if not team_a_names or not team_b_names:
            continue

        for name in team_a_names + team_b_names:
            ratings.setdefault(name, ELO_INITIAL_RATING)

        rating_a = sum(ratings[name] for name in team_a_names) / len(team_a_names)
        rating_b = sum(ratings[name] for name in team_b_names) / len(team_b_names)
        expected_a = _expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        if match.goals_a > match.goals_b:
            actual_a, actual_b = 1.0, 0.0
        elif match.goals_b > match.goals_a:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a = actual_b = 0.5

        delta_a = ELO_K_FACTOR * (actual_a - expected_a)
        delta_b = ELO_K_FACTOR * (actual_b - expected_b)

        for name in team_a_names:
            ratings[name] += delta_a
        for name in team_b_names:
            ratings[name] += delta_b

        names_in_match = {r.player for r in match.players}
        played_selected = list(names_in_match & selected)
        if not played_selected:
            continue

        labels.append(match.date.strftime("%Y-%m-%d"))
        snapshots: dict[str, dict[str, float | int]] = {}

        for player_name in played_selected:
            on_team_a = player_name in team_a_names
            player_goals = sum(r.goals for r in match.players if r.player == player_name)
            player_assists = sum(r.assists for r in match.players if r.player == player_name)

            if match.goals_a == match.goals_b:
                counters[player_name]["draws"] += 1
            elif (on_team_a and match.goals_a > match.goals_b) or (not on_team_a and match.goals_b > match.goals_a):
                counters[player_name]["wins"] += 1
            else:
                counters[player_name]["losses"] += 1

            counters[player_name]["goals_scored"] += player_goals
            counters[player_name]["assists"] += player_assists
            counters[player_name]["goals_conceded"] += match.goals_b if on_team_a else match.goals_a

            played = counters[player_name]["wins"] + counters[player_name]["draws"] + counters[player_name]["losses"]
            win_rate = (counters[player_name]["wins"] / played) * 100.0 if played else 0.0
            snapshots[player_name] = {
                "elo": round(ratings.get(player_name, ELO_INITIAL_RATING), 2),
                "wins": counters[player_name]["wins"],
                "draws": counters[player_name]["draws"],
                "losses": counters[player_name]["losses"],
                "goals_scored": counters[player_name]["goals_scored"],
                "goals_per_match": round(counters[player_name]["goals_scored"] / played, 3) if played else 0.0,
                "assists": counters[player_name]["assists"],
                "goals_conceded": counters[player_name]["goals_conceded"],
                "win_rate": round(win_rate, 2),
            }

        for metric in series.keys():
            for player_name in player_names:
                value = snapshots.get(player_name, {}).get(metric) if player_name in snapshots else None
                series[metric]["values_by_player"][player_name].append(value)

    return labels, series


def comparison_cumulative_series(
    matches: list[Match], primary_player: str, secondary_player: str
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    labels: list[str] = []
    ratings: dict[str, float] = {}
    players = [primary_player, secondary_player]
    counters = {
        primary_player: {"wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "assists": 0, "goals_conceded": 0},
        secondary_player: {"wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "assists": 0, "goals_conceded": 0},
    }

    series = {
        "elo": {"label": "ELO", "primary_values": [], "secondary_values": []},
        "wins": {"label": "Wins", "primary_values": [], "secondary_values": []},
        "draws": {"label": "Draws", "primary_values": [], "secondary_values": []},
        "losses": {"label": "Losses", "primary_values": [], "secondary_values": []},
        "goals_scored": {"label": "Goals Scored", "primary_values": [], "secondary_values": []},
        "goals_per_match": {"label": "Goals per Match", "primary_values": [], "secondary_values": []},
        "assists": {"label": "Assists", "primary_values": [], "secondary_values": []},
        "goals_conceded": {"label": "Goals Conceded", "primary_values": [], "secondary_values": []},
        "win_rate": {"label": "Win Rate %", "primary_values": [], "secondary_values": []},
    }

    for match in _sorted_matches(matches):
        team_a_names = [r.player for r in match.team_a]
        team_b_names = [r.player for r in match.team_b]
        if not team_a_names or not team_b_names:
            continue

        for name in team_a_names + team_b_names:
            ratings.setdefault(name, ELO_INITIAL_RATING)

        rating_a = sum(ratings[name] for name in team_a_names) / len(team_a_names)
        rating_b = sum(ratings[name] for name in team_b_names) / len(team_b_names)
        expected_a = _expected_score(rating_a, rating_b)
        expected_b = 1.0 - expected_a

        if match.goals_a > match.goals_b:
            actual_a, actual_b = 1.0, 0.0
        elif match.goals_b > match.goals_a:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a = actual_b = 0.5

        delta_a = ELO_K_FACTOR * (actual_a - expected_a)
        delta_b = ELO_K_FACTOR * (actual_b - expected_b)

        for name in team_a_names:
            ratings[name] += delta_a
        for name in team_b_names:
            ratings[name] += delta_b

        played_by = {
            primary_player: primary_player in team_a_names or primary_player in team_b_names,
            secondary_player: secondary_player in team_a_names or secondary_player in team_b_names,
        }
        if not played_by[primary_player] and not played_by[secondary_player]:
            continue

        labels.append(match.date.strftime("%Y-%m-%d"))

        snapshots: dict[str, dict[str, float | int]] = {}
        for player_name in players:
            if not played_by[player_name]:
                continue
            on_team_a = player_name in team_a_names
            player_goals = sum(r.goals for r in match.players if r.player == player_name)
            player_assists = sum(r.assists for r in match.players if r.player == player_name)

            if match.goals_a == match.goals_b:
                counters[player_name]["draws"] += 1
            elif (on_team_a and match.goals_a > match.goals_b) or (not on_team_a and match.goals_b > match.goals_a):
                counters[player_name]["wins"] += 1
            else:
                counters[player_name]["losses"] += 1

            counters[player_name]["goals_scored"] += player_goals
            counters[player_name]["assists"] += player_assists
            counters[player_name]["goals_conceded"] += match.goals_b if on_team_a else match.goals_a

            played = counters[player_name]["wins"] + counters[player_name]["draws"] + counters[player_name]["losses"]
            win_rate = (counters[player_name]["wins"] / played) * 100.0 if played else 0.0

            snapshots[player_name] = {
                "elo": round(ratings.get(player_name, ELO_INITIAL_RATING), 2),
                "wins": counters[player_name]["wins"],
                "draws": counters[player_name]["draws"],
                "losses": counters[player_name]["losses"],
                "goals_scored": counters[player_name]["goals_scored"],
                "goals_per_match": round(counters[player_name]["goals_scored"] / played, 3) if played else 0.0,
                "assists": counters[player_name]["assists"],
                "goals_conceded": counters[player_name]["goals_conceded"],
                "win_rate": round(win_rate, 2),
            }

        for metric in series.keys():
            primary_value = snapshots.get(primary_player, {}).get(metric) if played_by[primary_player] else None
            secondary_value = snapshots.get(secondary_player, {}).get(metric) if played_by[secondary_player] else None
            series[metric]["primary_values"].append(primary_value)
            series[metric]["secondary_values"].append(secondary_value)

    return labels, series


def combined_together_stats(matches: list[Match], player_names: list[str]) -> dict[str, float | int]:
    if not player_names:
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "win_rate": 0.0,
            "group_goals": 0,
            "group_assists": 0,
            "team_goals_for": 0,
            "team_goals_against": 0,
            "avg_goal_diff": 0.0,
        }

    def _team_of(match: Match, player_name: str) -> str | None:
        for row in match.team_a:
            if row.player == player_name:
                return "A"
        for row in match.team_b:
            if row.player == player_name:
                return "B"
        return None

    matches_count = wins = draws = losses = 0
    group_goals = group_assists = 0
    team_goals_for = team_goals_against = 0

    selected = set(player_names)
    for match in matches:
        teams = {name: _team_of(match, name) for name in selected}
        if any(team is None for team in teams.values()):
            continue

        first_team = next(iter(teams.values()))
        if any(team != first_team for team in teams.values()):
            continue
        if first_team is None:
            continue

        matches_count += 1
        team_for = match.goals_a if first_team == "A" else match.goals_b
        team_against = match.goals_b if first_team == "A" else match.goals_a
        team_goals_for += team_for
        team_goals_against += team_against

        if team_for > team_against:
            wins += 1
        elif team_for < team_against:
            losses += 1
        else:
            draws += 1

        for row in match.players:
            if row.player in selected:
                group_goals += row.goals
                group_assists += row.assists

    win_rate = (wins / matches_count) * 100.0 if matches_count else 0.0
    avg_goal_diff = ((team_goals_for - team_goals_against) / matches_count) if matches_count else 0.0
    return {
        "matches": matches_count,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "group_goals": group_goals,
        "group_assists": group_assists,
        "team_goals_for": team_goals_for,
        "team_goals_against": team_goals_against,
        "avg_goal_diff": round(avg_goal_diff, 2),
    }


def primary_on_off_stats(matches: list[Match], primary_player: str, partners: list[str]) -> dict[str, dict[str, float | int]]:
    def _empty_bucket() -> dict[str, float | int]:
        return {
            "matches": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "win_rate": 0.0,
            "goals_for": 0,
            "goals_against": 0,
            "primary_goals": 0,
            "primary_assists": 0,
        }

    def _team_of(match: Match, player_name: str) -> str | None:
        for row in match.team_a:
            if row.player == player_name:
                return "A"
        for row in match.team_b:
            if row.player == player_name:
                return "B"
        return None

    with_group = _empty_bucket()
    without_group = _empty_bucket()

    for match in matches:
        primary_team = _team_of(match, primary_player)
        if primary_team is None:
            continue

        partners_same_team = True
        for partner in partners:
            partner_team = _team_of(match, partner)
            if partner_team != primary_team:
                partners_same_team = False
                break

        bucket = with_group if partners_same_team else without_group
        bucket["matches"] += 1

        goals_for = match.goals_a if primary_team == "A" else match.goals_b
        goals_against = match.goals_b if primary_team == "A" else match.goals_a
        bucket["goals_for"] += goals_for
        bucket["goals_against"] += goals_against

        if goals_for > goals_against:
            bucket["wins"] += 1
        elif goals_for < goals_against:
            bucket["losses"] += 1
        else:
            bucket["draws"] += 1

        for row in match.players:
            if row.player == primary_player:
                bucket["primary_goals"] += row.goals
                bucket["primary_assists"] += row.assists

    for bucket in (with_group, without_group):
        played = int(bucket["matches"])
        wins = int(bucket["wins"])
        bucket["win_rate"] = round((wins / played) * 100.0, 2) if played else 0.0

    return {"with_group": with_group, "without_group": without_group}


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
        "elo_rating": player_stats.elo_rating,
        "elo_placeholder": player_stats.elo_placeholder,
    }


def parse_date(value: str) -> date:
    return date.fromisoformat(value)
