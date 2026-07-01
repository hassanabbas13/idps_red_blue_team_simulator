"""Plugin registries for attack vectors and defenses.

Adding a new attack or defense is just defining a class and decorating it with
@register_attack / @register_defense. The engine discovers everything through
these registries and never hardcodes a specific vector. This is what makes the
attack/defense library extensible.
"""

from __future__ import annotations

ATTACK_REGISTRY: dict[str, type] = {}
DEFENSE_REGISTRY: dict[str, type] = {}


def register_attack(cls):
    """Class decorator that registers an AttackVector by its `name`."""
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a `name`")
    if cls.name in ATTACK_REGISTRY:
        raise ValueError(f"Duplicate attack vector name: {cls.name}")
    ATTACK_REGISTRY[cls.name] = cls
    return cls


def register_defense(cls):
    """Class decorator that registers a Defense by its `name`."""
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a `name`")
    if cls.name in DEFENSE_REGISTRY:
        raise ValueError(f"Duplicate defense name: {cls.name}")
    DEFENSE_REGISTRY[cls.name] = cls
    return cls


def all_attacks() -> dict[str, type]:
    """Mapping of attack name -> AttackVector subclass."""
    return dict(ATTACK_REGISTRY)


def all_defenses() -> dict[str, type]:
    """Mapping of defense name -> Defense subclass."""
    return dict(DEFENSE_REGISTRY)


def get_attack(name: str) -> type:
    return ATTACK_REGISTRY[name]


def get_defense(name: str) -> type:
    return DEFENSE_REGISTRY[name]
