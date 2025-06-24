"""Tool templates for creating custom tools.

These templates provide patterns and base structures for creating tools
that handle common scenarios like authentication, environment setup,
and integration patterns.
"""

from .base import (
    ToolTemplate,
    DockerToolTemplate,
    AuthenticatedToolTemplate,
    CLIToolTemplate,
    DataProcessingToolTemplate,
)

__all__ = [
    "ToolTemplate",
    "DockerToolTemplate",
    "AuthenticatedToolTemplate",
    "CLIToolTemplate",
    "DataProcessingToolTemplate",
]
