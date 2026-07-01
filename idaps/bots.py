"""Bot strategies for Red and Blue teams.

A bot is just an "action source": given the current game state, it returns the
action its team takes this tick. The exact same engine runs whether the action
comes from a bot or a human - which is what lets Player-vs-AI and PvP reuse
everything in later phases.
"""

from __future__ import annotations

import random

from .base import Action
from .network import Network
from .registry import all_attacks, all_defenses


class RedBot:
    """Chooses an attack vector and a target host each tick."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.vectors = list(all_attacks().keys())

    def choose(self, network: Network) -> Action | None:
        targets = [h for h in network.hosts if h.online]
        if not targets:
            return None
        # Prefer hosts that aren't yet compromised; fall back to any online host.
        fresh = [h for h in targets if not h.compromised] or targets
        host = self.rng.choice(fresh)
        # Pick a vector whose target category matches one of the host's services.
        host_cats = {s.category for s in host.services}
        viable = [
            name for name, cls in all_attacks().items()
            if set(cls.targets) & host_cats
        ] or self.vectors
        vector = self.rng.choice(viable)
        return Action(team="red", vector_name=vector, target_hostname=host.hostname)


class BlueBot:
    """Deploys a defense to a host each tick.

    Strategy: shore up the least-defended online host, preferring a defense
    that counters something not yet defended there.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.defenses = list(all_defenses().keys())

    def choose(self, network: Network) -> Action | None:
        hosts = [h for h in network.hosts if h.online]
        if not hosts:
            return None
        # Target the host with the fewest active defenses.
        host = min(hosts, key=lambda h: len(h.defenses))
        existing = {d.name for d in host.defenses}
        candidates = [n for n in self.defenses if n not in existing] or self.defenses
        defense = self.rng.choice(candidates)
        return Action(team="blue", defense_name=defense, target_hostname=host.hostname)
