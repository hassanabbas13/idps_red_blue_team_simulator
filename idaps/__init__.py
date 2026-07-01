"""IDAPS - Intrusion Detection And Prevention Simulator.

A gamified Red Team vs Blue Team simulator. Everything here runs against a
*virtual* network model - there is no real scanning, exploitation, or network
traffic. Attacks are probabilistic models resolved against the defensive
posture of simulated hosts.
"""

__version__ = "0.1.0"

# Importing these modules runs their @register_* decorators, populating the
# registries. Without this, all_attacks()/all_defenses() would be empty.
from . import vectors as vectors  # noqa: E402,F401
from . import defenses as defenses  # noqa: E402,F401
