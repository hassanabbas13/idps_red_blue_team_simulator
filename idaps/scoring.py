"""The scoring engine.

Implements the project's core rule, extended:

    Attack success  -> +10 Red  (x severity multiplier)
    Detection       -> +10 Blue
    Prevention      -> +20 Blue

Plus bonuses:
    Stealth (success without detection) -> +5 Red
    Survival (Blue keeps a host clean each tick) handled by the game loop.

Severity multipliers let high-impact attacks (SQLi, phishing, MITM) be worth
more than medium ones (DDoS, brute force, XSS) - see vectors.py `points`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Base award values - kept here so they're easy to tune / show in the report.
ATTACK_SUCCESS_BASE = 10
DETECTION_AWARD = 10
PREVENTION_AWARD = 20
STEALTH_BONUS = 5

SEVERITY_MULTIPLIER = {
    "low": 1.0,
    "medium": 1.0,
    "high": 1.5,
}


@dataclass
class Scoreboard:
    red: int = 0
    blue: int = 0
    log: list = field(default_factory=list)

    def _record(self, side: str, points: int, reason: str):
        if side == "red":
            self.red += points
        else:
            self.blue += points
        self.log.append({"side": side, "points": points, "reason": reason})

    def award_attack_success(self, vector_name: str, points: int, severity: str):
        mult = SEVERITY_MULTIPLIER.get(severity, 1.0)
        total = int(round(points * mult))
        self._record("red", total, f"{vector_name} succeeded")
        return total

    def award_stealth(self, vector_name: str):
        self._record("red", STEALTH_BONUS, f"{vector_name} went undetected")
        return STEALTH_BONUS

    def award_detection(self, vector_name: str, defense_name: str):
        self._record("blue", DETECTION_AWARD, f"{defense_name} detected {vector_name}")
        return DETECTION_AWARD

    def award_prevention(self, vector_name: str, defense_name: str):
        self._record("blue", PREVENTION_AWARD, f"{defense_name} prevented {vector_name}")
        return PREVENTION_AWARD

    def award_survival(self, points: int = 2):
        self._record("blue", points, "kept the network clean this tick")
        return points

    def leader(self) -> str:
        if self.red > self.blue:
            return "Red"
        if self.blue > self.red:
            return "Blue"
        return "Tie"
