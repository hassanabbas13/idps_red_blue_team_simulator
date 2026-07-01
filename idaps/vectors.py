"""The attack vector library (Red Team).

Six vectors covering distinct categories: availability (DDoS), credential
(brute force), web injection (SQLi, XSS), social engineering (phishing), and
network interception (MITM).

To add a new vector: define a class, set its metadata, decorate with
@register_attack. The engine picks it up automatically - nothing else changes.
"""

from __future__ import annotations

from .base import AttackVector
from .registry import register_attack


@register_attack
class DDoS(AttackVector):
    name = "DDoS"
    targets = ["web", "network"]
    base_success = 0.55
    detection_difficulty = 0.2     # loud and easy to detect
    countered_by = ["Rate Limiting", "Firewall"]
    points = 10
    severity = "medium"
    description = "Flood a host with traffic to knock its services offline."


@register_attack
class BruteForce(AttackVector):
    name = "Brute Force"
    targets = ["auth", "user"]
    base_success = 0.5
    detection_difficulty = 0.35
    countered_by = ["MFA", "Rate Limiting", "Account Lockout"]
    points = 10
    severity = "medium"
    description = "Repeatedly guess credentials to gain access to an account."


@register_attack
class SQLInjection(AttackVector):
    name = "SQL Injection"
    targets = ["web", "database"]
    base_success = 0.6
    detection_difficulty = 0.5
    countered_by = ["WAF", "Input Validation", "Patching"]
    points = 15
    severity = "high"
    description = "Inject malicious SQL to read or alter a backend database."


@register_attack
class Phishing(AttackVector):
    name = "Phishing"
    targets = ["user", "auth"]
    base_success = 0.65
    detection_difficulty = 0.6     # hard to catch technically
    countered_by = ["Email Filter", "User Training"]
    points = 15
    severity = "high"
    description = "Trick a user into handing over credentials or running a payload."


@register_attack
class MITM(AttackVector):
    name = "MITM"
    targets = ["network", "auth"]
    base_success = 0.5
    detection_difficulty = 0.7     # quiet, hard to detect
    countered_by = ["TLS Encryption", "Network Segmentation"]
    points = 15
    severity = "high"
    description = "Intercept traffic between hosts to steal or alter data."


@register_attack
class XSS(AttackVector):
    name = "XSS"
    targets = ["web", "user"]
    base_success = 0.55
    detection_difficulty = 0.45
    countered_by = ["WAF", "Input Validation", "CSP"]
    points = 10
    severity = "medium"
    description = "Inject malicious script into a web page served to other users."
