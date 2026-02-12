from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .data_io import (
    DataBundle,
    MatchPlayerRow,
    add_player,
    bootstrap_mock_data_if_needed,
    load_bundle,
    soft_delete_match,
    write_match_excel,
)
from .stats import build_dashboard, compute_player_stats, match_to_view, player_elo_timeline

app = FastAPI(title="Calcetto App")
app.add_middleware(SessionMiddleware, secret_key="dev-secret-calcetto")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    bootstrap_mock_data_if_needed()


def current_user(request: Request) -> str | None:
    user = request.session.get("user")
    if isinstance(user, str) and user.strip():
        return user
    return None


def require_user(request: Request) -> RedirectResponse | None:
    if current_user(request):
        return None
    return RedirectResponse(url="/login", status_code=303)


def render_page(request: Request, template: str, bundle: DataBundle, extra: dict[str, Any] | None = None) -> HTMLResponse:
    context: dict[str, Any] = {
        "request": request,
        "current_user": current_user(request),
        "invalid_count": len(bundle.invalid_files),
    }
    if extra:
        context.update(extra)
    return templates.TemplateResponse(template, context)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    dashboard = build_dashboard(matches=bundle.matches, player_names=[p.name for p in bundle.players])
    return render_page(request, "index.html", bundle, {"dashboard": dashboard})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    bundle = load_bundle()
    return render_page(request, "login.html", bundle, {"players": bundle.players, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, player_name: str = Form(...)) -> HTMLResponse:
    bundle = load_bundle()
    valid_names = {p.name for p in bundle.players}
    if player_name not in valid_names:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "players": bundle.players,
                "error": "Please select a valid player.",
                "current_user": None,
                "invalid_count": len(bundle.invalid_files),
            },
            status_code=400,
        )

    request.session["user"] = player_name
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/players", response_class=HTMLResponse)
def players_page(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    return render_page(request, "players.html", bundle, {"players": bundle.players})


@app.get("/players/new", response_class=HTMLResponse)
def players_new_page(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    return render_page(request, "player_new.html", bundle, {"error": None, "name": ""})


@app.post("/players/new", response_class=HTMLResponse)
def players_new_submit(request: Request, name: str = Form(...)) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    cleaned = " ".join(name.strip().split())
    try:
        new_player = add_player(cleaned)
    except ValueError as exc:
        return render_page(request, "player_new.html", bundle, {"error": str(exc), "name": cleaned})
    return RedirectResponse(url=f"/players/{new_player.id}", status_code=303)


@app.get("/players/{player_id}", response_class=HTMLResponse)
def player_detail(request: Request, player_id: int) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    player = next((p for p in bundle.players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    stats_map = compute_player_stats(bundle.matches, [p.name for p in bundle.players])
    pstats = stats_map[player.name]
    timeline = player_elo_timeline(bundle.matches, player.name)

    return render_page(
        request,
        "player_detail.html",
        bundle,
        {
            "player": player,
            "stats": pstats,
            "timeline_labels": json.dumps([t.date for t in timeline]),
            "timeline_values": json.dumps([round(t.elo, 2) for t in timeline]),
        },
    )


@app.get("/matches", response_class=HTMLResponse)
def matches_page(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    views = [match_to_view(m) for m in bundle.matches]
    return render_page(request, "matches.html", bundle, {"matches": views})


@app.get("/matches/new", response_class=HTMLResponse)
def matches_new_page(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    return render_page(request, "match_new.html", bundle, {"players": bundle.players, "error": None, "form_data": {}})


@app.get("/matches/{match_id}", response_class=HTMLResponse)
def match_detail(request: Request, match_id: str) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    match = next((m for m in bundle.matches if m.match_id == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return render_page(request, "match_detail.html", bundle, {"match": match})


@app.post("/matches/{match_id}/delete")
def match_soft_delete(request: Request, match_id: str) -> RedirectResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    soft_delete_match(match_id)
    return RedirectResponse(url="/matches", status_code=303)


def _extract_match_form(form: Any, valid_names: set[str]) -> tuple[date, str, list[MatchPlayerRow]]:
    date_value = str(form.get("date", "")).strip()
    note_value = str(form.get("note", "")).strip()
    if not date_value:
        raise ValueError("Date is required")
    try:
        parsed_date = date.fromisoformat(date_value)
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format") from exc

    rows: list[MatchPlayerRow] = []
    selected: list[str] = []

    for team in ["A", "B"]:
        for idx in range(1, 6):
            player_key = f"team_{team}_{idx}"
            goals_key = f"goals_{team}_{idx}"
            player = str(form.get(player_key, "")).strip()
            goals_raw = str(form.get(goals_key, "")).strip()

            if not player:
                raise ValueError("All 10 player slots must be selected")
            if player not in valid_names:
                raise ValueError(f"Unknown player selected: {player}")

            if not goals_raw:
                raise ValueError("Goals are required for each selected player")
            try:
                goals = int(goals_raw)
            except ValueError as exc:
                raise ValueError("Goals must be integers") from exc
            if goals < 0:
                raise ValueError("Goals must be >= 0")

            rows.append(MatchPlayerRow(team=team, player=player, goals=goals))
            selected.append(player)

    if len(set(selected)) != 10:
        raise ValueError("Duplicate player selection is not allowed")

    return parsed_date, note_value, rows


@app.post("/matches/new", response_class=HTMLResponse)
async def matches_new_submit(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    form = await request.form()
    form_data = dict(form)

    try:
        match_date, note_value, rows = _extract_match_form(form_data, {p.name for p in bundle.players})
        match_id = write_match_excel(match_date=match_date, note=note_value, rows=rows)
    except ValueError as exc:
        return render_page(
            request,
            "match_new.html",
            bundle,
            {"players": bundle.players, "error": str(exc), "form_data": form_data},
        )

    return RedirectResponse(url=f"/matches/{match_id}", status_code=303)


@app.get("/debug", response_class=HTMLResponse)
def debug_page(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    return render_page(request, "debug.html", bundle, {"invalid_files": bundle.invalid_files})
