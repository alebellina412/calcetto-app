from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .data_io import (
    DataBundle,
    MatchPlayerRow,
    add_player,
    initialize_data_dirs,
    load_bundle,
    load_players,
    soft_delete_match,
    write_match_excel,
)
from .stats import (
    build_dashboard,
    combined_together_stats,
    compute_player_stats,
    match_to_view,
    multi_player_cumulative_series,
    multi_player_matches_views,
    player_cumulative_series,
    player_matches_views,
    primary_on_off_stats,
)

app = FastAPI(title="Calcetto App")
# Session cookie lasts only for the browser session (no multi-day persistence).
app.add_middleware(SessionMiddleware, secret_key="dev-secret-calcetto", max_age=None)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    initialize_data_dirs()


def current_user(request: Request) -> str | None:
    user = request.session.get("user")
    if isinstance(user, str) and user.strip():
        return user
    return None


def _normalize_name(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def _parse_int_query_list(values: list[str]) -> list[int]:
    parsed: list[int] = []
    for raw in values:
        cleaned = str(raw).strip()
        if not cleaned:
            continue
        try:
            parsed.append(int(cleaned))
        except ValueError:
            continue
    return parsed


def _parse_match_note(note: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for part in note.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            info[key] = value
    return info


def require_user(request: Request) -> RedirectResponse | None:
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    valid_names = {p.name for p in load_players()}
    if user not in valid_names:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    return None


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


@app.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    compare_with: list[str] = Query(default=[]),
    combo_size: int = 2,
    combo_with: list[str] = Query(default=[]),
) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    user_name = current_user(request)
    if not user_name:
        return RedirectResponse(url="/login", status_code=303)
    player = next((p for p in bundle.players if p.name == user_name), None)
    if not player:
        raise HTTPException(status_code=404, detail="Logged user not found in players")

    stats_map = compute_player_stats(bundle.matches, [p.name for p in bundle.players])
    pstats = stats_map[player.name]
    player_matches = player_matches_views(bundle.matches, player.name)  # Fallback for default view.
    compare_candidates = [p for p in bundle.players if p.id != player.id]
    candidates_by_id = {p.id: p for p in compare_candidates}

    compare_selected_ids: list[int] = []
    for cid in _parse_int_query_list(compare_with):
        if cid == player.id or cid in compare_selected_ids or cid not in candidates_by_id:
            continue
        compare_selected_ids.append(cid)
    compare_selected_ids = compare_selected_ids[:3]
    compare_selected_players = [candidates_by_id[cid] for cid in compare_selected_ids]
    compare_stats_list = [stats_map[p.name] for p in compare_selected_players]

    normalized_combo_size = combo_size if combo_size in {2, 3, 4} else 2
    needed_partners = normalized_combo_size - 1
    combo_selected_ids: list[int] = []
    for cid in _parse_int_query_list(combo_with):
        if cid == player.id or cid in combo_selected_ids or cid not in candidates_by_id:
            continue
        combo_selected_ids.append(cid)
    combo_selected_ids = combo_selected_ids[:needed_partners]
    combo_selected_players = [candidates_by_id[cid] for cid in combo_selected_ids]

    compare_active = len(compare_selected_players) > 0
    group_active = (len(combo_selected_players) > 0) and not compare_active

    combined_stats = None
    on_off_stats = None
    group_error: str | None = None
    compare_warnings: list[str] = []
    if group_active and len(combo_selected_players) == needed_partners:
        combined_names = [player.name] + [p.name for p in combo_selected_players]
        combined_stats = combined_together_stats(bundle.matches, combined_names)
        on_off_stats = primary_on_off_stats(bundle.matches, player.name, [p.name for p in combo_selected_players])
        if int(combined_stats["matches"]) == 0:
            group_error = "Nessuna partita in comune tra tutti i giocatori selezionati."
    elif compare_active:
        combo_selected_ids = []
        combo_selected_players = []

    if compare_active:
        timeline_labels, timeline_series = multi_player_cumulative_series(
            bundle.matches, [player.name] + [p.name for p in compare_selected_players]
        )
        shared_matches, primary_only_matches, compare_only_matches = multi_player_matches_views(
            bundle.matches, player.name, [p.name for p in compare_selected_players]
        )
        for p in compare_selected_players:
            if stats_map[p.name].matches == 0:
                compare_warnings.append(f"{p.name} non ha ancora partite registrate.")
    else:
        timeline_labels, single_series = player_cumulative_series(bundle.matches, player.name)
        timeline_series = {
            metric: {
                "label": metric_data["label"],
                "values_by_player": {player.name: metric_data["values"]},
            }
            for metric, metric_data in single_series.items()
        }
        shared_matches = []
        primary_only_matches = player_matches
        compare_only_matches = {}

    return render_page(
        request,
        "player_detail.html",
        bundle,
        {
            "player": player,
            "stats": pstats,
            "timeline_labels": json.dumps(timeline_labels),
            "timeline_series": json.dumps(timeline_series),
            "player_matches": player_matches,
            "compare_candidates": compare_candidates,
            "compare_selected_ids": compare_selected_ids,
            "compare_selected_players": compare_selected_players,
            "compare_stats_list": compare_stats_list,
            "shared_matches": shared_matches,
            "primary_only_matches": primary_only_matches,
            "compare_only_matches": compare_only_matches,
            "combo_size": normalized_combo_size,
            "combo_selected_ids": combo_selected_ids,
            "combo_selected_players": combo_selected_players,
            "combined_stats": combined_stats,
            "on_off_stats": on_off_stats,
            "compare_active": compare_active,
            "group_active": group_active,
            "group_error": group_error,
            "compare_warnings": compare_warnings,
            "compare_palette": [
                {"hex": "#dc2626", "text_class": "text-red-600"},
                {"hex": "#16a34a", "text_class": "text-green-600"},
                {"hex": "#f59e0b", "text_class": "text-amber-500"},
            ],
        },
    )


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
    return RedirectResponse(url="/matches/new", status_code=303)


@app.post("/players/new", response_class=HTMLResponse)
def players_new_submit(request: Request, name: str = Form(...)) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect
    return RedirectResponse(url="/matches/new", status_code=303)


@app.get("/players/{player_id}", response_class=HTMLResponse)
def player_detail(
    request: Request,
    player_id: int,
    compare_with: list[str] = Query(default=[]),
    combo_size: int = 2,
    combo_with: list[str] = Query(default=[]),
) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    player = next((p for p in bundle.players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    stats_map = compute_player_stats(bundle.matches, [p.name for p in bundle.players])
    pstats = stats_map[player.name]
    player_matches = player_matches_views(bundle.matches, player.name)  # Fallback for default view.
    compare_candidates = [p for p in bundle.players if p.id != player.id]
    candidates_by_id = {p.id: p for p in compare_candidates}

    compare_selected_ids: list[int] = []
    for cid in _parse_int_query_list(compare_with):
        if cid == player.id or cid in compare_selected_ids or cid not in candidates_by_id:
            continue
        compare_selected_ids.append(cid)
    compare_selected_ids = compare_selected_ids[:3]
    compare_selected_players = [candidates_by_id[cid] for cid in compare_selected_ids]
    compare_stats_list = [stats_map[p.name] for p in compare_selected_players]

    normalized_combo_size = combo_size if combo_size in {2, 3, 4} else 2
    needed_partners = normalized_combo_size - 1
    combo_selected_ids: list[int] = []
    for cid in _parse_int_query_list(combo_with):
        if cid == player.id or cid in combo_selected_ids or cid not in candidates_by_id:
            continue
        combo_selected_ids.append(cid)
    combo_selected_ids = combo_selected_ids[:needed_partners]
    combo_selected_players = [candidates_by_id[cid] for cid in combo_selected_ids]

    compare_active = len(compare_selected_players) > 0
    group_active = (len(combo_selected_players) > 0) and not compare_active

    combined_stats = None
    on_off_stats = None
    group_error: str | None = None
    compare_warnings: list[str] = []
    if group_active and len(combo_selected_players) == needed_partners:
        combined_names = [player.name] + [p.name for p in combo_selected_players]
        combined_stats = combined_together_stats(bundle.matches, combined_names)
        on_off_stats = primary_on_off_stats(bundle.matches, player.name, [p.name for p in combo_selected_players])
        if int(combined_stats["matches"]) == 0:
            group_error = "Nessuna partita in comune tra tutti i giocatori selezionati."
    elif compare_active:
        combo_selected_ids = []
        combo_selected_players = []

    if compare_active:
        timeline_labels, timeline_series = multi_player_cumulative_series(
            bundle.matches, [player.name] + [p.name for p in compare_selected_players]
        )
        shared_matches, primary_only_matches, compare_only_matches = multi_player_matches_views(
            bundle.matches, player.name, [p.name for p in compare_selected_players]
        )
        for p in compare_selected_players:
            if stats_map[p.name].matches == 0:
                compare_warnings.append(f"{p.name} non ha ancora partite registrate.")
    else:
        timeline_labels, single_series = player_cumulative_series(bundle.matches, player.name)
        timeline_series = {
            metric: {
                "label": metric_data["label"],
                "values_by_player": {player.name: metric_data["values"]},
            }
            for metric, metric_data in single_series.items()
        }
        shared_matches = []
        primary_only_matches = player_matches
        compare_only_matches = {}

    return render_page(
        request,
        "player_detail.html",
        bundle,
        {
            "player": player,
            "stats": pstats,
            "timeline_labels": json.dumps(timeline_labels),
            "timeline_series": json.dumps(timeline_series),
            "player_matches": player_matches,
            "compare_candidates": compare_candidates,
            "compare_selected_ids": compare_selected_ids,
            "compare_selected_players": compare_selected_players,
            "compare_stats_list": compare_stats_list,
            "shared_matches": shared_matches,
            "primary_only_matches": primary_only_matches,
            "compare_only_matches": compare_only_matches,
            "combo_size": normalized_combo_size,
            "combo_selected_ids": combo_selected_ids,
            "combo_selected_players": combo_selected_players,
            "combined_stats": combined_stats,
            "on_off_stats": on_off_stats,
            "compare_active": compare_active,
            "group_active": group_active,
            "group_error": group_error,
            "compare_warnings": compare_warnings,
            "compare_palette": [
                {"hex": "#dc2626", "text_class": "text-red-600"},
                {"hex": "#16a34a", "text_class": "text-green-600"},
                {"hex": "#f59e0b", "text_class": "text-amber-500"},
            ],
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
    note_info = _parse_match_note(match.note or "")
    extra = {
        "match": match,
        "match_source": note_info.get("source", ""),
        "match_row": note_info.get("row", ""),
        "match_campo": note_info.get("campo", ""),
        "match_mvp": note_info.get("mvp", ""),
    }
    return render_page(request, "match_detail.html", bundle, extra)


@app.post("/matches/{match_id}/delete")
def match_soft_delete(request: Request, match_id: str) -> RedirectResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    soft_delete_match(match_id)
    return RedirectResponse(url="/matches", status_code=303)


def _extract_match_form(form: Any, valid_names: set[str]) -> tuple[date, str, list[MatchPlayerRow], list[str]]:
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
    new_player_candidates: list[str] = []

    for team in ["A", "B"]:
        for idx in range(1, 6):
            player_key = f"team_{team}_{idx}"
            new_player_key = f"new_team_{team}_{idx}"
            goals_key = f"goals_{team}_{idx}"
            assists_key = f"assists_{team}_{idx}"
            selected_player = str(form.get(player_key, "")).strip()
            new_player_value = " ".join(str(form.get(new_player_key, "")).strip().split())
            goals_raw = str(form.get(goals_key, "")).strip()
            assists_raw = str(form.get(assists_key, "")).strip()

            player = new_player_value or selected_player
            if not player:
                raise ValueError("Each slot needs an existing player or a new player name")
            if not new_player_value and _normalize_name(player) not in valid_names:
                raise ValueError(f"Unknown player selected: {player}")

            if not goals_raw:
                raise ValueError("Goals are required for each selected player")
            try:
                goals = int(goals_raw)
            except ValueError as exc:
                raise ValueError("Goals must be integers") from exc
            if goals < 0:
                raise ValueError("Goals must be >= 0")
            if not assists_raw:
                raise ValueError("Assists are required for each selected player")
            try:
                assists = int(assists_raw)
            except ValueError as exc:
                raise ValueError("Assists must be integers") from exc
            if assists < 0:
                raise ValueError("Assists must be >= 0")

            rows.append(MatchPlayerRow(team=team, player=player, goals=goals, assists=assists))
            selected.append(player)
            if new_player_value:
                new_player_candidates.append(new_player_value)

    if len({_normalize_name(name) for name in selected}) != 10:
        raise ValueError("Duplicate player selection is not allowed")

    unique_new_players: list[str] = []
    seen_new: set[str] = set()
    for name in new_player_candidates:
        key = _normalize_name(name)
        if key in valid_names or key in seen_new:
            continue
        seen_new.add(key)
        unique_new_players.append(name)

    return parsed_date, note_value, rows, unique_new_players


@app.post("/matches/new", response_class=HTMLResponse)
async def matches_new_submit(request: Request) -> HTMLResponse:
    redirect = require_user(request)
    if redirect:
        return redirect

    bundle = load_bundle()
    form = await request.form()
    form_data = dict(form)

    try:
        valid_names = {p.name for p in bundle.players}
        valid_names_normalized = {_normalize_name(name) for name in valid_names}
        match_date, note_value, rows, new_players = _extract_match_form(form_data, valid_names_normalized)

        for name in new_players:
            add_player(name)

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
