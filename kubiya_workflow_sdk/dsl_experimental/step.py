from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from .executors import Executor, SignalType
from .control_flow import Precondition, RetryPolicy, RepeatPolicy, ContinueOn, ParallelConfig


# Step definitions
class BaseStep(BaseModel):
    """Base step model with common fields"""

    name: str
    description: Optional[str] = None
    depends: Optional[Union[str, List[str]]] = None
    id: Optional[str] = None  # Short identifier for referencing
    dir: Optional[str] = None  # Working directory
    output: Optional[str] = None  # Output variable name
    stdout: Optional[str] = None  # Redirect stdout to file
    stderr: Optional[str] = None  # Redirect stderr to file
    env: Optional[List[Union[str, Dict[str, str]]]] = None
    preconditions: Optional[List[Union[str, Precondition]]] = None
    retry_policy: Optional[RetryPolicy] = Field(None, alias="retryPolicy")
    repeat_policy: Optional[RepeatPolicy] = Field(None, alias="repeatPolicy")
    continue_on: Optional[ContinueOn] = Field(None, alias="continueOn")
    timeout_sec: Optional[int] = Field(None, alias="timeoutSec")
    signal_on_stop: SignalType = Field(SignalType.SIGTERM, alias="signalOnStop")
    mail_on_error: bool = Field(False, alias="mailOnError")

    model_config = ConfigDict(populate_by_name=True)


class CommandStep(BaseStep):
    """Step that executes a command"""

    command: str
    shell: Optional[str] = None


class ScriptStep(BaseStep):
    """Step that executes a script"""

    script: str
    shell: Optional[str] = None


class ExecutorStep(BaseStep):
    """Step that uses a specific executor"""

    executor: Executor
    command: Optional[str] = None
    script: Optional[str] = None


class DAGStep(BaseStep):
    """Step that runs another DAG/workflow"""

    run: str  # Path to the DAG file or DAG name
    params: Optional[str] = None


class ParallelStep(BaseStep):
    """Step that executes in parallel"""

    parallel: Union[List[str], ParallelConfig]
    run: Optional[str] = None  # Sub-workflow to run for each item
    command: Optional[str] = None
    script: Optional[str] = None
    executor: Optional[Executor] = None


# Union type for all step types
Step = Union[CommandStep, ScriptStep, ExecutorStep, DAGStep, ParallelStep]
