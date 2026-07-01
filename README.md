# IDAPS — Intrusion Detection And Prevention Simulator

A gamified **Red Team vs Blue Team** cybersecurity simulator. The Red Team launches attacks; the Blue Team deploys defenses that **detect** and **prevent** them. A scoring engine tracks the duel and decides a winner.

> ⚠️ **Everything is simulated.** IDAPS runs entirely against a *virtual* network model — no real scanning, no real network traffic, and no real exploitation. Attacks are probabilistic models resolved against the defensive posture of fake hosts: safe, legal, and reproducible for a demo.

---

## Features

- **Core engine** — plugin registries, virtual network model, tick loop, resolver, and scoring
- **6 attack vectors** (Red) and **13 defenses** (Blue)
- **Bot-vs-bot auto-battle** in the terminal
- **Web dashboard** — FastAPI + WebSocket streaming a live match to the browser (network map, animated attacks, scoreboard, event feed)
- **Four game modes** — AI vs AI, Player (Red) vs AI, Player (Blue) vs AI, and Player vs Player
- **Deterministic** — every match is seeded, so a given seed always replays identically (great for demos and tests)

---

## Quick start

```bash
# Terminal version (no dependencies — pure standard library)
python -m idaps.cli --seed 7

# Web dashboard (visual demo)
python -m pip install -r requirements.txt
python -m idaps.server
# then open http://localhost:8000

# Tests
python tests/test_engine.py
```

The engine and terminal version need **no third-party packages**. `fastapi` and `uvicorn` are only required for the web dashboard.

---

## Attack vectors (Red Team)

| Vector | Category | Countered by | Severity |
|---|---|---|---|
| DDoS | Availability | Rate Limiting, Firewall, Segmentation | medium |
| Brute Force | Credential | MFA, Rate Limiting, Account Lockout | medium |
| SQL Injection | Web injection | WAF, Input Validation, Patching | high |
| Phishing | Social engineering | Email Filter, User Training | high |
| MITM | Network intercept | TLS Encryption, Segmentation | high |
| XSS | Web injection | WAF, Input Validation, CSP | medium |

## Scoring

```
Attack success  → +10 Red  (×1.5 for high-severity vectors)
Detection       → +10 Blue
Prevention      → +20 Blue
Stealth bonus   → +5  Red  (success with no detection)
Survival bonus  → +2  Blue (a tick with no new compromise)
```

## How the resolver decides an outcome

For each attack, against the target host's active defenses:

1. **Prevention** — a prevention-capable defense (e.g. WAF, TLS) may block it outright. Worth the most to Blue.
2. **Success** — if not prevented, roll the vector's base success, reduced by the defenses present.
3. **Detection** — IDS / monitoring may raise an alert, independently of whether the attack succeeded. Harder-to-detect vectors (MITM, phishing) evade detectors more often.

All randomness flows through a single seeded RNG, so outcomes are reproducible.

---

## Architecture

```
idaps/
  registry.py   plugin registries for attacks & defenses
  network.py    virtual network: hosts, services, categories
  base.py       AttackVector / Defense base classes, Action, AttackResult
  vectors.py    the six attack vectors (Red)
  defenses.py   the defense library (Blue)
  scoring.py    the scoring engine
  resolver.py   prevention / success / detection logic — the core
  bots.py       Red & Blue bot strategies
  game.py       the tick loop / match engine
  cli.py        terminal runner
  server.py     FastAPI + WebSocket layer (all four game modes)
  serialize.py  turns engine objects into JSON for the dashboard
  static/       browser dashboard (index.html, app.js, style.css)
tests/
  test_engine.py
```

The engine never asks *who* chose an action — it just consumes `Action` objects. Bots, a human via the web UI, or two humans in PvP all produce the same `Action`. That single seam is what lets every game mode reuse the exact same engine.

## Extending it

Adding a new attack vector needs no engine changes — just declare a class and register it:

```python
# in idaps/vectors.py
@register_attack
class PrivilegeEscalation(AttackVector):
    name = "Privilege Escalation"
    targets = ["user", "auth"]
    base_success = 0.5
    detection_difficulty = 0.5
    countered_by = ["Patching", "IDS"]
    points = 15
    severity = "high"
    description = "Climb from a user account to admin on a compromised host."
```

Defenses work the same way via `@register_defense` in `idaps/defenses.py`.

---

## Tech stack

Python 3 · FastAPI · WebSockets · vanilla-JS dashboard · zero-dependency core engine
