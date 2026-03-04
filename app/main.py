from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.data_io import (
    DataBundle,
    MatchPlayerRow,
    add_player,
    initialize_data_dirs,
    load_bundle,
    load_players,
    soft_delete_match,
    write_match_excel,
    load_matches, Match
)
from app.stats import (
    compute_player_stats, build_dashboard, player_matches_views,
    comparison_matches_views, player_cumulative_series,
    multi_player_matches_views, multi_player_cumulative_series,
    comparison_cumulative_series, combined_together_stats,
    primary_on_off_stats, DashboardData
)
from app.utils import _extract_mvp_name, _month_label, SEASON2_START

app = FastAPI(title="Calcetto App")
# Session cookie lasts only for the browser session (no multi-day persistence).
app.add_middleware(SessionMiddleware, secret_key="dev-secret-calcetto", max_age=None)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Note: Jinja2Templates directory choice depends on deployment.
# We'll stick with the logic from the restored file.
templates = Jinja2Templates(directory="app/templates_legacy")

# React SPA index
SPA_INDEX = Path(__file__).resolve().parent / "templates" / "spa.html"


def current_user(request: Request) -> str | None:
    return request.session.get("user")


@app.on_event("startup")
def startup_event():
    initialize_data_dirs()


# ─────────────────────────────────────────────
# PAGES (REST API)
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Serve the modern React SPA."""
    if not SPA_INDEX.exists():
        # Fallback to dev message if spa.html isn't generated yet
        return HTMLResponse("<h1>Calcetto App</h1><p>SPA template (spa.html) not found. Run scripts/generate_spa.py first.</p>")
    return FileResponse(SPA_INDEX)


@app.get("/legacy", response_class=HTMLResponse)
def page_index(request: Request):
    bundle = load_bundle()
    dashboard = build_dashboard(bundle.matches)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "players": dashboard.players,
            "matches": dashboard.matches,
            "invalid_files": dashboard.invalid_files,
            "user": current_user(request),
        },
    )


@app.get("/login", response_class=HTMLResponse)
def page_login(request: Request):
    players = load_players()
    return templates.TemplateResponse(
        "login.html", {"request": request, "players": players, "user": current_user(request)}
    )


@app.post("/login")
def login_post(request: Request, player_name: str = Form(...)):
    request.session["user"] = player_name
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    if request.method == "POST":
        return JSONResponse({"status": "ok"})
    return RedirectResponse(url="/", status_code=303)


# ─────────────────────────────────────────────
# JSON API — Login/Auth
# ─────────────────────────────────────────────

@app.get("/api/me")
def api_me(request: Request):
    user = current_user(request)
    return JSONResponse({"user": user})


@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    player_name = body.get("player_name")
    if not player_name:
        return JSONResponse({"error": "Missing player_name"}, status_code=400)
    request.session["user"] = player_name
    return JSONResponse({"user": player_name})


# ─────────────────────────────────────────────
# JSON API — Players
# ─────────────────────────────────────────────

@app.get("/api/players")
def api_players(request: Request) -> JSONResponse:
    bundle = load_bundle()
    player_names = [p.name for p in bundle.players]
    stats_map = compute_player_stats(bundle.matches, player_names)
    
    # Calculate MVP counts
    mvp_counts = {}
    for m in bundle.matches:
        mvp = _extract_mvp_name(m.note)
        if mvp:
            mvp_counts[mvp] = mvp_counts.get(mvp, 0) + 1

    # Autogol counts (dummy for now, match doesn't report them clearly)
    autogol_counts = {}

    players_list = []
    for player in bundle.players:
        s = stats_map.get(player.name)
        if not s:
            continue
            
        name_parts = player.name.strip().split()
        cognome = name_parts[-1] if name_parts else player.name
        nome = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
        mvp = mvp_counts.get(player.name, 0)

        players_list.append({
            "id": str(player.id),
            "name": s.name,
            "cognome": cognome,
            "nome": nome,
            "partite": s.matches,
            "vittorie": s.wins,
            "vittorie_pct": round(s.win_rate * 100),
            "gol": s.goals_scored,
            "gol_pp": round(s.goals_per_match, 2),
            "assist": s.assists,
            "assist_pp": round(s.assists / s.matches if s.matches else 0, 2),
            "ga": s.goals_scored + s.assists,
            "ga_pp": round(s.goals_per_match + (s.assists / s.matches if s.matches else 0), 2),
            "mvp": mvp,
            "intonso": 0,   # not tracked at match level currently
            "autogol": autogol_counts.get(player.name, 0),
            "elo": round(s.elo_rating, 1),
        })
    return JSONResponse(players_list)


@app.get("/api/matches")
def api_matches(request: Request) -> JSONResponse:
    bundle = load_bundle()
    result = []
    for match in reversed(bundle.matches):  # chronological order
        mvp = _extract_mvp_name(match.note)
        gol = match.goals_a + match.goals_b
        assist_total = sum(r.assists for r in match.players)
        season = 2 if match.date >= SEASON2_START else 1
        result.append({
            "match_id": match.match_id,
            "d": match.date.strftime("%d/%m/%y"),
            "label": _month_label(match.date),
            "mvp": mvp,
            "gol": gol,
            "assist": assist_total,
            "autogol": 0,
            "season": season,
            "goals_a": match.goals_a,
            "goals_b": match.goals_b,
            "winner": match.winner,
            "team_a": [{"player": r.player, "goals": r.goals, "assists": r.assists} for r in match.team_a],
            "team_b": [{"player": r.player, "goals": r.goals, "assists": r.assists} for r in match.team_b],
        })
    return JSONResponse(result)


@app.post("/api/matches")
async def api_matches_submit(request: Request) -> JSONResponse:
    user = current_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    body = await request.json()
    bundle = load_bundle()
    
    from app.utils import normalize_name
    valid_names = {p.name for p in bundle.players}
    valid_names_normalized = {normalize_name(n) for n in valid_names}

    date_str = str(body.get("date", "")).strip()
    note = str(body.get("note", "")).strip()
    players_data = body.get("players", [])

    if not date_str or not players_data:
        return JSONResponse({"error": "Date and players are required"}, status_code=400)

    try:
        match_date = date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"error": "Invalid date format (use YYYY-MM-DD)"}, status_code=400)

    rows = []
    for p in players_data:
        name = str(p.get("player", "")).strip()
        if normalize_name(name) not in valid_names_normalized:
            return JSONResponse({"error": f"Unknown player: {name}"}, status_code=400)
        
        rows.append(MatchPlayerRow(
            team=p.get("team"),
            player=name,
            goals=int(p.get("goals", 0)),
            assists=int(p.get("assists", 0))
        ))

    try:
        match_id = write_match_excel(match_date, note, rows)
        return JSONResponse({"status": "ok", "match_id": match_id})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/stats/player/{player_name}")
def api_player_stats(player_name: str):
    bundle = load_bundle()
    views = player_matches_views(bundle.matches, player_name)
    timeline = player_cumulative_series(bundle.matches, player_name)
    return JSONResponse({"matches": views, "timeline": [t.__dict__ for t in timeline]})


@app.get("/api/stats/multi")
def api_multi_stats(names: str = Query(...)):
    bundle = load_bundle()
    player_names = names.split(",")
    views = multi_player_matches_views(bundle.matches, player_names)
    series = multi_player_cumulative_series(bundle.matches, player_names)
    return JSONResponse({"matches": views, "series": series})


@app.get("/api/stats/comparison")
def api_comparison_stats(p1: str = Query(...), p2: str = Query(...)):
    bundle = load_bundle()
    views = comparison_matches_views(bundle.matches, p1, p2)
    series = comparison_cumulative_series(bundle.matches, p1, p2)
    together = combined_together_stats(bundle.matches, p1, p2)
    on_off = primary_on_off_stats(bundle.matches, p1, p2)
    return JSONResponse({
        "matches": views,
        "series": series,
        "together": together,
        "on_off": on_off
    })
