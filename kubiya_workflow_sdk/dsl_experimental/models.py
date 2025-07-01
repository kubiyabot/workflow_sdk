from typing import Any

from pydantic import BaseModel, field_serializer, RootModel


class BasicStep(BaseModel):
    name: str
    description: str
    depends: list[str] | None = None
    output: str | None = None


class FileDefinition(BaseModel):
    destination: str
    content: str


class ArgDefinition(BaseModel):
    name: str
    type: str
    required: bool = False


class ToolDef(BaseModel):
    name: str
    description: str = ''
    type: str
    image: str
    content: str
    with_files: list[FileDefinition] | None = None
    args: list[ArgDefinition] | None = None
    secrets: list[str] | None = None


class ToolExecutorConfig(BaseModel):
    tool_def: ToolDef
    args: dict[str, Any] | None = None
    secrets: dict[str, Any] | None = None


class ToolExecutor(BaseModel):
    type: str
    config: ToolExecutorConfig


class ToolStep(BasicStep):
    executor: ToolExecutor


class CommandStep(BasicStep):
    command: str


class KubiyaExecutorConfig(BaseModel):
    url: str
    method: str


class KubiyaExecutor(BaseModel):
    type: str = 'kubiya'
    config: KubiyaExecutorConfig


class KubiyaStep(BasicStep):
    executor: KubiyaExecutor


class AgentExecutorConfig(BaseModel):
    agent_name: str
    message: str


class AgentExecutor(BaseModel):
    type: str = 'agent'
    config: AgentExecutorConfig


class AgentStep(BasicStep):
    executor: AgentExecutor


class Steps(RootModel[list[BasicStep]]):
    """Implements custom dump for list of Steps."""

    def model_dump(self, *args, **kwargs) -> Any:
        return [r.model_dump() for r in self.root]


class Workflow(BaseModel):
    name: str
    description: str
    steps: Steps
    params: dict[str, Any] | None = None
    secrets: list[dict[str, Any]] | None = None

    @field_serializer('steps')
    def dump_steps(self, v):
        return v.model_dump()
