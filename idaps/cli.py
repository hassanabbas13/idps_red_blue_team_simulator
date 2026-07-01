"""Terminal runner for IDAPS - watch a bot-vs-bot match play out live.

Usage:
    python -m idaps.cli                 # default 20-tick match
    python -m idaps.cli --ticks 30 --seed 7 --delay 0.3

This is the Phase 2 deliverable: it proves the engine end-to-end with a
readable, colorful play-by-play and a final scoreboard. The web dashboard in
later phases consumes the same TickEvent stream this prints.
"""

from __future__ import annotations

import argparse
import time

from .game import Game, GameConfig
from .registry import all_attacks, all_defenses


# Minimal ANSI colors (work in most terminals; --no-color disables them).
class C:
    RED = "\033[91m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _c(text: str, color: str, enabled: bool) -> str:
    return f"{color}{text}{C.RESET}" if enabled else text


def _render_attack(result, color: bool) -> str:
    if result is None:
        return _c("Red made no move", C.DIM, color)
    if result.prevented:
        tag = _c("PREVENTED", C.BLUE, color)
    elif result.success and result.detected:
        tag = _c("SUCCESS", C.RED, color) + "/" + _c("detected", C.YELLOW, color)
    elif result.success:
        tag = _c("SUCCESS", C.RED, color) + "/" + _c("stealth", C.GREEN, color)
    elif result.detected:
        tag = _c("failed", C.DIM, color) + "/" + _c("detected", C.YELLOW, color)
    else:
        tag = _c("failed", C.DIM, color)
    return f"{result.vector_name} -> {result.target_hostname}  [{tag}]"


def run(ticks: int, seed: int | None, delay: float, color: bool):
    game = Game(GameConfig(max_ticks=ticks, seed=seed))

    print(_c("=" * 60, C.DIM, color))
    print(_c(" IDAPS - Red Team vs Blue Team Simulator", C.BOLD, color))
    print(_c("=" * 60, C.DIM, color))
    print(f" Vectors: {', '.join(all_attacks().keys())}")
    print(f" Defenses: {len(all_defenses())} available")
    print(f" Network: {len(game.network.hosts)} hosts | seed={seed} | ticks={ticks}")
    print(_c("-" * 60, C.DIM, color))

    while not game.finished:
        event = game.step()
        blue_line = ""
        if event.defense_deployed:
            blue_line = _c(
                f"Blue deployed {event.defense_deployed} on {event.defense_host}",
                C.BLUE, color,
            )
        else:
            blue_line = _c("Blue held position", C.DIM, color)

        red_line = _render_attack(event.attack, color)

        score = (
            _c(f"R {event.red_total}", C.RED, color)
            + " | "
            + _c(f"B {event.blue_total}", C.BLUE, color)
        )
        print(f"[{event.tick:02d}] {blue_line}")
        print(f"     {red_line}")
        print(f"     score: {score}")
        if event.notes:
            print(_c(f"     ({'; '.join(event.notes)})", C.DIM, color))
        if delay:
            time.sleep(delay)

    print(_c("-" * 60, C.DIM, color))
    win = game.winner
    win_color = C.RED if win == "Red" else C.BLUE if win == "Blue" else C.YELLOW
    print(_c(f" WINNER: {win}", C.BOLD + win_color, color))
    print(
        f" Final score - "
        + _c(f"Red {game.scoreboard.red}", C.RED, color)
        + " vs "
        + _c(f"Blue {game.scoreboard.blue}", C.BLUE, color)
    )
    print(f" Hosts compromised: {game.network.compromised_count()}/{len(game.network.hosts)}")
    print(_c("=" * 60, C.DIM, color))


def main():
    parser = argparse.ArgumentParser(description="IDAPS terminal simulator")
    parser.add_argument("--ticks", type=int, default=20, help="number of ticks")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (reproducible)")
    parser.add_argument("--delay", type=float, default=0.25, help="seconds between ticks")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    args = parser.parse_args()
    run(ticks=args.ticks, seed=args.seed, delay=args.delay, color=not args.no_color)


if __name__ == "__main__":
    main()
