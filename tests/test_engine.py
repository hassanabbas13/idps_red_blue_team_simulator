"""Smoke + unit tests for the IDAPS engine (Phase 1).

Run with:  python -m pytest -q     (or)     python tests/test_engine.py
No external dependencies - falls back to a tiny runner if pytest is absent.
"""

from __future__ import annotations

import os
import random
import sys

# Allow running this file directly (python tests/test_engine.py) by putting the
# project root on the path. Not needed when run via pytest from the root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import idaps  # noqa: F401,E402  (ensures registries are populated)
from idaps.base import Action
from idaps.game import Game, GameConfig
from idaps.network import default_network
from idaps.registry import all_attacks, all_defenses, get_defense
from idaps.resolver import resolve_attack
from idaps.scoring import Scoreboard


def test_six_vectors_registered():
    assert set(all_attacks().keys()) == {
        "DDoS", "Brute Force", "SQL Injection", "Phishing", "MITM", "XSS"
    }


def test_defenses_registered():
    assert len(all_defenses()) >= 6
    # Every defense counters at least one *real* vector.
    valid = set(all_attacks().keys())
    for name, cls in all_defenses().items():
        assert cls.counters, f"{name} counters nothing"
        assert set(cls.counters) <= valid, f"{name} counters unknown vector"


def test_determinism():
    a = Game(GameConfig(max_ticks=15, seed=42))
    a.run()
    b = Game(GameConfig(max_ticks=15, seed=42))
    b.run()
    assert (a.scoreboard.red, a.scoreboard.blue) == (b.scoreboard.red, b.scoreboard.blue)
    assert a.winner == b.winner


def test_prevention_beats_detection_value():
    # The scoring rule: prevention (20) must be worth more than detection (10).
    sb = Scoreboard()
    sb.award_detection("DDoS", "IDS")
    sb.award_prevention("DDoS", "Firewall")
    # 10 for detection + 20 for prevention.
    assert sb.blue == 30


def test_tls_prevents_mitm_often():
    # With a strong, MITM-countering defense, prevention should dominate over
    # many trials (sanity check that defenses actually reduce attacker success).
    rng = random.Random(1)
    prevented = 0
    trials = 400
    for _ in range(trials):
        net = default_network()
        host = net.host("gw-01")
        host.defenses.append(get_defense("TLS Encryption")())
        sb = Scoreboard()
        res = resolve_attack(
            Action(team="red", vector_name="MITM", target_hostname="gw-01"),
            host, sb, rng,
        )
        if res.prevented:
            prevented += 1
    # TLS prevent_chance is 0.8 -> expect well over half prevented.
    assert prevented / trials > 0.6


def test_game_always_terminates():
    g = Game(GameConfig(max_ticks=10, seed=3))
    g.run()
    assert g.finished
    assert g.winner in {"Red", "Blue", "Tie"}
    assert g.tick <= 10


def _main():
    fns = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _main()
