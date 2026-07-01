"""The virtual network the game is played on.

Everything here is simulated. There is no real scanning, no real traffic, and
no real exploitation. A Host is a bag of state that the resolver reads and
mutates. This keeps the whole simulation safe, deterministic (given a seed),
and reproducible for a demo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Service categories an attack can target. Each attack vector declares which
# categories it can hit (see vectors.py).
CATEGORIES = ["web", "database", "network", "user", "auth"]


@dataclass
class Service:
    """A logical service running on a host (web app, DB, mail, etc.)."""

    name: str
    category: str          # one of CATEGORIES
    patched: bool = False  # patching closes some vulnerabilities


@dataclass
class Host:
    """A single machine in the virtual network."""

    hostname: str
    services: list[Service] = field(default_factory=list)
    compromised: bool = False
    privilege: str = "none"      # none -> user -> admin
    online: bool = True          # DDoS can knock a host offline
    defenses: list = field(default_factory=list)  # active Defense instances

    def has_category(self, category: str) -> bool:
        return any(s.category == category for s in self.services)

    def categories(self) -> set[str]:
        return {s.category for s in self.services}

    def defense_names(self) -> set[str]:
        return {d.name for d in self.defenses}


@dataclass
class Network:
    """The whole environment: a collection of hosts."""

    hosts: list[Host] = field(default_factory=list)

    def host(self, hostname: str) -> Host | None:
        for h in self.hosts:
            if h.hostname == hostname:
                return h
        return None

    def online_hosts(self) -> list[Host]:
        return [h for h in self.hosts if h.online]

    def compromised_count(self) -> int:
        return sum(1 for h in self.hosts if h.compromised)

    def compromise_ratio(self) -> float:
        if not self.hosts:
            return 0.0
        return self.compromised_count() / len(self.hosts)


def default_network() -> Network:
    """A small, demo-friendly network with a spread of service categories."""
    return Network(
        hosts=[
            Host("web-01", [Service("nginx", "web"), Service("login", "auth")]),
            Host("web-02", [Service("shop", "web"), Service("session", "user")]),
            Host("db-01", [Service("postgres", "database")]),
            Host("mail-01", [Service("smtp", "network"), Service("inbox", "user")]),
            Host("gw-01", [Service("router", "network"), Service("vpn", "auth")]),
        ]
    )
