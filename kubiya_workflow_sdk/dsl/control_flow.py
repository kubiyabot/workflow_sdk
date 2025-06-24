"""Control flow utilities for workflows."""

from typing import Dict, Any, List, Optional


def when(condition: str, expected: str) -> Dict[str, str]:
    """Create a condition."""
    return {"condition": condition, "expected": expected}


def retry_policy(
    limit: int = 3, interval_sec: int = 30, exit_codes: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Create retry policy."""
    policy = {"limit": limit, "intervalSec": interval_sec}
    if exit_codes:
        policy["exitCodes"] = exit_codes
    return policy


def repeat_policy(
    interval_sec: int = 60, repeat: bool = True, limit: Optional[int] = None
) -> Dict[str, Any]:
    """Create repeat policy."""
    policy = {"intervalSec": interval_sec}
    if repeat:
        policy["repeat"] = True
    if limit:
        policy["limit"] = limit
    return policy


def continue_on(failure: bool = True) -> Dict[str, bool]:
    """Create continue-on policy."""
    return {"failure": failure}


def precondition(condition: str, expected: str) -> Dict[str, str]:
    """Create a precondition."""
    return {"condition": condition, "expected": expected}
