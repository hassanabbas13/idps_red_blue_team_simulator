"""Turn engine objects into JSON-friendly dicts for the web dashboard.

The browser never touches the engine directly - the server runs the match and
sends these plain dicts over the WebSocket. Keeping serialization in one place
means the wire format is easy to see and change without poking the engine.
"""

from __future__ import annotations

from .network import Network
from .game import TickEvent


def network_to_dict(network: Network) -> dict:
    """Full snapshot of the network - sent on init and after every tick."""
    return {
        "hosts": [
            {
                "hostname": h.hostname,
                "services": [
                    {"name": s.name, "category": s.category} for s in h.services
                ],
                "compromised": h.compromised,
                "online": h.online,
                "privilege": h.privilege,
                "defenses": [d.name for d in h.defenses],
            }
            for h in network.hosts
        ]
    }


def event_to_dict(event: TickEvent) -> dict:
    """One tick's outcome - drives the animation, scoreboard, and feed."""
    attack = None
    if event.attack is not None:
        a = event.attack
        attack = {
            "vector": a.vector_name,
            "target": a.target_hostname,
            "success": a.success,
            "detected": a.detected,
            "prevented": a.prevented,
            "note": a.note,
            "headline": a.headline(),
        }
    return {
        "tick": event.tick,
        "attack": attack,
        "defense_deployed": event.defense_deployed,
        "defense_host": event.defense_host,
        "red_total": event.red_total,
        "blue_total": event.blue_total,
        "notes": event.notes,
    }
