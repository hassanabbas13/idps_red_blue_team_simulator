"""FastAPI + WebSocket server for the IDAPS web dashboard.

Run it with:
    python -m idaps.server
    # or: uvicorn idaps.server:app --reload

Then open http://localhost:8000 in a browser.

How it works:
  - GET  /            serves the dashboard (static/index.html)
  - WS   /ws          the browser opens this; the server runs a match and
                      pushes one JSON message per tick, paced by a delay the
                      client requests. The same engine that powers the CLI
                      drives this - the browser only renders what it receives.
"""

from __future__ import annotations

import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import idaps  # noqa: F401  populates the attack/defense registries
from .base import Action
from .game import Game, GameConfig
from .registry import all_attacks, all_defenses
from .serialize import event_to_dict, network_to_dict

app = FastAPI(title="IDAPS Dashboard")

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/api/info")
async def info():
    """Metadata the dashboard shows in its header / legend / action menus."""
    return {
        "vectors": [
            {
                "name": n,
                "severity": c.severity,
                "countered_by": c.countered_by,
                "points": c.points,
                "description": c.description,
            }
            for n, c in all_attacks().items()
        ],
        "defenses": [
            {
                "name": n,
                "counters": c.counters,
                "prevent_chance": c.prevent_chance,
                "detect_chance": c.detect_chance,
                "description": c.description,
            }
            for n, c in all_defenses().items()
        ],
    }


def _hostnames(game: Game) -> list[str]:
    return [h.hostname for h in game.network.hosts]


async def _send(ws: WebSocket, payload: dict):
    await ws.send_text(json.dumps(payload))


async def _recv(ws: WebSocket) -> dict:
    raw = await ws.receive_text()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _parse_action(msg: dict, team: str) -> Action | None:
    """Build an Action from a client move message, or None to let the bot act."""
    if not msg:
        return None
    if team == "red":
        vector = msg.get("vector")
        target = msg.get("target")
        if not vector or not target:
            return None
        return Action(team="red", vector_name=vector, target_hostname=target)
    else:
        defense = msg.get("defense")
        target = msg.get("target")
        if not defense or not target:
            return None
        return Action(team="blue", defense_name=defense, target_hostname=target)


async def _run_match(ws: WebSocket, config: GameConfig, delay: float, mode: str):
    """Play a full match in one of four modes.

    mode is one of:
      ai_vs_ai     - both sides driven by bots (auto-battle, streamed)
      player_red   - human plays Red, bot plays Blue
      player_blue  - human plays Blue, bot plays Red
      pvp          - both sides human (this single socket controls both)

    For human-controlled sides, the server pauses each tick and waits for a
    'move' message before resolving. Bot-controlled sides act automatically.
    """
    game = Game(config)
    human_red = mode in ("player_red", "pvp")
    human_blue = mode in ("player_blue", "pvp")

    await _send(ws, {
        "type": "init",
        "mode": mode,
        "network": network_to_dict(game.network),
        "config": {"max_ticks": config.max_ticks, "seed": config.seed},
        "hosts": _hostnames(game),
    })

    while not game.finished:
        # Ask the human side(s) for a move; bot sides stay None (engine fills in).
        red_action = None
        blue_action = None

        if human_blue:
            await _send(ws, {"type": "await_move", "team": "blue", "tick": game.tick + 1})
            msg = await _recv(ws)
            if msg.get("action") == "stop":
                break
            blue_action = _parse_action(msg, "blue")

        if human_red:
            await _send(ws, {"type": "await_move", "team": "red", "tick": game.tick + 1})
            msg = await _recv(ws)
            if msg.get("action") == "stop":
                break
            red_action = _parse_action(msg, "red")

        event = game.step(red_action=red_action, blue_action=blue_action)
        await _send(ws, {
            "type": "tick",
            "event": event_to_dict(event),
            "network": network_to_dict(game.network),
        })

        # Only pace automatically when no human is in the loop.
        if not (human_red or human_blue):
            await asyncio.sleep(delay)

    await _send(ws, {
        "type": "end",
        "winner": game.winner,
        "red": game.scoreboard.red,
        "blue": game.scoreboard.blue,
        "compromised": game.network.compromised_count(),
        "total_hosts": len(game.network.hosts),
    })


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await _recv(ws)
            if msg.get("action") != "start":
                continue
            config = GameConfig(
                max_ticks=int(msg.get("ticks", 20)),
                seed=msg.get("seed"),  # may be None for random
            )
            delay = float(msg.get("delay", 0.6))
            mode = msg.get("mode", "ai_vs_ai")
            await _run_match(ws, config, delay, mode)
    except WebSocketDisconnect:
        return


def main():
    import uvicorn
    uvicorn.run("idaps.server:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
