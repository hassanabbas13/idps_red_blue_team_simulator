"""Base classes and shared types for attacks, defenses, and resolution results."""

from __future__ import annotations

from dataclasses import dataclass, field

from .network import Host


@dataclass
class Action:
    """One team's chosen move for a tick.

    Red actions carry `vector_name`; Blue actions carry `defense_name`. The
    same type serves both so bots and human players share one interface.
    """

    team: str                      # "red" or "blue"
    target_hostname: str
    vector_name: str | None = None   # set for red actions
    defense_name: str | None = None  # set for blue actions


@dataclass
class AttackResult:
    """Outcome of resolving one attack action against the network."""

    vector_name: str
    target_hostname: str
    success: bool          # did the attack land?
    detected: bool         # did Blue's IDS/monitoring catch it?
    prevented: bool        # did a Blue defense block it outright?
    red_points: int = 0
    blue_points: int = 0
    note: str = ""

    def headline(self) -> str:
        if self.prevented:
            tag = "PREVENTED"
        elif self.success and self.detected:
            tag = "SUCCESS (detected)"
        elif self.success:
            tag = "SUCCESS (stealth)"
        elif self.detected:
            tag = "FAILED (detected)"
        else:
            tag = "FAILED"
        return f"{self.vector_name} -> {self.target_hostname}: {tag}"


class AttackVector:
    """Base class for a Red Team attack vector.

    Subclasses declare metadata as class attributes and are registered with
    @register_attack. The resolver reads this metadata - vectors carry no
    resolution logic of their own, which keeps balancing in one place.
    """

    name: str = ""
    targets: list[str] = []        # service categories this vector can hit
    base_success: float = 0.5      # success chance before defenses/randomness
    detection_difficulty: float = 0.5  # higher = harder for IDS to detect
    countered_by: list[str] = []   # defense names that reduce/prevent it
    points: int = 10               # base Red points on success
    severity: str = "medium"       # low | medium | high
    description: str = ""


class Defense:
    """Base class for a Blue Team defense.

    A defense lists the attack vector names it `counters`, and how strongly it
    prevents vs detects them. Prevention stops an attack outright (worth more
    points); detection only raises an alert. IDS-style defenses set
    prevent_chance=0 and rely purely on detection.
    """

    name: str = ""
    counters: list[str] = []       # attack vector names this defense acts on
    prevent_chance: float = 0.0    # chance to block a countered attack outright
    detect_chance: float = 0.0     # chance to detect a countered attack
    cost: int = 1                  # deployment cost (used in later phases)
    description: str = ""

    def acts_against(self, vector_name: str) -> bool:
        return vector_name in self.counters
