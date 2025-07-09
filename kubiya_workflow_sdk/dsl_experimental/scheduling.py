from enum import Enum


class WorkflowType(str, Enum):
    """Defines how the workflow steps are executed"""

    CHAIN = "chain"  # Sequential execution
    GRAPH = "graph"  # DAG-based execution with dependencies
