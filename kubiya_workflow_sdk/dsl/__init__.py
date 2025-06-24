"""
Kubiya Workflow DSL - Simple, intuitive workflow creation.

A comprehensive DSL that supports all Kubiya workflow features with clean,
chainable API and proper separation of concerns.
"""

from .workflow import Workflow, workflow, chain, graph
from .step import Step, step, parallel_step, conditional_step
from .executors import (
    python_executor,
    shell_executor,
    docker_executor,
    http_executor,
    ssh_executor,
    inline_agent_executor,
)
from .data import Output, Param, EnvVar, Secret
from .control_flow import when, retry_policy, repeat_policy, continue_on, precondition
from .lifecycle import HandlerOn, MailOn, Notifications
from .queue import Queue, QueueConfig
from .scheduling import Schedule
from .examples import examples
from .executors import tool_executor, kubiya_executor, jq_executor

__all__ = [
    # Workflow builders
    "Workflow",
    "workflow",
    "chain",
    "graph",
    # Step builders
    "Step",
    "step",
    "parallel_step",
    "conditional_step",
    # Executors
    "python_executor",
    "shell_executor",
    "docker_executor",
    "http_executor",
    "ssh_executor",
    "inline_agent_executor",
    "tool_executor",
    "kubiya_executor",
    "jq_executor",
    # Data handling
    "Output",
    "Param",
    "EnvVar",
    "Secret",
    # Control flow
    "when",
    "retry_policy",
    "repeat_policy",
    "continue_on",
    "precondition",
    # Lifecycle
    "HandlerOn",
    "MailOn",
    "Notifications",
    # Queue management
    "Queue",
    "QueueConfig",
    # Scheduling
    "Schedule",
    # Examples
    "examples",
]
