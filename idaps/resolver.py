"""The resolver: turns an attack Action into an AttackResult.

This is the heart of the simulation. Given an attack vector, a target host,
its active defenses, and a seeded RNG, it decides three independent questions:

    1. Is the attack PREVENTED?  (a prevention-capable defense blocks it)
    2. If not prevented, does it SUCCEED? (base chance, reduced by defenses)
    3. Is it DETECTED?           (IDS / monitoring raises an alert)

All randomness flows through a single `random.Random` instance so a given seed
always produces the same match - essential for reproducible demos and tests.
"""

from __future__ import annotations

import random

from .base import Action, AttackResult, AttackVector
from .network import Host
from .registry import get_attack
from .scoring import Scoreboard


def _relevant_defenses(host: Host, vector_name: str) -> list:
    return [d for d in host.defenses if vector_name in getattr(d, "counters", [])]


def resolve_attack(
    action: Action,
    host: Host,
    scoreboard: Scoreboard,
    rng: random.Random,
) -> AttackResult:
    """Resolve a single attack action, updating the scoreboard in place."""
    vector_cls: type[AttackVector] = get_attack(action.vector_name)
    defenses = _relevant_defenses(host, action.vector_name)

    result = AttackResult(
        vector_name=action.vector_name,
        target_hostname=host.hostname,
        success=False,
        detected=False,
        prevented=False,
    )

    # An offline host (already DDoSed) can't be meaningfully attacked further.
    if not host.online:
        result.note = "host offline"
        return result

    # --- 1. Prevention check -------------------------------------------------
    for d in defenses:
        if getattr(d, "prevent_chance", 0) > 0 and rng.random() < d.prevent_chance:
            result.prevented = True
            result.blue_points += scoreboard.award_prevention(action.vector_name, d.name)
            result.note = f"blocked by {d.name}"
            # A prevented attack may still trip a detector - check detection too.
            _detection_check(result, action, defenses, vector_cls, scoreboard, rng)
            return result

    # --- 2. Success check ----------------------------------------------------
    success_chance = vector_cls.base_success
    # Each prevention-capable defense that *didn't* block still lowers odds.
    for d in defenses:
        success_chance -= getattr(d, "prevent_chance", 0) * 0.3
    success_chance = max(0.05, min(0.95, success_chance))

    if rng.random() < success_chance:
        result.success = True
        result.red_points += scoreboard.award_attack_success(
            action.vector_name, vector_cls.points, vector_cls.severity
        )
        _apply_effect(action.vector_name, host)

    # --- 3. Detection check --------------------------------------------------
    _detection_check(result, action, defenses, vector_cls, scoreboard, rng)

    # Stealth bonus: succeeded AND nobody noticed.
    if result.success and not result.detected:
        result.red_points += scoreboard.award_stealth(action.vector_name)
        result.note = "stealthy"

    return result


def _detection_check(result, action, defenses, vector_cls, scoreboard, rng):
    """Roll detection against every detection-capable defense (once total)."""
    if result.detected:
        return
    detect_chance = 0.0
    detector_name = None
    for d in defenses:
        dc = getattr(d, "detect_chance", 0)
        # Harder-to-detect vectors reduce detector effectiveness.
        dc *= (1.0 - vector_cls.detection_difficulty * 0.5)
        if dc > detect_chance:
            detect_chance = dc
            detector_name = d.name
    if detector_name and rng.random() < detect_chance:
        result.detected = True
        result.blue_points += scoreboard.award_detection(action.vector_name, detector_name)


def _apply_effect(vector_name: str, host: Host):
    """Mutate host state to reflect a successful attack (for the visuals)."""
    if vector_name == "DDoS":
        host.online = False
    else:
        host.compromised = True
        if vector_name in ("Brute Force", "Phishing", "MITM"):
            host.privilege = "admin" if host.privilege == "user" else "user"
