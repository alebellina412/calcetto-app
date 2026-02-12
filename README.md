# Calcetto App

Simple mobile-friendly FastAPI app for a friends 5v5 soccer group.

## Features
- Login by selecting an existing player name (session cookie, no passwords).
- Dashboard with top scorers, win rate ranking, ELO placeholder ranking, latest matches.
- Players list with search, add player, player detail stats + ELO placeholder timeline chart.
- Matches list and detail pages.
- Add match form that enforces strict 5v5 and writes an Excel file to `data/matches/`.
- Auto-load manually dropped Excel files in `data/matches/`.
- Soft delete from UI using `data/deleted_matches.json` (Excel files are never removed).
- Debug page for invalid files ignored during parsing.

## Tech Stack
- Backend: FastAPI
- Templates: Jinja2
- Styling: Tailwind CSS (CDN)
- Charts: Chart.js (CDN)
- Excel read/write: pandas + openpyxl
- Session: Starlette SessionMiddleware

## Project Layout

```text
calcetto-app/
  app/
    main.py
    data_io.py
    stats.py
    templates/
      base.html
      login.html
      index.html
      players.html
      player_detail.html
      matches.html
      match_detail.html
      match_new.html
      player_new.html
      debug.html
    static/
  data/
    players.csv
    matches/
    deleted_matches.json
  requirements.txt
  README.md
```

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run app from `calcetto-app/`:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open `http://127.0.0.1:8000`.

## First Run Mock Data
On startup, if `data/players.csv` is missing/empty or `data/matches/` has no Excel files:
- 20 players are generated.
- 15 valid mock matches are generated with random dates in the last 90 days.

## Excel Match Format (Required)
Each match file must contain exactly two sheets:

1. `meta`
   - 2 columns (`key`, `value`) with at least:
     - `date`: `YYYY-MM-DD`
     - `note`: optional

2. `players`
   - Columns exactly: `team,player,goals`
   - Exactly 10 rows total: 5 team `A`, 5 team `B`
   - Players must be unique across all 10 rows
   - `goals` must be integer >= 0

Example:

```csv
team,player,goals
A,Luca Rossi,2
A,Marco Bianchi,1
...
B,Andrea Conti,0
```

## Manual Match Import
To add a match manually:
1. Create a `.xlsx` file with the exact format above.
2. Drop it into `data/matches/`.
3. Refresh the app pages; files are re-scanned on requests.

Invalid files are skipped and shown on `/debug`.

## Soft Delete Behavior
- Clicking **Soft Delete** on a match detail page only appends its `match_id` to `data/deleted_matches.json`.
- The corresponding Excel file in `data/matches/` is not deleted.
- Soft-deleted matches are hidden from lists/stats.

## Validation Rules Enforced
- Match creation always requires exactly 5 players in team A and 5 in team B.
- Duplicate player selection in one match is rejected.
- Selected players must exist in `players.csv`.
- Result/winner is always computed automatically from summed goals.
- Player names are unique case-insensitively when adding players.
