"""Data handling utilities for workflows."""

from typing import Optional, Any


class Output:
    """Output variable definition."""

    def __init__(self, name: str, json_path: Optional[str] = None):
        self.name = name
        self.json_path = json_path


class Param:
    """Parameter definition with default value."""

    def __init__(self, name: str, default: Any = None, description: str = ""):
        self.name = name
        self.default = default
        self.description = description


class EnvVar:
    """Environment variable definition."""

    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value


class Secret:
    """Secret reference."""

    def __init__(self, name: str):
        self.name = name
