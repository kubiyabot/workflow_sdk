"""Queue management for workflows."""

from typing import Optional


class Queue:
    """Queue configuration."""

    def __init__(self, name: str, max_active_runs: Optional[int] = None):
        self.name = name
        self.max_active_runs = max_active_runs


class QueueConfig:
    """Global queue configuration."""

    def __init__(self, name: str, max_concurrency: int):
        self.name = name
        self.max_concurrency = max_concurrency
