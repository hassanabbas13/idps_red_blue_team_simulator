"""Smoke test for all four game modes through the server's _run_match.

Uses a scripted fake WebSocket: it captures outgoing messages and, whenever the
server asks a human side for a move (await_move), replies with a valid move.
This verifies the interactive protocol without a real browser.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from idaps.server import _run_match  # noqa: E402
from idaps.game import GameConfig  # noqa: E402
from idaps.registry import all_attacks, all_defenses  # noqa: E402


class ScriptedWS:
    """Fake WebSocket. Captures sends; answers await_move with a canned move."""

    def __init__(self):
        self.sent = []
        self.hosts = []
        self.vectors = list(all_attacks().keys())
        self.defenses = list(all_defenses().keys())

    async def send_text(self, text):
        msg = json.loads(text)
        self.sent.append(msg)
        if msg.get("type") == "init":
            self.hosts = msg["hosts"]

    async def receive_text(self):
        # Find what the server last asked for.
        last = self.sent[-1]
        assert last.get("type") == "await_move", f"unexpected recv: {last}"
        team = last["team"]
        target = self.hosts[0]
        if team == "red":
            return json.dumps({"action": "move", "vector": self.vectors[0], "target": target})
        return json.dumps({"action": "move", "defense": self.defenses[0], "target": target})


async def run_mode(mode):
    ws = ScriptedWS()
    await _run_match(ws, GameConfig(max_ticks=8, seed=3), delay=0.0, mode=mode)
    types = [m["type"] for m in ws.sent]
    assert types[0] == "init"
    assert "end" in types
    end = [m for m in ws.sent if m["type"] == "end"][0]
    ticks = [m for m in ws.sent if m["type"] == "tick"]
    awaits = [m for m in ws.sent if m["type"] == "await_move"]
    print(f"  {mode:12s} ticks={len(ticks)} awaits={len(awaits)} "
          f"winner={end['winner']} R{end['red']} B{end['blue']}")


async def main():
    print("Testing all four modes:")
    for mode in ("ai_vs_ai", "player_red", "player_blue", "pvp"):
        await run_mode(mode)
    print("All modes OK")


asyncio.run(main())
