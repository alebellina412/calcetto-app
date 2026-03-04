import sys
import os
from datetime import date

# Re-add current directory as first entry
if os.getcwd() in sys.path:
    sys.path.remove(os.getcwd())
sys.path.insert(0, os.getcwd())

from app.data_io import Match, MatchPlayerRow
from app.stats import RatingEngine, ELO_INITIAL_RATING, ELO_K_FACTOR, ELO_MVP_BONUS

def test_rating_engine_zero_sum_win_loss():
    print("Testing zero-sum win/loss...", end=" ")
    engine = RatingEngine(["Player A", "Player B"])
    players = [
        MatchPlayerRow(team="A", player="Player A", goals=1, assists=0),
        MatchPlayerRow(team="B", player="Player B", goals=0, assists=0)
    ]
    match = Match(
        match_id="1", file_name="1.xlsx", date=date(2025, 1, 1), note="",
        players=players
    )
    ratings = engine.process_match(match)
    assert sum(ratings.values()) == 2 * ELO_INITIAL_RATING
    assert ratings["Player A"] > ELO_INITIAL_RATING
    assert ratings["Player B"] < ELO_INITIAL_RATING
    print("OK")

def test_rating_engine_performance_deltas():
    print("Testing performance deltas...", end=" ")
    engine = RatingEngine(["A1", "A2", "B1", "B2"])
    players = [
        MatchPlayerRow(team="A", player="A1", goals=2, assists=0),
        MatchPlayerRow(team="A", player="A2", goals=0, assists=0),
        MatchPlayerRow(team="B", player="B1", goals=0, assists=0),
        MatchPlayerRow(team="B", player="B2", goals=0, assists=0)
    ]
    match = Match(
        match_id="2", file_name="2.xlsx", date=date(2025, 1, 2), note="",
        players=players
    )
    ratings = engine.process_match(match)
    # Total rating must be 4 * 1000
    assert sum(ratings.values()) == 4 * ELO_INITIAL_RATING
    assert ratings["A1"] > ratings["A2"]
    print("OK")

def test_rating_engine_mvp_bonus():
    print("Testing MVP bonus...", end=" ")
    engine = RatingEngine(["Player A", "Player B"])
    players = [
        MatchPlayerRow(team="A", player="Player A", goals=1, assists=0),
        MatchPlayerRow(team="B", player="Player B", goals=1, assists=0)
    ]
    match = Match(
        match_id="3", file_name="3.xlsx", date=date(2025, 1, 3), note="mvp=Player A",
        players=players
    )
    ratings = engine.process_match(match)
    # Draw (W/L=0), but MVP bonus for A
    assert sum(ratings.values()) == 2 * ELO_INITIAL_RATING + ELO_MVP_BONUS
    assert ratings["Player A"] == ELO_INITIAL_RATING + ELO_MVP_BONUS
    print("OK")

if __name__ == "__main__":
    try:
        test_rating_engine_zero_sum_win_loss()
        test_rating_engine_performance_deltas()
        test_rating_engine_mvp_bonus()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
