"""Quick WebSocket smoke test: start a match, assert we get init/tick/end."""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from idaps.server import _run_match  # noqa
from idaps.game import GameConfig


class FakeWS:
    """Minimal stand-in that captures messages instead of sending over a socket."""
    def __init__(self):
        self.msgs = []
    async def send_text(self, text):
        self.msgs.append(json.loads(text))


async def main():
    ws = FakeWS()
    await _run_match(ws, GameConfig(max_ticks=20, seed=7), delay=0.0)
    types = [m["type"] for m in ws.msgs]
    assert types[0] == "init", types[:1]
    assert "end" in types, types[-3:]
    ticks = [m for m in ws.msgs if m["type"] == "tick"]
    end = [m for m in ws.msgs if m["type"] == "end"][0]
    assert all("network" in t and "event" in t for t in ticks)
    print(f"init=1 ticks={len(ticks)} end=1  winner={end['winner']} "
          f"R{end['red']} B{end['blue']} compromised={end['compromised']}/{end['total_hosts']}")
    print("WS smoke OK")


asyncio.run(main())
