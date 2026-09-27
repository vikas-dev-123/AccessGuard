from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.checks.base import Finding, ReviewContext

CheckFunction = Callable[[ReviewContext], list[Finding]]


@dataclass(frozen=True)
class CheckDefinition:
    code: str
    name: str
    criteria: str
    impact: str
    recommendation: str
    run: CheckFunction


_REGISTRY: dict[str, CheckDefinition] = {}


def register_check(*, code: str, name: str, criteria: str, impact: str, recommendation: str):
    """Register a check function. criteria/impact/recommendation feed the audit report."""

    def decorator(func: CheckFunction) -> CheckFunction:
        if code in _REGISTRY:
            raise ValueError(f"Check '{code}' is already registered")
        _REGISTRY[code] = CheckDefinition(code, name, criteria, impact, recommendation, func)
        return func

    return decorator


def get_checks() -> list[CheckDefinition]:
    return list(_REGISTRY.values())


def get_check(code: str) -> CheckDefinition:
    return _REGISTRY[code]
