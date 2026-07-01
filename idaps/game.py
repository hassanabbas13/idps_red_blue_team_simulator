"""The game loop / engine.

Drives the match tick by tick. Each tick:
    1. Red's action source picks an attack -> resolver decides the outcome.
    2. Blue's action source picks a defense -> it's deployed to a host.
    3. Survival bonus if Blue kept new compromises off the board.

The engine is agnostic about *who* picks actions - bots, a human via the API,
or two humans. It just consumes Actions. That's what lets every game mode
(auto-battle, player-vs-AI, PvP) share this exact code in later phases.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .base import Action, AttackResult
from .bots import BlueBot, RedBot
from .network import Network, default_network
from .registry import get_defense
from .resolver import resolve_attack
from .scoring import Scoreboard


@dataclass
class TickEvent:
    """A structured record of one tick - this is what the dashboard will stream."""

    tick: int
    attack: AttackResult | None = None
    defense_deployed: str | None = None
    defense_host: str | None = None
    red_total: int = 0
    blue_total: int = 0
    notes: list = field(default_factory=list)


@dataclass
class GameConfig:
    max_ticks: int = 20
    seed: int | None = None
    # Win condition: Red wins instantly if it compromises this fraction of hosts.
    red_compromise_win: float = 0.8


class Game:
    """A single match between a Red action source and a Blue action source."""

    def __init__(self, config: GameConfig | None = None, network: Network | None = None):
        self.config = config or GameConfig()
        self.rng = random.Random(self.config.seed)
        self.network = network or default_network()
        self.scoreboard = Scoreboard()
        self.tick = 0
        self.events: list[TickEvent] = []
        self.finished = False
        self.winner: str | None = None
        # Default to bots; later phases swap these for human action sources.
        self.red_source = RedBot(self.rng)
        self.blue_source = BlueBot(self.rng)

    # -- action application ---------------------------------------------------

    def _apply_blue(self, action: Action | None, event: TickEvent):
        if action is None or action.defense_name is None:
            return
        host = self.network.host(action.target_hostname)
        if host is None:
            return
        if action.defense_name in host.defense_names():
            event.notes.append(f"{action.target_hostname} already has {action.defense_name}")
            return
        defense_cls = get_defense(action.defense_name)
        host.defenses.append(defense_cls())
        event.defense_deployed = action.defense_name
        event.defense_host = action.target_hostname

    def _apply_red(self, action: Action | None, event: TickEvent):
        if action is None or action.vector_name is None:
            event.notes.append("Red had no valid move")
            return
        host = self.network.host(action.target_hostname)
        if host is None:
            return
        result = resolve_attack(action, host, self.scoreboard, self.rng)
        event.attack = result

    # -- main loop ------------------------------------------------------------

    def step(
        self,
        red_action: Action | None = None,
        blue_action: Action | None = None,
    ) -> TickEvent:
        """Advance the simulation by one tick and return the event.

        If an explicit action is passed for a side, it is used (a human played
        it). Otherwise that side's bot chooses. This single override is what
        powers every mode: AI-vs-AI passes nothing, Player-vs-AI passes one
        side, PvP passes both.
        """
        if self.finished:
            raise RuntimeError("Game already finished")
        self.tick += 1
        event = TickEvent(tick=self.tick)

        blue = blue_action if blue_action is not None else self.blue_source.choose(self.network)
        red = red_action if red_action is not None else self.red_source.choose(self.network)

        # Blue acts first (set up defenses), then Red attacks.
        self._apply_blue(blue, event)
        before = self.network.compromised_count()
        self._apply_red(red, event)
        after = self.network.compromised_count()

        # Survival bonus: no new compromise this tick.
        if after == before and (event.attack is None or not event.attack.success):
            self.scoreboard.award_survival()
            event.notes.append("Blue survival bonus")

        event.red_total = self.scoreboard.red
        event.blue_total = self.scoreboard.blue
        self.events.append(event)
        self._check_end()
        return event

    def _check_end(self):
        if self.network.compromise_ratio() >= self.config.red_compromise_win:
            self.finished = True
            self.winner = "Red"
        elif self.tick >= self.config.max_ticks:
            self.finished = True
            self.winner = self.scoreboard.leader()

    def run(self) -> list[TickEvent]:
        """Play the whole match and return every tick event."""
        while not self.finished:
            self.step()
        return self.events
