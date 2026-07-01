"""The defense library (Blue Team).

Each defense declares which attack vectors it counters (by name) and how it
counters them: 'prevent' (stops the attack outright), 'detect' (raises an
alert but doesn't stop it), or both. The resolver reads these to decide
outcomes and scoring.

To add a new defense: define a class, decorate with @register_defense.
"""

from __future__ import annotations

from .base import Defense
from .registry import register_defense


@register_defense
class Firewall(Defense):
    name = "Firewall"
    counters = ["DDoS", "MITM"]
    prevent_chance = 0.5
    detect_chance = 0.4
    cost = 2
    description = "Blocks unwanted traffic at the network edge."


@register_defense
class RateLimiting(Defense):
    name = "Rate Limiting"
    counters = ["DDoS", "Brute Force"]
    prevent_chance = 0.6
    detect_chance = 0.5
    cost = 1
    description = "Throttles repeated requests from the same source."


@register_defense
class MFA(Defense):
    name = "MFA"
    counters = ["Brute Force", "Phishing"]
    prevent_chance = 0.75
    detect_chance = 0.2
    cost = 2
    description = "Requires a second factor, defeating stolen-password attacks."


@register_defense
class AccountLockout(Defense):
    name = "Account Lockout"
    counters = ["Brute Force"]
    prevent_chance = 0.65
    detect_chance = 0.6
    cost = 1
    description = "Locks an account after too many failed logins."


@register_defense
class WAF(Defense):
    name = "WAF"
    counters = ["SQL Injection", "XSS"]
    prevent_chance = 0.6
    detect_chance = 0.6
    cost = 2
    description = "Web application firewall filtering malicious HTTP payloads."


@register_defense
class InputValidation(Defense):
    name = "Input Validation"
    counters = ["SQL Injection", "XSS"]
    prevent_chance = 0.7
    detect_chance = 0.3
    cost = 2
    description = "Sanitizes user input before it reaches code or the database."


@register_defense
class Patching(Defense):
    name = "Patching"
    counters = ["SQL Injection"]
    prevent_chance = 0.5
    detect_chance = 0.1
    cost = 1
    description = "Closes known vulnerabilities in software."


@register_defense
class CSP(Defense):
    name = "CSP"
    counters = ["XSS"]
    prevent_chance = 0.65
    detect_chance = 0.2
    cost = 1
    description = "Content Security Policy restricting what scripts a page runs."


@register_defense
class EmailFilter(Defense):
    name = "Email Filter"
    counters = ["Phishing"]
    prevent_chance = 0.55
    detect_chance = 0.6
    cost = 1
    description = "Quarantines suspicious emails before users see them."


@register_defense
class UserTraining(Defense):
    name = "User Training"
    counters = ["Phishing"]
    prevent_chance = 0.5
    detect_chance = 0.4
    cost = 1
    description = "Teaches users to recognize and report social engineering."


@register_defense
class TLSEncryption(Defense):
    name = "TLS Encryption"
    counters = ["MITM"]
    prevent_chance = 0.8
    detect_chance = 0.1
    cost = 2
    description = "Encrypts traffic so intercepted data is useless."


@register_defense
class NetworkSegmentation(Defense):
    name = "Network Segmentation"
    counters = ["MITM", "DDoS"]
    prevent_chance = 0.45
    detect_chance = 0.3
    cost = 2
    description = "Isolates hosts so a breach can't spread or sniff freely."


@register_defense
class IDS(Defense):
    name = "IDS"
    # IDS watches everything: detection-only, no prevention.
    counters = ["DDoS", "Brute Force", "SQL Injection", "Phishing", "MITM", "XSS"]
    prevent_chance = 0.0
    detect_chance = 0.45
    cost = 3
    description = "Intrusion Detection System - alerts on any suspicious activity."
