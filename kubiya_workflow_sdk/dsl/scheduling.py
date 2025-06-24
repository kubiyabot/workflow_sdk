"""Scheduling utilities for workflows."""

from typing import Optional


class Schedule:
    """Schedule configuration with cron expressions."""

    def __init__(self, cron: str, skip_if_successful: bool = False):
        self.cron = cron
        self.skip_if_successful = skip_if_successful

    @staticmethod
    def daily(hour: int = 0, minute: int = 0) -> str:
        """Daily schedule helper."""
        return f"{minute} {hour} * * *"

    @staticmethod
    def hourly(minute: int = 0) -> str:
        """Hourly schedule helper."""
        return f"{minute} * * * *"

    @staticmethod
    def every_n_minutes(n: int) -> str:
        """Run every N minutes."""
        return f"*/{n} * * * *"
