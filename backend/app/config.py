from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOD_RULES_PATH = BACKEND_DIR / "config" / "sod_rules.json"

DEFAULT_GENERIC_USERNAME_PATTERNS: tuple[str, ...] = (
    r"^(admin|administrator|root|sa|backup_admin)\d*$",
    r"^(test|testuser|tester)\d*$",
    r"^(temp|tmp|temp_user)\d*$",
    r"^shared",
    r"^(teller|cashier|operator|user)\d+$",
    r"^(training|demo|guest)\d*$",
)


def load_sod_rules(path: str | Path = DEFAULT_SOD_RULES_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        raise ValueError(f"SoD rules file {path} must contain a top-level 'rules' list")

    for rule in rules:
        roles = rule.get("conflicting_roles")
        valid = (
            rule.get("rule_id")
            and isinstance(roles, list)
            and len(roles) >= 2
            and all(isinstance(r, dict) and r.get("system") and r.get("role") for r in roles)
        )
        if not valid:
            raise ValueError(
                f"Invalid SoD rule {rule!r}: needs a rule_id and at least two "
                "conflicting_roles entries, each with 'system' and 'role'"
            )
    return rules


@dataclass
class ReviewConfig:
    as_of_date: date = field(default_factory=date.today)
    dormant_days: int = 90
    late_revocation_grace_days: int = 1
    privileged_roles: frozenset[str] = frozenset({"Admin", "DBA"})
    it_department: str = "IT"
    generic_username_patterns: tuple[str, ...] = DEFAULT_GENERIC_USERNAME_PATTERNS
    sod_rules: list[dict] = field(default_factory=load_sod_rules)
