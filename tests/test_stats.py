import sys
import os
from datetime import date

# Add root directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.data_io import Match, MatchPlayerRow
from app.stats import RatingEngine, ELO_INITIAL_RATING, ELO_K_FACTOR, ELO_MVP_BONUS

def test_rating_engine_zero_sum_win_loss():
    print("Testing zero-sum win/loss...", end=" ")
    engine = RatingEngine(["Player A", "Player B"])
    
    match = Match(
        match_id="1",
        file_name="1.xlsx",
        date=date(2025, 1, 1),
        note="",
        players=[
            MatchPlayerRow(team="A", player="Player A", goals=1, assists=0),
            MatchPlayerRow(team="B", player="Player B", goals=0, assists=0)
        ]
    )
    
    ratings = engine.process_match(match)
    assert sum(ratings.values()) == 2 * ELO_INITIAL_RATING
    assert ratings["Player A"] > ELO_INITIAL_RATING
    assert ratings["Player B"] < ELO_INITIAL_RATING
    print("OK")

def test_rating_engine_performance_deltas():
    print("Testing performance deltas...", end=" ")
    engine = RatingEngine(["A1", "A2", "B1", "B2"])
    
    match = Match(
        match_id="2",
        file_name="2.xlsx",
        date=date(2025, 1, 2),
        note="",
        players=[
            MatchPlayerRow(team="A", player="A1", goals=2, assists=0),
            MatchPlayerRow(team="A", player="A2", goals=0, assists=0),
            MatchPlayerRow(team="B", player="B1", goals=0, assists=0),
            MatchPlayerRow(team="B", player="B2", goals=0, assists=0)
        ]
    )
    
    ratings = engine.process_match(match)
    assert sum(ratings.values()) == 4 * ELO_INITIAL_RATING
    assert ratings["A1"] > ratings["A2"]
    print("OK")

def test_rating_engine_mvp_bonus():
    print("Testing MVP bonus...", end=" ")
    engine = RatingEngine(["Player A", "Player B"])
    
    match = Match(
        match_id="3",
        file_name="3.xlsx",
        date=date(2025, 1, 3),
        note="mvp=Player A",
        players=[
            MatchPlayerRow(team="A", player="Player A", goals=1, assists=0),
            MatchPlayerRow(team="B", player="Player B", goals=1, assists=0)
        ]
    )
    
    ratings = engine.process_match(match)
    assert sum(ratings.values()) == 2 * ELO_INITIAL_RATING + ELO_MVP_BONUS
    assert ratings["Player A"] == ELO_INITIAL_RATING + ELO_MVP_BONUS
    print("OK")

if __name__ == "__main__":
    test_rating_engine_zero_sum_win_loss()
    test_rating_engine_performance_deltas()
    test_rating_engine_mvp_bonus()
    print("\nAll backend tests passed!")
